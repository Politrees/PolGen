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
    """Класс для выполнения автотюна на аудиосигнале."""

    def __init__(self, a4_frequency: float = 440.0, scale_name: str = "chromatic", tonic_note: str = "C"):
        """Инициализирует класс AutoTune с заданными параметрами.

        Args:
            a4_frequency (float): Частота ноты A4 (Ля первой октавы).
            scale_name (str): Название гаммы.
            tonic_note (str): Тоника (основная нота) гаммы.

        """
        self.a4_frequency = a4_frequency

        # Интервалы гамм в полутонах от тоники
        scale_intervals = {
            "chromatic": list(range(12)),  # Все 12 нот (полутонов)
            "major": [0, 2, 4, 5, 7, 9, 11],  # Мажорная гамма
            "minor": [0, 2, 3, 5, 7, 8, 10],  # Минорная гамма
            "pentatonic_major": [0, 2, 4, 7, 9],  # Мажорная пентатоника
            "pentatonic_minor": [0, 3, 5, 7, 10],  # Минорная пентатоника
        }

        # Соответствие названий тоник их полутоновым значениям (относительно C)
        tonic_semitones = {
            "C": 0,
            "C#": 1,
            "Db": 1,
            "D": 2,
            "D#": 3,
            "Eb": 3,
            "E": 4,
            "F": 5,
            "F#": 6,
            "Gb": 6,
            "G": 7,
            "G#": 8,
            "Ab": 8,
            "A": 9,
            "A#": 10,
            "Bb": 10,
            "B": 11,
        }

        if scale_name not in scale_intervals:
            raise ValueError(f"Неизвестная гамма: '{scale_name}'. Доступные гаммы: {list(scale_intervals.keys())}")
        if tonic_note not in tonic_semitones:
            raise ValueError(f"Неизвестная тоника: '{tonic_note}'. Доступные тоники: {list(tonic_semitones.keys())}")

        selected_scale_intervals = scale_intervals[scale_name]
        selected_tonic_semitone = tonic_semitones[tonic_note]

        # Расчёт целевых частот для выбранной гаммы
        target_frequencies = []
        for midi_note in range(24, 109):  # Диапазон C1-C8 (MIDI-ноты 24-108)
            # Проверяем, принадлежит ли MIDI-нота выбранной гамме
            if (midi_note - selected_tonic_semitone) % 12 in selected_scale_intervals:
                # Конвертируем MIDI-ноту в частоту (Гц)
                frequency = self.a4_frequency * (2 ** ((midi_note - 69) / 12))
                target_frequencies.append(frequency)

        # Сохраняем массив целевых частот для быстрого поиска
        self.target_frequencies = np.array(target_frequencies)

    def apply_autotune(self, input_f0: np.ndarray, autotune_strength: float) -> np.ndarray:
        """Применяет автотюн к массиву основной частоты (F0) аудиосигнала.

        Args:
            input_f0 (np.ndarray): Входной массив основной частоты.
            autotune_strength (float): Сила автотюна (от 0.0 до 1.0).
                                    0.0 - нет коррекции, 1.0 - полная коррекция.

        Returns:
            np.ndarray: Массив основной частоты после применения автотюна.

        """
        # Если нет целевых частот или сила автотюна равна 0, возвращаем исходный массив
        if not self.target_frequencies.any() or autotune_strength == 0:
            return input_f0

        # Создаём копию входного массива для обработки
        output_f0 = input_f0.copy()
        # Определяем "вокализованные" участки (где F0 > 0)
        is_voiced = input_f0 > 0

        # Если вокализованных участков нет, возвращаем исходный массив
        if not np.any(is_voiced):
            return input_f0

        # Выбираем только те частоты, которые нужно обработать
        voiced_f0 = input_f0[is_voiced]

        # Находим индексы ближайших разрешённых нот в массиве target_frequencies
        insertion_indices = np.clip(np.searchsorted(self.target_frequencies, voiced_f0), 1, len(self.target_frequencies) - 1)

        # Получаем частоты ближайших нот "снизу" и "сверху"
        lower_note_freq = self.target_frequencies[insertion_indices - 1]
        upper_note_freq = self.target_frequencies[insertion_indices]

        # Определяем, какая из двух нот ближе к текущей частоте
        closest_target_frequencies = np.where(
            np.abs(voiced_f0 - lower_note_freq) < np.abs(voiced_f0 - upper_note_freq), lower_note_freq, upper_note_freq
        )

        # Применяем коррекцию: сдвигаем частоту в сторону ближайшей ноты с заданной силой
        output_f0[is_voiced] = voiced_f0 + (closest_target_frequencies - voiced_f0) * autotune_strength
        return output_f0


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
