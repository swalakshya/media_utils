"""
FastAPI server for YouTube Utils - Media CLI functionalities
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import tempfile
import os
import shutil
from pathlib import Path
from typing import Optional
import asyncio
import json

# Import job management and OCR processor
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.job_manager import job_manager, JobStatus, ProgressUpdate
from backend.pdf_ocr_processor import process_pdf_ocr

app = FastAPI(
    title="Media Utils API",
    description="API for media utilities including PDF OCR, subtitle downloads, video processing, etc.",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # React default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create temp directory for uploads
UPLOAD_DIR = Path(tempfile.gettempdir()) / "media_utils_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Create output directory for processed files
OUTPUT_DIR = Path(tempfile.gettempdir()) / "media_utils_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


@app.get("/api")
@app.get("/api/")
async def root():
    """API health check endpoint"""
    return {
        "status": "ok",
        "message": "Media Utils API is running",
        "version": "1.0.0",
        "endpoints": {
            "pdf_ocr_async": "/api/pdf/ocr/async",
            "pdf_ocr_stream": "/api/pdf/ocr/stream/{job_id}",
            "pdf_ocr_cancel": "/api/pdf/ocr/cancel/{job_id}",
            "pdf_download": "/api/pdf/download/{job_id}",
        }
    }


async def process_pdf_with_progress(
    job_id: str,
    input_path: Path,
    output_path: Path,
    language: str,
    start_page: Optional[int] = None,
    end_page: Optional[int] = None
):
    """
    Background task to process PDF with OCRmyPDF and emit real-time progress updates via SSE.
    """
    # Set job to processing
    job_manager.update_job_status(job_id, JobStatus.PROCESSING)
    print(f"[Job {job_id}] Starting OCR processing")

    # Define progress callback to send updates to job_manager
    def progress_callback(step_num, step_name, current, total, percentage, eta_data=None):
        """Called by process_pdf_ocr with progress updates"""
        # Special handling for process_started signal (step_num = -1)
        if step_num == -1 and step_name == "process_started":
            # current contains the PID
            job_manager.set_process_pid(job_id, current)
            return

        # Create progress update with ETA data if available
        update = ProgressUpdate(
            type="progress",
            step_number=step_num,
            total_steps=7,
            step_name=step_name,
            current=current,
            total=total,
            percentage=percentage,
            message=f"{step_name}: {current}/{total} pages ({percentage}%)"
        )

        # Add ETA fields if provided
        if eta_data:
            update.elapsed_seconds = eta_data.get('elapsed_seconds')
            update.eta_seconds = eta_data.get('eta_seconds')
            update.pages_per_second = eta_data.get('pages_per_second')
            update.step_eta_seconds = eta_data.get('step_eta_seconds')
            update.estimated_completion_time = eta_data.get('estimated_completion_time')

        job_manager.add_progress(job_id, update)

    # Define cancellation check callback
    def cancellation_check():
        """Called by process_pdf_ocr to check if job should be cancelled"""
        return job_manager.is_job_cancelled(job_id)

    try:
        # Run OCR in thread executor (it's a blocking operation)
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None,
            process_pdf_ocr,
            job_id,
            str(input_path),
            str(output_path),
            language,
            start_page,
            end_page,
            progress_callback,
            cancellation_check
        )

        if success:
            # Success!
            print(f"[Job {job_id}] OCR completed successfully! Output: {output_path}")
            job_manager.complete_job(job_id, str(output_path))
        else:
            # Failed
            error_msg = "OCR processing failed"
            print(f"[Job {job_id}] {error_msg}")
            job_manager.fail_job(job_id, error_msg)

        # Clean up input file
        if input_path.exists():
            os.remove(input_path)

    except Exception as e:
        error_msg = f"OCR processing failed: {str(e)}"
        print(f"[Job {job_id}] Exception: {error_msg}")
        import traceback
        traceback.print_exc()
        job_manager.fail_job(job_id, error_msg)

        # Clean up on error
        if input_path.exists():
            try:
                os.remove(input_path)
            except:
                pass


@app.post("/api/pdf/ocr/async")
async def ocr_pdf_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form(default="hin"),
    start_page: Optional[int] = Form(default=None),
    end_page: Optional[int] = Form(default=None)
):
    """
    Start PDF OCR processing asynchronously and return a job ID.
    Use /api/pdf/ocr/stream/{job_id} to get progress updates.
    """

    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Validate page range if provided
    if (start_page is not None and end_page is not None):
        if start_page < 1 or end_page < 1 or start_page > end_page:
            raise HTTPException(
                status_code=400,
                detail="Invalid page range"
            )

    # Save uploaded file
    input_path = UPLOAD_DIR / file.filename
    try:
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")
    finally:
        file.file.close()

    # Generate output filename
    base_name = os.path.splitext(file.filename)[0]
    output_filename = f"{base_name}_searchable.pdf"
    output_path = OUTPUT_DIR / output_filename

    # Create a job
    job_id = job_manager.create_job()

    # Start background processing
    background_tasks.add_task(
        process_pdf_with_progress,
        job_id, input_path, output_path, language, start_page, end_page
    )

    return {
        "job_id": job_id,
        "status": "processing",
        "message": "PDF OCR processing started"
    }


@app.get("/api/pdf/ocr/stream/{job_id}")
async def stream_ocr_progress(job_id: str):
    """
    Server-Sent Events endpoint for streaming OCR progress updates
    """
    # Wait briefly for job to be created (handles race condition)
    max_retries = 3
    retry_delay = 0.1  # 100ms
    job = None

    for attempt in range(max_retries):
        job = job_manager.get_job(job_id)
        if job:
            break
        if attempt < max_retries - 1:
            print(f"[SSE {job_id}] Job not found yet, retrying... (attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(retry_delay)

    if not job:
        # Debug: List all jobs
        print(f"[SSE {job_id}] Job not found after {max_retries} attempts")
        print(f"[SSE] Active jobs: {list(job_manager.jobs.keys())}")
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        """Generate SSE events"""
        try:
            # Send initial status
            yield f"data: {json.dumps({'type': 'connected', 'job_id': job_id})}\n\n"

            # Send any progress history that was added before SSE connection
            # This handles the race condition where background task starts before SSE connects
            job = job_manager.get_job(job_id)
            if job and job.progress_history:
                print(f"[SSE {job_id}] Sending {len(job.progress_history)} historical progress updates")
                for update in job.progress_history:
                    event_data = {
                        "type": update.type,
                        "step_number": update.step_number,
                        "total_steps": update.total_steps,
                        "step_name": update.step_name,
                        "current": update.current,
                        "total": update.total,
                        "percentage": update.percentage,
                        "message": update.message,
                        # ETA fields
                        "elapsed_seconds": update.elapsed_seconds,
                        "eta_seconds": update.eta_seconds,
                        "pages_per_second": update.pages_per_second,
                        "step_eta_seconds": update.step_eta_seconds,
                        "estimated_completion_time": update.estimated_completion_time,
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"

            # Clear the pending queue since we sent the history
            job.get_pending_updates()

            # Stream progress updates
            while True:
                job = job_manager.get_job(job_id)
                if not job:
                    break

                # Get pending updates
                updates = job.get_pending_updates()
                if updates:
                    print(f"[SSE {job_id}] Sending {len(updates)} new progress updates")
                for update in updates:
                    event_data = {
                        "type": update.type,
                        "step_number": update.step_number,
                        "total_steps": update.total_steps,
                        "step_name": update.step_name,
                        "current": update.current,
                        "total": update.total,
                        "percentage": update.percentage,
                        "message": update.message,
                        # ETA fields
                        "elapsed_seconds": update.elapsed_seconds,
                        "eta_seconds": update.eta_seconds,
                        "pages_per_second": update.pages_per_second,
                        "step_eta_seconds": update.step_eta_seconds,
                        "estimated_completion_time": update.estimated_completion_time,
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"

                # Check if job is complete, failed, or cancelled
                if job.status == JobStatus.COMPLETED:
                    print(f"[SSE {job_id}] Job completed, sending completion event")
                    yield f"data: {json.dumps({'type': 'complete', 'download_url': f'/api/pdf/download/{job_id}'})}\n\n"
                    break
                elif job.status == JobStatus.FAILED:
                    print(f"[SSE {job_id}] Job failed: {job.error}")
                    yield f"data: {json.dumps({'type': 'error', 'message': job.error})}\n\n"
                    break
                elif job.status == JobStatus.CANCELLED:
                    print(f"[SSE {job_id}] Job cancelled")
                    yield f"data: {json.dumps({'type': 'cancelled', 'message': 'Job cancelled by user'})}\n\n"
                    break

                # Wait a bit before checking again
                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            # Client disconnected
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@app.post("/api/pdf/ocr/cancel/{job_id}")
async def cancel_ocr_job(job_id: str):
    """
    Cancel a running OCR job
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check if job is already completed
    if job.status == JobStatus.COMPLETED:
        return {
            "success": False,
            "message": "Job already completed",
            "status": job.status.value
        }

    # Check if job is already cancelled
    if job.status == JobStatus.CANCELLED:
        return {
            "success": True,
            "message": "Job already cancelled",
            "status": job.status.value
        }

    # Cancel the job
    success = job_manager.cancel_job(job_id)

    if success:
        return {
            "success": True,
            "message": "Job cancellation requested",
            "status": "cancelled"
        }
    else:
        return {
            "success": False,
            "message": "Failed to cancel job (may have already finished)",
            "status": job.status.value
        }


