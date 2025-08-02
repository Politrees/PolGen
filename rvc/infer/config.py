from multiprocessing import cpu_count

import torch


class Config:
    def __init__(self):
        # Определение устройства
        self.device = self._get_device()
        print(f"Используемое устройство: {self.device}")

        # Конфигурация параметров GPU
        self.gpu_name, self.gpu_mem = (self._configure_gpu() if self.device == "cuda" else (None, None))

        # Установка параметров на основе памяти GPU
        self.x_pad, self.x_query, self.x_center, self.x_max = self._get_device_params()

    def _get_device(self):
        """Определяет доступное устройство (cuda, mps или cpu)."""
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _configure_gpu(self):
        """Возвращает имя и объем памяти GPU."""
        gpu_name = torch.cuda.get_device_name(self.device)
        total_memory_bytes = torch.cuda.get_device_properties(self.device).total_memory
        # Преобразуем байты в ГБ и округляем
        gpu_mem = round(total_memory_bytes / 1024**3)
        return gpu_name, gpu_mem

    def _get_device_params(self):
        """Возвращает параметры, специфичные для устройства, в зависимости от памяти GPU."""
        if self.gpu_mem is not None and self.gpu_mem <= 4:
            # Параметры для GPU с низкой памятью
            return (1, 5, 30, 32)
        else:
            # Параметры по умолчанию
            return (1, 6, 38, 41)
