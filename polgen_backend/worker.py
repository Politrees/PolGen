from __future__ import annotations

import gc
import json
import os
import sys
import traceback
from typing import Any

os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def emit(event: dict[str, Any]) -> None:
    payload = json.dumps(event, ensure_ascii=False)
    print(f"POLGEN_EVENT {payload}", flush=True)


class ProgressProxy:
    def __call__(self, percent: float, desc: str = "") -> None:
        emit({"type": "progress", "progress": float(percent), "message": str(desc)})


def main() -> int:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            emit({"type": "error", "error": "Worker: пустой stdin (нет payload)."})
            return 2

        payload = json.loads(raw)
        mode = payload.get("mode")

        # ensure base models
        from assets.model_installer import check_and_install_models

        check_and_install_models()

        if mode == "convert":
            from rvc.infer.infer import rvc_infer

            out_path = rvc_infer(
                rvc_model=payload["rvc_model"],
                input_path=payload["input_path"],
                f0_method=payload.get("f0_method", "rmvpe"),
                f0_min=payload.get("f0_min", 50),
                f0_max=payload.get("f0_max", 1100),
                rvc_pitch=payload.get("rvc_pitch", 0),
                protect=payload.get("protect", 0.5),
                index_rate=payload.get("index_rate", 0.0),
                volume_envelope=payload.get("volume_envelope", 1.0),
                autopitch=payload.get("autopitch", False),
                autopitch_threshold=payload.get("autopitch_threshold", 155.0),
                autotune=payload.get("autotune", False),
                autotune_tonic=payload.get("autotune_tonic", "C"),
                autotune_scale=payload.get("autotune_scale", "chromatic"),
                autotune_strength=payload.get("autotune_strength", 1.0),
                audio_upscaling=payload.get("audio_upscaling", False),
                stereo_sound=payload.get("stereo_sound", False),
                output_format=payload.get("output_format", "mp3"),
                progress=ProgressProxy(),
            )
            emit({"type": "result", "result": {"output_path": out_path}})
            return 0

        if mode == "tts_convert":
            from rvc.infer.infer import rvc_edgetts_infer

            tts_path, out_path = rvc_edgetts_infer(
                rvc_model=payload["rvc_model"],
                f0_method=payload.get("f0_method", "rmvpe"),
                f0_min=payload.get("f0_min", 50),
                f0_max=payload.get("f0_max", 1100),
                rvc_pitch=payload.get("rvc_pitch", 0),
                protect=payload.get("protect", 0.5),
                index_rate=payload.get("index_rate", 0.0),
                volume_envelope=payload.get("volume_envelope", 1.0),
                autopitch=payload.get("autopitch", False),
                autopitch_threshold=payload.get("autopitch_threshold", 155.0),
                autotune=payload.get("autotune", False),
                autotune_tonic=payload.get("autotune_tonic", "C"),
                autotune_scale=payload.get("autotune_scale", "chromatic"),
                autotune_strength=payload.get("autotune_strength", 1.0),
                stereo_sound=payload.get("stereo_sound", False),
                output_format=payload.get("output_format", "mp3"),
                tts_voice=payload["tts_voice"],
                tts_text=payload["tts_text"],
                tts_rate=payload.get("tts_rate", 0),
                tts_volume=payload.get("tts_volume", 0),
                tts_pitch=payload.get("tts_pitch", 0),
                audio_upscaling=payload.get("audio_upscaling", False),
                progress=ProgressProxy(),
            )
            emit({"type": "result", "result": {"tts_path": tts_path, "output_path": out_path}})
            return 0

        # ===== Model install modes =====
        from polgen_backend.model_install import (
            install_rvc_from_files,
            install_rvc_from_url,
            install_rvc_from_zip,
        )

        if mode == "install_rvc_url":
            out_dir = install_rvc_from_url(payload["url"], payload["model_name"], progress=ProgressProxy())
            emit({"type": "result", "result": {"message": "RVC model installed", "model_dir": out_dir}})
            return 0

        if mode == "install_rvc_zip":
            out_dir = install_rvc_from_zip(payload["zip_path"], payload["model_name"], progress=ProgressProxy())
            emit({"type": "result", "result": {"message": "RVC model installed", "model_dir": out_dir}})
            return 0

        if mode == "install_rvc_files":
            out_dir = install_rvc_from_files(
                payload["pth_path"],
                payload.get("index_path"),
                payload["model_name"],
                progress=ProgressProxy(),
            )
            emit({"type": "result", "result": {"message": "RVC model installed", "model_dir": out_dir}})
            return 0

        emit({"type": "error", "error": f"Worker: неизвестный mode={mode!r}"})
        return 2

    except Exception as e:
        tb = traceback.format_exc()
        emit({"type": "error", "error": f"{e!s}\n\n{tb}"})
        return 1
    finally:
        try:
            gc.collect()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())