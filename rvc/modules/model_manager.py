import os
import shutil
import sys
import zipfile

from rvc.lib.progress import notify_progress
from rvc.modules.download_source import download_file

# Путь к директории, где будут храниться модели RVC
rvc_models_dir = os.path.join(os.getcwd(), "models", "RVC_models")
os.makedirs(rvc_models_dir, exist_ok=True)


# ═══════════════════════════════════════════════════════════════
# Утилиты для работы с ZIP и файлами моделей
# ═══════════════════════════════════════════════════════════════


def extract_zip(extraction_folder, zip_name, delete_zip=True):
    """Распаковывает zip-файл и находит файлы модели (.pth и .index)."""
    os.makedirs(extraction_folder, exist_ok=True)
    with zipfile.ZipFile(zip_name, "r") as zip_ref:
        zip_ref.extractall(extraction_folder)

    if delete_zip:
        os.remove(zip_name)

    index_filepath, model_filepath = None, None
    for root, _, files in os.walk(extraction_folder):
        for name in files:
            file_path = os.path.join(root, name)
            if name.endswith(".index") and os.stat(file_path).st_size > 1024 * 100:
                index_filepath = file_path
            if name.endswith(".pth") and os.stat(file_path).st_size > 1024 * 1024 * 40:
                model_filepath = file_path

    if not model_filepath:
        raise FileNotFoundError(f"Не найден файл модели .pth в распакованном zip-файле ({extraction_folder}).")

    rename_and_cleanup(extraction_folder, model_filepath, index_filepath)


def rename_and_cleanup(extraction_folder, model_filepath, index_filepath):
    """Переименовывает файлы модели и удаляет пустые папки."""
    os.rename(model_filepath, os.path.join(extraction_folder, os.path.basename(model_filepath)))
    if index_filepath:
        os.rename(index_filepath, os.path.join(extraction_folder, os.path.basename(index_filepath)))

    for filepath in os.listdir(extraction_folder):
        full_path = os.path.join(extraction_folder, filepath)
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)


# ═══════════════════════════════════════════════════════════════
# Чистые функции (без Gradio-зависимостей)
# ═══════════════════════════════════════════════════════════════


def install_from_url(url, model_name, progress=None):
    """Скачивает модель по URL и устанавливает."""
    notify_progress(progress, 0, f"[~] Загрузка голосовой модели {model_name}...")
    zip_name = os.path.join(rvc_models_dir, model_name + ".zip")
    extraction_folder = os.path.join(rvc_models_dir, model_name)

    if os.path.exists(extraction_folder):
        raise FileExistsError(f"Директория голосовой модели {model_name} уже существует! Выберите другое имя.")

    download_file(url, zip_name, progress)
    notify_progress(progress, 0.8, "[~] Распаковка zip-файла...")
    extract_zip(extraction_folder, zip_name, delete_zip=True)
    return f"[+] Модель {model_name} успешно загружена!"


def install_from_zip_path(zip_path, model_name, progress=None):
    """Устанавливает модель из ZIP-файла по строковому пути."""
    extraction_folder = os.path.join(rvc_models_dir, model_name)

    if os.path.exists(extraction_folder):
        raise FileExistsError(f"Директория голосовой модели {model_name} уже существует! Выберите другое имя.")

    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"ZIP файл не найден: {zip_path}")

    notify_progress(progress, 0.8, "[~] Распаковка zip-файла...")
    extract_zip(extraction_folder, zip_path, delete_zip=False)
    return f"[+] Модель {model_name} успешно загружена!"


def install_from_files_path(pth_path, index_path, model_name, progress=None):
    """Устанавливает модель из отдельных файлов по строковым путям."""
    extraction_folder = os.path.join(rvc_models_dir, model_name)

    if os.path.exists(extraction_folder):
        raise FileExistsError(f"Директория голосовой модели {model_name} уже существует! Выберите другое имя.")

    if not pth_path or not os.path.exists(pth_path):
        raise FileNotFoundError(f"PTH файл не найден: {pth_path}")

    os.makedirs(extraction_folder, exist_ok=True)

    notify_progress(progress, 0.4, "[~] Копирование .pth файла...")
    shutil.copyfile(pth_path, os.path.join(extraction_folder, os.path.basename(pth_path)))

    if index_path and os.path.exists(index_path):
        notify_progress(progress, 0.8, "[~] Копирование .index файла...")
        shutil.copyfile(index_path, os.path.join(extraction_folder, os.path.basename(index_path)))

    return f"[+] Модель {model_name} успешно загружена!"


# ═══════════════════════════════════════════════════════════════
# Удаление модели
# ═══════════════════════════════════════════════════════════════


def delete_model(model_name):
    """Удаляет папку модели RVC по имени."""
    if not model_name or not model_name.strip():
        raise ValueError("Имя модели пустое")

    if ".." in model_name or "/" in model_name or "\\" in model_name:
        raise ValueError(f"Некорректное имя модели: {model_name}")

    target_dir = os.path.join(rvc_models_dir, model_name.strip())
    if not os.path.isdir(target_dir):
        raise FileNotFoundError(f"Модель не найдена: {model_name}")

    try:
        from rvc.infer.infer import get_model_cache
        get_model_cache().invalidate_rvc_model(model_name.strip())
    except ImportError:
        pass

    shutil.rmtree(target_dir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


def main():
    if len(sys.argv) != 3:
        print('\nИспользование:\npython3 -m rvc.modules.model_manager "url" "dir_name"\n')
        sys.exit(1)

    url = sys.argv[1]
    dir_name = sys.argv[2]

    try:
        from rvc.lib.progress import ConsoleProgress
        result = install_from_url(url, dir_name, progress=ConsoleProgress())
        print(result)
    except Exception as e:
        print(f"Ошибка: {e!s}")
        sys.exit(1)


if __name__ == "__main__":
    main()