import logging
import os
import re
import shutil
import subprocess

import gradio as gr
import torch
from PolUVR.separator import Separator

device = "cuda" if torch.cuda.is_available() else "cpu"
use_autocast = device == "cuda"

# ===== Модели Roformer ===== #
ROFORMER_MODELS = {
    # BS Roformer
    "BS-Roformer-Viperx-1053": "model_bs_roformer_ep_937_sdr_10.5309.ckpt",
    "BS-Roformer-Viperx-1296": "model_bs_roformer_ep_368_sdr_12.9628.ckpt",
    "BS-Roformer-Viperx-1297": "model_bs_roformer_ep_317_sdr_12.9755.ckpt",
    "BS-Roformer-De-Reverb": "deverb_bs_roformer_8_384dim_10depth.ckpt",
    "BS Roformer | Chorus Male-Female by Sucial": "model_chorus_bs_roformer_ep_267_sdr_24.1275.ckpt",
    # MelBand Roformer
    "Mel-Roformer-Crowd-Aufr33-Viperx": "mel_band_roformer_crowd_aufr33_viperx_sdr_8.7144.ckpt",
    "Mel-Roformer-Karaoke-Aufr33-Viperx": "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt",
    "Mel-Roformer-Viperx-1143": "model_mel_band_roformer_ep_3005_sdr_11.4360.ckpt",
    "Mel-Roformer-Denoise-Aufr33": "denoise_mel_band_roformer_aufr33_sdr_27.9959.ckpt",
    "Mel-Roformer-Denoise-Aufr33-Aggr": "denoise_mel_band_roformer_aufr33_aggr_sdr_27.9768.ckpt",
    "MelBand Roformer | Aspiration by Sucial": "aspiration_mel_band_roformer_sdr_18.9845.ckpt",
    "MelBand Roformer | Aspiration Less Aggressive by Sucial": "aspiration_mel_band_roformer_less_aggr_sdr_18.1201.ckpt",
    "MelBand Roformer | De-Reverb by anvuew": "dereverb_mel_band_roformer_anvuew_sdr_19.1729.ckpt",
    "MelBand Roformer | De-Reverb Less Aggressive by anvuew": "dereverb_mel_band_roformer_less_aggressive_anvuew_sdr_18.8050.ckpt",
    "MelBand Roformer | De-Reverb Big by Sucial": "dereverb_big_mbr_ep_362.ckpt",
    "MelBand Roformer | De-Reverb Super Big by Sucial": "dereverb_super_big_mbr_ep_346.ckpt",
    "MelBand Roformer | De-Reverb-Echo by Sucial": "dereverb-echo_mel_band_roformer_sdr_10.0169.ckpt",
    "MelBand Roformer | De-Reverb-Echo V2 by Sucial": "dereverb-echo_mel_band_roformer_sdr_13.4843_v2.ckpt",
    "MelBand Roformer | De-Reverb-Echo Fused by Sucial": "dereverb_echo_mbr_fused.ckpt",
    "MelBand Roformer | Vocals by Kimberley Jensen": "vocals_mel_band_roformer.ckpt",
    "MelBand Roformer | Vocals by becruily": "mel_band_roformer_vocals_becruily.ckpt",
    "MelBand Roformer | Instrumental by becruily": "mel_band_roformer_instrumental_becruily.ckpt",
    "MelBand Roformer | Bleed Suppressor V1 by unwa-97chris": "mel_band_roformer_bleed_suppressor_v1.ckpt",
    # MelBand Roformer Kim
    "MelBand Roformer Kim | FT by unwa": "mel_band_roformer_kim_ft_unwa.ckpt",
    "MelBand Roformer Kim | FT 2 by unwa": "mel_band_roformer_kim_ft2_unwa.ckpt",
    "MelBand Roformer Kim | Big Beta 4 FT by unwa": "melband_roformer_big_beta4.ckpt",
    "MelBand Roformer Kim | Big Beta 5e FT by unwa": "melband_roformer_big_beta5e.ckpt",
    "MelBand Roformer Kim | Inst V1 by Unwa": "melband_roformer_inst_v1.ckpt",
    "MelBand Roformer Kim | Inst V1 (E) by Unwa": "melband_roformer_inst_v1e.ckpt",
    "MelBand Roformer Kim | Inst V2 by Unwa": "melband_roformer_inst_v2.ckpt",
    "MelBand Roformer Kim | InstVoc Duality V1 by Unwa": "melband_roformer_instvoc_duality_v1.ckpt",
    "MelBand Roformer Kim | InstVoc Duality V2 by Unwa": "melband_roformer_instvox_duality_v2.ckpt",
    "MelBand Roformer Kim | SYHFT by SYH99999": "MelBandRoformerSYHFT.ckpt",
    "MelBand Roformer Kim | SYHFT V2 by SYH99999": "MelBandRoformerSYHFTV2.ckpt",
    "MelBand Roformer Kim | SYHFT V2.5 by SYH99999": "MelBandRoformerSYHFTV2.5.ckpt",
    "MelBand Roformer Kim | SYHFT V3 by SYH99999": "MelBandRoformerSYHFTV3Epsilon.ckpt",
    "MelBand Roformer Kim | Big SYHFT V1 by SYH99999": "MelBandRoformerBigSYHFTV1.ckpt",
}
# ===== Модели MDX23C ===== #
MDX23C_MODELS = {
    "MDX23C DrumSep by aufr33-jarredou": "MDX23C-DrumSep-aufr33-jarredou.ckpt",
    "MDX23C De-Reverb by aufr33-jarredou": "MDX23C-De-Reverb-aufr33-jarredou.ckpt",
    "MDX23C-InstVoc HQ": "MDX23C-8KFFT-InstVoc_HQ.ckpt",
    "VIP | MDX23C-InstVoc HQ 2": "MDX23C-8KFFT-InstVoc_HQ_2.ckpt",
    "VIP | MDX23C_D1581": "MDX23C_D1581.ckpt",
}
# ===== Модели MDXN-NET ===== #
MDXNET_MODELS = {
    "UVR-MDX-NET 1": "UVR_MDXNET_1_9703.onnx",
    "UVR-MDX-NET 2": "UVR_MDXNET_2_9682.onnx",
    "UVR-MDX-NET 3": "UVR_MDXNET_3_9662.onnx",
    "UVR_MDXNET_9482": "UVR_MDXNET_9482.onnx",
    "UVR-MDX-NET Inst 1": "UVR-MDX-NET-Inst_1.onnx",
    "UVR-MDX-NET Inst 2": "UVR-MDX-NET-Inst_2.onnx",
    "UVR-MDX-NET Inst 3": "UVR-MDX-NET-Inst_3.onnx",
    "UVR-MDX-NET Inst HQ 1": "UVR-MDX-NET-Inst_HQ_1.onnx",
    "UVR-MDX-NET Inst HQ 2": "UVR-MDX-NET-Inst_HQ_2.onnx",
    "UVR-MDX-NET Inst HQ 3": "UVR-MDX-NET-Inst_HQ_3.onnx",
    "UVR-MDX-NET Inst HQ 4": "UVR-MDX-NET-Inst_HQ_4.onnx",
    "UVR-MDX-NET Inst HQ 5": "UVR-MDX-NET-Inst_HQ_5.onnx",
    "UVR-MDX-NET Inst Main": "UVR-MDX-NET-Inst_Main.onnx",
    "UVR-MDX-NET Karaoke": "UVR_MDXNET_KARA.onnx",
    "UVR-MDX-NET Karaoke 2": "UVR_MDXNET_KARA_2.onnx",
    "UVR-MDX-NET Main": "UVR_MDXNET_Main.onnx",
    "UVR-MDX-NET Voc FT": "UVR-MDX-NET-Voc_FT.onnx",
    "Kim Inst": "Kim_Inst.onnx",
    "Kim Vocal 1": "Kim_Vocal_1.onnx",
    "Kim Vocal 2": "Kim_Vocal_2.onnx",
    "kuielab_a_bass": "kuielab_a_bass.onnx",
    "kuielab_a_drums": "kuielab_a_drums.onnx",
    "kuielab_a_other": "kuielab_a_other.onnx",
    "kuielab_a_vocals": "kuielab_a_vocals.onnx",
    "kuielab_b_bass": "kuielab_b_bass.onnx",
    "kuielab_b_drums": "kuielab_b_drums.onnx",
    "kuielab_b_other": "kuielab_b_other.onnx",
    "kuielab_b_vocals": "kuielab_b_vocals.onnx",
    "Reverb HQ By FoxJoy": "Reverb_HQ_By_FoxJoy.onnx",
    "VIP | UVR-MDX-NET_Inst_82_beta": "UVR-MDX-NET_Inst_82_beta.onnx",
    "VIP | UVR-MDX-NET_Inst_90_beta": "UVR-MDX-NET_Inst_90_beta.onnx",
    "VIP | UVR-MDX-NET_Inst_187_beta": "UVR-MDX-NET_Inst_187_beta.onnx",
    "VIP | UVR-MDX-NET-Inst_full_292": "UVR-MDX-NET-Inst_full_292.onnx",
    "VIP | UVR-MDX-NET_Main_340": "UVR-MDX-NET_Main_340.onnx",
    "VIP | UVR-MDX-NET_Main_390": "UVR-MDX-NET_Main_390.onnx",
    "VIP | UVR-MDX-NET_Main_406": "UVR-MDX-NET_Main_406.onnx",
    "VIP | UVR-MDX-NET_Main_427": "UVR-MDX-NET_Main_427.onnx",
    "VIP | UVR-MDX-NET_Main_438": "UVR-MDX-NET_Main_438.onnx",
}
# ===== Модели VR-ARCH ===== #
VR_ARCH_MODELS = {
    "1_HP-UVR": "1_HP-UVR.pth",
    "2_HP-UVR": "2_HP-UVR.pth",
    "3_HP-Vocal-UVR": "3_HP-Vocal-UVR.pth",
    "4_HP-Vocal-UVR": "4_HP-Vocal-UVR.pth",
    "5_HP-Karaoke-UVR": "5_HP-Karaoke-UVR.pth",
    "6_HP-Karaoke-UVR": "6_HP-Karaoke-UVR.pth",
    "7_HP2-UVR": "7_HP2-UVR.pth",
    "8_HP2-UVR": "8_HP2-UVR.pth",
    "9_HP2-UVR": "9_HP2-UVR.pth",
    "10_SP-UVR-2B-32000-1": "10_SP-UVR-2B-32000-1.pth",
    "11_SP-UVR-2B-32000-2": "11_SP-UVR-2B-32000-2.pth",
    "12_SP-UVR-3B-44100": "12_SP-UVR-3B-44100.pth",
    "13_SP-UVR-4B-44100-1": "13_SP-UVR-4B-44100-1.pth",
    "14_SP-UVR-4B-44100-2": "14_SP-UVR-4B-44100-2.pth",
    "15_SP-UVR-MID-44100-1": "15_SP-UVR-MID-44100-1.pth",
    "16_SP-UVR-MID-44100-2": "16_SP-UVR-MID-44100-2.pth",
    "17_HP-Wind_Inst-UVR": "17_HP-Wind_Inst-UVR.pth",
    "MGM_HIGHEND_v4": "MGM_HIGHEND_v4.pth",
    "MGM_LOWEND_A_v4": "MGM_LOWEND_A_v4.pth",
    "MGM_LOWEND_B_v4": "MGM_LOWEND_B_v4.pth",
    "MGM_MAIN_v4": "MGM_MAIN_v4.pth",
    "UVR-BVE-4B_SN-44100-1": "UVR-BVE-4B_SN-44100-1.pth",
    "UVR-De-Reverb by aufr33-jarredou": "UVR-De-Reverb-aufr33-jarredou.pth",
    "UVR-De-Echo-Aggressive by FoxJoy": "UVR-De-Echo-Aggressive.pth",
    "UVR-De-Echo-Normal by FoxJoy": "UVR-De-Echo-Normal.pth",
    "UVR-DeEcho-DeReverb by FoxJoy": "UVR-DeEcho-DeReverb.pth",
    "UVR-DeNoise-Lite by FoxJoy": "UVR-DeNoise-Lite.pth",
    "UVR-DeNoise by FoxJoy": "UVR-DeNoise.pth",
}
# ===== Модели DEMUCS ===== #
DEMUCS_MODELS = {
    "htdemucs": "htdemucs.yaml",
    "htdemucs_6s": "htdemucs_6s.yaml",
    "htdemucs_ft": "htdemucs_ft.yaml",
    "hdemucs_mmi": "hdemucs_mmi.yaml",
}

