from __future__ import annotations

import os
import shutil
import uuid
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
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
    TtsConvertRequest,
)

RVC_MODELS_DIR = os.path.join(os.getcwd(), "models", "RVC_models")
TMP_DIR = os.path.join(os.getcwd(), "output", "_tmp_uploads")

os.makedirs(RVC_MODELS_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

jobs = JobManager()
app = FastAPI(title="PolGen Backend", version="0.3.0")

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
        raise HTTPException(status_code=400, detail="rvc_model пустой")
    if not os.path.exists(req.input_path):
        raise HTTPException(status_code=400, detail=f"Файл не найден: {req.input_path}")

    job = jobs.create_job()
    payload = req.model_dump()
    payload["mode"] = "convert"
    jobs.run_worker_job(job, payload)
    return {"job_id": job.job_id}


@app.post("/jobs/tts_convert", response_model=JobStartedResponse)
def start_tts_convert(req: TtsConvertRequest):
    if not req.rvc_model:
        raise HTTPException(status_code=400, detail="rvc_model пустой")
    if not req.tts_voice:
        raise HTTPException(status_code=400, detail="tts_voice пустой")
    if not req.tts_text:
        raise HTTPException(status_code=400, detail="tts_text пустой")

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


@app.post("/jobs/models/install_zip", response_model=JobStartedResponse)
async def install_model_zip(zip_file: UploadFile = File(...), model_name: str = Form(...)):
    job = jobs.create_job()

    job_tmp = os.path.join(TMP_DIR, job.job_id)
    os.makedirs(job_tmp, exist_ok=True)

    dst = os.path.join(job_tmp, zip_file.filename or "model.zip")
    with open(dst, "wb") as f:
        f.write(await zip_file.read())

    payload = {"mode": "install_rvc_zip", "zip_path": dst, "model_name": model_name}
    jobs.run_worker_job(job, payload)
    return {"job_id": job.job_id}


@app.post("/jobs/models/install_files", response_model=JobStartedResponse)
async def install_model_files(
    pth_file: UploadFile = File(...),
    index_file: UploadFile | None = File(None),
    model_name: str = Form(...),
):
    job = jobs.create_job()

    job_tmp = os.path.join(TMP_DIR, job.job_id)
    os.makedirs(job_tmp, exist_ok=True)

    pth_dst = os.path.join(job_tmp, pth_file.filename or "model.pth")
    with open(pth_dst, "wb") as f:
        f.write(await pth_file.read())

    idx_dst = None
    if index_file is not None:
        idx_dst = os.path.join(job_tmp, index_file.filename or "model.index")
        with open(idx_dst, "wb") as f:
            f.write(await index_file.read())

    payload = {"mode": "install_rvc_files", "pth_path": pth_dst, "index_path": idx_dst, "model_name": model_name}
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