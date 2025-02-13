import asyncio
import gc
import os

import edge_tts
import gradio as gr
import torch
from fairseq import checkpoint_utils
from pydub import AudioSegment
from scipy.io import wavfile

from PolGen.rvc.infer.config import Config
from PolGen.rvc.infer.pipeline import VC
from PolGen.rvc.lib.algorithm.synthesizers import Synthesizer
from PolGen.rvc.lib.my_utils import load_audio

# Определяем пути к папкам и файлам (константы)
RVC_MODELS_DIR = os.path.join(os.getcwd(), "models", "RVC_models")
OUTPUT_DIR = os.path.join(os.getcwd(), "output", "RVC_output")
HUBERT_BASE_PATH = os.path.join(os.getcwd(), "PolGen", "rvc", "models", "embedders", "hubert_base.pt")

# Создаем папки, если их нет
os.makedirs(RVC_MODELS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Инициализация конфигурации
config = Config()


# Отображает прогресс выполнения задачи.
def display_progress(percent, message, progress=gr.Progress()):
    print(message)
    progress(percent, desc=message)


# Загружает модель RVC и индекс по имени модели.
def load_rvc_model(rvc_model):
    # Формируем путь к директории модели
    model_dir = os.path.join(RVC_MODELS_DIR, rvc_model)
    # Получаем список файлов в директории модели
    model_files = os.listdir(model_dir)

    # Находим файл модели с расширением .pth
    rvc_model_path = next((os.path.join(model_dir, f) for f in model_files if f.endswith(".pth")), None)
    # Находим файл индекса с расширением .index
    rvc_index_path = next((os.path.join(model_dir, f) for f in model_files if f.endswith(".index")), None)

    # Проверяем, существует ли файл модели
    if not rvc_model_path:
        raise ValueError(
            f"\033[91mОШИБКА!\033[0m Модель {rvc_model} не обнаружена. Возможно, вы допустили ошибку в названии или указали неверную ссылку при установке."
        )

    return rvc_model_path, rvc_index_path


# Загружает модель Hubert
def load_hubert(model_path):
    model, _, _ = checkpoint_utils.load_model_ensemble_and_task([model_path], suffix="")
    hubert = model[0].to(config.device).float()
    hubert.eval()
    return hubert


# Получает конвертер голоса
def get_vc(model_path):
    # Загружаем состояние модели из файла
    cpt = torch.load(model_path, map_location="cpu", weights_only=True)

    # Проверяем корректность формата модели
    if "config" not in cpt or "weight" not in cpt:
        raise ValueError(f"Некорректный формат для {model_path}. Используйте голосовую модель, обученную на RVC v2.")

    # Извлекаем параметры модели
    tgt_sr = cpt["config"][-1]
    cpt["config"][-3] = cpt["weight"]["emb_g.weight"].shape[0]
    pitch_guidance = cpt.get("f0", 1)
    version = cpt.get("version", "v1")
    # vocoder = cpt.get("vocoder", "HiFi-GAN") — на будущее
    input_dim = 768 if version == "v2" else 256

    # Инициализируем синтезатор
    net_g = Synthesizer(*cpt["config"], use_f0=pitch_guidance, input_dim=input_dim)

    # Удаляем ненужный слой
    del net_g.enc_q
    net_g.load_state_dict(cpt["weight"], strict=False)
    net_g = net_g.to(config.device).float()
    net_g.eval()

    # Инициализируем объект конвертера голоса
    vc = VC(tgt_sr, config)
    return cpt, version, net_g, tgt_sr, vc


# Конвертируем файл в стерео и выбранный пользователем формат
def convert_audio(input_audio, output_audio, output_format):
    # Загружаем аудиофайл
    audio = AudioSegment.from_file(input_audio)

    # Если аудио моно, конвертируем его в стерео
    if audio.channels == 1:
        audio = audio.set_channels(2)

    # Сохраняем аудиофайл в выбранном формате
    audio.export(output_audio, format=output_format)


# Синтезирует текст в речь с использованием edge_tts.
async def text_to_speech(text, voice, rate, output_path):
    rate = f"+{rate}%" if rate >= 0 else f"{rate}%"
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    await communicate.save(output_path)


# Выполнение инференса с использованием RVC
def rvc_infer(
    voice_rvc=None,
    voice_tts=None,
    input_audio=None,
    input_text=None,
    f0_method="rmvpe",
    hop_length=128,
    pitch=0,
    tts_rate=0,
    index_rate=0,
    volume_envelope=1,
    protect=0.5,
    f0_min=50,
    f0_max=1100,
    output_format="wav",
    use_tts=False,
):
    if not voice_rvc:
        raise ValueError("Выберите модель голоса для преобразования.")

    display_progress(0, "\n[⚙️] Запуск конвейера генерации...")
    if use_tts:
        if not input_text:
            raise ValueError("Введите необходимый текст в поле для ввода.")
        if not voice_tts:
            raise ValueError("Выберите язык и голос для синтеза речи.")

        display_progress(0.2, "[🎙️] Синтез речи...")
        input_audio = os.path.join(OUTPUT_DIR, "TTS_Voice.wav")
        asyncio.run(text_to_speech(input_text, voice_tts, tts_rate, input_audio))
    else:
        if not os.path.exists(input_audio):
            raise ValueError(
                f"Не удалось найти аудиофайл {input_audio}. Убедитесь, что файл загрузился или проверьте правильность пути к нему."
            )

    base_name = os.path.splitext(os.path.basename(input_audio))[0]
    output_audio = os.path.join(OUTPUT_DIR, f"{base_name}_(Converted).{output_format}")

    # Загружаем модель Hubert
    hubert_model = load_hubert(HUBERT_BASE_PATH)
    # Загружаем модель RVC и индекс
    model_path, index_path = load_rvc_model(voice_rvc)
    # Получаем конвертер голоса
    cpt, version, net_g, tgt_sr, vc = get_vc(model_path)
    # Загружаем аудиофайл
    audio = load_audio(input_audio, 16000)
    pitch_guidance = cpt.get("f0", 1)

    display_progress(0.5, f"[🌌] Преобразование аудио — {base_name}...")
    audio_opt = vc.pipeline(
        hubert_model,
        net_g,
        0,
        audio,
        pitch,
        f0_method,
        index_path,
        index_rate,
        pitch_guidance,
        volume_envelope,
        version,
        protect,
        hop_length,
        f0_file=None,
        f0_min=f0_min,
        f0_max=f0_max,
    )
    # Сохраняем результат в wav файл
    wavfile.write(output_audio, tgt_sr, audio_opt)

    # Конвертируем файл в стерео и выбранный пользователем формат
    display_progress(0.8, "[💫] Конвертация аудио в стерео...")
    convert_audio(output_audio, output_audio, output_format)

    display_progress(1.0, f"[✅] Преобразование завершено — {output_audio}")

    # Освобождаем память
    del hubert_model, cpt, net_g, vc
    gc.collect()
    torch.cuda.empty_cache()

    if use_tts:
        return output_audio, input_audio
    return output_audio
