"""
Job management system for tracking long-running tasks
"""
import uuid
from enum import Enum
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from collections import deque
import threading


class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressUpdate:
    type: str  # "progress", "warning", "info", "complete", "error"
    step_number: Optional[int] = None
    total_steps: Optional[int] = None
    step_name: Optional[str] = None
    current: Optional[int] = None
    total: Optional[int] = None
    percentage: Optional[int] = None
    message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    # ETA fields
    elapsed_seconds: Optional[float] = None
    eta_seconds: Optional[float] = None
    pages_per_second: Optional[float] = None
    step_eta_seconds: Optional[float] = None
    estimated_completion_time: Optional[str] = None  # ISO format


@dataclass
class Job:
    job_id: str
    status: JobStatus
    created_at: datetime
    output_path: Optional[str] = None
    error: Optional[str] = None
    process_pid: Optional[int] = None  # Process ID for cancellation
    progress_history: List[ProgressUpdate] = field(default_factory=list)
    _progress_queue: deque = field(default_factory=deque, repr=False)

    def add_progress(self, update: ProgressUpdate):
        """Add a progress update to both history and queue"""
        self.progress_history.append(update)
        self._progress_queue.append(update)

    def get_pending_updates(self) -> List[ProgressUpdate]:
        """Get and clear pending updates"""
        updates = list(self._progress_queue)
        self._progress_queue.clear()
        return updates


class JobManager:
    """
    Thread-safe manager for background jobs and their progress.
    Supports concurrent access from multiple threads (e.g., thread pool executors).
    """

    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()  # Thread safety lock

    def create_job(self) -> str:
        """Create a new job and return its ID (thread-safe)"""
        job_id = str(uuid.uuid4())
        job = Job(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=datetime.now()
        )
        with self._lock:
            self.jobs[job_id] = job
        return job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID (thread-safe)"""
        with self._lock:
            return self.jobs.get(job_id)

    def update_job_status(self, job_id: str, status: JobStatus):
        """Update job status (thread-safe)"""
        with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].status = status

    def add_progress(self, job_id: str, update: ProgressUpdate):
        """Add a progress update to a job (thread-safe)"""
        with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].add_progress(update)

    def complete_job(self, job_id: str, output_path: str):
        """Mark job as completed (thread-safe)"""
        with self._lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.status = JobStatus.COMPLETED
                job.output_path = output_path
                # Add completion event
                job.add_progress(ProgressUpdate(
                    type="complete",
                    message="PDF processing completed successfully",
                    percentage=100
                ))

    def fail_job(self, job_id: str, error: str):
        """Mark job as failed (thread-safe)"""
        with self._lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.status = JobStatus.FAILED
                job.error = error
                # Add error event
                job.add_progress(ProgressUpdate(
                    type="error",
                    message=error
                ))

    def cancel_job(self, job_id: str) -> bool:
        """Mark job as cancelled (thread-safe)"""
        with self._lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                # Can only cancel pending or processing jobs
                if job.status in [JobStatus.PENDING, JobStatus.PROCESSING]:
                    job.status = JobStatus.CANCELLED
                    # Add cancellation event
                    job.add_progress(ProgressUpdate(
                        type="cancelled",
                        message="Job cancelled by user"
                    ))
                    return True
        return False

    def set_process_pid(self, job_id: str, pid: int):
        """Set the process PID for a job (thread-safe)"""
        with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].process_pid = pid

    def is_job_cancelled(self, job_id: str) -> bool:
        """Check if a job has been cancelled (thread-safe)"""
        with self._lock:
            if job_id in self.jobs:
                return self.jobs[job_id].status == JobStatus.CANCELLED
        return False

    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Remove jobs older than max_age_hours (thread-safe)"""
        now = datetime.now()
        to_remove = []

        with self._lock:
            for job_id, job in self.jobs.items():
                age_hours = (now - job.created_at).total_seconds() / 3600
                if age_hours > max_age_hours:
                    to_remove.append(job_id)

            for job_id in to_remove:
                del self.jobs[job_id]


# Global job manager instance
job_manager = JobManager()