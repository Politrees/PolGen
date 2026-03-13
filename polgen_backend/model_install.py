from __future__ import annotations

import os
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from typing import Callable

import requests

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


def _download_file_http(url: str, dst: str, progress: ProgressCb | None = None) -> None:
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", "0") or "0")
        done = 0
        with open(dst, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue
                f.write(chunk)
                done += len(chunk)
                if progress and total > 0:
                    progress(0.15 + 0.65 * (done / total), f"Скачивание... {done/1024/1024:.1f} MB / {total/1024/1024:.1f} MB")


def _download_from_google_drive(url: str, dst: str, progress: ProgressCb | None = None) -> None:
    import gdown

    if progress:
        progress(0.2, "Скачивание с Google Drive...")
    # file/d/<id>/view или ?id=<id>
    file_id = None
    if "file/d/" in url:
        file_id = url.split("file/d/")[1].split("/")[0]
    elif "id=" in url:
        file_id = url.split("id=")[1].split("&")[0]
    if not file_id:
        raise ValueError("Не удалось извлечь file_id из Google Drive URL")
    gdown.download(id=file_id, output=dst, quiet=False)


def _download_from_pixeldrain(url: str, dst: str, progress: ProgressCb | None = None) -> None:
    if progress:
        progress(0.2, "Скачивание с Pixeldrain...")
    file_id = url.split("pixeldrain.com/u/")[1]
    r = requests.get(f"https://pixeldrain.com/api/file/{file_id}", timeout=60)
    r.raise_for_status()
    with open(dst, "wb") as f:
        f.write(r.content)


def _download_from_mega(url: str, dst: str, progress: ProgressCb | None = None) -> None:
    from mega import Mega

    if progress:
        progress(0.2, "Скачивание с Mega...")
    m = Mega()
    m.download_url(url, dest_filename=dst)


def _download_from_yandex(url: str, dst: str, progress: ProgressCb | None = None) -> None:
    if progress:
        progress(0.2, "Скачивание с Яндекс.Диска...")
    yandex_public_key = f"download?public_key={url}"
    api = f"https://cloud-api.yandex.net/v1/disk/public/resources/{yandex_public_key}"
    r = requests.get(api, timeout=60)
    r.raise_for_status()
    href = r.json().get("href")
    if not href:
        raise ValueError("Яндекс.Диск не вернул href")
    urllib.request.urlretrieve(href, dst)


def _download_from_dropbox(url: str, dst: str, progress: ProgressCb | None = None) -> None:
    if progress:
        progress(0.2, "Скачивание с Dropbox...")
    # делаем прямую ссылку
    if "?dl=0" in url:
        url = url.replace("?dl=0", "?dl=1")
    elif "dl=1" not in url:
        url += "?dl=1" if "?" not in url else "&dl=1"
    _download_file_http(url, dst, progress)


def download_zip_from_url(url: str, dst_zip: str, progress: ProgressCb | None = None) -> None:
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    host = host.lower()

    if "drive.google.com" in host:
        return _download_from_google_drive(url, dst_zip, progress)
    if "huggingface.co" in host:
        # huggingface resolve/... ?download=true обычно отлично работает по HTTP
        return _download_file_http(url, dst_zip, progress)
    if "pixeldrain.com" in host:
        return _download_from_pixeldrain(url, dst_zip, progress)
    if "mega.nz" in host:
        return _download_from_mega(url, dst_zip, progress)
    if host in {"disk.yandex.ru", "yadi.sk"}:
        return _download_from_yandex(url, dst_zip, progress)
    if host in {"www.dropbox.com", "dropbox.com"}:
        return _download_from_dropbox(url, dst_zip, progress)

    raise ValueError(f"Неподдерживаемый источник: {host}")


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
        download_zip_from_url(url, zip_path, progress)
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


def delete_rvc_model(model_name: str) -> None:
    model_name = _sanitize_model_name(model_name)
    target_dir = os.path.join(RVC_MODELS_DIR, model_name)
    if not os.path.isdir(target_dir):
        raise FileNotFoundError(f"Модель не найдена: {model_name}")
    shutil.rmtree(target_dir, ignore_errors=True)