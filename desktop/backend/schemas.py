from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ConvertBase(BaseModel):
    rvc_model: str
    f0_method: str = "rmvpe"
    f0_min: int = 50
    f0_max: int = 1100
    rvc_pitch: int = 0
    protect: float = 0.5
    index_rate: float = 0.0
    volume_envelope: float = 1.0
    autopitch: bool = False
    autopitch_threshold: float = 155.0
    autotune: bool = False
    autotune_tonic: str = "C"
    autotune_scale: str = "chromatic"
    autotune_strength: float = 1.0
    audio_upscaling: bool = False
    stereo_sound: bool = False
    output_format: str = "mp3"


class ConvertFileRequest(ConvertBase):
    input_path: str


class TtsConvertRequest(ConvertBase):
    tts_voice: str
    tts_text: str
    tts_rate: int = 0
    tts_volume: int = 0
    tts_pitch: int = 0


class ModelInstallUrlRequest(BaseModel):
    url: str
    model_name: str


class ModelInstallLocalRequest(BaseModel):
    path: str
    extra_path: Optional[str] = None
    model_name: str


class JobStartedResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    message: str
    result: Optional[dict] = None
    error: Optional[str] = None


class EdgeVoicesResponse(BaseModel):
    voices: dict[str, list[str]]