import gradio as gr


def settings():
    with gr.Accordion("Настройки преобразования", open=False):
        with gr.Column(variant="panel"):
            with gr.Accordion("Стандартные настройки", open=False):
                with gr.Group():
                    with gr.Column(variant="panel"):
                        f0_method = gr.Dropdown(
                            value="rmvpe",
                            label="Метод выделения тона",
                            choices=["rmvpe+", "rmvpe", "fcpe", "crepe", "crepe-tiny"],
                            interactive=True,
                            visible=True,
                        )
                    with gr.Column(variant="panel"):
                        index_rate = gr.Slider(
                            minimum=0,
                            maximum=1,
                            step=0.01,
                            value=0,
                            label="Влияние индекса",
                            info="Влияние, оказываемое индексным файлом; Чем выше значение, тем больше влияние. Однако выбор более низких значений может помочь смягчить артефакты, присутствующие в аудио.",
                            interactive=True,
                            visible=True,
                        )
                        volume_envelope = gr.Slider(
                            minimum=0,
                            maximum=1,
                            step=0.01,
                            value=1,
                            label="Скорость смешивания RMS",
                            info="Заменить или смешать с огибающей громкости выходного сигнала. Чем ближе значение к 1, тем больше используется огибающая выходного сигнала.",
                            interactive=True,
                            visible=True,
                        )
                        protect = gr.Slider(
                            minimum=0,
                            maximum=0.5,
                            step=0.01,
                            value=0.5,
                            label="Защита согласных",
                            info="Защитить согласные и звуки дыхания, чтобы избежать электроакустических разрывов и артефактов. Максимальное значение параметра 0.5 обеспечивает полную защиту. Уменьшение этого значения может снизить защиту, но уменьшить эффект индексирования.",
                            interactive=True,
                            visible=True,
                        )

            with gr.Accordion("Дополнительные настройки", open=False):
                with gr.Group():
                    with gr.Column():
                        with gr.Row(variant="panel"):
                            with gr.Column():
                                stereo_sound = gr.Checkbox(
                                    value=False,
                                    label="Преобразовать в стерео",
                                    info="Преобразование моно звука в стерео",
                                    interactive=True,
                                    visible=True,
                                )
                                audio_upscaling = gr.Checkbox(
                                    value=False,
                                    label="Аудио-апскейл",
                                    info="Улучшение качества аудио (долгая обработка)",
                                    interactive=True,
                                    visible=True,
                                )
                            with gr.Column():
                                autotune = gr.Checkbox(
                                    value=False,
                                    label="АвтоТюн",
                                    info="Коррекция высоты тона",
                                    interactive=True,
                                    visible=True,
                                )
                                autotune_scale = gr.Dropdown(
                                    value="chromatic",
                                    label="Музыкальная гамма",
                                    choices=["chromatic", "major", "minor", "pentatonic_major", "pentatonic_minor"],
                                    interactive=True,
                                    visible=True,
                                )
                                autotune_strength = gr.Slider(
                                    minimum=0,
                                    maximum=1,
                                    step=0.1,
                                    value=1,
                                    label="Сила коррекции автотюна",
                                    interactive=True,
                                    visible=False,
                                )
                        with gr.Row(variant="panel"):
                            f0_min = gr.Slider(
                                minimum=1,
                                maximum=120,
                                step=1,
                                value=50,
                                label="Минимальный диапазон тона",
                                info="Определяет нижнюю границу диапазона тона, который алгоритм будет использовать для определения основной частоты (F0) в аудиосигнале.",
                                interactive=True,
                                visible=True,
                            )
                            f0_max = gr.Slider(
                                minimum=380,
                                maximum=16000,
                                step=1,
                                value=1100,
                                label="Максимальный диапазон тона",
                                info="Определяет верхнюю границу диапазона тона, который алгоритм будет использовать для определения основной частоты (F0) в аудиосигнале.",
                                interactive=True,
                                visible=True,
                            )

    return f0_method, index_rate, volume_envelope, protect, stereo_sound, audio_upscaling, autotune, autotune_scale, autotune_strength, f0_min, f0_max
