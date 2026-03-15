import gradio as gr

from rvc.infer.infer import rvc_edgetts_infer, rvc_infer
from rvc.modules.edge_voices import edge_voices
from gradio_ui.components.modules import (
    OUTPUT_FORMAT,
    get_folders,
    process_file_upload,
    show_autotune,
    swap_buttons,
    swap_visibility,
    update_edge_voices,
    update_models_list,
    update_visible,
)
from gradio_ui.components.settings import settings


def inference_tab():
    with gr.Row():
        with gr.Column(scale=1, variant="panel"):
            with gr.Group():
                rvc_model = gr.Dropdown(
                    label="Голосовые модели:",
                    choices=get_folders(),
                    interactive=True,
                    visible=True,
                )
                ref_btn = gr.Button(
                    value="Обновить список моделей",
                    variant="primary",
                    interactive=True,
                    visible=True,
                )
            with gr.Group():
                autopitch = gr.Checkbox(
                    value=False,
                    label="Автоматическое определение высоты тона",
                    interactive=True,
                    visible=True,
                )
                autopitch_threshold = gr.Radio(
                    value=155.0,
                    choices=[("Мужская модель", 155.0), ("Женская модель", 255.0)],
                    show_label=False,
                    interactive=True,
                    visible=False,
                )
                rvc_pitch = gr.Slider(
                    minimum=-24,
                    maximum=24,
                    step=1,
                    value=0,
                    label="Регулировка высоты тона",
                    info="-24 — Мужская модель | 24 — Женская модель",
                    interactive=True,
                    visible=True,
                )

        with gr.Column(scale=2, variant="panel"):
            with gr.Column() as upload_file:
                local_file = gr.Audio(
                    label="Аудио",
                    type="filepath",
                    show_download_button=False,
                    show_share_button=False,
                    interactive=True,
                    visible=True,
                )

            with gr.Column(visible=False) as enter_local_file:
                song_input = gr.Text(
                    label="Путь к файлу:",
                    info="Введите полный путь к файлу.",
                    interactive=True,
                    visible=True,
                )

            with gr.Column():
                show_upload_button = gr.Button(
                    value="Загрузить файл с устройства",
                    interactive=True,
                    visible=False,
                )
                show_enter_button = gr.Button(
                    value="Ввести путь к файлу",
                    interactive=True,
                    visible=True,
                )

    with gr.Group(), gr.Row(equal_height=True):
        generate_btn = gr.Button(
            value="Генерировать",
            variant="primary",
            interactive=True,
            visible=True,
            scale=2,
        )
        converted_voice = gr.Audio(
            label="Преобразованный голос",
            show_download_button=True,
            show_share_button=False,
            interactive=False,
            visible=True,
            scale=9,
        )
        with gr.Column(min_width=160):
            output_format = gr.Dropdown(
                value="mp3",
                label="Формат файла",
                choices=OUTPUT_FORMAT,
                interactive=True,
                visible=True,
            )

    # Компонент настроек
    (
        f0_method,
        index_rate,
        volume_envelope,
        protect,
        stereo_sound,
        audio_upscaling,
        autotune,
        autotune_tonic,
        autotune_scale,
        autotune_strength,
        f0_min,
        f0_max,
    ) = settings()

    # Загрузка файлов
    local_file.input(process_file_upload, inputs=[local_file], outputs=[song_input, local_file])

    # Обновление кнопок
    show_upload_button.click(swap_visibility, outputs=[upload_file, enter_local_file, song_input, local_file])
    show_enter_button.click(swap_visibility, outputs=[enter_local_file, upload_file, song_input, local_file])
    show_upload_button.click(swap_buttons, outputs=[show_upload_button, show_enter_button])
    show_enter_button.click(swap_buttons, outputs=[show_enter_button, show_upload_button])

    # Обновление метода регулировки высоты тона
    autopitch.change(update_visible, inputs=autopitch, outputs=[autopitch_threshold, rvc_pitch])

    # Показать параметры автотюна
    autotune.change(show_autotune, inputs=autotune, outputs=[autotune_tonic, autotune_scale, autotune_strength])

    # Обновление списка моделей
    ref_btn.click(update_models_list, None, outputs=rvc_model)

    # Запуск процесса преобразования
    generate_btn.click(
        rvc_infer,
        inputs=[
            rvc_model,
            song_input,
            f0_method,
            f0_min,
            f0_max,
            rvc_pitch,
            protect,
            index_rate,
            volume_envelope,
            autopitch,
            autopitch_threshold,
            autotune,
            autotune_tonic,
            autotune_scale,
            autotune_strength,
            audio_upscaling,
            stereo_sound,
            output_format,
        ],
        outputs=[converted_voice],
    )


