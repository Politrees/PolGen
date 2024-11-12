import logging
import os
import shutil

import gradio as gr
import torch
from audio_separator.separator import Separator

device = "cuda" if torch.cuda.is_available() else "cpu"
use_autocast = device == "cuda"

# Списки моделей
ROFORMER_MODELS = {
    "BS-Roformer-Viperx-1297.ckpt": "model_bs_roformer_ep_317_sdr_12.9755.ckpt",
    "BS-Roformer-Viperx-1296.ckpt": "model_bs_roformer_ep_368_sdr_12.9628.ckpt",
    "BS-Roformer-Viperx-1053.ckpt": "model_bs_roformer_ep_937_sdr_10.5309.ckpt",
    "BS-Roformer-De-Reverb.ckpt": "deverb_bs_roformer_8_384dim_10depth.ckpt",
    "Mel-Roformer-Viperx-1143.ckpt": "model_mel_band_roformer_ep_3005_sdr_11.4360.ckpt",
    "Mel-Roformer-Crowd-Aufr33-Viperx.ckpt": "mel_band_roformer_crowd_aufr33_viperx_sdr_8.7144.ckpt",
    "Mel-Roformer-Karaoke-Aufr33-Viperx.ckpt": "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt",
    "Mel-Roformer-Denoise-Aufr33": "denoise_mel_band_roformer_aufr33_sdr_27.9959.ckpt",
    "Mel-Roformer-Denoise-Aufr33-Aggr": "denoise_mel_band_roformer_aufr33_aggr_sdr_27.9768.ckpt",
    "MB-Roformer-Inst-v1 by Kim": "melband_roformer_inst_v1.ckpt",
    "MB-Roformer-InstVoc-Duality-v1 by Unwa": "melband_roformer_instvoc_duality_v1.ckpt",
    "MB-Roformer-InstVoc-Duality-v2 by Unwa": "melband_roformer_instvox_duality_v2.ckpt",
}
MDX23C_MODELS = [
    "MDX23C_D1581.ckpt",
    "MDX23C-8KFFT-InstVoc_HQ.ckpt",
    "MDX23C-8KFFT-InstVoc_HQ_2.ckpt",
]
MDXNET_MODELS = [
    "UVR-MDX-NET-Inst_full_292.onnx",
    "UVR-MDX-NET_Inst_187_beta.onnx",
    "UVR-MDX-NET_Inst_82_beta.onnx",
    "UVR-MDX-NET_Inst_90_beta.onnx",
    "UVR-MDX-NET_Main_340.onnx",
    "UVR-MDX-NET_Main_390.onnx",
    "UVR-MDX-NET_Main_406.onnx",
    "UVR-MDX-NET_Main_427.onnx",
    "UVR-MDX-NET_Main_438.onnx",
    "UVR-MDX-NET-Inst_HQ_1.onnx",
    "UVR-MDX-NET-Inst_HQ_2.onnx",
    "UVR-MDX-NET-Inst_HQ_3.onnx",
    "UVR-MDX-NET-Inst_HQ_4.onnx",
    "UVR_MDXNET_Main.onnx",
    "UVR-MDX-NET-Inst_Main.onnx",
    "UVR_MDXNET_1_9703.onnx",
    "UVR_MDXNET_2_9682.onnx",
    "UVR_MDXNET_3_9662.onnx",
    "UVR-MDX-NET-Inst_1.onnx",
    "UVR-MDX-NET-Inst_2.onnx",
    "UVR-MDX-NET-Inst_3.onnx",
    "UVR_MDXNET_KARA.onnx",
    "UVR_MDXNET_KARA_2.onnx",
    "UVR_MDXNET_9482.onnx",
    "UVR-MDX-NET-Voc_FT.onnx",
    "Kim_Vocal_1.onnx",
    "Kim_Vocal_2.onnx",
    "Kim_Inst.onnx",
    "Reverb_HQ_By_FoxJoy.onnx",
    "UVR-MDX-NET_Crowd_HQ_1.onnx",
    "kuielab_a_vocals.onnx",
    "kuielab_a_other.onnx",
    "kuielab_a_bass.onnx",
    "kuielab_a_drums.onnx",
    "kuielab_b_vocals.onnx",
    "kuielab_b_other.onnx",
    "kuielab_b_bass.onnx",
    "kuielab_b_drums.onnx",
]
VR_ARCH_MODELS = [
    "1_HP-UVR.pth",
    "2_HP-UVR.pth",
    "3_HP-Vocal-UVR.pth",
    "4_HP-Vocal-UVR.pth",
    "5_HP-Karaoke-UVR.pth",
    "6_HP-Karaoke-UVR.pth",
    "7_HP2-UVR.pth",
    "8_HP2-UVR.pth",
    "9_HP2-UVR.pth",
    "10_SP-UVR-2B-32000-1.pth",
    "11_SP-UVR-2B-32000-2.pth",
    "12_SP-UVR-3B-44100.pth",
    "13_SP-UVR-4B-44100-1.pth",
    "14_SP-UVR-4B-44100-2.pth",
    "15_SP-UVR-MID-44100-1.pth",
    "16_SP-UVR-MID-44100-2.pth",
    "17_HP-Wind_Inst-UVR.pth",
    "UVR-DeEcho-DeReverb.pth",
    "UVR-De-Echo-Normal.pth",
    "UVR-De-Echo-Aggressive.pth",
    "UVR-DeNoise.pth",
    "UVR-DeNoise-Lite.pth",
    "UVR-BVE-4B_SN-44100-1.pth",
    "MGM_HIGHEND_v4.pth",
    "MGM_LOWEND_A_v4.pth",
    "MGM_LOWEND_B_v4.pth",
    "MGM_MAIN_v4.pth",
]
DEMUCS_MODELS = [
    "htdemucs_ft.yaml",
    "htdemucs_6s.yaml",
    "htdemucs.yaml",
    "hdemucs_mmi.yaml",
]


