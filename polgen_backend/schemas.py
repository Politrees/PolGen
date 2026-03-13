from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ConvertBase(BaseModel):
    rvc_model: str = Field(...)

    f0_method: str = "rmvpe"
    f0_min: int = Field(default=50, ge=1, le=120)
    f0_max: int = Field(default=1100, ge=380, le=16000)

    rvc_pitch: int = Field(default=0, ge=-24, le=24)
    protect: float = Field(default=0.5, ge=0.0, le=0.5)
    index_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    volume_envelope: float = Field(default=1.0, ge=0.0, le=1.0)

    autopitch: bool = False
    autopitch_threshold: float = 155.0

    autotune: bool = False
    autotune_tonic: str = "C"
    autotune_scale: str = "chromatic"
    autotune_strength: float = Field(default=1.0, ge=0.0, le=1.0)

    audio_upscaling: bool = False
    stereo_sound: bool = False
    output_format: Literal["wav", "flac", "mp3", "ogg", "m4a"] = "mp3"


class ConvertFileRequest(ConvertBase):
    input_path: str = Field(...)


class TtsConvertRequest(ConvertBase):
    tts_voice: str
    tts_text: str = Field(..., min_length=1)
    tts_rate: int = Field(default=0, ge=-100, le=100)
    tts_volume: int = Field(default=0, ge=-100, le=100)
    tts_pitch: int = Field(default=0, ge=-100, le=100)


class ModelInstallUrlRequest(BaseModel):
    url: str
    model_name: str


class JobStartedResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "done", "error"]
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    message: str = ""
    result: dict | None = None
    error: str | None = None


class EdgeVoicesResponse(BaseModel):
    voices: dict[str, list[str]]