def edge_tts_tab():
    with gr.Row():
        with gr.Column(variant="panel", scale=1):
            with gr.Group():
                rvc_model = gr.Dropdown(
                    label="Голосовые модели:",
                    choices=get_folders(),
                    interactive=True,
                    visible=True,
                )
                ref_btn = gr.Button(
                    value="Обновить список моделей",
                    variant="primary",
                    interactive=True,
                    visible=True,
                )
            with gr.Group():
                language = gr.Dropdown(
                    label="Язык",
                    choices=list(edge_voices.keys()),
                    interactive=True,
                    visible=True,
                )
                tts_voice = gr.Dropdown(
                    value="en-GB-SoniaNeural",
                    label="Голос",
                    choices=["en-GB-SoniaNeural", "en-GB-RyanNeural"],
                    interactive=True,
                    visible=True,
                )
        with gr.Column(variant="panel", scale=2):
            with gr.Column(), gr.Group():
                autopitch = gr.Checkbox(
                    value=False,
                    label="Автоматическое определение высоты тона",
                    interactive=True,
                    visible=True,
                )
                autopitch_threshold = gr.Radio(
                    value=155.0,
                    choices=[("Мужская модель", 155.0), ("Женская модель", 255.0)],
                    show_label=False,
                    interactive=True,
                    visible=False,
                )
                rvc_pitch = gr.Slider(
                    minimum=-24,
                    maximum=24,
                    step=1,
                    value=0,
                    label="Регулировка высоты тона",
                    info="-24 — Мужская модель || 24 — Женская модель",
                    interactive=True,
                    visible=True,
                )
            synth_voice = gr.Audio(
                label="Синтзированный TTS голос",
                show_download_button=True,
                show_share_button=False,
                interactive=False,
                visible=True,
            )

    with gr.Accordion("Настройки синтеза речи", open=False), gr.Group(), gr.Row():
        tts_pitch = gr.Slider(
            minimum=-100,
            maximum=100,
            step=1,
            value=0,
            label="Регулировка высоты тона TTS",
            info="-100 - мужской голос || 100 - женский голос",
            interactive=True,
            visible=True,
        )
        tts_volume = gr.Slider(
            minimum=-100,
            maximum=100,
            step=1,
            value=0,
            label="Громкость речи",
            info="Громкость воспроизведения синтеза речи",
            interactive=True,
            visible=True,
        )
        tts_rate = gr.Slider(
            minimum=-100,
            maximum=100,
            step=1,
            value=0,
            label="Скорость речи",
            info="Скорость воспроизведения синтеза речи",
            interactive=True,
            visible=True,
        )

    tts_text = gr.Textbox(label="Введите текст", lines=5)

    with gr.Group(), gr.Row(equal_height=True):
        generate_btn = gr.Button(
            value="Генерировать",
            variant="primary",
            interactive=True,
            visible=True,
            scale=2,
        )
        converted_synth_voice = gr.Audio(
            label="Преобразованный TTS голос",
            show_download_button=True,
            show_share_button=False,
            interactive=False,
            visible=True,
            scale=9,
        )
        with gr.Column(min_width=160):
            output_format = gr.Dropdown(
                value="mp3",
                label="Формат файла",
                choices=OUTPUT_FORMAT,
                interactive=True,
                visible=True,
            )

    # Компонент настроек
    (
        f0_method,
        index_rate,
        volume_envelope,
        protect,
        stereo_sound,
        audio_upscaling,
        autotune,
        autotune_tonic,
        autotune_scale,
        autotune_strength,
        f0_min,
        f0_max,
    ) = settings()

    # Обновление списка TTS-голосов
    language.change(update_edge_voices, inputs=language, outputs=tts_voice)

    # Обновление метода регулировки высоты тона
    autopitch.change(update_visible, inputs=autopitch, outputs=[autopitch_threshold, rvc_pitch])

    # Показать параметры автотюна
    autotune.change(show_autotune, inputs=autotune, outputs=[autotune_tonic, autotune_scale, autotune_strength])

    # Обновление списка моделей
    ref_btn.click(update_models_list, None, outputs=rvc_model)

    # Запуск процесса преобразования
    generate_btn.click(
        rvc_edgetts_infer,
        inputs=[
            rvc_model,
            f0_method,
            f0_min,
            f0_max,
            rvc_pitch,
            protect,
            index_rate,
            volume_envelope,
            autopitch,
            autopitch_threshold,
            autotune,
            autotune_tonic,
            autotune_scale,
            autotune_strength,
            stereo_sound,
            output_format,
            tts_voice,
            tts_text,
            tts_rate,
            tts_volume,
            tts_pitch,
            audio_upscaling,
        ],
        outputs=[synth_voice, converted_synth_voice],
    )