def print_message(input_file, model_name):
    """Выводит информацию о процессе разделения аудио."""
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    print("\n")
    print("🎵 PolUVR 🎵")
    print("Входной аудиофайл:", base_name)
    print("Модель разделения:", model_name)
    print("Процесс разделения аудио...")


def prepare_output_dir(input_file, output_dir):
    """Создает директорию для выходных файлов и очищает её, если она уже существует."""
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    out_dir = os.path.join(output_dir, base_name)
    try:
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(out_dir)
    except Exception as e:
        raise RuntimeError(f"Не удалось подготовить выходную директорию {out_dir}: {e}")
    return out_dir


def roformer_separator(
    audio,
    model_key,
    seg_size,
    override_seg_size,
    overlap,
    pitch_shift,
    model_dir,
    out_dir,
    out_format,
    norm_thresh,
    amp_thresh,
    batch_size,
    progress=gr.Progress(track_tqdm=True),
):
    """Разделяет аудио с использованием модели Roformer."""
    base_name = os.path.splitext(os.path.basename(audio))[0]
    print_message(audio, model_key)
    model = ROFORMER_MODELS[model_key]
    try:
        out_dir = prepare_output_dir(audio, out_dir)
        separator = Separator(
            log_level=logging.WARNING,
            model_file_dir=model_dir,
            output_dir=out_dir,
            output_format=out_format,
            normalization_threshold=norm_thresh,
            amplification_threshold=amp_thresh,
            use_autocast=use_autocast,
            mdxc_params={
                "segment_size": seg_size,
                "override_model_segment_size": override_seg_size,
                "batch_size": batch_size,
                "overlap": overlap,
                "pitch_shift": pitch_shift,
            },
        )

        progress(0.2, desc="Модель загружена...")
        separator.load_model(model_filename=model)

        progress(0.7, desc="Аудио разделено...")
        separation = separator.separate(
            audio, f"{base_name}_(Stem1)", f"{base_name}_(Stem2)"
        )
        print(f"Разделение завершено!\nРезультаты: {', '.join(separation)}")

        stems = [os.path.join(out_dir, file_name) for file_name in separation]
        return stems[0], stems[1]
    except Exception as e:
        raise RuntimeError(
            f"Разделение с использованием Roformer не удалось: {e}"
        ) from e


