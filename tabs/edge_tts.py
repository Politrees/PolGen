import os
import librosa
import asyncio
import edge_tts
import numpy as np
import gradio as gr
import soundfile as sf

from rvc.infer.infer import rvc_infer


RVC_MODELS_DIR = os.path.join(os.getcwd(), "models")
OUTPUT_DIR = os.path.join(os.getcwd(), "output", "converted_audio")


edge_voices = {
    "Английский (Великобритания)": ["en-GB-SoniaNeural", "en-GB-RyanNeural"],
    "Английский (США)": ["en-US-JennyNeural", "en-US-GuyNeural"],
    "Арабский (Египет)": ["ar-EG-SalmaNeural", "ar-EG-ShakirNeural"],
    "Арабский (Саудовская Аравия)": ["ar-SA-HamedNeural", "ar-SA-ZariyahNeural"],
    "Бенгальский (Бангладеш)": ["bn-BD-RubaiyatNeural", "bn-BD-KajalNeural"],
    "Венгерский": ["hu-HU-TamasNeural", "hu-HU-NoemiNeural"],
    "Вьетнамский": ["vi-VN-HoaiMyNeural", "vi-VN-HuongNeural"],
    "Греческий": ["el-GR-AthinaNeural", "el-GR-NestorasNeural"],
    "Датский": ["da-DK-PernilleNeural", "da-DK-MadsNeural"],
    "Иврит": ["he-IL-AvriNeural", "he-IL-HilaNeural"],
    "Испанский (Испания)": ["es-ES-ElviraNeural", "es-ES-AlvaroNeural"],
    "Испанский (Мексика)": ["es-MX-DaliaNeural", "es-MX-JorgeNeural"],
    "Итальянский": ["it-IT-ElsaNeural", "it-IT-DiegoNeural"],
    "Китайский (упрощенный)": ["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural"],
    "Корейский": ["ko-KR-SunHiNeural", "ko-KR-InJoonNeural"],
    "Немецкий": ["de-DE-KatjaNeural", "de-DE-ConradNeural"],
    "Нидерландский": ["nl-NL-ColetteNeural", "nl-NL-FennaNeural"],
    "Норвежский": ["nb-NO-PernilleNeural", "nb-NO-FinnNeural"],
    "Польский": ["pl-PL-MajaNeural", "pl-PL-JacekNeural"],
    "Португальский (Бразилия)": ["pt-BR-FranciscaNeural", "pt-BR-AntonioNeural"],
    "Португальский (Португалия)": ["pt-PT-RaquelNeural", "pt-PT-DuarteNeural"],
    "Румынский": ["ro-RO-EmilNeural", "ro-RO-AndreiNeural"],
    "Русский": ["ru-RU-SvetlanaNeural", "ru-RU-DmitryNeural"],
    "Тагальский": ["tl-PH-AngeloNeural", "tl-PH-TessaNeural"],
    "Тамильский": ["ta-IN-ValluvarNeural", "ta-IN-KannanNeural"],
    "Тайский": ["th-TH-PremwadeeNeural", "th-TH-NiwatNeural"],
    "Турецкий": ["tr-TR-AhmetNeural", "tr-TR-EmelNeural"],
    "Украинский": ["uk-UA-OstapNeural", "uk-UA-PolinaNeural"],
    "Филиппинский": ["fil-PH-AngeloNeural", "fil-PH-TessaNeural"],
    "Финский": ["fi-FI-NooraNeural", "fi-FI-SelmaNeural"],
    "Французский (Канада)": ["fr-CA-SylvieNeural", "fr-CA-AntoineNeural"],
    "Французский (Франция)": ["fr-FR-DeniseNeural", "fr-FR-HenriNeural"],
    "Чешский": ["cs-CZ-VlastaNeural", "cs-CZ-AntoninNeural"],
    "Шведский": ["sv-SE-HilleviNeural", "sv-SE-MattiasNeural"],
    "Японский": ["ja-JP-NanamiNeural", "ja-JP-KeitaNeural"],
}


