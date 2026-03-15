from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


# ═══════════════════════════════════════════════════════════════
# RVC
# ═══════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════
# Model management
# ═══════════════════════════════════════════════════════════════


class ModelInstallUrlRequest(BaseModel):
    url: str
    model_name: str


class ModelInstallLocalRequest(BaseModel):
    path: str
    extra_path: Optional[str] = None
    model_name: str


# ═══════════════════════════════════════════════════════════════
# UVR
# ═══════════════════════════════════════════════════════════════


class UvrSeparateRequest(BaseModel):
    """Универсальная схема для сепарации аудио.

    Поле `arch` определяет архитектуру модели и какие параметры используются:
    - roformer, mdx23c: segment_size, override_segment_size, overlap, pitch_shift, batch_size
    - mdx: hop_length, segment_size, overlap, denoise, batch_size
    - vr: window_size, aggression, enable_tta, enable_post_process, post_process_threshold, high_end_process, batch_size
    - demucs: segment_size, shifts, overlap, segments_enabled
    """
    # Обязательные
    audio_path: str
    arch: str  # roformer | mdx23c | mdx | vr | demucs
    model_key: str

    # Директории
    model_dir: str = "models/UVR_models"
    output_dir: str = "output/UVR_output"
    output_format: str = "wav"
    rename_template: str = "NAME_(STEM)_MODEL"

    # Общие параметры
    norm_threshold: float = 0.9
    amp_threshold: float = 0.0
    batch_size: int = 1

    # Roformer / MDX23C
    segment_size: int = 256
    override_segment_size: bool = False
    overlap: float = 8  # int для roformer/mdx23c, float для mdx/demucs
    pitch_shift: int = 0

    # MDX-NET
    hop_length: int = 1024
    denoise: bool = False

    # VR ARCH
    window_size: int = 512
    aggression: int = 5
    enable_tta: bool = False
    enable_post_process: bool = False
    post_process_threshold: float = 0.2
    high_end_process: bool = False

    # Demucs
    shifts: int = 2
    segments_enabled: bool = True


class UvrModelsResponse(BaseModel):
    models: dict[str, list[str]]


class UvrClearModelsRequest(BaseModel):
    model_dir: str


# ═══════════════════════════════════════════════════════════════
# Job responses
# ═══════════════════════════════════════════════════════════════


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