@app.get("/api/pdf/download/{job_id}")
async def download_pdf(job_id: str):
    """
    Download the processed PDF for a completed job
    """
    job = job_manager.get_job(job_id)
    if not job:
        print(f"[Download] Job {job_id} not found")
        raise HTTPException(status_code=404, detail="Job not found")

    print(f"[Download] Job {job_id} status: {job.status.value}, output_path: {job.output_path}")

    if job.status != JobStatus.COMPLETED:
        print(f"[Download] Job {job_id} not completed: {job.status.value}")
        raise HTTPException(status_code=400, detail=f"Job is not completed. Status: {job.status.value}")

    if not job.output_path:
        print(f"[Download] Job {job_id} has no output_path")
        raise HTTPException(status_code=404, detail="Output file path not set")

    if not os.path.exists(job.output_path):
        print(f"[Download] Job {job_id} output file does not exist at: {job.output_path}")
        # List files in OUTPUT_DIR for debugging
        print(f"[Download] Files in OUTPUT_DIR: {list(OUTPUT_DIR.iterdir())}")
        raise HTTPException(status_code=404, detail=f"Output file not found at: {job.output_path}")

    filename = os.path.basename(job.output_path)
    print(f"[Download] Sending file: {filename} from {job.output_path}")
    return FileResponse(
        path=job.output_path,
        media_type='application/pdf',
        filename=filename,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


# Mount static files (React frontend) - must be last
# This serves the built React app at the root path
frontend_build_dir = Path(__file__).parent.parent / "frontend" / "build"
if frontend_build_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_build_dir), html=True), name="frontend")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    # Clean up temporary files
    try:
        for file_path in UPLOAD_DIR.iterdir():
            if file_path.is_file():
                os.remove(file_path)
        for file_path in OUTPUT_DIR.iterdir():
            if file_path.is_file():
                os.remove(file_path)
    except Exception:
        pass


if __name__ == "__main__":
    import uvicorn
    # Use single worker to ensure in-memory job_manager is shared
    # reload=True already forces single worker, but we make it explicit
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1,  # Explicit single worker for in-memory job state
        log_level="info"
    )