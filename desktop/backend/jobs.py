from __future__ import annotations

import asyncio
import gc
import json
import queue
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Job:
    job_id: str
    status: str = "queued"  # queued|running|done|error
    progress: float = 0.0
    message: str = ""
    result: dict | None = None
    error: str | None = None

    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    _subscribers: list[queue.Queue] = field(default_factory=list, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def snapshot(self) -> dict:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "progress": float(self.progress),
            "message": self.message,
            "result": self.result,
            "error": self.error,
        }

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=400)
        with self._lock:
            self._subscribers.append(q)
        self.publish({"type": "snapshot", **self.snapshot()})
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            self._subscribers = [x for x in self._subscribers if x is not q]

    def publish(self, event: dict) -> None:
        event = {**event, "ts": time.time()}
        payload = json.dumps(event, ensure_ascii=False)
        with self._lock:
            subs = list(self._subscribers)
        for sub in subs:
            try:
                sub.put_nowait(payload)
            except queue.Full:
                pass

    def update_progress(self, progress: float, message: str) -> None:
        self.progress = max(0.0, min(1.0, float(progress)))
        self.message = message
        self.updated_at = time.time()
        self.publish({"type": "progress", "progress": self.progress, "message": self.message})

    def set_status(self, status: str, message: str = "") -> None:
        self.status = status
        if message:
            self.message = message
        self.updated_at = time.time()
        self.publish({"type": "status", "status": self.status, "message": self.message})


class JobManager:
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

        self._queue: queue.Queue[tuple[Job, dict]] = queue.Queue()
        self._worker_thread = threading.Thread(target=self._loop, daemon=True)
        self._worker_thread.start()

    def create_job(self) -> Job:
        job_id = uuid.uuid4().hex
        job = Job(job_id=job_id)
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def run_worker_job(self, job: Job, payload: dict) -> None:
        self._queue.put((job, payload))

    def _loop(self) -> None:
        while True:
            job, payload = self._queue.get()
            try:
                self._run_one(job, payload)
            except BaseException as e:
                job.error = str(e)
                job.progress = 0.0
                job.message = "Ошибка"
                job.publish({"type": "error", "error": job.error})
                job.set_status("error", "Ошибка")
            finally:
                gc.collect()
                self._queue.task_done()

    def _run_one(self, job: Job, payload: dict) -> None:
        job.set_status("running", "Запуск...")
        job.update_progress(0.01, "Старт...")

        try:
            from desktop.backend.worker import run_job

            run_job(job, payload)
        except Exception as e:
            tb = traceback.format_exc()
            job.error = f"{e}\n\n{tb}"
            job.publish({"type": "error", "error": job.error})
            job.set_status("error", "Ошибка")
            return

        if job.error:
            job.progress = 0.0
            job.message = "Ошибка"
            job.set_status("error", "Ошибка")
            return

        # Публикуем result ПЕРЕД статусом done —
        # чтобы SSE-клиент получил output_path до завершения
        if job.result:
            job.publish({"type": "result", "result": job.result})

        job.update_progress(1.0, "Готово.")
        job.set_status("done", "Готово.")


async def sse_event_generator(job: Job):
    q = job.subscribe()
    try:
        while True:
            payload = await asyncio.to_thread(q.get)
            yield f"data: {payload}\n\n"
    finally:
        job.unsubscribe(q)