from assets.logging_config import configure_logging

configure_logging(True, False, "WARNING")

import argparse

from PolGen.rvc.infer.infer import rvc_infer


def create_parser():
    # Базовый парсер с общими аргументами
    base_parser = argparse.ArgumentParser(add_help=False)
    base_parser.add_argument("-m", "--model_name", type=str, required=True, help="Название RVC модели")
    base_parser.add_argument("-p", "--pitch", type=float, default=0, help="Высота тона RVC модели")
    base_parser.add_argument("-ir", "--index_rate", type=float, default=0, help="Коэффициент индекса (0-1)")
    base_parser.add_argument("-rms", "--volume_envelope", type=float, default=1, help="Огибающая громкости")
    base_parser.add_argument("-f0", "--f0_method", type=str, default="rmvpe", help="Метод извлечения F0")
    base_parser.add_argument("-hop", "--hop_length", type=int, default=128, help="Длина хопа для обработки")
    base_parser.add_argument("-pro", "--protect", type=float, default=0.5, help="Защита согласных")
    base_parser.add_argument("-f0min", "--f0_min", type=int, default=50, help="Минимальная частота F0")
    base_parser.add_argument("-f0max", "--f0_max", type=int, default=1100, help="Максимальная частота F0")
    base_parser.add_argument("-f", "--format", type=str, default="mp3", help="Формат выходного файла")

    # Главный парсер с субкомандами
    parser = argparse.ArgumentParser(description="Инструмент замены голоса RVC")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Субкоманда для аудио-конвертации
    audio_parser = subparsers.add_parser("rvc", parents=[base_parser], help="Конвертация аудио файла")
    audio_parser.add_argument("-i", "--input_path", type=str, required=True, help="Путь к входному аудио файлу")

    # Субкоманда для TTS
    tts_parser = subparsers.add_parser("tts", parents=[base_parser], help="Синтез речи из текста")
    tts_parser.add_argument("-t", "--text", type=str, required=True, help="Текст для синтеза речи")
    tts_parser.add_argument("-v", "--voice", type=str, required=True, help="Голос для синтеза речи")
    tts_parser.add_argument("-r", "--rate", type=int, default=0, help="Скорость синтеза речи")

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    common_params = {
        "voice_rvc": args.model_name,
        "pitch": args.pitch,
        "index_rate": args.index_rate,
        "volume_envelope": args.volume_envelope,
        "f0_method": args.f0_method,
        "hop_length": args.hop_length,
        "protect": args.protect,
        "f0_min": args.f0_min,
        "f0_max": args.f0_max,
        "output_format": args.format,
    }

    if args.command == "rvc":
        output = rvc_infer(**common_params, input_audio=args.input_path, use_tts=False)
    elif args.command == "tts":
        output = rvc_infer(**common_params, input_text=args.text, voice_tts=args.voice, tts_rate=args.rate, use_tts=True)

    print(f"\033[1;92m\nГолос успешно заменен!\n\033[0m — {', '.join(output)}")


if __name__ == "__main__":
    main()
