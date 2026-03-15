from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from desktop.backend.jobs import Job


class _JobProgressAdapter:
    """Адаптер: преобразует Job.update_progress() в интерфейс progress(percent, desc=...).

    Совместим с:
    - gr.Progress (Gradio): progress(percent, desc="...")
    - _notify_progress (model_manager): progress(value, desc=message) / progress(value, message)
    - _call_progress (download_source): progress(value, desc=message) / progress(value, message)
    """

    def __init__(self, job: Job) -> None:
        self._job = job

    def __call__(self, percent: float, desc: str = "", **kwargs: Any) -> None:
        self._job.update_progress(float(percent), str(desc))


def run_job(job: Job, payload: dict) -> None:
    """Выполняет задачу в текущем потоке. Вызывается из JobManager._run_one().

    Модели кешируются в памяти между вызовами (см. rvc/infer/infer.py ModelCache).
    Результат записывается в job.result, ошибки — в job.error.
    """
    mode = payload.get("mode")
    progress = _JobProgressAdapter(job)

    # Проверяем наличие базовых моделей (idempotent — пропускает если файлы уже есть)
    from assets.model_installer import check_and_install_models

    check_and_install_models()

    if mode == "convert":
        _handle_convert(job, payload, progress)
        return

    if mode == "tts_convert":
        _handle_tts_convert(job, payload, progress)
        return

    if mode == "install_rvc_url":
        _handle_install_url(job, payload, progress)
        return

    if mode == "install_rvc_zip":
        _handle_install_zip(job, payload, progress)
        return

    if mode == "install_rvc_files":
        _handle_install_files(job, payload, progress)
        return

    raise ValueError(f"Неизвестный mode: {mode!r}")


# ═══════════════════════════════════════════════════════════════
# Обработчики задач
# ═══════════════════════════════════════════════════════════════


def _handle_convert(job: Job, payload: dict, progress: _JobProgressAdapter) -> None:
    from rvc.infer.infer import rvc_infer

    out_path = rvc_infer(
        rvc_model=payload["rvc_model"],
        input_path=payload["input_path"],
        f0_method=payload.get("f0_method", "rmvpe"),
        f0_min=payload.get("f0_min", 50),
        f0_max=payload.get("f0_max", 1100),
        rvc_pitch=payload.get("rvc_pitch", 0),
        protect=payload.get("protect", 0.5),
        index_rate=payload.get("index_rate", 0.0),
        volume_envelope=payload.get("volume_envelope", 1.0),
        autopitch=payload.get("autopitch", False),
        autopitch_threshold=payload.get("autopitch_threshold", 155.0),
        autotune=payload.get("autotune", False),
        autotune_tonic=payload.get("autotune_tonic", "C"),
        autotune_scale=payload.get("autotune_scale", "chromatic"),
        autotune_strength=payload.get("autotune_strength", 1.0),
        audio_upscaling=payload.get("audio_upscaling", False),
        stereo_sound=payload.get("stereo_sound", False),
        output_format=payload.get("output_format", "mp3"),
        progress=progress,
    )
    job.result = {"output_path": out_path}


def _handle_tts_convert(job: Job, payload: dict, progress: _JobProgressAdapter) -> None:
    from rvc.infer.infer import rvc_edgetts_infer

    tts_path, out_path = rvc_edgetts_infer(
        rvc_model=payload["rvc_model"],
        f0_method=payload.get("f0_method", "rmvpe"),
        f0_min=payload.get("f0_min", 50),
        f0_max=payload.get("f0_max", 1100),
        rvc_pitch=payload.get("rvc_pitch", 0),
        protect=payload.get("protect", 0.5),
        index_rate=payload.get("index_rate", 0.0),
        volume_envelope=payload.get("volume_envelope", 1.0),
        autopitch=payload.get("autopitch", False),
        autopitch_threshold=payload.get("autopitch_threshold", 155.0),
        autotune=payload.get("autotune", False),
        autotune_tonic=payload.get("autotune_tonic", "C"),
        autotune_scale=payload.get("autotune_scale", "chromatic"),
        autotune_strength=payload.get("autotune_strength", 1.0),
        stereo_sound=payload.get("stereo_sound", False),
        output_format=payload.get("output_format", "mp3"),
        tts_voice=payload["tts_voice"],
        tts_text=payload["tts_text"],
        tts_rate=payload.get("tts_rate", 0),
        tts_volume=payload.get("tts_volume", 0),
        tts_pitch=payload.get("tts_pitch", 0),
        audio_upscaling=payload.get("audio_upscaling", False),
        progress=progress,
    )
    job.result = {"tts_path": tts_path, "output_path": out_path}


def _handle_install_url(job: Job, payload: dict, progress: _JobProgressAdapter) -> None:
    from rvc.modules.model_manager import install_from_url

    result = install_from_url(payload["url"], payload["model_name"], progress=progress)
    job.result = {"message": result}


def _handle_install_zip(job: Job, payload: dict, progress: _JobProgressAdapter) -> None:
    from rvc.modules.model_manager import install_from_zip_path

    result = install_from_zip_path(payload["zip_path"], payload["model_name"], progress=progress)
    job.result = {"message": result}


def _handle_install_files(job: Job, payload: dict, progress: _JobProgressAdapter) -> None:
    from rvc.modules.model_manager import install_from_files_path

    result = install_from_files_path(
        payload["pth_path"],
        payload.get("index_path"),
        payload["model_name"],
        progress=progress,
    )
    job.result = {"message": result}