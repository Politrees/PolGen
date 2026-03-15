"""Gradio-обёртки над core-функциями.

Этот модуль — единственное место, где Gradio используется для взаимодействия
с core-логикой (rvc.infer, rvc.modules.model_manager).

Обёртки добавляют:
- gr.Progress(track_tqdm=True) — отслеживание tqdm в Gradio UI
- gr.Error — конвертация стандартных исключений в Gradio-ошибки
"""

import gradio as gr

from rvc.infer.infer import rvc_infer as _rvc_infer
from rvc.infer.infer import rvc_edgetts_infer as _rvc_edgetts_infer
from rvc.modules.model_manager import (
    install_from_url,
    install_from_zip_path,
    install_from_files_path,
)


# ═══════════════════════════════════════════════════════════════
# RVC инференс
# ═══════════════════════════════════════════════════════════════


def rvc_infer(
    rvc_model=None,
    input_path=None,
    f0_method="rmvpe",
    f0_min=50,
    f0_max=1100,
    rvc_pitch=0,
    protect=0.5,
    index_rate=0.25,
    volume_envelope=1.0,
    autopitch=False,
    autopitch_threshold=155.0,
    autotune=False,
    autotune_tonic="C",
    autotune_scale="chromatic",
    autotune_strength=1.0,
    audio_upscaling=False,
    stereo_sound=False,
    output_format="wav",
    progress=gr.Progress(track_tqdm=True),
):
    """Gradio-обёртка для rvc_infer: добавляет gr.Progress с отслеживанием tqdm."""
    return _rvc_infer(
        rvc_model=rvc_model,
        input_path=input_path,
        f0_method=f0_method,
        f0_min=f0_min,
        f0_max=f0_max,
        rvc_pitch=rvc_pitch,
        protect=protect,
        index_rate=index_rate,
        volume_envelope=volume_envelope,
        autopitch=autopitch,
        autopitch_threshold=autopitch_threshold,
        autotune=autotune,
        autotune_tonic=autotune_tonic,
        autotune_scale=autotune_scale,
        autotune_strength=autotune_strength,
        audio_upscaling=audio_upscaling,
        stereo_sound=stereo_sound,
        output_format=output_format,
        progress=progress,
    )


def rvc_edgetts_infer(
    # RVC
    rvc_model=None,
    f0_method="rmvpe",
    f0_min=50,
    f0_max=1100,
    rvc_pitch=0,
    protect=0.5,
    index_rate=0.25,
    volume_envelope=1.0,
    autopitch=False,
    autopitch_threshold=155.0,
    autotune=False,
    autotune_tonic="C",
    autotune_scale="chromatic",
    autotune_strength=1.0,
    stereo_sound=False,
    output_format="wav",
    # EdgeTTS
    tts_voice=None,
    tts_text=None,
    tts_rate=0,
    tts_volume=0,
    tts_pitch=0,
    # FlashSR
    audio_upscaling=False,
    progress=gr.Progress(track_tqdm=True),
):
    """Gradio-обёртка для rvc_edgetts_infer: добавляет gr.Progress с отслеживанием tqdm."""
    return _rvc_edgetts_infer(
        rvc_model=rvc_model,
        f0_method=f0_method,
        f0_min=f0_min,
        f0_max=f0_max,
        rvc_pitch=rvc_pitch,
        protect=protect,
        index_rate=index_rate,
        volume_envelope=volume_envelope,
        autopitch=autopitch,
        autopitch_threshold=autopitch_threshold,
        autotune=autotune,
        autotune_tonic=autotune_tonic,
        autotune_scale=autotune_scale,
        autotune_strength=autotune_strength,
        stereo_sound=stereo_sound,
        output_format=output_format,
        tts_voice=tts_voice,
        tts_text=tts_text,
        tts_rate=tts_rate,
        tts_volume=tts_volume,
        tts_pitch=tts_pitch,
        audio_upscaling=audio_upscaling,
        progress=progress,
    )


# ═══════════════════════════════════════════════════════════════
# Установка моделей (Gradio-обёртки)
# ═══════════════════════════════════════════════════════════════


def download_from_url(url, dir_name, progress=gr.Progress()):
    """Gradio-обёртка: скачивает модель по URL."""
    try:
        return install_from_url(url, dir_name, progress)
    except Exception as e:
        raise gr.Error(f"Ошибка при загрузке модели: {e!s}")


def upload_zip_file(zip_path, dir_name, progress=gr.Progress()):
    """Gradio-обёртка: устанавливает модель из загруженного ZIP."""
    try:
        zip_name = zip_path.name  # Gradio File object → строковый путь
        return install_from_zip_path(zip_name, dir_name, progress)
    except Exception as e:
        raise gr.Error(f"Ошибка при загрузке модели: {e!s}")


def upload_separate_files(pth_file, index_file, dir_name, progress=gr.Progress()):
    """Gradio-обёртка: устанавливает модель из отдельных файлов."""
    try:
        pth_path = pth_file.name if pth_file else None
        index_path = index_file.name if index_file else None
        return install_from_files_path(pth_path, index_path, dir_name, progress)
    except Exception as e:
        raise gr.Error(f"Ошибка при загрузке модели: {e!s}")