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

    if mode == "uvr_separate":
        _handle_uvr_separate(job, payload, progress)
        return

    raise ValueError(f"Неизвестный mode: {mode!r}")


# ═══════════════════════════════════════════════════════════════
# RVC handlers
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


# ═══════════════════════════════════════════════════════════════
# Model install handlers
# ═══════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════
# UVR handler
# ═══════════════════════════════════════════════════════════════


def _handle_uvr_separate(job: Job, payload: dict, progress: _JobProgressAdapter) -> None:
    arch = payload["arch"]

    from rvc.modules.uvr_core import (
        separate_roformer,
        separate_mdx23c,
        separate_mdx,
        separate_vr,
        separate_demucs,
    )

    common = {
        "audio_path": payload["audio_path"],
        "model_key": payload["model_key"],
        "model_dir": payload.get("model_dir", "models/UVR_models"),
        "output_dir": payload.get("output_dir", "output/UVR_output"),
        "output_format": payload.get("output_format", "wav"),
        "norm_threshold": payload.get("norm_threshold", 0.9),
        "amp_threshold": payload.get("amp_threshold", 0.0),
        "rename_template": payload.get("rename_template", "NAME_(STEM)_MODEL"),
        "progress": progress,
    }

    if arch == "roformer":
        out_dir, results = separate_roformer(
            **common,
            segment_size=payload.get("segment_size", 256),
            override_segment_size=payload.get("override_segment_size", False),
            overlap=payload.get("overlap", 8),
            pitch_shift=payload.get("pitch_shift", 0),
            batch_size=payload.get("batch_size", 1),
        )
    elif arch == "mdx23c":
        out_dir, results = separate_mdx23c(
            **common,
            segment_size=payload.get("segment_size", 256),
            override_segment_size=payload.get("override_segment_size", False),
            overlap=payload.get("overlap", 8),
            pitch_shift=payload.get("pitch_shift", 0),
            batch_size=payload.get("batch_size", 1),
        )
    elif arch == "mdx":
        out_dir, results = separate_mdx(
            **common,
            hop_length=payload.get("hop_length", 1024),
            segment_size=payload.get("segment_size", 256),
            overlap=payload.get("overlap", 0.25),
            denoise=payload.get("denoise", False),
            batch_size=payload.get("batch_size", 1),
        )
    elif arch == "vr":
        out_dir, results = separate_vr(
            **common,
            window_size=payload.get("window_size", 512),
            aggression=payload.get("aggression", 5),
            enable_tta=payload.get("enable_tta", False),
            enable_post_process=payload.get("enable_post_process", False),
            post_process_threshold=payload.get("post_process_threshold", 0.2),
            high_end_process=payload.get("high_end_process", False),
            batch_size=payload.get("batch_size", 1),
        )
    elif arch == "demucs":
        out_dir, results = separate_demucs(
            **common,
            segment_size=payload.get("segment_size", 40),
            shifts=payload.get("shifts", 2),
            overlap=payload.get("overlap", 0.25),
            segments_enabled=payload.get("segments_enabled", True),
        )
    else:
        raise ValueError(f"Неизвестная архитектура UVR: {arch!r}")

    # Формируем полные пути к стемам
    stem_paths = [os.path.join(out_dir, f) for f in results]

    job.result = {
        "output_dir": out_dir,
        "stems": stem_paths,
        "stem_names": results,
    }