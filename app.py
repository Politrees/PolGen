import os
import sys

import gradio as gr

from tabs.edge_tts.edge_tts import edge_tts_tab
from tabs.inference.inference_batch import inference_batch_tab
from tabs.inference.inference_single import inference_single_tab
from tabs.install.install import (
    files_upload,
    install_hubert_tab,
    output_message,
    url_download,
    zip_upload,
)
from tabs.uvr.uvr import uvr_tab
from tabs.welcome import welcome_tab

DEFAULT_PORT = 4000
MAX_PORT_ATTEMPTS = 10

output_message_component = output_message()


with gr.Blocks(
    title="PolGen - Politrees",
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

    with gr.Tab("Преобразование голоса"):
        with gr.Tab("Одиночное преобразование"):
            inference_single_tab()
        with gr.Tab("Пакетное преобразование"):
            inference_batch_tab()

    with gr.Tab("Преобразование текста в речь"):
        edge_tts_tab()

    with gr.Tab("UVR"):
        uvr_tab()

    with gr.Tab("Загрузка моделей"):
        with gr.Tab("Загрузка RVC моделей"):
            url_download(output_message_component)
            zip_upload(output_message_component)
            files_upload(output_message_component)
            output_message_component.render()
        with gr.Tab("Загрузка HuBERT моделей"):
            install_hubert_tab()


def launch(port):
    PolGen.launch(
        favicon_path=os.path.join(os.getcwd(), "assets", "logo.ico"),
        share="--share" in sys.argv,
        inbrowser="--open" in sys.argv,
        server_port=port,
    )


def get_port_from_args():
    if "--port" in sys.argv:
        port_index = sys.argv.index("--port") + 1
        if port_index < len(sys.argv):
            return int(sys.argv[port_index])
    return DEFAULT_PORT


if __name__ == "__main__":
    port = get_port_from_args()
    for _ in range(MAX_PORT_ATTEMPTS):
        try:
            launch(port)
            break
        except OSError:
            print(
                f"Не удалось запустить на порту {port}, повторяем попытку на порту {port - 1}..."
            )
            port -= 1
        except Exception as error:
            print(f"Произошла ошибка при запуске Gradio: {error}")
            break