OUTPUT_FORMAT = ["wav", "flac", "mp3", "ogg", "opus", "m4a", "aiff", "ac3"]


def print_message(input_file, model_name):
    """Отображает информацию о процессе разделения аудиофайла."""
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    print("\n")
    print("🎵 PolUVR 🎵")
    print("Обрабатываемый файл:", base_name)
    print("Используемая модель:", model_name)
    print("Идет процесс разделения аудио...")


def prepare_output_dir(input_file, output_dir):
    """Создает директорию для сохранения результатов и очищает её, если она уже существует."""
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    out_dir = os.path.join(output_dir, base_name)
    try:
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(out_dir)
    except Exception as e:
        raise RuntimeError(f"Ошибка при создании выходной директории {out_dir}: {e}") from e
    return out_dir


def rename_stems(
    audio,
    vocals_stem,
    instrumental_stem,
    other_stem,
    drums_stem,
    bass_stem,
    guitar_stem,
    piano_stem,
    model,
):
    base_name = os.path.splitext(os.path.basename(audio))[0]
    stems = {
        "Vocals": vocals_stem.replace("NAME", base_name).replace("STEM", "Vocals").replace("MODEL", model),
        "Instrumental": instrumental_stem.replace("NAME", base_name).replace("STEM", "Instrumental").replace("MODEL", model),
        "Drums": drums_stem.replace("NAME", base_name).replace("STEM", "Drums").replace("MODEL", model),
        "Bass": bass_stem.replace("NAME", base_name).replace("STEM", "Bass").replace("MODEL", model),
        "Other": other_stem.replace("NAME", base_name).replace("STEM", "Other").replace("MODEL", model),
        "Guitar": guitar_stem.replace("NAME", base_name).replace("STEM", "Guitar").replace("MODEL", model),
        "Piano": piano_stem.replace("NAME", base_name).replace("STEM", "Piano").replace("MODEL", model),
    }
    return stems


