"""UVR core — чистые функции сепарации аудио (без Gradio зависимостей).

Используется из:
- gradio_ui/uvr.py (Gradio UI обёртки)
- desktop/backend/worker.py (Desktop backend)
- CLI (при необходимости)
"""

import gc
import logging
import os
import re
import shutil
import subprocess

import torch
from PolUVR.separator import Separator
from UVR_resources import (
    FORMATS,
    MDX23C_MODELS,
    MDXNET_MODELS,
    ROFORMER_MODELS,
    STEMS,
    VR_ARCH_MODELS,
    DEMUCS_v4_MODELS,
)

# ═══════════════════════════════════════════════════════════════
# Device detection
# ═══════════════════════════════════════════════════════════════

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
USE_AUTOCAST = DEVICE == "cuda"


# ═══════════════════════════════════════════════════════════════
# Утилиты
# ═══════════════════════════════════════════════════════════════


def _notify_progress(progress, value, message):
    """Безопасный вызов progress callback."""
    if progress is None:
        return
    try:
        progress(value, desc=message)
    except TypeError:
        try:
            progress(value, message)
        except Exception:
            pass


def _cleanup_gpu():
    """Очистка GPU памяти после сепарации."""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
    gc.collect()


def prepare_output_directory(input_file, output_directory):
    """Создаёт директорию для результатов сепарации и очищает если существует.

    Args:
        input_file: Путь к входному аудиофайлу.
        output_directory: Базовая директория для выходных файлов.

    Returns:
        str: Путь к созданной поддиректории.
    """
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_dir = os.path.join(output_directory, base_name)

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    return output_dir


def generate_stem_names(audio_path, name_template, model_name):
    """Генерирует имена стемов по шаблону.

    Args:
        audio_path: Путь к входному аудиофайлу.
        name_template: Шаблон имени (ключи: NAME, STEM, MODEL).
        model_name: Отображаемое имя модели.

    Returns:
        dict: Словарь {stem_type: formatted_name}.
    """
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    return {
        "All Stems": name_template
        .replace("NAME", base_name)
        .replace("STEM", "All Stems")
        .replace("MODEL", model_name)
    }


def get_available_models():
    """Возвращает словарь всех доступных моделей по архитектурам.

    Returns:
        dict: {arch_type: list[model_key]}
    """
    return {
        "roformer": list(ROFORMER_MODELS.keys()),
        "mdx23c": list(MDX23C_MODELS.keys()),
        "mdx": list(MDXNET_MODELS.keys()),
        "vr": list(VR_ARCH_MODELS.keys()),
        "demucs": list(DEMUCS_v4_MODELS.keys()),
    }


def get_output_formats():
    """Возвращает список доступных форматов выходных файлов."""
    return list(FORMATS)


def get_stem_types():
    """Возвращает список типов стемов для фильтрации leaderboard."""
    return list(STEMS)


# ═══════════════════════════════════════════════════════════════
# Управление моделями
# ═══════════════════════════════════════════════════════════════


def clear_models(model_dir):
    """Удаляет все файлы моделей из указанной директории.

    Args:
        model_dir: Путь к директории с моделями.

    Returns:
        str: Сообщение о результате.

    Raises:
        RuntimeError: При ошибке удаления.
    """
    try:
        count = 0
        for filename in os.listdir(model_dir):
            if filename.endswith((".th", ".pth", ".onnx", ".ckpt", ".json", ".yaml")):
                file_path = os.path.join(model_dir, filename)
                os.remove(file_path)
                count += 1
        return f"Удалено {count} файлов моделей."
    except Exception as e:
        raise RuntimeError(f"Ошибка удаления моделей: {e}") from e


