import os
import sys


def colab_check() -> bool:
    """Проверьте, запускается ли интерфейс из Google Colab."""
    try:
        import google.colab

        return True
    except ImportError:
        return (
            "google.colab" in sys.modules
            or bool(os.environ.get("COLAB_GPU"))
            or bool(os.environ.get("COLAB_TPU_ADDR"))
            or (os.path.exists("/content"))
        )


def kaggle_check() -> bool:
    """Проверьте, запускается ли интерфейс из Kaggle"""
    return bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")) or bool(os.environ.get("KAGGLE_URL_BASE")) or os.path.exists("/kaggle/working")
