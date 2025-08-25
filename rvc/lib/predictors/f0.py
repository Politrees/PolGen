import os

import numpy as np
import torch
import torchcrepe
from torchfcpe import spawn_bundled_infer_model

from rvc.lib.predictors.RMVPE import RMVPEF0Predictor


def median_interp_pitch(f0):
    f0 = np.where(f0 == 0, np.nan, f0)
    return float(np.median(np.interp(np.arange(len(f0)), np.where(~np.isnan(f0))[0], f0[~np.isnan(f0)])))


def calc_pitch_shift(f0, target_f0=155.0, limit_f0=12):
    return max(-limit_f0, min(limit_f0, int(np.round(12 * np.log2(target_f0 / median_interp_pitch(f0))))))


class AutoTune:
    def __init__(self, a4_pitch: float = 440.0, scale: str = "chromatic"):
        self.a4_pitch = a4_pitch

        scales = {
            "chromatic": list(range(12)),  # Все 12 нот
            "major": [0, 2, 4, 5, 7, 9, 11],
            "minor": [0, 2, 3, 5, 7, 8, 10],
            "pentatonic_major": [0, 2, 4, 7, 9],
            "pentatonic_minor": [0, 3, 5, 7, 10],
        }

        if isinstance(scale, str):
            if scale not in scales:
                raise ValueError(f"Неизвестный масштаб: {scale}. Доступные масштабы: {list(scales.keys())}")
            scale_semitones = scales[scale]
        else:
            scale_semitones = scale  # Пользовательский набор полутонов

        note_freqs = []
        for midi_note in range(24, 109):  # Диапазон C1-C8
            if (midi_note % 12) in scale_semitones:
                freq = self.a4_pitch * (2 ** ((midi_note - 69) / 12))
                note_freqs.append(freq)

        self.note_array = np.array(note_freqs)

    def autotune_f0(self, f0: np.ndarray, f0_autotune_strength: float) -> np.ndarray:
        if not self.note_array.any() or f0_autotune_strength == 0:
            return f0  # Если нет нот для настройки или сила равна нулю, ничего не делаем

        autotuned_f0 = f0.copy()
        voiced_mask = f0 > 0
        if not np.any(voiced_mask):
            return f0  # Если нет вокализованных участков

        f0_voiced = f0[voiced_mask]

        # Находим ближайшие разрешенные ноты для каждой вокализованной частоты
        insertion_indices = np.clip(np.searchsorted(self.note_array, f0_voiced), 1, len(self.note_array) - 1)
        note_below = self.note_array[insertion_indices - 1]
        note_above = self.note_array[insertion_indices]
        closest_notes = np.where(np.abs(f0_voiced - note_below) < np.abs(f0_voiced - note_above), note_below, note_above)

        # Применяем коррекцию только к вокализованным участкам
        autotuned_f0[voiced_mask] = f0_voiced + (closest_notes - f0_voiced) * f0_autotune_strength
        return autotuned_f0


class RMVPE:
    def __init__(self, device, sample_rate=16000):
        self.device = device
        self.sample_rate = sample_rate
        self.model = RMVPEF0Predictor(os.path.join("rvc", "models", "predictors", "rmvpe.pt"), device=self.device)

    def get_f0(self, audio, type_rmvpe="rmvpe"):
        if type_rmvpe == "rmvpe":
            return self.model.infer_from_audio(audio, thred=0.03)

        if type_rmvpe == "rmvpe+":
            return self.model.infer_from_audio_modified(audio, thred=0.02)

        raise ValueError(f"Недопустимое значение: {type_rmvpe!r}")


class CREPE:
    def __init__(self, device, sample_rate=16000, hop_size=160):
        self.device = device
        self.sample_rate = sample_rate
        self.hop_size = hop_size

    def get_f0(self, audio, f0_min=50, f0_max=1100, p_len=None, model="full"):
        if p_len is None:
            p_len = audio.shape[0] // self.hop_size

        if not torch.is_tensor(audio):
            audio = torch.from_numpy(audio)

        f0, pd = torchcrepe.predict(
            audio.float().to(self.device).unsqueeze(dim=0),
            self.sample_rate,
            self.hop_size,
            f0_min,
            f0_max,
            model=model,
            batch_size=512,
            device=self.device,
            return_periodicity=True,
        )
        pd = torchcrepe.filter.median(pd, 3)
        f0 = torchcrepe.filter.mean(f0, 3)
        f0[pd < 0.1] = 0
        f0 = f0[0].cpu().numpy()

        return f0


class FCPE:
    def __init__(self, device, sample_rate=16000, hop_size=160):
        self.device = device
        self.sample_rate = sample_rate
        self.hop_size = hop_size
        self.model = spawn_bundled_infer_model(self.device)

    def get_f0(self, audio, p_len=None):
        if p_len is None:
            p_len = audio.shape[0] // self.hop_size

        if not torch.is_tensor(audio):
            audio = torch.from_numpy(audio)

        f0 = (
            self.model.infer(
                audio.float().to(self.device).unsqueeze(0),
                sr=self.sample_rate,
                decoder_mode="local_argmax",
                threshold=0.006,
            )
            .squeeze()
            .cpu()
            .numpy()
        )

        return f0