def mdx23c_separator(
    audio,
    model,
    seg_size,
    override_seg_size,
    overlap,
    pitch_shift,
    model_dir,
    out_dir,
    out_format,
    norm_thresh,
    amp_thresh,
    batch_size,
    progress=gr.Progress(track_tqdm=True),
):
    """Разделяет аудио с использованием модели MDX23C."""
    base_name = os.path.splitext(os.path.basename(audio))[0]
    print_message(audio, model)
    try:
        out_dir = prepare_output_dir(audio, out_dir)
        separator = Separator(
            log_level=logging.WARNING,
            model_file_dir=model_dir,
            output_dir=out_dir,
            output_format=out_format,
            normalization_threshold=norm_thresh,
            amplification_threshold=amp_thresh,
            use_autocast=use_autocast,
            mdxc_params={
                "segment_size": seg_size,
                "override_model_segment_size": override_seg_size,
                "batch_size": batch_size,
                "overlap": overlap,
                "pitch_shift": pitch_shift,
            },
        )

        progress(0.2, desc="Модель загружена...")
        separator.load_model(model_filename=model)

        progress(0.7, desc="Аудио разделено...")
        separation = separator.separate(
            audio, f"{base_name}_(Stem1)", f"{base_name}_(Stem2)"
        )
        print(f"Разделение завершено!\nРезультаты: {', '.join(separation)}")

        stems = [os.path.join(out_dir, file_name) for file_name in separation]
        return stems[0], stems[1]
    except Exception as e:
        raise RuntimeError(f"Разделение с использованием MDX23C не удалось: {e}") from e


def mdx_separator(
    audio,
    model,
    hop_length,
    seg_size,
    overlap,
    denoise,
    model_dir,
    out_dir,
    out_format,
    norm_thresh,
    amp_thresh,
    batch_size,
    progress=gr.Progress(track_tqdm=True),
):
    """Разделяет аудио с использованием модели MDX-NET."""
    base_name = os.path.splitext(os.path.basename(audio))[0]
    print_message(audio, model)
    try:
        out_dir = prepare_output_dir(audio, out_dir)
        separator = Separator(
            log_level=logging.WARNING,
            model_file_dir=model_dir,
            output_dir=out_dir,
            output_format=out_format,
            normalization_threshold=norm_thresh,
            amplification_threshold=amp_thresh,
            use_autocast=use_autocast,
            mdx_params={
                "hop_length": hop_length,
                "segment_size": seg_size,
                "overlap": overlap,
                "batch_size": batch_size,
                "enable_denoise": denoise,
            },
        )

        progress(0.2, desc="Модель загружена...")
        separator.load_model(model_filename=model)

        progress(0.7, desc="Аудио разделено...")
        separation = separator.separate(
            audio, f"{base_name}_(Stem1)", f"{base_name}_(Stem2)"
        )
        print(f"Разделение завершено!\nРезультаты: {', '.join(separation)}")

        stems = [os.path.join(out_dir, file_name) for file_name in separation]
        return stems[0], stems[1]
    except Exception as e:
        raise RuntimeError(
            f"Разделение с использованием MDX-NET не удалось: {e}"
        ) from e


