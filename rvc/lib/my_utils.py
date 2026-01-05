import subprocess

import librosa
import numpy as np
import soundfile as sf


def load_audio(file, sample_rate):
    try:
        file = file.strip(" ").strip('"').strip("\n").strip('"').strip(" ")
        audio, sr = sf.read(file)
        if len(audio.shape) > 1:
            audio = librosa.to_mono(audio.T)
        if sr != sample_rate:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=sample_rate)
    except Exception as error:
        raise RuntimeError(f"Произошла ошибка при загрузке аудио: {error}") from error

    return audio.flatten()


def save_audio(audio_data, sample_rate, output_path, output_format="wav", stereo=False):
    """Сохраняет аудио используя прямой вызов FFmpeg через pipe."""
    # Конвертируем в int16 или float32 в зависимости от формата
    if output_format in ["wav", "flac"]:
        # Для lossless форматов используем 24-bit
        audio_data = np.clip(audio_data, -1.0, 1.0)
        # Конвертируем в 32-bit float для максимальной точности
        audio_bytes = audio_data.astype(np.float32).tobytes()
        input_format = "f32le"
    else:
        # Для lossy форматов используем 16-bit
        audio_int16 = (audio_data * 32767).astype(np.int16)
        audio_bytes = audio_int16.tobytes()
        input_format = "s16le"

    channels = 2 if stereo else 1

    # Базовые параметры FFmpeg
    cmd = [
        "ffmpeg",
        "-y",  # Перезаписывать выходной файл
        "-f",
        input_format,  # Формат входных данных
        "-ar",
        str(sample_rate),  # Частота дискретизации
        "-ac",
        "1",  # Входные каналы (всегда моно из RVC)
        "-i",
        "pipe:0",  # Читать из stdin
        "-ac",
        str(channels),  # Выходные каналы
    ]

    # Настройки качества для каждого формата
    format_settings = {
        "wav": [
            "-c:a",
            "pcm_f32le",  # 32-bit float PCM для максимального качества
            "-sample_fmt",
            "flt",
        ],
        "flac": [
            "-c:a",
            "flac",
            "-compression_level",
            "12",  # Максимальное сжатие (без потерь)
            "-sample_fmt",
            "s32",  # 32-bit для максимального качества
        ],
        "mp3": [
            "-c:a",
            "libmp3lame",
            "-b:a",
            "320k",  # Максимальный битрейт
            "-q:a",
            "0",  # Наилучшее качество
        ],
        "ogg": [
            "-c:a",
            "libvorbis",
            "-q:a",
            "10",  # Максимальное качество (500kbps+)
        ],
        "m4a": [
            "-c:a",
            "aac",
            "-b:a",
            "320k",  # Максимальный битрейт
            "-q:a",
            "2",  # Максимальное качество
            "-aac_coder",
            "twoloop",  # Лучший кодировщик
            "-profile:a",
            "aac_low",
        ],
    }

    if output_format in format_settings:
        cmd.extend(format_settings[output_format])
    else:
        raise ValueError(f"Неподдерживаемый формат: {output_format}")

    # Добавляем выходной файл
    cmd.append(output_path)

    # Запускаем FFmpeg
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,  # Подавляем вывод FFmpeg для чистоты
    )

    try:
        stdout, stderr = process.communicate(input=audio_bytes, timeout=300)
    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError("FFmpeg timeout: операция заняла слишком много времени")

    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg завершился с ошибкой (код: {process.returncode})")

    return output_path