def get_leaderboard(list_filter="vocals", list_limit=5):
    """Получает таблицу лидеров моделей через CLI PolUVR.

    Args:
        list_filter: Фильтр по типу стема.
        list_limit: Максимальное количество моделей.

    Returns:
        str: HTML таблица или сообщение об ошибке.
    """
    try:
        result = subprocess.run(
            ["PolUVR", "-l", f"--list_filter={list_filter}", f"--list_limit={list_limit}"],
            capture_output=True,
            text=True,
            check=True,
        )

        if result.returncode != 0:
            return f"Error: {result.stderr}"

        return "<table border='1'>" + "".join(
            f"<tr style='{'font-weight: bold; font-size: 1.2em;' if i == 0 else ''}'>" +
            "".join(f"<td>{cell}</td>" for cell in re.split(r"\s{2,}", line.strip())) +
            "</tr>"
            for i, line in enumerate(re.findall(r"^(?!-+)(.+)$", result.stdout.strip(), re.MULTILINE))
        ) + "</table>"

    except Exception as e:
        return f"Error: {e}"


# ═══════════════════════════════════════════════════════════════
# Общая внутренняя функция сепарации
# ═══════════════════════════════════════════════════════════════


def _run_separation(
    audio_path,
    model_filename,
    model_dir,
    output_dir,
    output_format,
    norm_threshold,
    amp_threshold,
    separator_kwargs,
    rename_template,
    model_display_name,
    progress=None,
):
    """Общая core-функция сепарации аудио.

    Args:
        audio_path: Путь к входному аудио.
        model_filename: Имя файла модели (для загрузки).
        model_dir: Директория для хранения/кеширования моделей.
        output_dir: Базовая директория для выходных файлов.
        output_format: Формат выходных файлов (wav, flac, mp3...).
        norm_threshold: Порог нормализации.
        amp_threshold: Порог усиления.
        separator_kwargs: Параметры архитектуры (mdxc_params, mdx_params, vr_params, demucs_params).
        rename_template: Шаблон переименования стемов.
        model_display_name: Отображаемое имя модели (для логов).
        progress: Callback для прогресса (callable или None).

    Returns:
        tuple[str, list[str]]: (output_dir, list_of_result_filenames)

    Raises:
        Exception: При ошибке сепарации.
    """
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    print(f"\n🎵 PolUVR 🎵")
    print(f"Input file: {base_name}")
    print(f"Model used: {model_display_name}")
    print("Audio separation in progress...")

    out_dir = prepare_output_directory(audio_path, output_dir)
    stem_names = generate_stem_names(audio_path, rename_template, model_display_name)

    separator = Separator(
        log_level=logging.WARNING,
        model_file_dir=model_dir,
        output_dir=out_dir,
        output_format=output_format,
        normalization_threshold=norm_threshold,
        amplification_threshold=amp_threshold,
        use_autocast=USE_AUTOCAST,
        **separator_kwargs,
    )

    try:
        _notify_progress(progress, 0.2, "Model loading...")
        separator.load_model(model_filename=model_filename)

        _notify_progress(progress, 0.7, "Audio separation...")
        results = separator.separate(audio_path, stem_names)
        print(f"Separation complete!\nResults: {', '.join(results)}")

        return out_dir, results
    finally:
        del separator
        _cleanup_gpu()


# ═══════════════════════════════════════════════════════════════
# Публичные функции сепарации по архитектурам
# ═══════════════════════════════════════════════════════════════


def separate_roformer(
    audio_path, model_key, segment_size, override_segment_size,
    overlap, pitch_shift, model_dir, output_dir, output_format,
    norm_threshold, amp_threshold, batch_size, rename_template,
    progress=None,
):
    """Сепарация с использованием модели Roformer.

    Returns:
        tuple[str, list[str]]: (output_dir, result_filenames)
    """
    model_filename = ROFORMER_MODELS[model_key]
    return _run_separation(
        audio_path=audio_path,
        model_filename=model_filename,
        model_dir=model_dir,
        output_dir=output_dir,
        output_format=output_format,
        norm_threshold=norm_threshold,
        amp_threshold=amp_threshold,
        separator_kwargs={
            "mdxc_params": {
                "segment_size": segment_size,
                "override_model_segment_size": override_segment_size,
                "batch_size": batch_size,
                "overlap": overlap,
                "pitch_shift": pitch_shift,
            }
        },
        rename_template=rename_template,
        model_display_name=model_key,
        progress=progress,
    )


