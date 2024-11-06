import os
import re
import gdown
import shutil
import zipfile
import requests
import gradio as gr
import urllib.request
from mega import Mega


EMBEDDERS_DIR = os.path.join(os.getcwd(), "rvc", "models", "embedders")
HUBERT_BASE_PATH = os.path.join(EMBEDDERS_DIR, "hubert_base.pt")
RVC_MODELS_DIR = os.path.join(os.getcwd(), "models")

base_url = "https://huggingface.co/Politrees/RVC_resources/resolve/main/embedders/"

models = [
    "hubert_base.pt",
    "contentvec_base.pt",
    "korean_hubert_base.pt",
    "chinese_hubert_base.pt",
    "portuguese_hubert_base.pt",
    "japanese_hubert_base.pt",
]


# Универсальная функция для скачивания файла с разных источников
def download_file(url, zip_name):
    try:
        if "drive.google.com" in url:
            download_from_google_drive(url, zip_name)
        elif "huggingface.co" in url:
            download_from_huggingface(url, zip_name)
        elif "pixeldrain.com" in url:
            download_from_pixeldrain(url, zip_name)
        elif "mega.nz" in url:
            download_from_mega(url, zip_name)
        elif "disk.yandex.ru" in url or "yadi.sk" in url:
            download_from_yandex(url, zip_name)
        else:
            raise ValueError(f"Неподдерживаемый источник: {url}")
    except Exception as e:
        raise gr.Error(f"Ошибка при скачивании: {str(e)}")


# Скачивание файла с Google Drive с помощью библиотеки gdown
def download_from_google_drive(url, zip_name):
    progress(0.5, desc="Загрузка модели с Google Drive...")
    file_id = (
        url.split("file/d/")[1].split("/")[0]
        if "file/d/" in url
        else url.split("id=")[1].split("&")[0]
    )
    gdown.download(id=file_id, output=str(zip_name), quiet=False)


# Скачивание файла с HuggingFace через urllib
def download_from_huggingface(url, zip_name):
    progress(0.5, desc="Загрузка модели с HuggingFace...")
    urllib.request.urlretrieve(url, zip_name)


# Скачивание файла с Pixeldrain через API
def download_from_pixeldrain(url, zip_name):
    progress(0.5, desc="Загрузка модели с Pixeldrain...")
    file_id = url.split("pixeldrain.com/u/")[1]
    response = requests.get(f"https://pixeldrain.com/api/file/{file_id}")
    with open(zip_name, "wb") as f:
        f.write(response.content)


# Скачивание файла с Mega через библиотеку Mega
def download_from_mega(url, zip_name):
    progress(0.5, desc="Загрузка модели с Mega...")
    m = Mega()
    m.download_url(url, dest_filename=str(zip_name))


# Скачивание файла с Яндекс Диска через публичное API
def download_from_yandex(url, zip_name):
    progress(0.5, desc="Загрузка модели с Яндекс Диска...")
    yandex_public_key = f"download?public_key={url}"
    yandex_api_url = (
        f"https://cloud-api.yandex.net/v1/disk/public/resources/{yandex_public_key}"
    )
    response = requests.get(yandex_api_url)
    if response.status_code == 200:
        download_link = response.json().get("href")
        urllib.request.urlretrieve(download_link, zip_name)
    else:
        raise gr.Error(
            f"Ошибка при получении ссылки с Яндекс Диска: {response.status_code}"
        )


# Основная функция для скачивания модели по ссылке и распаковки zip-файла
def download_from_url(url, dir_name, progress=gr.Progress(track_tqdm=True)):
    try:
        progress(0, desc=f"Загрузка голосовой модели {dir_name}...")
        zip_name = os.path.join(RVC_MODELS_DIR, dir_name + ".zip")
        extraction_folder = os.path.join(RVC_MODELS_DIR, dir_name)
        if os.path.exists(extraction_folder):
            raise gr.Error(
                f"Директория голосовой модели {dir_name} уже существует! Выберите другое имя для вашей голосовой модели."
            )

        download_file(url, zip_name)
        progress(0.8, desc="Распаковка zip-файла...")
        extract_zip(extraction_folder, zip_name)
        return f"Модель {dir_name} успешно загружена!"
    except Exception as e:
        raise gr.Error(f"Ошибка при загрузке модели: {str(e)}")


