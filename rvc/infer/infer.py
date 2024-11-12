import gc
import os
import librosa
import numpy as np
import soundfile as sf
import torch
import asyncio
import gradio as gr
from fairseq import checkpoint_utils
from pydub import AudioSegment
from scipy.io import wavfile
import random

from rvc.infer.config import Config
from rvc.infer.pipeline import VC
from rvc.lib.algorithm.synthesizers import Synthesizer
from rvc.lib.my_utils import load_audio

config = Config()

RVC_MODELS_DIR = os.path.join(os.getcwd(), "models")
EMBEDDERS_DIR = os.path.join(os.getcwd(), "rvc", "models", "embedders")
HUBERT_BASE_PATH = os.path.join(EMBEDDERS_DIR, "hubert_base.pt")
OUTPUT_DIRS = {
    "single": os.path.join(os.getcwd(), "output", "converted_audio", "single"),
    "batch": os.path.join(os.getcwd(), "output", "converted_audio", "batch"),
    "tts": os.path.join(os.getcwd(), "output", "converted_audio", "tts")
}

for dir_path in OUTPUT_DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

def create_unique_output_dir(base_dir, prefix=""):
    counter = 1
    while True:
        unique_dir = os.path.join(base_dir, f"{prefix}{counter}")
        if not os.path.exists(unique_dir):
            os.makedirs(unique_dir)
            return unique_dir
        counter += 1

def load_rvc_model(rvc_model):
    model_dir = os.path.join(RVC_MODELS_DIR, rvc_model)
    model_files = os.listdir(model_dir)
    rvc_model_path = next((os.path.join(model_dir, f) for f in model_files if f.endswith(".pth")), None)
    rvc_index_path = next((os.path.join(model_dir, f) for f in model_files if f.endswith(".index")), None)
    if not rvc_model_path:
        raise ValueError(f"Модель {rvc_model} не найдена.")
    return rvc_model_path, rvc_index_path

def load_hubert(model_path):
    models, _, _ = checkpoint_utils.load_model_ensemble_and_task([model_path])
    hubert = models[0].to(config.device)
    hubert.eval().half() if config.is_half else hubert.float()
    return hubert

def get_vc(model_path):
    cpt = torch.load(model_path, map_location="cpu")
    tgt_sr = cpt["config"][-1]
    cpt["config"][-3] = cpt["weight"]["emb_g.weight"].shape[0]
    net_g = Synthesizer(
        *cpt["config"],
        use_f0=cpt.get("f0", 1),
        input_dim=768 if cpt.get("version") == "v2" else 256,
        is_half=config.is_half,
    )
    del net_g.enc_q
    net_g.eval().to(config.device).half() if config.is_half else net_g.float()
    return cpt, cpt.get("version", "v1"), net_g, tgt_sr, VC(tgt_sr, config)

def convert_audio(input_path, output_path, stereo=True, output_format="flac"):
    audio, sr = sf.read(input_path)
    if stereo and len(audio.shape) == 1:
        audio = np.vstack([audio, audio]).T
    sf.write(output_path, audio, sr, format=output_format)

async def text_to_speech(text, voice, output_path):
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(output_path)

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
    progress=None,
):
    progress(0.1, "Загрузка модели Hubert...")
    hubert_model = load_hubert(HUBERT_BASE_PATH)

    progress(0.4, "Загрузка RVC модели...")
    model_path, index_path = load_rvc_model(voice_model)
    cpt, version, net_g, tgt_sr, vc = get_vc(model_path)
    audio = load_audio(input_path, 16000)

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    temp_output_path = os.path.join(output_dir, f"{base_name}_(Converted).flac")
    final_output_path = os.path.join(output_dir, f"{base_name}_(Converted).{output_format}")

    progress(0.5, "Выполнение конверсии голоса...")
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
        None,
    )
    wavfile.write(temp_output_path, tgt_sr, audio_opt)

    progress(0.8, "Конвертация в стерео и финальный формат...")
    convert_audio(temp_output_path, final_output_path, stereo=True, output_format=output_format)
    os.remove(temp_output_path)

    # Очистка памяти
    del hubert_model, cpt, net_g, vc
    gc.collect()
    torch.cuda.empty_cache()

    progress(1, "Обработка завершена.")
    return final_output_path


def voice_pipeline_single(uploaded_file, voice_model, *args, **kwargs):
    progress = kwargs.pop('progress', None)
    output_dir = create_unique_output_dir(OUTPUT_DIRS["single"], prefix=os.path.splitext(os.path.basename(uploaded_file))[0])
    return rvc_infer(voice_model, uploaded_file, output_dir, *args, **kwargs, progress=progress)

def voice_pipeline_batch(uploaded_files, voice_model, *args, **kwargs):
    progress = kwargs.pop('progress', None)
    output_dir = create_unique_output_dir(OUTPUT_DIRS["batch"], prefix="batch_")
    completed_files = []
    num_files = len(uploaded_files)

    for i, input_file in enumerate(uploaded_files):
        progress(i / num_files, f"Преобразование файла {input_file}...")
        output_path = rvc_infer(voice_model, input_file, output_dir, *args, **kwargs, progress=None)
        completed_files.append(f"{os.path.basename(input_file)} - Готово")

    progress(1, "Все файлы обработаны.")
    return "\n".join(completed_files) + f"\n\nФайлы расположены в {output_dir}"

def edge_tts_pipeline(text, voice_model, voice, *args, **kwargs):
    progress = kwargs.pop('progress', None)
    tts_path = os.path.join(OUTPUT_DIRS["tts"], "TTS_Voice.wav")

    progress(0.2, "Синтез речи...")
    asyncio.run(text_to_speech(text, voice, tts_path))

    output_dir = create_unique_output_dir(OUTPUT_DIRS["tts"], prefix="tts_")
    return rvc_infer(voice_model, tts_path, output_dir, *args, **kwargs, progress=progress)