def separate_mdx23c(
    audio_path, model_key, segment_size, override_segment_size,
    overlap, pitch_shift, model_dir, output_dir, output_format,
    norm_threshold, amp_threshold, batch_size, rename_template,
    progress=None,
):
    """Сепарация с использованием модели MDX23C.

    Returns:
        tuple[str, list[str]]: (output_dir, result_filenames)
    """
    model_filename = MDX23C_MODELS[model_key]
    return _run_separation(
        audio_path=audio_path,
        model_filename=model_filename,
        model_dir=model_dir,
        output_dir=output_dir,
        output_format=output_format,
        norm_threshold=norm_threshold,
        amp_threshold=amp_threshold,
        separator_kwargs={
            "mdxc_params": {
                "segment_size": segment_size,
                "override_model_segment_size": override_segment_size,
                "batch_size": batch_size,
                "overlap": overlap,
                "pitch_shift": pitch_shift,
            }
        },
        rename_template=rename_template,
        model_display_name=model_key,
        progress=progress,
    )


def separate_mdx(
    audio_path, model_key, hop_length, segment_size, overlap,
    denoise, model_dir, output_dir, output_format,
    norm_threshold, amp_threshold, batch_size, rename_template,
    progress=None,
):
    """Сепарация с использованием модели MDX-NET.

    Returns:
        tuple[str, list[str]]: (output_dir, result_filenames)
    """
    model_filename = MDXNET_MODELS[model_key]
    return _run_separation(
        audio_path=audio_path,
        model_filename=model_filename,
        model_dir=model_dir,
        output_dir=output_dir,
        output_format=output_format,
        norm_threshold=norm_threshold,
        amp_threshold=amp_threshold,
        separator_kwargs={
            "mdx_params": {
                "hop_length": hop_length,
                "segment_size": segment_size,
                "overlap": overlap,
                "batch_size": batch_size,
                "enable_denoise": denoise,
            }
        },
        rename_template=rename_template,
        model_display_name=model_key,
        progress=progress,
    )


def separate_vr(
    audio_path, model_key, window_size, aggression, enable_tta,
    enable_post_process, post_process_threshold, high_end_process,
    model_dir, output_dir, output_format,
    norm_threshold, amp_threshold, batch_size, rename_template,
    progress=None,
):
    """Сепарация с использованием модели VR ARCH.

    Returns:
        tuple[str, list[str]]: (output_dir, result_filenames)
    """
    model_filename = VR_ARCH_MODELS[model_key]
    return _run_separation(
        audio_path=audio_path,
        model_filename=model_filename,
        model_dir=model_dir,
        output_dir=output_dir,
        output_format=output_format,
        norm_threshold=norm_threshold,
        amp_threshold=amp_threshold,
        separator_kwargs={
            "vr_params": {
                "batch_size": batch_size,
                "window_size": window_size,
                "aggression": aggression,
                "enable_tta": enable_tta,
                "enable_post_process": enable_post_process,
                "post_process_threshold": post_process_threshold,
                "high_end_process": high_end_process,
            }
        },
        rename_template=rename_template,
        model_display_name=model_key,
        progress=progress,
    )


def separate_demucs(
    audio_path, model_key, segment_size, shifts, overlap,
    segments_enabled, model_dir, output_dir, output_format,
    norm_threshold, amp_threshold, rename_template,
    progress=None,
):
    """Сепарация с использованием модели Demucs.

    Returns:
        tuple[str, list[str]]: (output_dir, result_filenames)
    """
    model_filename = DEMUCS_v4_MODELS[model_key]
    return _run_separation(
        audio_path=audio_path,
        model_filename=model_filename,
        model_dir=model_dir,
        output_dir=output_dir,
        output_format=output_format,
        norm_threshold=norm_threshold,
        amp_threshold=amp_threshold,
        separator_kwargs={
            "demucs_params": {
                "segment_size": segment_size,
                "shifts": shifts,
                "overlap": overlap,
                "segments_enabled": segments_enabled,
            }
        },
        rename_template=rename_template,
        model_display_name=model_key,
        progress=progress,
    )