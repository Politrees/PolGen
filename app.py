import logging
import os
import sys
import warnings
from typing import Any

# Configuring the environment and logging
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Disable unnecessary TensorFlow logs
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"  # Disabling Gradio analytics
logging.basicConfig(level=logging.WARNING)  # Disable all logs, except WARNING and above
warnings.filterwarnings("ignore")  # Disable all warnings

import gradio as gr
from PolUVR.utils import PolUVR_UI

from assets.model_installer import check_and_install_models
from assets.notebook_check import colab_check, kaggle_check
from assets.version import __version__, __version_info__
from tabs.components.modules import output_message
from tabs.inference import edge_tts_tab, inference_tab
from tabs.install import files_upload, install_hubert_tab, url_zip_download, zip_upload
from tabs.welcome import welcome_tab

# Constants
DEFAULT_SERVER_NAME = "127.0.0.1"
DEFAULT_PORT = 4000
MAX_PORT_ATTEMPTS = 10

OUTPUT_MESSAGE_COMPONENT = output_message()
RUN_FROM_JUPYTER_NOTEBOOKS = colab_check() or kaggle_check()


def is_offline_mode() -> bool:
    return "--offline" in sys.argv


def get_title() -> str:
    """Формирует заголовок окна с версией."""
    base_title = f"PolGen v{__version__} - Politrees"
    if is_offline_mode():
        return f"{base_title} (offline)"
    return base_title


# Gradio Interface
with gr.Blocks(
    title=get_title(),
    css="footer{display:none !important}",
    theme=gr.themes.Soft(
        primary_hue="green",
        secondary_hue="green",
        neutral_hue="neutral",
        spacing_size="sm",
        radius_size="lg",
    ),
) as PolGen:
    with gr.Tab("Велком/Контакты"):
        welcome_tab()

    with gr.Tab("Преобразование голоса (RVC)"):
        inference_tab()

    if not is_offline_mode():
        with gr.Tab("Преобразование текста в речь (TTS)"):
            edge_tts_tab()

    with gr.Tab("PolUVR (UVR)"):
        if is_offline_mode():
            gr.HTML(
                "<center><h3>PolUVR не будет функционировать без подключения к интернету, если вы ранее не установили необходимые модели.</h3></center>",
            )
        # https://github.com/Politrees/PolUVR?tab=readme-ov-file#integrate-our-interface-into-your-gradio-projects
        PolUVR_UI("models/UVR_models", "output/UVR_output")

    with gr.Tab("Загрузка моделей"):
        if not is_offline_mode():
            with gr.Tab("Загрузка RVC моделей"):
                url_zip_download(OUTPUT_MESSAGE_COMPONENT)
                zip_upload(OUTPUT_MESSAGE_COMPONENT)
                files_upload(OUTPUT_MESSAGE_COMPONENT)
                OUTPUT_MESSAGE_COMPONENT.render()

            with gr.Tab("Загрузка HuBERT моделей"):
                install_hubert_tab()
        else:
            with gr.Tab("Загрузка RVC моделей"):
                zip_upload(OUTPUT_MESSAGE_COMPONENT)
                files_upload(OUTPUT_MESSAGE_COMPONENT)
                OUTPUT_MESSAGE_COMPONENT.render()


def launch_gradio(server_name: str, server_port: int) -> None:
    PolGen.launch(
        favicon_path="assets/logo.ico",
        inbrowser=not RUN_FROM_JUPYTER_NOTEBOOKS,
        share=RUN_FROM_JUPYTER_NOTEBOOKS,
        quiet=RUN_FROM_JUPYTER_NOTEBOOKS,
        server_name=server_name,
        server_port=server_port,
        show_error=True,
        debug=True,
    )


def get_value_from_args(key: str, default: Any = None) -> Any:
    if key in sys.argv:
        index = sys.argv.index(key) + 1
        if index < len(sys.argv):
            return sys.argv[index]
    return default


if __name__ == "__main__":
    print("Среда запуска: ", "Jupyter Notebook" if RUN_FROM_JUPYTER_NOTEBOOKS else "LocalHost")

    # Красивый вывод версии
    print(f"\n╔{'═' * 42}╗")
    print(f"║{'PolGen v' + __version__:^42}║")
    if __version_info__["is_prerelease"]:
        print(f"║{'⚠️ Pre-release версия':^42}║")
    print(f"╚{'═' * 42}╝\n")

    print("\nЗапуск интерфейса PolGen. Подождите...")
    check_and_install_models()  # Checking and installing models

    port = int(get_value_from_args("--port", DEFAULT_PORT))
    server = get_value_from_args("--server-name", DEFAULT_SERVER_NAME)

    for _ in range(MAX_PORT_ATTEMPTS):
        try:
            launch_gradio(server, port)
            break
        except OSError:
            print(f"Не удалось запустить на порту {port}, повторите попытку на порту {port - 1}...")
            port -= 1
        except Exception as error:
            print(f"Произошла ошибка при запуске Gradio: {error}")
            break
