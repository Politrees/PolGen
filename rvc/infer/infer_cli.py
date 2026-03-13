import argparse
import logging
import os
import sys
import warnings

# --- Unicode-safe stdio ---
def _configure_unicode_stdio() -> None:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


_configure_unicode_stdio()

# Configuring the environment and logging
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Disable unnecessary TensorFlow logs
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"  # Disabling Gradio analytics
logging.basicConfig(level=logging.WARNING)  # Disable all logs, except WARNING and above
warnings.filterwarnings("ignore")  # Disable all warnings

from assets.model_installer import check_and_install_models
from rvc.infer.infer import rvc_edgetts_infer, rvc_infer


def strtobool(val: str) -> bool:
    lower_val = val.lower()
    if lower_val in ("y", "yes", "t", "true", "on", "1"):
        return True
    if lower_val in ("n", "no", "f", "false", "off", "0"):
        return False
    raise ValueError(f"Недопустимое значение: {val!r}")


def create_parser():
    base = argparse.ArgumentParser(add_help=False)
    base.add_argument("--rvc_model", type=str, required=True, help="Название RVC модели")
    base.add_argument("--f0_method", type=str, default="rmvpe", help="Метод извлечения F0")
    base.add_argument("--f0_min", type=int, default=50, help="Минимальная частота F0")
    base.add_argument("--f0_max", type=int, default=1100, help="Максимальная частота F0")
    base.add_argument("--rvc_pitch", type=float, default=0, help="Высота тона RVC модели")
    base.add_argument("--protect", type=float, default=0.5, help="Защита согласных")
    base.add_argument("--index_rate", type=float, default=0, help="Коэффициент индекса")
    base.add_argument("--volume_envelope", type=float, default=1, help="Огибающая громкости")
    base.add_argument("--autopitch", type=lambda x: bool(strtobool(x)), default=False, help="Автоматическое определение высоты тона")
    base.add_argument("--autopitch_threshold", type=float, default=155.0, help="155.0 — Мужская модель | 255.0 — Женская модель")
    base.add_argument("--autotune", type=lambda x: bool(strtobool(x)), default=False, help="Коррекция высоты тона")
    base.add_argument("--autotune_tonic", type=str, default="C", help="Тоника (основная нота) гаммы")
    base.add_argument("--autotune_scale", type=str, default="chromatic", help="Музыкальная гамма")
    base.add_argument("--autotune_strength", type=float, default=1.0, help="Сила автотюна")
    base.add_argument("--upscale", type=lambda x: bool(strtobool(x)), default=False, help="Улучшение качества звука")
    base.add_argument("--stereo", type=lambda x: bool(strtobool(x)), default=False, help="Преобразование моно звука в стерео")
    base.add_argument("--output_format", type=str, default="mp3", help="Формат выходного файла")

    parser = argparse.ArgumentParser(description="Инструмент для замены голоса при помощи RVC")
    subparsers = parser.add_subparsers(dest="command", required=True)

    rvc = subparsers.add_parser("rvc", parents=[base], help="Конвертация аудио-файла")
    rvc.add_argument("--input_path", type=str, required=True, help="Путь к аудио-файлу")

    edge_tts = subparsers.add_parser("tts", parents=[base], help="Синтез речи из текста")
    edge_tts.add_argument("--tts_voice", type=str, required=True, help="Голос для синтеза речи")
    edge_tts.add_argument("--tts_text", type=str, required=True, help="Текст для синтеза речи")
    edge_tts.add_argument("--tts_rate", type=int, default=0, help="Скорость синтеза речи")
    edge_tts.add_argument("--tts_volume", type=int, default=0, help="Громкость синтеза речи")
    edge_tts.add_argument("--tts_pitch", type=int, default=0, help="Высота тона синтеза речи")

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    common_params = {
        "rvc_model": args.rvc_model,
        "f0_method": args.f0_method,
        "f0_min": args.f0_min,
        "f0_max": args.f0_max,
        "rvc_pitch": args.rvc_pitch,
        "protect": args.protect,
        "index_rate": args.index_rate,
        "volume_envelope": args.volume_envelope,
        "autopitch": args.autopitch,
        "autopitch_threshold": args.autopitch_threshold,
        "autotune": args.autotune,
        "autotune_tonic": args.autotune_tonic,
        "autotune_scale": args.autotune_scale,
        "autotune_strength": args.autotune_strength,
        "audio_upscaling": args.upscale,
        "stereo_sound": args.stereo,
        "output_format": args.output_format,
    }

    if args.command == "rvc":
        rvc_infer(**common_params, input_path=args.input_path)
    elif args.command == "tts":
        rvc_edgetts_infer(
            **common_params,
            tts_voice=args.tts_voice,
            tts_text=args.tts_text,
            tts_rate=args.tts_rate,
            tts_volume=args.tts_volume,
            tts_pitch=args.tts_pitch,
        )

    print("\033[1;92m\nГолос успешно заменен!\n\033[0m")


if __name__ == "__main__":
    check_and_install_models()
    main()