# Функция для загрузки и распаковки zip-файла модели через интерфейс
def upload_zip_file(zip_path, dir_name, progress=gr.Progress(track_tqdm=True)):
    try:
        extraction_folder = os.path.join(RVC_MODELS_DIR, dir_name)
        if os.path.exists(extraction_folder):
            raise gr.Error(
                f"Директория голосовой модели {dir_name} уже существует! Выберите другое имя для вашей голосовой модели."
            )

        zip_name = zip_path.name
        progress(0.8, desc="Распаковка zip-файла...")
        extract_zip(extraction_folder, zip_name)
        return f"Модель {dir_name} успешно загружена!"
    except Exception as e:
        raise gr.Error(f"Ошибка при загрузке модели: {str(e)}")


# Функция для загрузки отдельных файлов модели (.pth и .index)
def upload_separate_files(pth_file, index_file, dir_name, progress=gr.Progress(track_tqdm=True)):
    try:
        extraction_folder = os.path.join(RVC_MODELS_DIR, dir_name)
        if os.path.exists(extraction_folder):
            raise gr.Error(
                f"Директория голосовой модели {dir_name} уже существует! Выберите другое имя для вашей голосовой модели."
            )

        os.makedirs(extraction_folder, exist_ok=True)

        # Копируем файл .pth
        if pth_file:
            pth_path = os.path.join(extraction_folder, os.path.basename(pth_file.name))
            shutil.copyfile(pth_file.name, pth_path)

        # Копируем файл .index
        if index_file:
            index_path = os.path.join(
                extraction_folder, os.path.basename(index_file.name)
            )
            shutil.copyfile(index_file.name, index_path)
        return f"Модель {dir_name} успешно загружена!"
    except Exception as e:
        raise gr.Error(f"Ошибка при загрузке модели: {str(e)}")


# Распаковывает zip-файл в указанную директорию и находит файлы модели (.pth и .index)
def extract_zip(extraction_folder, zip_name):
    os.makedirs(extraction_folder, exist_ok=True)
    with zipfile.ZipFile(zip_name, "r") as zip_ref:
        zip_ref.extractall(extraction_folder)
    os.remove(zip_name)

    index_filepath, model_filepath = None, None
    # Проходим по всем файлам в распакованной директории для поиска .pth и .index
    for root, _, files in os.walk(extraction_folder):
        for name in files:
            file_path = os.path.join(root, name)
            if (
                name.endswith(".index") and os.stat(file_path).st_size > 1024 * 100
            ):
                index_filepath = file_path
            if (
                name.endswith(".pth") and os.stat(file_path).st_size > 1024 * 1024 * 40
            ):
                model_filepath = file_path

    if not model_filepath:
        raise gr.Error(
            f"Не найден файл модели .pth в распакованном zip-файле. Проверьте содержимое в {extraction_folder}."
        )

    # Переименовываем и удаляем ненужные папки
    rename_and_cleanup(extraction_folder, model_filepath, index_filepath)


# Функция для переименования файлов и удаления пустых папок
def rename_and_cleanup(extraction_folder, model_filepath, index_filepath):
    os.rename(
        model_filepath,
        os.path.join(extraction_folder, os.path.basename(model_filepath)),
    )
    if index_filepath:
        os.rename(
            index_filepath,
            os.path.join(extraction_folder, os.path.basename(index_filepath)),
        )

    # Удаляем оставшиеся пустые директории после распаковки
    for filepath in os.listdir(extraction_folder):
        full_path = os.path.join(extraction_folder, filepath)
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)


def download_file(url, destination):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(destination, "wb") as out_file:
        for chunk in response.iter_content(chunk_size=8192):
            out_file.write(chunk)


def download_and_replace_model(model_name, custom_url, progress=gr.Progress(track_tqdm=True)):
    try:
        if custom_url:
            if not re.search(r"\.pt(\?.*)?$", custom_url):
                return "Ошибка: URL должен указывать на файл в формате .pt"
            model_url = custom_url
        else:
            model_url = base_url + model_name

        tmp_model_path = os.path.join(EMBEDDERS_DIR, "tmp_model.pt")

        progress(0.4, desc=f'Установка модели "{model_name}"...')
        download_file(model_url, tmp_model_path)

        progress(0.8, desc="Удаление старой HuBERT модели...")
        if os.path.exists(HUBERT_BASE_PATH):
            os.remove(HUBERT_BASE_PATH)

        os.rename(tmp_model_path, HUBERT_BASE_PATH)
        return f'Модель "{model_name}" успешно установлена.'
    except Exception as e:
        return f'Ошибка при установке модели "{model_name}": {str(e)}'


