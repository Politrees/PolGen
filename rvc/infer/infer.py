import os
import gc
import torch
import librosa
import numpy as np
import soundfile as sf
from fairseq import checkpoint_utils
from pydub import AudioSegment
from scipy.io import wavfile
import asyncio
import edge_tts
import gradio as gr

from rvc.lib.algorithm.synthesizers import Synthesizer
from rvc.lib.my_utils import load_audio
from rvc.infer.config import Config
from rvc.infer.pipeline import VC

# Инициализация конфигурации
config = Config()

# Определение путей к директориям с моделями
RVC_MODELS_DIR = os.path.join(os.getcwd(), "models")
HUBERT_PATH = os.path.join(os.getcwd(), "rvc", "models", "embedders", "hubert_base.pt")
OUTPUT_DIR = os.path.join(os.getcwd(), "output", "converted_audio")


# Загружает модель RVC и индекс по имени модели.
def load_rvc_model(rvc_model):
    # Формируем путь к директории модели
    model_dir = os.path.join(RVC_MODELS_DIR, rvc_model)
    # Получаем список файлов в директории модели
    model_files = os.listdir(model_dir)

    # Находим файл модели с расширением .pth
    rvc_model_path = next(
        (os.path.join(model_dir, f) for f in model_files if f.endswith(".pth")), None
    )
    # Находим файл индекса с расширением .index
    rvc_index_path = next(
        (os.path.join(model_dir, f) for f in model_files if f.endswith(".index")), None
    )

    # Проверяем, существует ли файл модели
    if not rvc_model_path:
        raise ValueError(
            f"Модель {rvc_model} не существует. Возможно, вы ввели имя неправильно."
        )

    return rvc_model_path, rvc_index_path


# Загружает модель Hubert
def load_hubert(model_path):
    # Загружаем модель Hubert и её конфигурацию
    models, saved_cfg, task = checkpoint_utils.load_model_ensemble_and_task(
        [model_path], suffix=""
    )
    # Перемещаем модель на устройство (GPU или CPU)
    hubert = models[0].to(config.device)
    # Преобразуем модель в полуточность (half) или полную точность (float)
    hubert = hubert.half() if config.is_half else hubert.float()
    # Устанавливаем модель в режим оценки (инференс)
    hubert.eval()
    return hubert


# Получает конвертер голоса
def get_vc(model_path):
    # Загружаем состояние модели из файла
    cpt = torch.load(model_path, map_location="cpu", weights_only=True)

    # Проверяем корректность формата модели
    if "config" not in cpt or "weight" not in cpt:
        raise ValueError(
            f"Некорректный формат для {model_path}. Используйте голосовую модель, обученную с RVC v2."
        )

    # Извлекаем параметры модели
    tgt_sr = cpt["config"][-1]
    cpt["config"][-3] = cpt["weight"]["emb_g.weight"].shape[0]
    pitch_guidance = cpt.get("f0", 1)
    version = cpt.get("version", "v1")
    input_dim = 768 if version == "v2" else 256

    # Инициализируем синтезатор
    net_g = Synthesizer(
        *cpt["config"],
        use_f0=pitch_guidance,
        input_dim=input_dim,
        is_half=config.is_half,
    )

    # Удаляем ненужный слой
    del net_g.enc_q
    print(net_g.load_state_dict(cpt["weight"], strict=False))
    # Устанавливаем модель в режим оценки и перемещаем на устройство
    net_g.eval().to(config.device)
    net_g = net_g.half() if config.is_half else net_g.float()

    # Инициализируем объект конвертера голоса
    vc = VC(tgt_sr, config)
    return cpt, version, net_g, tgt_sr, vc


# Функция для синтеза речи с помощью Edge TTS
async def text_to_speech(text, voice, output_path):
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(output_path)


# Конвертирует аудиофайл в стерео формат.
def convert_to_stereo(input_path, output_path):
    # Загружаем аудиофайл
    y, sr = sf.read(input_path)

    # Если аудио моно, дублируем канал
    if len(y.shape) == 1:
        y = np.vstack([y, y]).T
    elif len(y.shape) > 2:
        y = y[:, :2]

    # Сохраняем результат в файл с форматом .flac
    sf.write(output_path, y, sr, format="FLAC")


# Конвертирует аудиофайл в выбранный пользователем формат.
def convert_to_user_format(input_path, base_name, output_format):
    # Загружаем аудиофайл
    audio = AudioSegment.from_file(input_path)
    
    output_name = os.path.splitext(os.path.basename(base_name))[0]
    output_path = os.path.join(OUTPUT_DIR, f"{output_name}_(Converted).{output_format}")

    # Сохраняем аудиофайл в выбранном формате
    audio.export(output_path, format=output_format)
    return output_path


# Выполняет инференс с использованием RVC
def rvc_infer(
    voice_model,
    input_path_or_text,
    index_rate,
    pitch,
    f0_method,
    filter_radius,
    volume_envelope,
    protect,
    hop_length,
    f0_min,
    f0_max,
    output_format,
    is_tts=False,
    voice=None,
    progress=gr.Progress(track_tqdm=True),
):
    progress(0, "Запуск конвейера генерации...")

    # Загружаем модель Hubert
    progress(0.1, "Загрузка Hubert модели...")
    hubert_model = load_hubert(HUBERT_PATH)

    # Загружаем модель RVC и индекс
    progress(0.2, "Загрузка RVC модели...")
    model_path, index_path = load_rvc_model(voice_model)

    # Получаем конвертер голоса
    progress(0.3, "Получение конвертера голоса...")
    cpt, version, net_g, tgt_sr, vc = get_vc(model_path)

    if is_tts:
        # Синтез речи с помощью Edge TTS
        progress(0.4, "Синтез речи...")
        tts_voice_path = os.path.join(OUTPUT_DIR, "TTS_Voice.wav")
        asyncio.run(text_to_speech(input_path_or_text, voice, tts_voice_path))
        output_path = os.path.join(OUTPUT_DIR, f"TTS_Voice_Converted.wav")
        input_path = tts_voice_path
    else:
        output_path = os.path.join(OUTPUT_DIR, f"Voice_Converted.wav")
        input_path = input_path_or_text

    # Загружаем аудиофайл
    progress(0.5, "Загрузка аудиофайла...")
    audio = load_audio(input_path, 16000)

    # Выполняем конвертацию голоса
    progress(0.6, "Преобразование голоса...")
    audio_opt = vc.pipeline(
        hubert_model,
        net_g,
        0,
        audio,
        input_path,
        pitch,
        f0_method,
        index_path,
        index_rate,
        filter_radius,
        tgt_sr,
        volume_envelope,
        version,
        protect,
        hop_length,
        f0_min,
        f0_max,
        f0_file=None,
    )

    # Сохраняем результат в файл
    progress(0.7, "Сохранение результата...")
    wavfile.write(output_path, tgt_sr, audio_opt)

    # Конвертируем файл в стерео и в выбранный формат
    progress(0.8, "Подготовка аудио выводу...")
    convert_to_stereo(output_path, output_path)
    final_output_path = convert_to_user_format(output_path, input_path, output_format)

    # Удаляем временный файл
    if os.path.exists(output_path):
        os.remove(output_path)

    # Освобождаем память
    progress(0.9, "Освобождение памяти...")
    del hubert_model, cpt, net_g, vc
    gc.collect()
    torch.cuda.empty_cache()

    progress(1, "Готово!")
    return tts_voice_path if is_tts else None, final_output_path