def update_edge_voices(selected_language):
    return gr.update(choices=edge_voices[selected_language])


# Синтезирует текст в речь с использованием edge_tts.
async def text_to_speech(text, voice, output_path):
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(output_path)


# Конвертирует аудиофайл в стерео формат.
def convert_to_stereo(input_path, output_path):
    y, sr = librosa.load(input_path, sr=None, mono=False)
    if y.ndim == 1:
        y = np.vstack([y, y])
    elif y.ndim > 2:
        y = y[:2, :]
    sf.write(output_path, y.T, sr, format="WAV")


# Основной конвейер для синтеза речи и преобразования голоса.
def edge_tts_pipeline(
    text,
    voice_model,
    voice,
    pitch,
    index_rate=0.5,
    filter_radius=3,
    volume_envelope=0.25,
    f0_method="rmvpe+",
    hop_length=128,
    protect=0.33,
    output_format="mp3",
    f0_min=50,
    f0_max=1100,
    progress=gr.Progress(track_tqdm=True),
):
    if not text:
        raise ValueError("Введите необходимый текст в поле для ввода.")
    if not voice:
        raise ValueError("Выберите язык и голос для синтеза речи.")
    if not voice_model:
        raise ValueError("Выберите модель голоса для преобразования.")

    progress(0, "Запуск конвейера генерации...")
    tts_voice_path = os.path.join(OUTPUT_DIR, "TTS_Voice.wav")
    tts_voice_convert_path = os.path.join(
        OUTPUT_DIR, f"TTS_Voice_Converted.{output_format}"
    )

    progress(0.25, "Синтез речи...")
    asyncio.run(text_to_speech(text, voice, tts_voice_path))

    progress(0.5, "Преобразование речи...")
    rvc_infer(
        voice_model,
        tts_voice_path,
        tts_voice_convert_path,
        index_rate,
        pitch,
        f0_method,
        filter_radius,
        volume_envelope,
        protect,
        hop_length,
        f0_min,
        f0_max,
    )

    progress(0.75, f"Конвертация речи в стерео формат...")
    convert_to_stereo(tts_voice_convert_path, tts_voice_convert_path)

    return tts_voice_convert_path, tts_voice_path


# Возвращает список папок, находящихся в директории моделей
def get_folders(models_dir):
    return [
        item
        for item in os.listdir(models_dir)
        if os.path.isdir(os.path.join(models_dir, item))
    ]


# Обновляет список моделей для отображения в интерфейсе Gradio
def update_models_list():
    models_folders = get_folders(RVC_MODELS_DIR)
    return gr.update(choices=models_folders)


def show_hop_slider(pitch_detection_algo):
    if pitch_detection_algo in ["mangio-crepe"]:
        return gr.update(visible=True)
    else:
        return gr.update(visible=False)


