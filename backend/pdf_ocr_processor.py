"""
Simple PDF OCR processor with clear progress reporting
Uses pty to capture OCRmyPDF terminal output
"""
import subprocess
import re
import sys
import pty
import os
import select
from typing import Optional, Callable
from pathlib import Path


def get_available_cores():
    """
    Get the number of available CPU cores, respecting Docker container limits.
    Returns half the available cores to be conservative.
    """
    try:
        # First, try to detect Docker CPU limits from cgroups (cgroup v1 and v2)
        # Docker limits are in /sys/fs/cgroup/cpu/cpu.cfs_quota_us and cpu.cfs_period_us
        # or in /sys/fs/cgroup/cpu.max for cgroup v2

        # Try cgroup v2 first (newer)
        try:
            with open('/sys/fs/cgroup/cpu.max', 'r') as f:
                content = f.read().strip()
                if content != 'max':
                    quota, period = content.split()
                    if quota != 'max':
                        docker_cpus = int(quota) / int(period)
                        cores = max(1, int(docker_cpus / 2))  # Use half, minimum 1
                        print(f"[CPU Detection] Docker cgroup v2 limit: {docker_cpus:.1f} cores, using {cores}")
                        return cores
        except (FileNotFoundError, ValueError, PermissionError):
            pass

        # Try cgroup v1
        try:
            with open('/sys/fs/cgroup/cpu/cpu.cfs_quota_us', 'r') as f:
                quota = int(f.read().strip())
            with open('/sys/fs/cgroup/cpu/cpu.cfs_period_us', 'r') as f:
                period = int(f.read().strip())

            if quota > 0 and period > 0:
                docker_cpus = quota / period
                cores = max(1, int(docker_cpus / 2))  # Use half, minimum 1
                print(f"[CPU Detection] Docker cgroup v1 limit: {docker_cpus:.1f} cores, using {cores}")
                return cores
        except (FileNotFoundError, ValueError, PermissionError):
            pass

        # Not in Docker or no CPU limit set - use host CPU count
        import multiprocessing
        total_cpus = multiprocessing.cpu_count()
        cores = max(1, total_cpus // 2)  # Use half, minimum 1
        print(f"[CPU Detection] Host CPUs: {total_cpus}, using {cores}")
        return cores

    except Exception as e:
        print(f"[CPU Detection] Error detecting CPUs: {e}, defaulting to 2")
        return 2  # Safe default


def process_pdf_ocr(
    job_id: str,
    input_file: str,
    output_file: str,
    language: str = 'hin',
    start_page: Optional[int] = None,
    end_page: Optional[int] = None,
    progress_callback: Optional[Callable] = None,
    cancellation_check: Optional[Callable] = None
):
    """
    Process PDF with OCR and print clear progress updates.

    Args:
        job_id: Unique identifier for this job
        input_file: Path to input PDF file
        output_file: Path to output searchable PDF file
        language: OCR language code (hin, guj, eng, etc.)
        start_page: Starting page number (1-indexed, optional)
        end_page: Ending page number (1-indexed, optional)
        progress_callback: Optional callback function(step_num, step_name, current, total, percentage)
        cancellation_check: Optional callback function() -> bool to check if job is cancelled

    Returns:
        True if successful, False otherwise
    """

    print(f"\n{'='*60}")
    print(f"[Job {job_id}] PDF OCR Processing Started")
    print(f"[Job {job_id}] Input: {input_file}")
    print(f"[Job {job_id}] Output: {output_file}")
    print(f"[Job {job_id}] Language: {language}")
    if start_page and end_page:
        print(f"[Job {job_id}] Page Range: {start_page}-{end_page}")
    print(f"{'='*60}\n")

    # Detect available CPU cores (Docker-aware)
    num_jobs = get_available_cores()

    # Build OCRmyPDF command with parallel processing
    cmd = [
        'ocrmypdf',
        '--language', language,
        '--jobs', str(num_jobs),  # Parallel processing for speed
        '--deskew',
        '--force-ocr',
        '--optimize', '1',
    ]

    print(f"[Job {job_id}] Using {num_jobs} parallel workers for OCR processing")

    if start_page and end_page:
        cmd.extend(['--pages', f'{start_page}-{end_page}'])

    cmd.extend([input_file, output_file])

    print(f"[Job {job_id}] Running command: {' '.join(cmd)}\n")

    # Map step names to step numbers (technical names from OCRmyPDF)
    step_map = {
        "Scanning contents": 1,
        "OCR": 2,
        "PDF/A conversion": 3,
        "Linearizing": 4,
        "Recompressing JPEGs": 5,
        "Deflating JPEGs": 6,
        "JBIG2": 7,
    }

    # Map technical names to user-friendly display names
    display_name_map = {
        "Scanning contents": "Reading your PDF",
        "OCR": "Recognizing text",
        "PDF/A conversion": "Creating searchable PDF",
        "Linearizing": "Optimizing file",
        "Recompressing JPEGs": "Compressing images",
        "Deflating JPEGs": "Optimizing images",
        "JBIG2": "Finalizing document",
    }

    current_step_name = None

    try:
        # Use pty to make OCRmyPDF think it's running in a terminal (so tqdm works)
        master, slave = pty.openpty()

        process = subprocess.Popen(
            cmd,
            stdout=slave,
            stderr=slave,
            close_fds=True
        )
        os.close(slave)

        # Store process PID via callback (if provided)
        if progress_callback:
            progress_callback(-1, "process_started", process.pid, 0, 0)

        # Pattern to strip ANSI escape codes (including cursor control)
        ansi_escape = re.compile(r'\x1b\[[0-9;?]*[a-zA-Z]|\x1b\]8;[^\x1b]*\x1b\\')

        # Pattern to match tqdm progress output (after ANSI stripping)
        # Must start with capital letter (to avoid matching partial lines)
        # Matches lines like: "OCR                   ━━━━╸━━━━━━  29%  69/236 0:01:03"
        progress_pattern = re.compile(r'^([A-Z][A-Za-z /]+?)\s+[━╸\s]*?\s*(\d+)%\s+(\d+)/(\d+)')

        output_buffer = ""

        while True:
            # Check if process is still running
            if process.poll() is not None:
                break

            # Check for cancellation request
            if cancellation_check and cancellation_check():
                print(f"[Job {job_id}] Cancellation requested, terminating process...")
                try:
                    # Try graceful termination first
                    process.terminate()
                    import time
                    time.sleep(2)

                    # Force kill if still running
                    if process.poll() is None:
                        print(f"[Job {job_id}] Process didn't terminate gracefully, forcing kill...")
                        process.kill()

                    # Wait for process to exit
                    process.wait(timeout=5)
                except Exception as e:
                    print(f"[Job {job_id}] Error killing process: {e}")

                # Clean up files
                try:
                    if os.path.exists(input_file):
                        os.remove(input_file)
                    if os.path.exists(output_file):
                        os.remove(output_file)
                except Exception as e:
                    print(f"[Job {job_id}] Error cleaning up files: {e}")

                os.close(master)
                print(f"[Job {job_id}] Job cancelled successfully")
                return False

            # Check if there's data to read (with timeout)
            try:
                ready, _, _ = select.select([master], [], [], 0.1)
                if not ready:
                    continue

                # Read available data
                try:
                    data = os.read(master, 1024).decode('utf-8', errors='ignore')
                    if not data:
                        break

                    output_buffer += data

                    # Process complete lines and carriage-return-terminated updates
                    lines = output_buffer.split('\n')
                    output_buffer = lines[-1]  # Keep incomplete line in buffer

                    for line in lines[:-1]:
                        # Split by carriage return to get the latest update
                        parts = line.split('\r')
                        for part in parts:
                            part = part.strip()
                            if not part:
                                continue

                            # Strip ANSI escape codes
                            clean_part = ansi_escape.sub('', part).strip()
                            if not clean_part:
                                continue

                            # Try to parse progress
                            match = progress_pattern.search(clean_part)
                            if match:
                                step_name = match.group(1).strip()
                                percentage = int(match.group(2))
                                current = int(match.group(3))
                                total = int(match.group(4))

                                step_num = step_map.get(step_name, 0)

                                # Get user-friendly display name
                                display_name = display_name_map.get(step_name, step_name)

                                # Always call the callback for every update (with friendly name)
                                if progress_callback:
                                    progress_callback(step_num, display_name, current, total, percentage)

                                # Print on step change or every 3% (for logging - use technical name)
                                if step_name != current_step_name or percentage % 3 == 0:
                                    print(f"[Job {job_id}] STEP {step_num}/7: {step_name} - {current}/{total} pages ({percentage}%)")
                                    current_step_name = step_name

                            # Print errors/warnings
                            elif 'error' in part.lower() or 'warning' in part.lower():
                                print(f"[Job {job_id}] {part}")

                except OSError:
                    break

            except OSError:
                break

        # Wait for process to complete
        return_code = process.wait()
        os.close(master)

        if return_code == 0:
            print(f"\n{'='*60}")
            print(f"[Job {job_id}] PDF OCR Processing COMPLETED SUCCESSFULLY!")
            print(f"[Job {job_id}] Output saved to: {output_file}")
            print(f"{'='*60}\n")
            return True
        else:
            print(f"[Job {job_id}] ERROR: OCR processing failed with return code {return_code}")
            return False

    except Exception as e:
        print(f"[Job {job_id}] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


# Test function
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python pdf_ocr_processor.py <input_pdf> <output_pdf> [language] [start_page] [end_page]")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2]
    language = sys.argv[3] if len(sys.argv) > 3 else 'hin'
    start_page = int(sys.argv[4]) if len(sys.argv) > 4 else None
    end_page = int(sys.argv[5]) if len(sys.argv) > 5 else None

    job_id = "test-job-001"

    def my_progress_callback(step_num, step_name, current, total, percentage):
        # Custom callback - you can send this to job_manager
        pass

    success = process_pdf_ocr(
        job_id=job_id,
        input_file=input_pdf,
        output_file=output_pdf,
        language=language,
        start_page=start_page,
        end_page=end_page,
        progress_callback=my_progress_callback
    )

    sys.exit(0 if success else 1)