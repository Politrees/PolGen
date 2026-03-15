import asyncio
import gc
import os
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

import edge_tts
import gradio as gr
import torch

from rvc.infer.config import Config
from rvc.infer.pipeline import VC
from rvc.lib.algorithm.synthesizers import Synthesizer
from rvc.lib.fairseq import load_model
from rvc.lib.my_utils import load_audio, save_audio
from rvc.modules.audio_upscaler import upscale

# Определяем пути к папкам и файлам (константы)
RVC_MODELS_DIR = os.path.join(os.getcwd(), "models", "RVC_models")
OUTPUT_DIR = os.path.join(os.getcwd(), "output", "RVC_output")
HUBERT_BASE_PATH = os.path.join(os.getcwd(), "rvc", "models", "embedders", "hubert_base.pt")

# Создаем папки, если их нет
os.makedirs(RVC_MODELS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Инициализация конфигурации
config = Config()


def clear_gpu_cache():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()


def display_progress(percent, message, is_print, progress=None):
    """
    progress — любой объект/функция, которую можно вызвать как:
      progress(percent, desc="...")
    """
    if is_print:
        print(message)
    if progress is not None:
        try:
            progress(percent, desc=message)
        except TypeError:
            # на случай если progress ожидает (percent, message)
            progress(percent, message)


def load_rvc_model(rvc_model):
    model_dir = os.path.join(RVC_MODELS_DIR, rvc_model)
    if not os.path.isdir(model_dir):
        raise FileNotFoundError(f"Папка модели {rvc_model} не найдена в {RVC_MODELS_DIR}")

    rvc_model_path = next((os.path.join(model_dir, f) for f in os.listdir(model_dir) if f.endswith(".pth")), None)
    rvc_index_path = next((os.path.join(model_dir, f) for f in os.listdir(model_dir) if f.endswith(".index")), None)

    if not rvc_model_path:
        raise FileNotFoundError(f"Модель {rvc_model} не содержит .pth файла!")

    return rvc_model_path, rvc_index_path


def load_hubert(model_path):
    hubert = load_model(model_path).to(config.device).eval()
    return hubert


def get_vc(model_path):
    cpt = torch.load(model_path, map_location="cpu", weights_only=True)
    if "config" not in cpt or "weight" not in cpt:
        raise ValueError(f"Некорректный формат модели {model_path}. Используйте модель RVC.")

    tgt_sr = cpt["config"][-1]
    cpt["config"][-3] = cpt["weight"]["emb_g.weight"].shape[0]

    use_f0 = cpt.get("f0", 1)
    version = cpt.get("version", "v1")
    vocoder = cpt.get("vocoder", "HiFi-GAN")
    input_dim = 768 if version == "v2" else 256

    net_g = Synthesizer(*cpt["config"], use_f0=use_f0, text_enc_hidden_dim=input_dim, vocoder=vocoder)

    del net_g.enc_q
    net_g.load_state_dict(cpt["weight"], strict=False)
    net_g = net_g.to(config.device).float().eval()

    vc = VC(tgt_sr, config)
    return cpt, version, net_g, tgt_sr, vc, use_f0


# ═══════════════════════════════════════════════════════════════
# Model Cache — кеширование моделей в GPU/CPU памяти между вызовами
# ═══════════════════════════════════════════════════════════════


@dataclass
class _CachedRvcModel:
    """Закешированная RVC модель: всё необходимое для инференса."""

    version: str
    net_g: Any
    tgt_sr: int
    vc: Any
    use_f0: int
    index_path: str | None


class ModelCache:
    """LRU-кеш для HuBERT и RVC моделей.

    HuBERT загружается один раз и переиспользуется (он общий для всех RVC моделей).
    RVC модели хранятся с LRU-вытеснением (макс. кол-во зависит от VRAM).
    """

    def __init__(self, max_rvc_models: int = 2):
        self._hubert: Any | None = None
        self._rvc_models: OrderedDict[str, _CachedRvcModel] = OrderedDict()
        self._max_rvc = max_rvc_models
        self._lock = threading.Lock()

    def get_hubert(self) -> Any:
        """Возвращает HuBERT модель. Загружает при первом вызове."""
        if self._hubert is None:
            self._hubert = load_hubert(HUBERT_BASE_PATH)
        return self._hubert

    def invalidate_hubert(self) -> None:
        """Сбрасывает кеш HuBERT (после установки кастомной модели)."""
        with self._lock:
            if self._hubert is not None:
                del self._hubert
                self._hubert = None
                clear_gpu_cache()
                print("[Cache] HuBERT кеш сброшен")

    def get_rvc_model(self, model_name: str) -> _CachedRvcModel:
        """Возвращает RVC модель. Загружает и кеширует при первом вызове."""
        # Быстрая проверка — модель уже в кеше?
        with self._lock:
            if model_name in self._rvc_models:
                self._rvc_models.move_to_end(model_name)
                return self._rvc_models[model_name]

        # Загрузка вне лока (IO + GPU transfer может быть долгим)
        model_path, index_path = load_rvc_model(model_name)
        cpt, version, net_g, tgt_sr, vc, use_f0 = get_vc(model_path)
        del cpt  # checkpoint dict больше не нужен (веса уже в net_g)

        cached = _CachedRvcModel(
            version=version,
            net_g=net_g,
            tgt_sr=tgt_sr,
            vc=vc,
            use_f0=use_f0,
            index_path=index_path,
        )

        with self._lock:
            # Double-check: другой поток мог загрузить эту модель пока мы грузили
            if model_name in self._rvc_models:
                self._rvc_models.move_to_end(model_name)
                del cached
                clear_gpu_cache()
                return self._rvc_models[model_name]

            # Вытесняем самую старую модель если кеш полон
            while len(self._rvc_models) >= self._max_rvc:
                evicted_name, evicted = self._rvc_models.popitem(last=False)
                del evicted
                clear_gpu_cache()
                print(f"[Cache] Вытеснена модель '{evicted_name}'")

            self._rvc_models[model_name] = cached
            print(f"[Cache] Модель '{model_name}' закеширована ({len(self._rvc_models)}/{self._max_rvc})")

        return cached

    def invalidate_rvc_model(self, model_name: str) -> None:
        """Удаляет конкретную RVC модель из кеша."""
        with self._lock:
            if model_name in self._rvc_models:
                evicted = self._rvc_models.pop(model_name)
                del evicted
                clear_gpu_cache()
                print(f"[Cache] Модель '{model_name}' удалена из кеша")

    def clear_all(self) -> None:
        """Полный сброс кеша (HuBERT + все RVC модели)."""
        with self._lock:
            self._rvc_models.clear()
            self._hubert = None
        clear_gpu_cache()
        print("[Cache] Кеш полностью очищен")

    @property
    def cached_model_names(self) -> list[str]:
        """Список имён закешированных RVC моделей."""
        with self._lock:
            return list(self._rvc_models.keys())


def _detect_max_cached_models() -> int:
    """Определяет лимит кеша RVC моделей по объёму VRAM."""
    if config.gpu_mem is None:
        return 1  # CPU/MPS — кешируем минимум
    if config.gpu_mem <= 4:
        return 1
    if config.gpu_mem <= 8:
        return 2
    return 3


# Глобальный кеш моделей
_model_cache = ModelCache(max_rvc_models=_detect_max_cached_models())


def get_model_cache() -> ModelCache:
    """Доступ к глобальному кешу моделей (для внешних модулей)."""
    return _model_cache


# ═══════════════════════════════════════════════════════════════


async def text_to_speech(voice, text, rate, volume, pitch, output_path):
    if not -100 <= rate <= 100 or not -100 <= volume <= 100 or not -100 <= pitch <= 100:
        raise ValueError("Параметры Rate, Volume и Pitch должны быть в диапазоне от -100 до +100.")

    communicate = edge_tts.Communicate(
        voice=voice,
        text=text,
        rate=f"{rate:+d}%",
        volume=f"{volume:+d}%",
        pitch=f"{pitch:+d}Hz",
    )
    await communicate.save(output_path)


def rvc_infer(
    rvc_model=None,
    input_path=None,
    f0_method="rmvpe",
    f0_min=50,
    f0_max=1100,
    rvc_pitch=0,
    protect=0.5,
    index_rate=0.25,
    volume_envelope=1.0,
    autopitch=False,
    autopitch_threshold=155.0,
    autotune=False,
    autotune_tonic="C",
    autotune_scale="chromatic",
    autotune_strength=1.0,
    audio_upscaling=False,  # FlashSR
    stereo_sound=False,
    output_format="wav",
    progress=gr.Progress(track_tqdm=True),
):
    if not rvc_model:
        raise ValueError("Не выбрана модель для RVC-инференса")
    if not input_path or not os.path.exists(input_path):
        raise FileNotFoundError(f"Файл '{input_path}' не найден!")

    display_progress(0, "\n[⚙️] Запуск конвейера генерации...", True, progress)

    display_progress(0.1, "Загружаем модель HuBERT...", False, progress)
    hubert_model = _model_cache.get_hubert()

    display_progress(0.2, f"Загружаем модель '{rvc_model}'...", False, progress)
    cached = _model_cache.get_rvc_model(rvc_model)

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    if len(base_name) > 100:
        print("[!] Имя файла > 100 символов — будет сокращено.")
        base_name = f"{base_name[:25]}... (Made_in_PolGen)"
    output_path = os.path.join(OUTPUT_DIR, f"{base_name}_({rvc_model}).{output_format}")

    display_progress(0.4, "Загружаем аудио...", False, progress)
    audio = load_audio(input_path, 16000)

    display_progress(0.5, f"[🌌] Преобразуем аудио '{base_name}'...", True, progress)

    try:
        audio_opt = cached.vc.pipeline(
            model=hubert_model,
            net_g=cached.net_g,
            sid=0,
            audio=audio,
            pitch=0 if autopitch else rvc_pitch,
            f0_min=f0_min,
            f0_max=f0_max,
            f0_method=f0_method,
            file_index=cached.index_path,
            index_rate=index_rate,
            pitch_guidance=cached.use_f0,
            volume_envelope=volume_envelope,
            version=cached.version,
            protect=protect,
            autopitch=autopitch,
            autopitch_threshold=autopitch_threshold,
            autotune=autotune,
            autotune_tonic=autotune_tonic,
            autotune_scale=autotune_scale,
            autotune_strength=autotune_strength,
        )

        display_progress(0.8, "[💫] Сохраняем результат...", True, progress)
        save_audio(audio_opt, cached.tgt_sr, output_path, output_format, stereo_sound)

        if audio_upscaling:
            display_progress(0.9, "[🚀] Улучшаем качество аудио...", True, progress)
            upscale(output_path, OUTPUT_DIR, 2, config.device)

    except Exception as e:
        clear_gpu_cache()
        raise e

    display_progress(1.0, f"[✅] Преобразование завершено — {output_path}", True, progress)
    return output_path


def rvc_edgetts_infer(
    # RVC
    rvc_model=None,
    f0_method="rmvpe",
    f0_min=50,
    f0_max=1100,
    rvc_pitch=0,
    protect=0.5,
    index_rate=0.25,
    volume_envelope=1.0,
    autopitch=False,
    autopitch_threshold=155.0,
    autotune=False,
    autotune_tonic="C",
    autotune_scale="chromatic",
    autotune_strength=1.0,
    stereo_sound=False,
    output_format="wav",
    # EdgeTTS
    tts_voice=None,
    tts_text=None,
    tts_rate=0,
    tts_volume=0,
    tts_pitch=0,
    # FlashSR
    audio_upscaling=False,
    progress=gr.Progress(track_tqdm=True),
):
    if not tts_text:
        raise ValueError("Введите текст!")
    if not tts_voice:
        raise ValueError("Выберите голос!")
    if not rvc_model:
        raise ValueError("Не выбрана RVC модель!")

    display_progress(0.05, "[🎙️] Синтезируем речь...", False, progress)
    input_path = os.path.join(OUTPUT_DIR, "TTS_Voice.wav")
    asyncio.run(text_to_speech(tts_voice, tts_text, tts_rate, tts_volume, tts_pitch, input_path))

    output_path = rvc_infer(
        rvc_model=rvc_model,
        input_path=input_path,
        f0_method=f0_method,
        f0_min=f0_min,
        f0_max=f0_max,
        rvc_pitch=rvc_pitch,
        protect=protect,
        index_rate=index_rate,
        volume_envelope=volume_envelope,
        autopitch=autopitch,
        autopitch_threshold=autopitch_threshold,
        autotune=autotune,
        autotune_tonic=autotune_tonic,
        autotune_scale=autotune_scale,
        autotune_strength=autotune_strength,
        audio_upscaling=audio_upscaling,
        stereo_sound=stereo_sound,
        output_format=output_format,
        progress=progress,
    )

    return input_path, output_path
