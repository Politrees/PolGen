import urllib.request
from urllib.parse import urlparse

import requests

from rvc.lib.progress import notify_progress


# Универсальная функция для скачивания файла с разных источников
def download_file(url, zip_name, progress=None):
    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname or ""
        if hostname == "drive.google.com":
            download_from_google_drive(url, zip_name, progress)
        elif hostname == "huggingface.co":
            download_from_huggingface(url, zip_name, progress)
        elif hostname == "pixeldrain.com":
            download_from_pixeldrain(url, zip_name, progress)
        elif hostname == "mega.nz":
            download_from_mega(url, zip_name, progress)
        elif hostname in {"disk.yandex.ru", "yadi.sk"}:
            download_from_yandex(url, zip_name, progress)
        elif hostname in {"www.dropbox.com", "dropbox.com"}:
            download_from_dropbox(url, zip_name, progress)
        else:
            raise ValueError(f"Неподдерживаемый источник: {url}")
    except Exception as e:
        raise RuntimeError(f"Ошибка при скачивании: {e!s}") from e


# Скачивание файла с Google Drive
def download_from_google_drive(url, zip_name, progress=None):
    import gdown

    notify_progress(progress, 0.5, "[~] Загрузка модели с Google Drive...")
    file_id = url.split("file/d/")[1].split("/")[0] if "file/d/" in url else url.split("id=")[1].split("&")[0]
    gdown.download(id=file_id, output=str(zip_name), quiet=False)


# Скачивание файла с HuggingFace
def download_from_huggingface(url, zip_name, progress=None):
    notify_progress(progress, 0.5, "[~] Загрузка модели с HuggingFace...")
    urllib.request.urlretrieve(url, zip_name)


# Скачивание файла с Pixeldrain
def download_from_pixeldrain(url, zip_name, progress=None):
    notify_progress(progress, 0.5, "[~] Загрузка модели с Pixeldrain...")
    file_id = url.split("pixeldrain.com/u/")[1]
    response = requests.get(f"https://pixeldrain.com/api/file/{file_id}")
    with open(zip_name, "wb") as f:
        f.write(response.content)


# Скачивание файла с Mega
def download_from_mega(url, zip_name, progress=None):
    from mega import Mega

    notify_progress(progress, 0.5, "[~] Загрузка модели с Mega...")
    m = Mega()
    m.download_url(url, dest_filename=str(zip_name))


# Скачивание Яндекс Диска
def download_from_yandex(url, zip_name, progress=None):
    notify_progress(progress, 0.5, "[~] Загрузка модели с Яндекс Диска...")
    yandex_public_key = f"download?public_key={url}"
    yandex_api_url = f"https://cloud-api.yandex.net/v1/disk/public/resources/{yandex_public_key}"
    response = requests.get(yandex_api_url)
    if response.status_code == 200:
        download_link = response.json().get("href")
        urllib.request.urlretrieve(download_link, zip_name)
    else:
        raise RuntimeError(f"Ошибка при получении ссылки с Яндекс Диска: {response.status_code}")


# Скачивание с Dropbox
def download_from_dropbox(url, zip_name, progress=None):
    notify_progress(progress, 0.5, "[~] Загрузка модели с Dropbox...")
    if "?dl=0" in url:
        url = url.replace("?dl=0", "?dl=1")
    elif "?dl=1" not in url:
        url += "?dl=1" if "?" not in url else "&dl=1"
    urllib.request.urlretrieve(url, zip_name)