def leaderboard(list_filter, list_limit):
    try:
        result = subprocess.run(
            [
                "PolUVR",
                "-l",
                f"--list_filter={list_filter}",
                f"--list_limit={list_limit}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        if result.returncode != 0:
            return f"Ошибка: {result.stderr}"

        return (
            "<table border='1'>"
            + "".join(
                f"<tr style='{'font-weight: bold; font-size: 1.2em;' if i == 0 else ''}'>"
                + "".join(f"<td>{cell}</td>" for cell in re.split(r"\s{2,}", line.strip()))
                + "</tr>"
                for i, line in enumerate(re.findall(r"^(?!-+)(.+)$", result.stdout.strip(), re.MULTILINE))
            )
            + "</table>"
        )

    except Exception as e:
        return f"Ошибка: {e}"


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
    vocals_stem,
    instrumental_stem,
    other_stem,
    drums_stem,
    bass_stem,
    guitar_stem,
    piano_stem,
    progress=gr.Progress(track_tqdm=True),
):
    """Выполняет разделение аудио с использованием модели Roformer."""
    stemname = rename_stems(
        audio,
        vocals_stem,
        instrumental_stem,
        other_stem,
        drums_stem,
        bass_stem,
        guitar_stem,
        piano_stem,
        model_key,
    )
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

        progress(0.2, desc="Загрузка модели...")
        separator.load_model(model_filename=model)

        progress(0.7, desc="Разделение аудио...")
        separation = separator.separate(audio, stemname)
        print(f"Разделение завершено!\nРезультаты: {', '.join(separation)}")

        stems = [os.path.join(out_dir, file_name) for file_name in separation]
        return stems[0], stems[1]
    except Exception as e:
        raise RuntimeError(f"Ошибка при разделении аудио с помощью Roformer: {e}") from e


def mdx23c_separator(
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
    vocals_stem,
    instrumental_stem,
    other_stem,
    drums_stem,
    bass_stem,
    guitar_stem,
    piano_stem,
    progress=gr.Progress(track_tqdm=True),
):
    """Выполняет разделение аудио с использованием модели MDX23C."""
    stemname = rename_stems(
        audio,
        vocals_stem,
        instrumental_stem,
        other_stem,
        drums_stem,
        bass_stem,
        guitar_stem,
        piano_stem,
        model_key,
    )
    print_message(audio, model_key)
    model = MDX23C_MODELS[model_key]
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

        progress(0.2, desc="Загрузка модели...")
        separator.load_model(model_filename=model)

        progress(0.7, desc="Разделение аудио...")
        separation = separator.separate(audio, stemname)
        print(f"Разделение завершено!\nРезультаты: {', '.join(separation)}")

        stems = [os.path.join(out_dir, file_name) for file_name in separation]
        return stems[0], stems[1]
    except Exception as e:
        raise RuntimeError(f"Ошибка при разделении аудио с помощью MDX23C: {e}") from e


def mdx_separator(
    audio,
    model_key,
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
    vocals_stem,
    instrumental_stem,
    other_stem,
    drums_stem,
    bass_stem,
    guitar_stem,
    piano_stem,
    progress=gr.Progress(track_tqdm=True),
):
    """Выполняет разделение аудио с использованием модели MDX-NET."""
    stemname = rename_stems(
        audio,
        vocals_stem,
        instrumental_stem,
        other_stem,
        drums_stem,
        bass_stem,
        guitar_stem,
        piano_stem,
        model_key,
    )
    print_message(audio, model_key)
    model = MDXNET_MODELS[model_key]
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

        progress(0.2, desc="Загрузка модели...")
        separator.load_model(model_filename=model)

        progress(0.7, desc="Разделение аудио...")
        separation = separator.separate(audio, stemname)
        print(f"Разделение завершено!\nРезультаты: {', '.join(separation)}")

        stems = [os.path.join(out_dir, file_name) for file_name in separation]
        return stems[0], stems[1]
    except Exception as e:
        raise RuntimeError(f"Ошибка при разделении аудио с помощью MDX-NET: {e}") from e


def vr_separator(
    audio,
    model_key,
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
    vocals_stem,
    instrumental_stem,
    other_stem,
    drums_stem,
    bass_stem,
    guitar_stem,
    piano_stem,
    progress=gr.Progress(track_tqdm=True),
):
    """Выполняет разделение аудио с использованием модели VR ARCH."""
    stemname = rename_stems(
        audio,
        vocals_stem,
        instrumental_stem,
        other_stem,
        drums_stem,
        bass_stem,
        guitar_stem,
        piano_stem,
        model_key,
    )
    print_message(audio, model_key)
    model = VR_ARCH_MODELS[model_key]
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

        progress(0.2, desc="Загрузка модели...")
        separator.load_model(model_filename=model)

        progress(0.7, desc="Разделение аудио...")
        separation = separator.separate(audio, stemname)
        print(f"Разделение завершено!\nРезультаты: {', '.join(separation)}")

        stems = [os.path.join(out_dir, file_name) for file_name in separation]
        return stems[0], stems[1]
    except Exception as e:
        raise RuntimeError(f"Ошибка при разделении аудио с помощью VR ARCH: {e}") from e


def demucs_separator(
    audio,
    model_key,
    seg_size,
    shifts,
    overlap,
    segments_enabled,
    model_dir,
    out_dir,
    out_format,
    norm_thresh,
    amp_thresh,
    vocals_stem,
    instrumental_stem,
    other_stem,
    drums_stem,
    bass_stem,
    guitar_stem,
    piano_stem,
    progress=gr.Progress(track_tqdm=True),
):
    """Выполняет разделение аудио с использованием модели Demucs."""
    stemname = rename_stems(
        audio,
        vocals_stem,
        instrumental_stem,
        other_stem,
        drums_stem,
        bass_stem,
        guitar_stem,
        piano_stem,
        model_key,
    )
    print_message(audio, model_key)
    model = DEMUCS_MODELS[model_key]
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

        progress(0.2, desc="Загрузка модели...")
        separator.load_model(model_filename=model)

        progress(0.7, desc="Разделение аудио...")
        separation = separator.separate(audio, stemname)
        print(f"Разделение завершено!\nРезультаты: {', '.join(separation)}")

        stems = [os.path.join(out_dir, file_name) for file_name in separation]

        if model_key == "htdemucs_6s":
            return stems[0], stems[1], stems[2], stems[3], stems[4], stems[5]
        return stems[0], stems[1], stems[2], stems[3], None, None
    except Exception as e:
        raise RuntimeError(f"Ошибка при разделении аудио с помощью Demucs: {e}") from e


def update_stems(model):
    """Обновляет видимость выходных стемов в зависимости от выбранной модели Demucs."""
    if model == "htdemucs_6s":
        return gr.update(visible=True)
    return gr.update(visible=False)


def show_hide_params(param):
    """Обновляет видимость параметра в зависимости от состояния флажка."""
    return gr.update(visible=param)


def poluvr_tab():
    with gr.Tab("Roformer"):
        with gr.Group():
            with gr.Row():
                roformer_model = gr.Dropdown(
                    value="MelBand Roformer Kim | Big Beta 5e FT by unwa",
                    label="Модель",
                    choices=list(ROFORMER_MODELS.keys()),
                    scale=3,
                )
                roformer_output_format = gr.Dropdown(
                    value="wav",
                    choices=OUTPUT_FORMAT,
                    label="Формат выходного файла",
                    info="Выберите формат для сохранения результатов.",
                    scale=1,
                )
            with gr.Accordion("Дополнительные параметры", open=False):
                with gr.Column(variant="panel"):
                    with gr.Group():
                        roformer_override_seg_size = gr.Checkbox(
                            value=False,
                            label="Переопределить размер сегмента",
                            info="Использовать пользовательский размер сегмента вместо значения по умолчанию.",
                        )
                        with gr.Row():
                            roformer_seg_size = gr.Slider(
                                minimum=32,
                                maximum=4000,
                                step=32,
                                value=256,
                                label="Размер сегмента",
                                info="Увеличение размера может улучшить качество, но требует больше ресурсов.",
                                visible=False,
                            )
                            roformer_overlap = gr.Slider(
                                minimum=2,
                                maximum=10,
                                step=1,
                                value=8,
                                label="Перекрытие",
                                info="Уменьшение перекрытия улучшает качество, но замедляет обработку.",
                            )
                            roformer_pitch_shift = gr.Slider(
                                minimum=-24,
                                maximum=24,
                                step=1,
                                value=0,
                                label="Сдвиг тона",
                                info="Сдвиг тона может улучшить разделение для определенных типов голосов.",
                            )
                with gr.Column(variant="panel"):
                    with gr.Group():
                        with gr.Row():
                            roformer_batch_size = gr.Slider(
                                minimum=1,
                                maximum=16,
                                step=1,
                                value=1,
                                label="Размер пакета",
                                info="Увеличение размера пакета ускоряет обработку, но требует больше памяти.",
                            )
                            roformer_norm_threshold = gr.Slider(
                                minimum=0.1,
                                maximum=1,
                                step=0.1,
                                value=0.9,
                                label="Порог нормализации",
                                info="Порог для нормализации громкости аудио.",
                            )
                            roformer_amp_threshold = gr.Slider(
                                minimum=0.0,
                                maximum=1,
                                step=0.1,
                                value=0.0,
                                label="Порог усиления",
                                info="Порог для усиления тихих частей аудио.",
                            )
        with gr.Row():
            roformer_audio = gr.Audio(label="Входное аудио", type="filepath")
        with gr.Row():
            roformer_button = gr.Button("Запустить разделение", variant="primary")
        with gr.Row():
            roformer_stem1 = gr.Audio(label="Стем 1", type="filepath", interactive=False)
            roformer_stem2 = gr.Audio(label="Стем 2", type="filepath", interactive=False)

    with gr.Tab("MDX23C"):
        with gr.Group():
            with gr.Row():
                mdx23c_model = gr.Dropdown(
                    value="MDX23C-InstVoc HQ",
                    label="Модель",
                    choices=list(MDX23C_MODELS.keys()),
                    scale=3,
                )
                mdx23c_output_format = gr.Dropdown(
                    value="wav",
                    choices=OUTPUT_FORMAT,
                    label="Формат выходного файла",
                    info="Выберите формат для сохранения результатов.",
                    scale=1,
                )
            with gr.Accordion("Дополнительные параметры", open=False):
                with gr.Column(variant="panel"):
                    with gr.Group():
                        mdx23c_override_seg_size = gr.Checkbox(
                            value=False,
                            label="Переопределить размер сегмента",
                            info="Использовать пользовательский размер сегмента вместо значения по умолчанию.",
                        )
                        with gr.Row():
                            mdx23c_seg_size = gr.Slider(
                                minimum=32,
                                maximum=4000,
                                step=32,
                                value=256,
                                label="Размер сегмента",
                                info="Увеличение размера может улучшить качество, но требует больше ресурсов.",
                                visible=False,
                            )
                            mdx23c_overlap = gr.Slider(
                                minimum=2,
                                maximum=50,
                                step=1,
                                value=8,
                                label="Перекрытие",
                                info="Увеличение перекрытия улучшает качество, но замедляет обработку.",
                            )
                            mdx23c_pitch_shift = gr.Slider(
                                minimum=-24,
                                maximum=24,
                                step=1,
                                value=0,
                                label="Сдвиг тона",
                                info="Сдвиг тона может улучшить разделение для определенных типов голосов.",
                            )
                with gr.Column(variant="panel"):
                    with gr.Group():
                        with gr.Row():
                            mdx23c_batch_size = gr.Slider(
                                minimum=1,
                                maximum=16,
                                step=1,
                                value=1,
                                label="Размер пакета",
                                info="Увеличение размера пакета ускоряет обработку, но требует больше памяти.",
                            )
                            mdx23c_norm_threshold = gr.Slider(
                                minimum=0.1,
                                maximum=1,
                                step=0.1,
                                value=0.9,
                                label="Порог нормализации",
                                info="Порог для нормализации громкости аудио.",
                            )
                            mdx23c_amp_threshold = gr.Slider(
                                minimum=0.0,
                                maximum=1,
                                step=0.1,
                                value=0.0,
                                label="Порог усиления",
                                info="Порог для усиления тихих частей аудио.",
                            )
        with gr.Row():
            mdx23c_audio = gr.Audio(label="Входное аудио", type="filepath")
        with gr.Row():
            mdx23c_button = gr.Button("Запустить разделение", variant="primary")
        with gr.Row():
            mdx23c_stem1 = gr.Audio(label="Стем 1", type="filepath", interactive=False)
            mdx23c_stem2 = gr.Audio(label="Стем 2", type="filepath", interactive=False)

    with gr.Tab("MDX-NET"):
        with gr.Group():
            with gr.Row():
                mdx_model = gr.Dropdown(
                    value="UVR-MDX-NET Inst HQ 5",
                    label="Модель",
                    choices=list(MDXNET_MODELS.keys()),
                    scale=3,
                )
                mdx_output_format = gr.Dropdown(
                    value="wav",
                    choices=OUTPUT_FORMAT,
                    label="Формат выходного файла",
                    info="Выберите формат для сохранения результатов.",
                    scale=1,
                )
            with gr.Accordion("Дополнительные параметры", open=False):
                with gr.Column(variant="panel"):
                    with gr.Group():
                        mdx_denoise = gr.Checkbox(
                            value=False,
                            label="Шумоподавление",
                            info="Включить подавление шума после разделения.",
                        )
                        with gr.Row():
                            mdx_hop_length = gr.Slider(
                                minimum=32,
                                maximum=2048,
                                step=32,
                                value=1024,
                                label="Длина шага",
                                info="Параметр, влияющий на точность разделения.",
                            )
                            mdx_seg_size = gr.Slider(
                                minimum=32,
                                maximum=4000,
                                step=32,
                                value=256,
                                label="Размер сегмента",
                                info="Увеличение размера может улучшить качество, но требует больше ресурсов.",
                            )
                            mdx_overlap = gr.Slider(
                                minimum=0.001,
                                maximum=0.999,
                                step=0.001,
                                value=0.25,
                                label="Перекрытие",
                                info="Увеличение перекрытия улучшает качество, но замедляет обработку.",
                            )
                with gr.Column(variant="panel"):
                    with gr.Group():
                        with gr.Row():
                            mdx_batch_size = gr.Slider(
                                minimum=1,
                                maximum=16,
                                step=1,
                                value=1,
                                label="Размер пакета",
                                info="Увеличение размера пакета ускоряет обработку, но требует больше памяти.",
                            )
                            mdx_norm_threshold = gr.Slider(
                                minimum=0.1,
                                maximum=1,
                                step=0.1,
                                value=0.9,
                                label="Порог нормализации",
                                info="Порог для нормализации громкости аудио.",
                            )
                            mdx_amp_threshold = gr.Slider(
                                minimum=0.0,
                                maximum=1,
                                step=0.1,
                                value=0.0,
                                label="Порог усиления",
                                info="Порог для усиления тихих частей аудио.",
                            )
        with gr.Row():
            mdx_audio = gr.Audio(label="Входное аудио", type="filepath")
        with gr.Row():
            mdx_button = gr.Button("Запустить разделение", variant="primary")
        with gr.Row():
            mdx_stem1 = gr.Audio(label="Стем 1", type="filepath", interactive=False)
            mdx_stem2 = gr.Audio(label="Стем 2", type="filepath", interactive=False)

    with gr.Tab("VR ARCH"):
        with gr.Group():
            with gr.Row():
                vr_model = gr.Dropdown(
                    value="1_HP-UVR",
                    label="Модель",
                    choices=list(VR_ARCH_MODELS.keys()),
                    scale=3,
                )
                vr_output_format = gr.Dropdown(
                    value="wav",
                    choices=OUTPUT_FORMAT,
                    label="Формат выходного файла",
                    info="Выберите формат для сохранения результатов.",
                    scale=1,
                )
            with gr.Accordion("Дополнительные параметры", open=False):
                with gr.Column(variant="panel"):
                    with gr.Group():
                        with gr.Row():
                            vr_post_process = gr.Checkbox(
                                value=False,
                                label="Постобработка",
                                info="Включить дополнительную обработку для улучшения качества разделения.",
                            )
                            vr_tta = gr.Checkbox(
                                value=False,
                                label="TTA",
                                info="Включить увеличение времени тестирования для повышения качества.",
                            )
                            vr_high_end_process = gr.Checkbox(
                                value=False,
                                label="Обработка высоких частот",
                                info="Восстановление недостающих высоких частот.",
                            )
                        with gr.Row():
                            vr_post_process_threshold = gr.Slider(
                                minimum=0.1,
                                maximum=0.3,
                                step=0.1,
                                value=0.2,
                                label="Порог постобработки",
                                info="Порог для применения постобработки.",
                                visible=False,
                            )
                            vr_window_size = gr.Slider(
                                minimum=320,
                                maximum=1024,
                                step=32,
                                value=512,
                                label="Размер окна",
                                info="Уменьшение размера окна улучшает качество, но замедляет обработку.",
                            )
                            vr_aggression = gr.Slider(
                                minimum=1,
                                maximum=100,
                                step=1,
                                value=5,
                                label="Агрессия",
                                info="Интенсивность разделения основного стема.",
                            )
                with gr.Column(variant="panel"):
                    with gr.Group():
                        with gr.Row():
                            vr_batch_size = gr.Slider(
                                minimum=1,
                                maximum=16,
                                step=1,
                                value=1,
                                label="Размер пакета",
                                info="Увеличение размера пакета ускоряет обработку, но требует больше памяти.",
                            )
                            vr_norm_threshold = gr.Slider(
                                minimum=0.1,
                                maximum=1,
                                step=0.1,
                                value=0.9,
                                label="Порог нормализации",
                                info="Порог для нормализации громкости аудио.",
                            )
                            vr_amp_threshold = gr.Slider(
                                minimum=0.0,
                                maximum=1,
                                step=0.1,
                                value=0.0,
                                label="Порог усиления",
                                info="Порог для усиления тихих частей аудио.",
                            )
        with gr.Row():
            vr_audio = gr.Audio(label="Входное аудио", type="filepath")
        with gr.Row():
            vr_button = gr.Button("Запустить разделение", variant="primary")
        with gr.Row():
            vr_stem1 = gr.Audio(label="Стем 1", type="filepath", interactive=False)
            vr_stem2 = gr.Audio(label="Стем 2", type="filepath", interactive=False)

    with gr.Tab("Demucs"):
        with gr.Group():
            with gr.Row():
                demucs_model = gr.Dropdown(
                    value="htdemucs_ft",
                    label="Модель",
                    choices=list(DEMUCS_MODELS.keys()),
                    scale=3,
                )
                demucs_output_format = gr.Dropdown(
                    value="wav",
                    choices=OUTPUT_FORMAT,
                    label="Формат выходного файла",
                    info="Выберите формат для сохранения результатов.",
                    scale=1,
                )
            with gr.Accordion("Дополнительные параметры", open=False):
                with gr.Column(variant="panel"):
                    with gr.Group():
                        demucs_segments_enabled = gr.Checkbox(
                            value=True,
                            label="Обработка по сегментам",
                            info="Включить разделение аудио на сегменты для обработки.",
                        )
                        with gr.Row():
                            demucs_seg_size = gr.Slider(
                                minimum=1,
                                maximum=100,
                                step=1,
                                value=40,
                                label="Размер сегмента",
                                info="Увеличение размера сегмента улучшает качество, но замедляет обработку.",
                            )
                            demucs_overlap = gr.Slider(
                                minimum=0.001,
                                maximum=0.999,
                                step=0.001,
                                value=0.25,
                                label="Перекрытие",
                                info="Увеличение перекрытия улучшает качество, но замедляет обработку.",
                            )
                            demucs_shifts = gr.Slider(
                                minimum=0,
                                maximum=20,
                                step=1,
                                value=2,
                                label="Сдвиги",
                                info="Увеличение количества сдвигов улучшает качество, но замедляет обработку.",
                            )
                with gr.Column(variant="panel"):
                    with gr.Group():
                        with gr.Row():
                            demucs_norm_threshold = gr.Slider(
                                minimum=0.1,
                                maximum=1,
                                step=0.1,
                                value=0.9,
                                label="Порог нормализации",
                                info="Порог для нормализации громкости аудио.",
                            )
                            demucs_amp_threshold = gr.Slider(
                                minimum=0.0,
                                maximum=1,
                                step=0.1,
                                value=0.0,
                                label="Порог усиления",
                                info="Порог для усиления тихих частей аудио.",
                            )
        with gr.Row():
            demucs_audio = gr.Audio(label="Входное аудио", type="filepath")
        with gr.Row():
            demucs_button = gr.Button("Запустить разделение", variant="primary")
        with gr.Row():
            demucs_stem1 = gr.Audio(label="Стем 1", type="filepath", interactive=False)
            demucs_stem2 = gr.Audio(label="Стем 2", type="filepath", interactive=False)
        with gr.Row():
            demucs_stem3 = gr.Audio(label="Стем 3", type="filepath", interactive=False)
            demucs_stem4 = gr.Audio(label="Стем 4", type="filepath", interactive=False)
        with gr.Row(visible=False) as stem6:
            demucs_stem5 = gr.Audio(label="Стем 5", type="filepath", interactive=False)
            demucs_stem6 = gr.Audio(label="Стем 6", type="filepath", interactive=False)

    with gr.Tab("Настройки"):
        with gr.Group():
            with gr.Row():
                model_file_dir = gr.Textbox(
                    value="models/UVR_models",
                    label="Директория моделей",
                    info="Укажите путь для хранения файлов моделей.",
                    placeholder="models/UVR_models",
                )
                output_dir = gr.Textbox(
                    value="output/UVR_output",
                    label="Директория для результатов",
                    info="Укажите путь для сохранения выходных файлов.",
                    placeholder="output/UVR_output",
                )

        with gr.Accordion("Переименование стемов", open=False):
            gr.Markdown(
                """
                Используйте ключи для автоматического формирования имен выходных файлов.

                Доступные ключи:
                * **NAME** - Имя входного файла
                * **STEM** - Тип стема (например, Vocals, Instrumental)
                * **MODEL** - Имя модели (например, BS-Roformer-Viperx-1297)

                > Пример:
                > * **Шаблон:** NAME_(STEM)_MODEL
                > * **Результат:** Music_(Vocals)_BS-Roformer-Viperx-1297
                """
            )
            with gr.Row():
                vocals_stem = gr.Textbox(
                    value="NAME_(STEM)_MODEL",
                    label="Вокальный стем",
                    info="Пример: Music_(Vocals)_BS-Roformer-Viperx-1297",
                    placeholder="NAME_(STEM)_MODEL",
                )
                instrumental_stem = gr.Textbox(
                    value="NAME_(STEM)_MODEL",
                    label="Инструментальный стем",
                    info="Пример: Music_(Instrumental)_BS-Roformer-Viperx-1297",
                    placeholder="NAME_(STEM)_MODEL",
                )
                other_stem = gr.Textbox(
                    value="NAME_(STEM)_MODEL",
                    label="Другой стем",
                    info="Пример: Music_(Other)_BS-Roformer-Viperx-1297",
                    placeholder="NAME_(STEM)_MODEL",
                )
            with gr.Row():
                drums_stem = gr.Textbox(
                    value="NAME_(STEM)_MODEL",
                    label="Барабанный стем",
                    info="Пример: Music_(Drums)_BS-Roformer-Viperx-1297",
                    placeholder="NAME_(STEM)_MODEL",
                )
                bass_stem = gr.Textbox(
                    value="NAME_(STEM)_MODEL",
                    label="Басовый стем",
                    info="Пример: Music_(Bass)_BS-Roformer-Viperx-1297",
                    placeholder="NAME_(STEM)_MODEL",
                )
            with gr.Row():
                guitar_stem = gr.Textbox(
                    value="NAME_(STEM)_MODEL",
                    label="Гитарный стем",
                    info="Пример: Music_(Guitar)_BS-Roformer-Viperx-1297",
                    placeholder="NAME_(STEM)_MODEL",
                )
                piano_stem = gr.Textbox(
                    value="NAME_(STEM)_MODEL",
                    label="Пианинный стем",
                    info="Пример: Music_(Piano)_BS-Roformer-Viperx-1297",
                    placeholder="NAME_(STEM)_MODEL",
                )

    with gr.Tab("Рейтинг моделей"):
        with gr.Group():
            with gr.Row(equal_height=True):
                list_filter = gr.Dropdown(
                    value="vocals",
                    choices=[
                        "vocals",
                        "instrumental",
                        "drums",
                        "bass",
                        "guitar",
                        "piano",
                        "other",
                    ],
                    label="Фильтр",
                    info="Фильтровать модели по типу стема.",
                )
                list_limit = gr.Slider(
                    minimum=1,
                    maximum=10,
                    step=1,
                    value=5,
                    label="Лимит",
                    info="Ограничить количество отображаемых моделей.",
                )
                list_button = gr.Button("Обновить список", variant="primary")

        output_list = gr.HTML(label="Рейтинг моделей")

    roformer_override_seg_size.change(
        show_hide_params,
        inputs=[roformer_override_seg_size],
        outputs=[roformer_seg_size],
    )
    mdx23c_override_seg_size.change(show_hide_params, inputs=[mdx23c_override_seg_size], outputs=[mdx23c_seg_size])
    vr_post_process.change(show_hide_params, inputs=[vr_post_process], outputs=[vr_post_process_threshold])

    demucs_model.change(update_stems, inputs=[demucs_model], outputs=stem6)

    list_button.click(leaderboard, inputs=[list_filter, list_limit], outputs=output_list)

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
            roformer_output_format,
            roformer_norm_threshold,
            roformer_amp_threshold,
            roformer_batch_size,
            vocals_stem,
            instrumental_stem,
            other_stem,
            drums_stem,
            bass_stem,
            guitar_stem,
            piano_stem,
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
            mdx23c_output_format,
            mdx23c_norm_threshold,
            mdx23c_amp_threshold,
            mdx23c_batch_size,
            vocals_stem,
            instrumental_stem,
            other_stem,
            drums_stem,
            bass_stem,
            guitar_stem,
            piano_stem,
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
            mdx_output_format,
            mdx_norm_threshold,
            mdx_amp_threshold,
            mdx_batch_size,
            vocals_stem,
            instrumental_stem,
            other_stem,
            drums_stem,
            bass_stem,
            guitar_stem,
            piano_stem,
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
            vr_output_format,
            vr_norm_threshold,
            vr_amp_threshold,
            vr_batch_size,
            vocals_stem,
            instrumental_stem,
            other_stem,
            drums_stem,
            bass_stem,
            guitar_stem,
            piano_stem,
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
            demucs_output_format,
            demucs_norm_threshold,
            demucs_amp_threshold,
            vocals_stem,
            instrumental_stem,
            other_stem,
            drums_stem,
            bass_stem,
            guitar_stem,
            piano_stem,
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