def vr_separator(
    audio,
    model,
    window_size,
    aggression,
    tta,
    post_process,
    post_process_threshold,
    high_end_process,
    model_dir,
    out_dir,
    out_format,
    norm_thresh,
    amp_thresh,
    batch_size,
    progress=gr.Progress(track_tqdm=True),
):
    """Разделяет аудио с использованием модели VR ARCH."""
    base_name = os.path.splitext(os.path.basename(audio))[0]
    print_message(audio, model)
    try:
        out_dir = prepare_output_dir(audio, out_dir)
        separator = Separator(
            log_level=logging.WARNING,
            model_file_dir=model_dir,
            output_dir=out_dir,
            output_format=out_format,
            normalization_threshold=norm_thresh,
            amplification_threshold=amp_thresh,
            use_autocast=use_autocast,
            vr_params={
                "batch_size": batch_size,
                "window_size": window_size,
                "aggression": aggression,
                "enable_tta": tta,
                "enable_post_process": post_process,
                "post_process_threshold": post_process_threshold,
                "high_end_process": high_end_process,
            },
        )

        progress(0.2, desc="Модель загружена...")
        separator.load_model(model_filename=model)

        progress(0.7, desc="Аудио разделено...")
        separation = separator.separate(
            audio, f"{base_name}_(Stem1)", f"{base_name}_(Stem2)"
        )
        print(f"Разделение завершено!\nРезультаты: {', '.join(separation)}")

        stems = [os.path.join(out_dir, file_name) for file_name in separation]
        return stems[0], stems[1]
    except Exception as e:
        raise RuntimeError(
            f"Разделение с использованием VR ARCH не удалось: {e}"
        ) from e


def demucs_separator(
    audio,
    model,
    seg_size,
    shifts,
    overlap,
    segments_enabled,
    model_dir,
    out_dir,
    out_format,
    norm_thresh,
    amp_thresh,
    progress=gr.Progress(track_tqdm=True),
):
    """Разделяет аудио с использованием модели Demucs."""
    print_message(audio, model)
    try:
        out_dir = prepare_output_dir(audio, out_dir)
        separator = Separator(
            log_level=logging.WARNING,
            model_file_dir=model_dir,
            output_dir=out_dir,
            output_format=out_format,
            normalization_threshold=norm_thresh,
            amplification_threshold=amp_thresh,
            use_autocast=use_autocast,
            demucs_params={
                "segment_size": seg_size,
                "shifts": shifts,
                "overlap": overlap,
                "segments_enabled": segments_enabled,
            },
        )

        progress(0.2, desc="Модель загружена...")
        separator.load_model(model_filename=model)

        progress(0.7, desc="Аудио разделено...")
        separation = separator.separate(audio)
        print(f"Разделение завершено!\nРезультаты: {', '.join(separation)}")

        stems = [os.path.join(out_dir, file_name) for file_name in separation]

        if model == "htdemucs_6s.yaml":
            return stems[0], stems[1], stems[2], stems[3], stems[4], stems[5]
        else:
            return stems[0], stems[1], stems[2], stems[3], None, None
    except Exception as e:
        raise RuntimeError(f"Разделение с использованием Demucs не удалось: {e}") from e


def update_stems(model):
    if model == "htdemucs_6s.yaml":
        return gr.update(visible=True)
    else:
        return gr.update(visible=False)