def edge_tts_tab():
    with gr.Row(equal_height=False):
        with gr.Column(variant="panel", scale=2):
            with gr.Group():
                rvc_model = gr.Dropdown(get_folders(RVC_MODELS_DIR), label="Модели голоса")
                ref_btn = gr.Button("Обновить список моделей", variant="primary")
            with gr.Group():
                pitch = gr.Slider(
                    value=0,
                    step=1,
                    minimum=-24,
                    maximum=24,
                    label="Регулировка тона",
                    info="-24 - мужской голос || 24 - женский голос",
                )

        with gr.Column(variant="panel", scale=3):
            tts_voice = gr.Audio(label="TTS голос")

        with gr.Column(variant="panel", scale=2):
            with gr.Group():
                language = gr.Dropdown(list(edge_voices.keys()), label="Язык")
                voice = gr.Dropdown([], label="Голос")
                language.change(update_edge_voices, inputs=language, outputs=voice)

    text_input = gr.Textbox(label="Введите текст", lines=5)

    with gr.Group():
        with gr.Row(equal_height=True):
            generate_btn = gr.Button("Генерировать", variant="primary", scale=2)
            converted_tts_voice = gr.Audio(label="Преобразованный голос", scale=9)
            output_format = gr.Dropdown(
                ["wav", "flac", "mp3"],
                value="mp3",
                label="Формат файла",
                scale=1,
            )

    with gr.Accordion("Настройки преобразования", open=False):
        with gr.Accordion("Стандартные настройки", open=False):
            with gr.Group():
                with gr.Column(variant="panel"):
                    f0_method = gr.Dropdown(
                        ["rmvpe+", "fcpe", "mangio-crepe"],
                        value="rmvpe+",
                        label="Метод выделения тона",
                        allow_custom_value=False,
                        filterable=False,
                    )
                    hop_length = gr.Slider(
                        value=128,
                        step=8,
                        minimum=8,
                        maximum=512,
                        label="Длина шага",
                        info="Меньшие значения приводят к более длительным преобразованиям, что увеличивает риск появления артефактов в голосе, однако при этом достигается более точная передача тона.",
                        visible=False,
                    )
                    f0_method.change(
                        show_hop_slider, inputs=f0_method, outputs=hop_length
                    )
                with gr.Column(variant="panel"):
                    index_rate = gr.Slider(
                        value=0,
                        step=0.1,
                        minimum=0,
                        maximum=1,
                        label="Влияние индекса",
                        info="Влияние, оказываемое индексным файлом; Чем выше значение, тем больше влияние. Однако выбор более низких значений может помочь смягчить артефакты, присутствующие в аудио.",
                    )
                    filter_radius = gr.Slider(
                        value=3,
                        step=1,
                        minimum=0,
                        maximum=7,
                        label="Радиус фильтра",
                        info="Если это число больше или равно трем, использование медианной фильтрации по собранным результатам тона может привести к снижению дыхания..",
                    )
                    volume_envelope = gr.Slider(
                        value=0.25,
                        step=0.01,
                        minimum=0,
                        maximum=1,
                        label="Скорость смешивания RMS",
                        info="Заменить или смешать с огибающей громкости выходного сигнала. Чем ближе значение к 1, тем больше используется огибающая выходного сигнала.",
                    )
                    protect = gr.Slider(
                        value=0.33,
                        step=0.01,
                        minimum=0,
                        maximum=0.5,
                        label="Защита согласных",
                        info="Защитить согласные и звуки дыхания, чтобы избежать электроакустических разрывов и артефактов. Максимальное значение параметра 0.5 обеспечивает полную защиту. Уменьшение этого значения может снизить защиту, но уменьшить эффект индексирования.",
                    )

        with gr.Accordion("Расширенные настройки", open=False):
            with gr.Column(variant="panel"):
                with gr.Row():
                    f0_min = gr.Slider(
                        value=50,
                        step=1,
                        minimum=1,
                        maximum=120,
                        label="Минимальный диапазон тона",
                        info="Определяет нижнюю границу диапазона тона, который алгоритм будет использовать для определения основной частоты (F0) в аудиосигнале.",
                    )
                    f0_max = gr.Slider(
                        value=1100,
                        step=1,
                        minimum=380,
                        maximum=16000,
                        label="Максимальный диапазон тона",
                        info="Определяет верхнюю границу диапазона тона, который алгоритм будет использовать для определения основной частоты (F0) в аудиосигнале.",
                    )

    ref_btn.click(update_models_list, None, outputs=rvc_model)
    generate_btn.click(
        edge_tts_pipeline,
        inputs=[
            text_input,
            rvc_model,
            voice,
            pitch,
            index_rate,
            filter_radius,
            volume_envelope,
            f0_method,
            hop_length,
            protect,
            output_format,
            f0_min,
            f0_max,
        ],
        outputs=[converted_tts_voice, tts_voice],
    )
