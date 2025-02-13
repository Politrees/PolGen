from multiprocessing import cpu_count

import torch


# Конфигурация устройства и параметров
class Config:
    def __init__(self):
        # Определяем устройство для использования
        self.device = self.get_device()
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
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    # Конфигурируем параметры, специфичные для устройства
    def device_config(self):
        if torch.cuda.is_available():
            print("Используемое устройство - CUDA")
            self._configure_gpu()
        elif torch.backends.mps.is_available():
            print("Используемое устройство - MPS")
            self.device = "mps"
        else:
            print("Используемое устройство - CPU")
            self.device = "cpu"

        # Устанавливаем значения отступов, запросов, центра и максимума
        x_pad, x_query, x_center, x_max = (1, 6, 38, 41)
        # Корректируем параметры, если объем памяти GPU низкий
        if self.gpu_mem is not None and self.gpu_mem <= 4:
            x_pad, x_query, x_center, x_max = (1, 5, 30, 32)

        return x_pad, x_query, x_center, x_max

    # Конфигурируем настройки, специфичные для GPU
    def _configure_gpu(self):
        # Получаем имя GPU
        self.gpu_name = torch.cuda.get_device_name(self.device)
        # Вычисляем объем памяти GPU в ГБ
        self.gpu_mem = int(torch.cuda.get_device_properties(self.device).total_memory / 1024 / 1024 / 1024 + 0.4)
