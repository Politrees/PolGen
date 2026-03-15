from __future__ import annotations

import os
import re
import shutil
import tempfile
import zipfile
from typing import Callable

from rvc.modules.download_source import download_file

ProgressCb = Callable[[float, str], None]

RVC_MODELS_DIR = os.path.join(os.getcwd(), "models", "RVC_models")
os.makedirs(RVC_MODELS_DIR, exist_ok=True)


def _sanitize_model_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValueError("model_name пустой")
    # оставим буквы/цифры/пробел/._-; остальное заменим на _
    name = re.sub(r"[^0-9A-Za-zА-Яа-я ._\-()]", "_", name)
    name = name.strip(" .")
    if not name:
        raise ValueError("model_name некорректный")
    return name


def _extract_zip_to_model(zip_path: str, model_name: str, progress: ProgressCb | None = None) -> str:
    model_name = _sanitize_model_name(model_name)
    target_dir = os.path.join(RVC_MODELS_DIR, model_name)

    if os.path.exists(target_dir):
        raise FileExistsError(f"Модель '{model_name}' уже существует")

    os.makedirs(target_dir, exist_ok=True)

    if progress:
        progress(0.75, "Распаковка ZIP...")

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(target_dir)

    # найти pth/index в распакованном дереве
    pth_path = None
    index_path = None

    for root, _, files in os.walk(target_dir):
        for name in files:
            fp = os.path.join(root, name)
            if name.endswith(".pth"):
                pth_path = fp
            if name.endswith(".index") and os.path.getsize(fp) > 1024 * 100:
                index_path = fp

    if not pth_path:
        shutil.rmtree(target_dir, ignore_errors=True)
        raise FileNotFoundError("В ZIP не найден .pth файл модели")

    # перенести pth/index в корень папки модели
    pth_dst = os.path.join(target_dir, os.path.basename(pth_path))
    if pth_path != pth_dst:
        shutil.move(pth_path, pth_dst)

    if index_path:
        idx_dst = os.path.join(target_dir, os.path.basename(index_path))
        if index_path != idx_dst:
            shutil.move(index_path, idx_dst)

    # подчистить вложенные папки
    for item in os.listdir(target_dir):
        p = os.path.join(target_dir, item)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)

    return target_dir


def install_rvc_from_url(url: str, model_name: str, progress: ProgressCb | None = None) -> str:
    model_name = _sanitize_model_name(model_name)

    if progress:
        progress(0.05, f"Скачивание модели '{model_name}' по ссылке...")

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = os.path.join(tmp, f"{model_name}.zip")
        download_file(url, zip_path, progress)
        if progress:
            progress(0.7, "Скачивание завершено.")
        out_dir = _extract_zip_to_model(zip_path, model_name, progress)
        if progress:
            progress(1.0, "Готово.")
        return out_dir


def install_rvc_from_zip(zip_path: str, model_name: str, progress: ProgressCb | None = None) -> str:
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"ZIP не найден: {zip_path}")
    if progress:
        progress(0.2, f"Установка модели '{model_name}' из ZIP...")
    out_dir = _extract_zip_to_model(zip_path, model_name, progress)
    if progress:
        progress(1.0, "Готово.")
    return out_dir


def install_rvc_from_files(pth_path: str, index_path: str | None, model_name: str, progress: ProgressCb | None = None) -> str:
    model_name = _sanitize_model_name(model_name)
    target_dir = os.path.join(RVC_MODELS_DIR, model_name)

    if os.path.exists(target_dir):
        raise FileExistsError(f"Модель '{model_name}' уже существует")

    if not os.path.exists(pth_path):
        raise FileNotFoundError(f"pth не найден: {pth_path}")
    if index_path and not os.path.exists(index_path):
        raise FileNotFoundError(f"index не найден: {index_path}")

    os.makedirs(target_dir, exist_ok=True)

    if progress:
        progress(0.4, "Копирование .pth...")
    shutil.copyfile(pth_path, os.path.join(target_dir, os.path.basename(pth_path)))

    if index_path:
        if progress:
            progress(0.7, "Копирование .index...")
        shutil.copyfile(index_path, os.path.join(target_dir, os.path.basename(index_path)))

    if progress:
        progress(1.0, "Готово.")
    return target_dir
