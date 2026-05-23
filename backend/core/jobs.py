import asyncio
import uuid
import time
from dataclasses import dataclass, field
from typing import Literal, Optional

JobStatus = Literal["queued", "running", "done", "failed", "cancelled"]


@dataclass
class Job:
    id: str
    module: str
    label: str
    status: JobStatus = "queued"
    progress: float = 0.0
    message: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    result: Optional[dict] = None
    error: Optional[str] = None
    _subscribers: list = field(default_factory=list, repr=False)

    def update(
        self,
        status: Optional[JobStatus] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
    ) -> None:
        if status:
            self.status = status
        if progress is not None:
            self.progress = progress
        if message:
            self.message = message
        self.updated_at = time.time()
        payload = dict(status=self.status, progress=self.progress, message=self.message)
        for q in self._subscribers:
            q.put_nowait(payload)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass


_jobs: dict[str, Job] = {}


def create_job(module: str, label: str) -> Job:
    job = Job(id=str(uuid.uuid4()), module=module, label=label)
    _jobs[job.id] = job
    return job


def get_job(job_id: str) -> Optional[Job]:
    return _jobs.get(job_id)


def list_jobs(module: Optional[str] = None) -> list[Job]:
    jobs = list(_jobs.values())
    if module:
        jobs = [j for j in jobs if j.module == module]
    return jobs