def toggle_custom_url(checkbox_value):
    return gr.update(visible=checkbox_value), gr.update(visible=not checkbox_value)


def output_message():
    return gr.Text(label="Сообщение вывода", interactive=False)


def url_download(output_message, progress=gr.Progress(track_tqdm=True)):
    with gr.Accordion("Загрузить по ссылке", open=False):
        gr.HTML(
            "<h3>"
            "Поддерживаемые сайты: "
            "<a href='https://huggingface.co/' target='_blank'>HuggingFace</a>, "
            "<a href='https://pixeldrain.com/' target='_blank'>Pixeldrain</a>, "
            "<a href='https://drive.google.com/' target='_blank'>Google Drive</a>, "
            "<a href='https://mega.nz/' target='_blank'>Mega</a>, "
            "<a href='https://disk.yandex.ru/' target='_blank'>Яндекс Диск</a>"
            "</h3>"
        )
        with gr.Column():
            with gr.Group():
                link = gr.Text(label="Ссылка на загрузку модели")
                model_name = gr.Text(
                    label="Имя модели",
                    info="Дайте вашей загружаемой модели уникальное имя, отличное от других голосовых моделей.",
                )
            download_btn = gr.Button("Загрузить модель", variant="primary")

    download_btn.click(
        download_from_url,
        inputs=[link, model_name],
        outputs=output_message,
    )


def zip_upload(output_message, progress=gr.Progress(track_tqdm=True)):
    with gr.Accordion("Загрузить ZIP архивом", open=False):
        with gr.Column():
            with gr.Group():
                zip_file = gr.File(
                    label="Zip-файл", file_types=[".zip"], file_count="single"
                )
                model_name = gr.Text(
                    label="Имя модели",
                    info="Дайте вашей загружаемой модели уникальное имя, отличное от других голосовых моделей.",
                )
            upload_btn = gr.Button("Загрузить модель", variant="primary")

    upload_btn.click(
        upload_zip_file,
        inputs=[zip_file, model_name],
        outputs=output_message,
    )


def files_upload(output_message, progress=gr.Progress(track_tqdm=True)):
    with gr.Accordion("Загрузить файлами", open=False):
        with gr.Column():
            with gr.Group():
                with gr.Row(equal_height=False):
                    pth_file = gr.File(
                        label="pth-файл", file_types=[".pth"], file_count="single"
                    )
                    index_file = gr.File(
                        label="index-файл", file_types=[".index"], file_count="single"
                    )
                model_name = gr.Text(
                    label="Имя модели",
                    info="Дайте вашей загружаемой модели уникальное имя, отличное от других голосовых моделей.",
                )
            upload_btn = gr.Button("Загрузить модель", variant="primary")

    upload_btn.click(
        upload_separate_files,
        inputs=[pth_file, index_file, model_name],
        outputs=output_message,
    )


def install_hubert_tab(progress=gr.Progress(track_tqdm=True)):
    with gr.Column():
        custom_url_checkbox = gr.Checkbox(label="Другой HuBERT", value=False)
        custom_url_textbox = gr.Textbox(label="URL модели", visible=False)
        hubert_model_dropdown = gr.Dropdown(
            models, label="HuBERT модели:", visible=True
        )
        hubert_download_btn = gr.Button("Скачать", variant="primary")

    hubert_output_message = gr.Text(label="Сообщение вывода", interactive=False)

    custom_url_checkbox.change(
        toggle_custom_url,
        inputs=custom_url_checkbox,
        outputs=[custom_url_textbox, hubert_model_dropdown],
    )

    hubert_download_btn.click(
        download_and_replace_model,
        inputs=[hubert_model_dropdown, custom_url_textbox],
        outputs=hubert_output_message,
    )


# Основная функция для вызова из командной строки
def main():
    if len(sys.argv) != 3:
        print('\nИспользование:\npython3 -m rvc.modules.model_manager "url" "dir_name"\n')
        sys.exit(1)

    url = sys.argv[1]
    dir_name = sys.argv[2]

    try:
        # Скачивание и загрузка модели через командную строку
        result = download_from_url(url, dir_name)
        print(result)
    except gr.Error as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()