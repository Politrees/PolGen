import argparse
import os
from rvc.infer.infer import tts_infer, RVC_MODELS_DIR

parser = argparse.ArgumentParser(
    description="Замена голоса в директории output/", add_help=True
)
parser.add_argument("-i", "--text_input", type=str, required=True)
parser.add_argument("-m", "--model_name", type=str, required=True)
parser.add_argument("-v", "--tts_voice", type=str, required=True)
parser.add_argument("-p", "--pitch", type=float, required=True)
parser.add_argument("-ir", "--index_rate", type=float, default=0)
parser.add_argument("-fr", "--filter_radius", type=int, default=3)
parser.add_argument("-rms", "--volume_envelope", type=float, default=0.25)
parser.add_argument("-f0", "--method", type=str, default="rmvpe+")
parser.add_argument("-hop", "--hop_length", type=int, default=128)
parser.add_argument("-pro", "--protect", type=float, default=0.33)
parser.add_argument("-f0min", "--f0_min", type=int, default=50)
parser.add_argument("-f0max", "--f0_max", type=int, default=1100)
parser.add_argument("-f", "--format", type=str, default="mp3")
args = parser.parse_args()

model_name = args.model_name
if not os.path.exists(os.path.join(RVC_MODELS_DIR, model_name)):
    raise Exception(
        f"\033[91mМодели {model_name} не существует. Возможно, вы неправильно ввели имя.\033[0m"
    )

cover_path = tts_infer(
    voice_model=model_name,
    input_path_or_text=args.text_input,
    index_rate=args.index_rate,
    pitch=args.pitch,
    f0_method=args.method,
    filter_radius=args.filter_radius,
    volume_envelope=args.volume_envelope,
    protect=args.protect,
    hop_length=args.hop_length,
    f0_min=args.f0_min,
    f0_max=args.f0_max,
    output_format=args.format,
    voice=args.tts_voice,
)

print("\033[1;92m\nГолос успешно заменен!\n\033[0m")
