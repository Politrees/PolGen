import torch
from multiprocessing import cpu_count


# Конфигурация устройства и параметров
class Config:
    def __init__(self):
        # Определяем устройство для использования
        self.device = self.get_device()
        # Определяем, следует ли использовать полуточность
        self.is_half = self.device == "cpu"
        # Получаем количество ядер CPU
        self.n_cpu = cpu_count()
        # Инициализируем имя GPU и объем памяти
        self.gpu_name = None
        self.gpu_mem = None
        # Конфигурируем параметры, специфичные для устройства
        self.x_pad, self.x_query, self.x_center, self.x_max = self.device_config()

    # Определяем устройство для использования
    def get_device(self):
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"

    # Конфигурируем параметры, специфичные для устройства
    def device_config(self):
        if torch.cuda.is_available():
            print("Используется CUDA устройство")
            self._configure_gpu()
        elif torch.backends.mps.is_available():
            print("Используется MPS устройство")
            self.device = "mps"
        else:
            print("Используется CPU")
            self.device = "cpu"
            self.is_half = True

        # Устанавливаем значения отступов, запросов, центра и максимума в зависимости от точности
        x_pad, x_query, x_center, x_max = (
            (3, 10, 60, 65) if self.is_half else (1, 6, 38, 41)
        )
        # Корректируем параметры, если объем памяти GPU низкий
        if self.gpu_mem is not None and self.gpu_mem <= 4:
            x_pad, x_query, x_center, x_max = (1, 5, 30, 32)

        return x_pad, x_query, x_center, x_max

    # Конфигурируем настройки, специфичные для GPU
    def _configure_gpu(self):
        # Получаем имя GPU
        self.gpu_name = torch.cuda.get_device_name(self.device)
        # Список низкопроизводительных GPU
        low_end_gpus = ["16", "P40", "P10", "1060", "1070", "1080"]
        # Проверяем, является ли GPU низкопроизводительным и не является ли он V100
        if (
            any(gpu in self.gpu_name for gpu in low_end_gpus)
            and "V100" not in self.gpu_name.upper()
        ):
            self.is_half = False
        # Вычисляем объем памяти GPU в ГБ
        self.gpu_mem = int(
            torch.cuda.get_device_properties(self.device).total_memory
            / 1024
            / 1024
            / 1024
            + 0.4
        )