"""UI-утилиты для Gradio интерфейса PolGen.

Содержит вспомогательные функции для обновления компонентов,
работы со списком моделей и переключения видимости элементов.
"""

import os
import re

import gradio as gr

from rvc.infer.infer import RVC_MODELS_DIR
from rvc.modules.edge_voices import edge_voices

OUTPUT_FORMAT = ["wav", "flac", "mp3", "ogg", "m4a"]


def update_edge_voices(selected_language):
    voices = edge_voices[selected_language]
    return gr.update(choices=voices, value=voices[0] if voices else None)


def get_folders():
    return sorted(
        (item for item in os.listdir(RVC_MODELS_DIR) if os.path.isdir(os.path.join(RVC_MODELS_DIR, item))),
        key=lambda x: [int(text) if text.isdigit() else text.lower() for text in re.split("([0-9]+)", x)],
    )


def update_models_list():
    return gr.update(choices=get_folders())


def process_file_upload(file):
    return file, gr.update(value=file)


def swap_visibility():
    return (
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(value=""),
        gr.update(value=None),
    )


def swap_buttons():
    return gr.update(visible=False), gr.update(visible=True)


def update_visible(autopitch):
    if autopitch:
        return gr.update(visible=True), gr.update(visible=False)
    return gr.update(visible=False), gr.update(visible=True)


def show_autotune(autotune):
    return gr.update(visible=autotune), gr.update(visible=autotune), gr.update(visible=autotune)


def output_message():
    return gr.Text(label="Сообщение вывода", interactive=False)