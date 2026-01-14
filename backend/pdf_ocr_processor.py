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
import time
from typing import Optional, Callable
from pathlib import Path
from datetime import datetime


class ETACalculator:
    """
    Calculate estimated time to completion based on actual progress.
    Uses sliding window for recent speed and blends with overall speed.
    """

    def __init__(self, total_pages: int):
        self.total_pages = total_pages
        self.job_start_time = time.time()
        self.step_start_time = time.time()
        self.current_step = 0
        self.step_start_page = 0

        # Historical data for better estimates
        self.page_times = []  # List of (page_num, timestamp) tuples
        self.step_speeds = {}  # {step_num: pages_per_second}
        self.last_eta = None

        # Empirical step weights (based on observed 236-page PDF processing)
        self.step_weights = {
            1: 0.02,  # Reading: 2%
            2: 0.60,  # OCR: 60% (slowest)
            3: 0.10,  # Creating PDF: 10%
            4: 0.05,  # Optimizing: 5%
            5: 0.15,  # Compressing: 15%
            6: 0.08,  # Optimizing images: 8%
            7: 0.02   # Finalizing: 2%
        }

    def update(self, step_num: int, current_page: int, total_pages: int) -> dict:
        """
        Calculate ETA based on actual progress.
        Returns dict with eta_seconds, elapsed_seconds, pages_per_second, etc.
        """
        now = time.time()
        elapsed = now - self.job_start_time

        # Track step changes
        if step_num != self.current_step:
            if self.current_step > 0:
                # Record speed for completed step
                step_elapsed = now - self.step_start_time
                pages_in_step = current_page - self.step_start_page
                if pages_in_step > 0 and step_elapsed > 0:
                    self.step_speeds[self.current_step] = pages_in_step / step_elapsed

            self.current_step = step_num
            self.step_start_time = now
            self.step_start_page = current_page

        # Add current page timing first
        self.page_times.append((current_page, now))

        # Keep only last 50 page timings (sliding window)
        if len(self.page_times) > 50:
            self.page_times = self.page_times[-50:]

        # Don't calculate ETA until we have at least 10% progress AND minimum elapsed time
        # This prevents wildly inaccurate estimates at the start
        progress_percentage = (current_page / total_pages * 100) if total_pages > 0 else 0
        min_elapsed_time = 5  # Wait at least 5 seconds before showing ETA

        if progress_percentage < 10 or elapsed < min_elapsed_time or len(self.page_times) < 5:
            # Not enough data yet, return None for ETA fields
            return {
                'elapsed_seconds': round(elapsed, 1),
                'eta_seconds': None,
                'pages_per_second': None,
                'step_eta_seconds': None,
                'estimated_completion_time': None
            }

        # Calculate current speed (weighted recent + overall)
        # Use last 20 pages for recent speed
        recent_pages = self.page_times[-20:]
        if len(recent_pages) >= 2:
            recent_elapsed = recent_pages[-1][1] - recent_pages[0][1]
            # Protect against very small time intervals (< 0.5 seconds)
            if recent_elapsed < 0.5:
                recent_speed = 0
            else:
                recent_speed = len(recent_pages) / recent_elapsed
        else:
            recent_speed = current_page / elapsed if elapsed > 0 else 0

        # Overall speed
        overall_speed = current_page / elapsed if elapsed > 0 else 0

        # Weighted average: 70% recent, 30% overall (favor recent speed)
        pages_per_second = 0.7 * recent_speed + 0.3 * overall_speed

        # Sanity check: speed should be reasonable (< 10 pages/sec for OCR)
        if pages_per_second > 10:
            pages_per_second = overall_speed  # Fall back to overall speed if recent seems wrong

        # Calculate ETA for current step
        remaining_pages_in_step = total_pages - current_page
        if pages_per_second > 0:
            step_eta = remaining_pages_in_step / pages_per_second
        else:
            step_eta = None

        # Estimate remaining steps (using historical data if available)
        remaining_steps_time = 0
        for future_step in range(step_num + 1, 8):  # Steps 1-7
            if future_step in self.step_speeds:
                # Use historical speed from completed steps
                remaining_steps_time += total_pages / self.step_speeds[future_step]
            else:
                # Use fallback estimates based on step weights
                if pages_per_second > 0:
                    # Estimate total time based on current speed, then scale by weight
                    estimated_total_time = total_pages / pages_per_second
                    remaining_steps_time += estimated_total_time * self.step_weights.get(future_step, 0.1)

        # Total ETA
        eta_seconds = (step_eta if step_eta else 0) + remaining_steps_time

        # Cap maximum ETA growth to prevent sudden jumps (max 20% increase)
        if self.last_eta and eta_seconds > self.last_eta * 1.2:
            eta_seconds = self.last_eta * 1.2

        # Ensure minimum ETA when progress > 0
        if eta_seconds < 1 and current_page > 0 and current_page < total_pages:
            eta_seconds = 1

        self.last_eta = eta_seconds

        # Estimated completion time
        completion_time = datetime.fromtimestamp(now + eta_seconds)

        return {
            'elapsed_seconds': round(elapsed, 1),
            'eta_seconds': round(eta_seconds, 1),
            'pages_per_second': round(pages_per_second, 3),
            'step_eta_seconds': round(step_eta, 1) if step_eta else None,
            'estimated_completion_time': completion_time.isoformat() + 'Z'
        }


def get_available_cores():
    """
    Get the number of parallel OCR workers.
    Default to 2 workers for balanced performance and memory usage.
    """
    return 2


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

    # Get number of parallel workers
    num_jobs = get_available_cores()

    # Build OCRmyPDF command with parallel processing
    cmd = [
        'ocrmypdf',
        '--language', language,
        '--jobs', str(num_jobs),  # Parallel processing for speed
        '--deskew',
        '--force-ocr',
        '--optimize', '0',  # Disable optimization to avoid corrupted image issues during JPEG recompression
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
        eta_calculator = None  # Initialize on first progress update

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

                                # Initialize ETA calculator on first progress update
                                if eta_calculator is None:
                                    eta_calculator = ETACalculator(total)

                                # Calculate ETA
                                eta_data = eta_calculator.update(step_num, current, total)

                                # Always call the callback for every update (with friendly name and ETA data)
                                if progress_callback:
                                    progress_callback(step_num, display_name, current, total, percentage, eta_data)

                                # Print on step change or every 3% (for logging - use technical name)
                                if step_name != current_step_name or percentage % 3 == 0:
                                    print(f"[Job {job_id}] STEP {step_num}/7: {step_name} - {current}/{total} pages ({percentage}%) | ETA: {eta_data['eta_seconds']}s | Speed: {eta_data['pages_per_second']} p/s")
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