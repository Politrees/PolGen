import os
import gc
import torch
import librosa
import numpy as np
import soundfile as sf
from scipy.io import wavfile
from pydub import AudioSegment
from fairseq import checkpoint_utils

from rvc.lib.algorithm.synthesizers import Synthesizer
from rvc.lib.my_utils import load_audio
from rvc.infer.config import Config
from rvc.infer.pipeline import VC

# Инициализация конфигурации
config = Config()


RVC_MODELS_DIR = os.path.join(os.getcwd(), "models")
EMBEDDERS_DIR = os.path.join(os.getcwd(), "rvc", "models", "embedders")
HUBERT_BASE_PATH = os.path.join(EMBEDDERS_DIR, "hubert_base.pt")

os.makedirs(EMBEDDERS_DIR, exist_ok=True)
os.makedirs(RVC_MODELS_DIR, exist_ok=True)


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
    sf.write(output_path, y, sr, format='FLAC')


# Конвертирует аудиофайл в выбранный пользователем формат.
def convert_to_user_format(input_path, output_path, output_format):
    # Загружаем аудиофайл
    audio = AudioSegment.from_file(input_path)

    # Сохраняем аудиофайл в выбранном формате
    audio.export(output_path, format=output_format)


# Выполняет инференс с использованием RVC
def rvc_infer(
    voice_model,
    input_path,
    output_dir,
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
):
    # Загружаем модель Hubert
    hubert_model = load_hubert(HUBERT_BASE_PATH)
    # Загружаем модель RVC и индекс
    model_path, index_path = load_rvc_model(voice_model)
    # Получаем конвертер голоса
    cpt, version, net_g, tgt_sr, vc = get_vc(model_path)
    # Загружаем аудиофайл
    audio = load_audio(input_path, 16000)

    # Формируем имя выходного файла
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    temp_output_path = os.path.join(output_dir, f"{base_name}_(Converted).flac")
    final_output_path = os.path.join(output_dir, f"{base_name}_(Converted).{output_format}")

    # Выполняем конвертацию голоса
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
    wavfile.write(temp_output_path, tgt_sr, audio_opt)

    # Конвертируем файл в стерео формат с использованием scipy
    convert_to_stereo(temp_output_path, temp_output_path)

    # Конвертируем файл в выбранный пользователем формат
    convert_to_user_format(temp_output_path, final_output_path, output_format)

    # Удаляем временный файл
    os.remove(temp_output_path)

    # Освобождаем память
    del hubert_model, cpt, net_g, vc
    gc.collect()
    torch.cuda.empty_cache()

    return final_output_path  # Возвращаем путь к выходному файлу


# Выполняет пакетное преобразование файлов с использованием rvc_infer
def rvc_infer_batch(
    voice_model,
    input_dir,
    output_dir,
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
):
    # Получаем список файлов в директории input_dir
    input_files = [
        f
        for f in os.listdir(input_dir)
        if f.endswith(
            (
                "wav",
                "mp3",
                "flac",
                "ogg",
                "opus",
                "m4a",
                "mp4",
                "aac",
                "alac",
                "wma",
                "aiff",
                "webm",
                "ac3",
            )
        )
    ]

    for input_file in input_files:
        # Формируем пути к входному и выходному файлам
        input_path = os.path.join(input_dir, input_file)

        print(f"Преобразование {input_file}...")

        # Выполняем преобразование для текущего файла
        rvc_infer(
            voice_model,
            input_path,
            output_dir,
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
        )