def uvr_tab():
    with gr.Accordion("Общие настройки", open=False):
        with gr.Group():
            model_file_dir = gr.Textbox(
                value="/tmp/audio-separator-models/",
                label="Директория для кэширования файлов моделей",
                info="Директория, где хранятся файлы моделей.",
                placeholder="/tmp/audio-separator-models/",
            )
            with gr.Row():
                output_dir = gr.Textbox(
                    value="output/separated_audio",
                    label="Директория для выходных файлов",
                    info="Директория, куда будут сохранены выходные файлы.",
                    placeholder="output",
                )
                output_format = gr.Dropdown(
                    value="wav",
                    choices=["wav", "flac", "mp3"],
                    label="Формат вывода",
                    info="Формат выходного аудиофайла.",
                )
            with gr.Row():
                norm_threshold = gr.Slider(
                    minimum=0.1,
                    maximum=1,
                    step=0.1,
                    value=0.9,
                    label="Порог нормализации",
                    info="Порог для нормализации аудио.",
                )
                amp_threshold = gr.Slider(
                    minimum=0.1,
                    maximum=1,
                    step=0.1,
                    value=0.6,
                    label="Порог усиления",
                    info="Порог для усиления аудио.",
                )
            with gr.Row():
                batch_size = gr.Slider(
                    minimum=1,
                    maximum=16,
                    step=1,
                    value=1,
                    label="Размер пакета",
                    info="Больше потребляет больше ОЗУ, но может обрабатываться немного быстрее.",
                )

    with gr.Tab("Roformer"):
        with gr.Group():
            with gr.Row():
                roformer_model = gr.Dropdown(
                    label="Выберите модель", choices=list(ROFORMER_MODELS.keys())
                )
            with gr.Row():
                roformer_seg_size = gr.Slider(
                    minimum=32,
                    maximum=4000,
                    step=32,
                    value=256,
                    label="Размер сегмента",
                    info="Больше потребляет больше ресурсов, но может дать лучшие результаты.",
                )
                roformer_override_seg_size = gr.Checkbox(
                    value=False,
                    label="Переопределить размер сегмента",
                    info="Переопределить размер сегмента модели вместо использования значения по умолчанию.",
                )
                roformer_overlap = gr.Slider(
                    minimum=2,
                    maximum=10,
                    step=1,
                    value=8,
                    label="Перекрытие",
                    info="Количество перекрытия между окнами предсказания. Меньше - лучше, но медленнее.",
                )
                roformer_pitch_shift = gr.Slider(
                    minimum=-12,
                    maximum=12,
                    step=1,
                    value=0,
                    label="Сдвиг высоты тона",
                    info="Сдвинуть высоту тона аудио на указанное количество полутонов во время обработки. Может улучшить результат для низких/высоких вокала.",
                )
        with gr.Row():
            roformer_audio = gr.Audio(label="Входной аудиофайл", type="filepath")
        with gr.Row():
            roformer_button = gr.Button("Разделить!", variant="primary")
        with gr.Row():
            roformer_stem1 = gr.Audio(
                label="Стем 1", type="filepath", interactive=False
            )
            roformer_stem2 = gr.Audio(
                label="Стем 2", type="filepath", interactive=False
            )

    with gr.Tab("MDX23C"):
        with gr.Group():
            with gr.Row():
                mdx23c_model = gr.Dropdown(
                    label="Выберите модель", choices=MDX23C_MODELS
                )
            with gr.Row():
                mdx23c_seg_size = gr.Slider(
                    minimum=32,
                    maximum=4000,
                    step=32,
                    value=256,
                    label="Размер сегмента",
                    info="Больше потребляет больше ресурсов, но может дать лучшие результаты.",
                )
                mdx23c_override_seg_size = gr.Checkbox(
                    value=False,
                    label="Переопределить размер сегмента",
                    info="Переопределить размер сегмента модели вместо использования значения по умолчанию.",
                )
                mdx23c_overlap = gr.Slider(
                    minimum=2,
                    maximum=50,
                    step=1,
                    value=8,
                    label="Перекрытие",
                    info="Количество перекрытия между окнами предсказания. Больше - лучше, но медленнее.",
                )
                mdx23c_pitch_shift = gr.Slider(
                    minimum=-12,
                    maximum=12,
                    step=1,
                    value=0,
                    label="Сдвиг высоты тона",
                    info="Сдвинуть высоту тона аудио на указанное количество полутонов во время обработки. Может улучшить результат для низких/высоких вокала.",
                )
        with gr.Row():
            mdx23c_audio = gr.Audio(label="Входной аудиофайл", type="filepath")
        with gr.Row():
            mdx23c_button = gr.Button("Разделить!", variant="primary")
        with gr.Row():
            mdx23c_stem1 = gr.Audio(label="Стем 1", type="filepath", interactive=False)
            mdx23c_stem2 = gr.Audio(label="Стем 2", type="filepath", interactive=False)

    with gr.Tab("MDX-NET"):
        with gr.Group():
            with gr.Row():
                mdx_model = gr.Dropdown(label="Выберите модель", choices=MDXNET_MODELS)
            with gr.Row():
                mdx_hop_length = gr.Slider(
                    minimum=32,
                    maximum=2048,
                    step=32,
                    value=1024,
                    label="Длина прыжка",
                    info="Обычно называется шагом в нейронных сетях; изменять только если знаете, что делаете.",
                )
                mdx_seg_size = gr.Slider(
                    minimum=32,
                    maximum=4000,
                    step=32,
                    value=256,
                    label="Размер сегмента",
                    info="Больше потребляет больше ресурсов, но может дать лучшие результаты.",
                )
                mdx_overlap = gr.Slider(
                    minimum=0.001,
                    maximum=0.999,
                    step=0.001,
                    value=0.25,
                    label="Перекрытие",
                    info="Количество перекрытия между окнами предсказания. Больше - лучше, но медленнее.",
                )
                mdx_denoise = gr.Checkbox(
                    value=False,
                    label="Денойзинг",
                    info="Включить денойзинг после разделения.",
                )
        with gr.Row():
            mdx_audio = gr.Audio(label="Входной аудиофайл", type="filepath")
        with gr.Row():
            mdx_button = gr.Button("Разделить!", variant="primary")
        with gr.Row():
            mdx_stem1 = gr.Audio(label="Стем 1", type="filepath", interactive=False)
            mdx_stem2 = gr.Audio(label="Стем 2", type="filepath", interactive=False)

    with gr.Tab("VR ARCH"):
        with gr.Group():
            with gr.Row():
                vr_model = gr.Dropdown(label="Выберите модель", choices=VR_ARCH_MODELS)
            with gr.Row():
                vr_window_size = gr.Slider(
                    minimum=320,
                    maximum=1024,
                    step=32,
                    value=512,
                    label="Размер окна",
                    info="Баланс качества и скорости. 1024 = быстро, но ниже качество, 320 = медленнее, но лучше качество.",
                )
                vr_aggression = gr.Slider(
                    minimum=1,
                    maximum=50,
                    step=1,
                    value=5,
                    label="Агрессия",
                    info="Интенсивность извлечения основного стема.",
                )
                vr_tta = gr.Checkbox(
                    value=False,
                    label="TTA",
                    info="Включить Test-Time-Augmentation; медленно, но улучшает качество.",
                )
                vr_post_process = gr.Checkbox(
                    value=False,
                    label="Постобработка",
                    info="Идентифицировать остаточные артефакты в вокальном выводе; может улучшить разделение для некоторых песен.",
                )
                vr_post_process_threshold = gr.Slider(
                    minimum=0.1,
                    maximum=0.3,
                    step=0.1,
                    value=0.2,
                    label="Порог постобработки",
                    info="Порог для постобработки.",
                )
                vr_high_end_process = gr.Checkbox(
                    value=False,
                    label="Обработка высоких частот",
                    info="Отразить недостающий частотный диапазон вывода.",
                )
        with gr.Row():
            vr_audio = gr.Audio(label="Входной аудиофайл", type="filepath")
        with gr.Row():
            vr_button = gr.Button("Разделить!", variant="primary")
        with gr.Row():
            vr_stem1 = gr.Audio(label="Стем 1", type="filepath", interactive=False)
            vr_stem2 = gr.Audio(label="Стем 2", type="filepath", interactive=False)

    with gr.Tab("Demucs"):
        with gr.Group():
            with gr.Row():
                demucs_model = gr.Dropdown(
                    label="Выберите модель", choices=DEMUCS_MODELS
                )
            with gr.Row():
                demucs_seg_size = gr.Slider(
                    minimum=1,
                    maximum=100,
                    step=1,
                    value=40,
                    label="Размер сегмента",
                    info="Размер сегментов, на которые разбивается аудио. Больше = медленнее, но лучше качество.",
                )
                demucs_shifts = gr.Slider(
                    minimum=0,
                    maximum=20,
                    step=1,
                    value=2,
                    label="Сдвиги",
                    info="Количество предсказаний со случайными сдвигами, больше = медленнее, но лучше качество.",
                )
                demucs_overlap = gr.Slider(
                    minimum=0.001,
                    maximum=0.999,
                    step=0.001,
                    value=0.25,
                    label="Перекрытие",
                    info="Перекрытие между окнами предсказания. Больше = медленнее, но лучше качество.",
                )
                demucs_segments_enabled = gr.Checkbox(
                    value=True,
                    label="Сегментная обработка",
                    info="Включить сегментную обработку.",
                )
        with gr.Row():
            demucs_audio = gr.Audio(label="Входной аудиофайл", type="filepath")
        with gr.Row():
            demucs_button = gr.Button("Разделить!", variant="primary")
        with gr.Row():
            demucs_stem1 = gr.Audio(label="Стем 1", type="filepath", interactive=False)
            demucs_stem2 = gr.Audio(label="Стем 2", type="filepath", interactive=False)
        with gr.Row():
            demucs_stem3 = gr.Audio(label="Стем 3", type="filepath", interactive=False)
            demucs_stem4 = gr.Audio(label="Стем 4", type="filepath", interactive=False)
        with gr.Row(visible=False) as stem6:
            demucs_stem5 = gr.Audio(label="Стем 5", type="filepath", interactive=False)
            demucs_stem6 = gr.Audio(label="Стем 6", type="filepath", interactive=False)

    demucs_model.change(update_stems, inputs=[demucs_model], outputs=stem6)

    roformer_button.click(
        roformer_separator,
        inputs=[
            roformer_audio,
            roformer_model,
            roformer_seg_size,
            roformer_override_seg_size,
            roformer_overlap,
            roformer_pitch_shift,
            model_file_dir,
            output_dir,
            output_format,
            norm_threshold,
            amp_threshold,
            batch_size,
        ],
        outputs=[roformer_stem1, roformer_stem2],
    )
    mdx23c_button.click(
        mdx23c_separator,
        inputs=[
            mdx23c_audio,
            mdx23c_model,
            mdx23c_seg_size,
            mdx23c_override_seg_size,
            mdx23c_overlap,
            mdx23c_pitch_shift,
            model_file_dir,
            output_dir,
            output_format,
            norm_threshold,
            amp_threshold,
            batch_size,
        ],
        outputs=[mdx23c_stem1, mdx23c_stem2],
    )
    mdx_button.click(
        mdx_separator,
        inputs=[
            mdx_audio,
            mdx_model,
            mdx_hop_length,
            mdx_seg_size,
            mdx_overlap,
            mdx_denoise,
            model_file_dir,
            output_dir,
            output_format,
            norm_threshold,
            amp_threshold,
            batch_size,
        ],
        outputs=[mdx_stem1, mdx_stem2],
    )
    vr_button.click(
        vr_separator,
        inputs=[
            vr_audio,
            vr_model,
            vr_window_size,
            vr_aggression,
            vr_tta,
            vr_post_process,
            vr_post_process_threshold,
            vr_high_end_process,
            model_file_dir,
            output_dir,
            output_format,
            norm_threshold,
            amp_threshold,
            batch_size,
        ],
        outputs=[vr_stem1, vr_stem2],
    )
    demucs_button.click(
        demucs_separator,
        inputs=[
            demucs_audio,
            demucs_model,
            demucs_seg_size,
            demucs_shifts,
            demucs_overlap,
            demucs_segments_enabled,
            model_file_dir,
            output_dir,
            output_format,
            norm_threshold,
            amp_threshold,
        ],
        outputs=[
            demucs_stem1,
            demucs_stem2,
            demucs_stem3,
            demucs_stem4,
            demucs_stem5,
            demucs_stem6,
        ],
    )
