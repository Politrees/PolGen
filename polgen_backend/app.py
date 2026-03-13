from __future__ import annotations

import os
import shutil
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from polgen_backend.edge_voices import edge_voices
from polgen_backend.jobs import JobManager, sse_event_generator
from polgen_backend.model_install import delete_rvc_model
from polgen_backend.schemas import (
    ConvertFileRequest,
    EdgeVoicesResponse,
    JobStartedResponse,
    JobStatusResponse,
    ModelInstallUrlRequest,
    ModelInstallLocalRequest,
    TtsConvertRequest,
)

RVC_MODELS_DIR = os.path.join(os.getcwd(), "models", "RVC_models")

os.makedirs(RVC_MODELS_DIR, exist_ok=True)

jobs = JobManager()
app = FastAPI(title="PolGen Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["tauri://localhost"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True}

@app.get("/voices/edge", response_model=EdgeVoicesResponse)
def list_edge_voices():
    return {"voices": edge_voices}

@app.get("/models/rvc")
def list_rvc_models() -> dict[str, list[str]]:
    if not os.path.isdir(RVC_MODELS_DIR):
        return {"models": []}
    models = sorted([d for d in os.listdir(RVC_MODELS_DIR) if os.path.isdir(os.path.join(RVC_MODELS_DIR, d))])
    return {"models": models}

@app.delete("/models/rvc/{model_name}")
def delete_model(model_name: str) -> dict[str, str]:
    delete_rvc_model(model_name)
    return {"message": "deleted"}

@app.post("/jobs/convert", response_model=JobStartedResponse)
def start_convert(req: ConvertFileRequest):
    if not req.rvc_model:
        raise HTTPException(status_code=400, detail="rvc_model is empty")
    
    job = jobs.create_job()
    payload = req.model_dump()
    payload["mode"] = "convert"
    jobs.run_worker_job(job, payload)
    return {"job_id": job.job_id}

@app.post("/jobs/tts_convert", response_model=JobStartedResponse)
def start_tts_convert(req: TtsConvertRequest):
    job = jobs.create_job()
    payload = req.model_dump()
    payload["mode"] = "tts_convert"
    jobs.run_worker_job(job, payload)
    return {"job_id": job.job_id}

@app.post("/jobs/models/install_url", response_model=JobStartedResponse)
def install_model_url(req: ModelInstallUrlRequest):
    job = jobs.create_job()
    payload = req.model_dump()
    payload["mode"] = "install_rvc_url"
    jobs.run_worker_job(job, payload)
    return {"job_id": job.job_id}

@app.post("/jobs/models/install_local_zip", response_model=JobStartedResponse)
def install_model_zip(req: ModelInstallLocalRequest):
    job = jobs.create_job()
    payload = req.model_dump()
    payload["mode"] = "install_rvc_zip"
    payload["zip_path"] = req.path
    jobs.run_worker_job(job, payload)
    return {"job_id": job.job_id}

@app.post("/jobs/models/install_local_files", response_model=JobStartedResponse)
def install_model_files(req: ModelInstallLocalRequest):
    job = jobs.create_job()
    payload = req.model_dump()
    payload["mode"] = "install_rvc_files"
    # Для этого режима передается pth через path, index через extra_path
    payload["pth_path"] = req.path
    payload["index_path"] = req.extra_path
    jobs.run_worker_job(job, payload)
    return {"job_id": job.job_id}

@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
def job_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job.snapshot()

@app.get("/jobs/{job_id}/events")
async def job_events(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return StreamingResponse(
        sse_event_generator(job),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )