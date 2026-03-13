from __future__ import annotations

import asyncio
import json
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


WORKER_TIMEOUT_S = int(os.environ.get("POLGEN_WORKER_TIMEOUT_S", "3600"))  # 1 hour default


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


def _kill_process_tree(proc: subprocess.Popen) -> None:
    """Гарантированно убивает процесс (и детей на Windows)."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            proc.kill()
    except Exception:
        pass


class JobManager:
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

        # строго по одной задаче
        self._queue: "queue.Queue[tuple[Job, dict]]" = queue.Queue()
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
                self._queue.task_done()

    def _run_one(self, job: Job, payload: dict) -> None:
        job.set_status("running", "Запуск worker...")
        job.update_progress(0.01, "Старт...")

        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        # ВАЖНО: worker должен стартовать из корня проекта (os.getcwd() путями пользуются)
        proc = subprocess.Popen(
            [sys.executable, "-m", "polgen_backend.worker"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=os.getcwd(),
            env=env,
            bufsize=1,
        )

        assert proc.stdin is not None
        assert proc.stdout is not None

        proc.stdin.write(json.dumps(payload, ensure_ascii=False))
        proc.stdin.close()

        lines_q: "queue.Queue[str]" = queue.Queue()

        def reader_thread():
            try:
                for line in proc.stdout:  # type: ignore[assignment]
                    lines_q.put(line.rstrip("\n"))
            except Exception:
                pass
            finally:
                lines_q.put("__POLGEN__EOF__")

        t = threading.Thread(target=reader_thread, daemon=True)
        t.start()

        started = time.monotonic()
        got_result = False
        got_error = False

        # Основной цикл: читаем события и следим за timeout
        while True:
            # timeout check
            if (time.monotonic() - started) > WORKER_TIMEOUT_S:
                _kill_process_tree(proc)
                job.error = f"Worker timeout: {WORKER_TIMEOUT_S}s"
                job.progress = 0.0
                job.message = "Ошибка"
                job.publish({"type": "error", "error": job.error})
                job.set_status("error", "Ошибка")
                return

            try:
                line = lines_q.get(timeout=0.2)
            except queue.Empty:
                # процесс мог завершиться без новых строк
                if proc.poll() is not None:
                    break
                continue

            if line == "__POLGEN__EOF__":
                break

            if not line:
                continue

            if line.startswith("POLGEN_EVENT "):
                try:
                    ev = json.loads(line.removeprefix("POLGEN_EVENT ").strip())
                except Exception:
                    job.publish({"type": "log", "line": line})
                    continue

                tp = ev.get("type")

                if tp == "progress":
                    job.update_progress(float(ev.get("progress", 0.0)), str(ev.get("message", "")))
                    continue

                if tp == "result":
                    job.result = ev.get("result") or {}
                    got_result = True
                    continue

                if tp == "error":
                    job.error = str(ev.get("error", "Unknown error"))
                    got_error = True
                    job.publish({"type": "error", "error": job.error})
                    continue

                job.publish({"type": "log", "line": line})
                continue

            job.publish({"type": "log", "line": line})

        # Дожидаемся завершения процесса
        try:
            rc = proc.wait(timeout=5)
        except Exception:
            _kill_process_tree(proc)
            rc = -1

        if got_result and not got_error and rc == 0:
            job.update_progress(1.0, "Готово.")
            job.set_status("done", "Готово.")
            return

        if got_error:
            job.progress = 0.0
            job.message = "Ошибка"
            job.set_status("error", "Ошибка")
            return

        job.error = f"Worker завершился с кодом {rc} без result/error события."
        job.progress = 0.0
        job.message = "Ошибка"
        job.publish({"type": "error", "error": job.error})
        job.set_status("error", "Ошибка")


async def sse_event_generator(job: Job):
    q = job.subscribe()
    try:
        while True:
            payload = await asyncio.to_thread(q.get)
            yield f"data: {payload}\n\n"
    finally:
        job.unsubscribe(q)