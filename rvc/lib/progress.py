"""Единый протокол прогресса для всего проекта PolGen.

Используется как общий интерфейс для:
- Gradio UI (gr.Progress)
- Desktop backend (_JobProgressAdapter)
- CLI (ConsoleProgress)
- Core-функции (rvc_infer, model_manager, uvr_core, download_source)

Все core-функции принимают `progress: ProgressCallback = None`.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProgressCallback(Protocol):
    """Протокол для progress-callback.

    Любой callable, который можно вызвать как:
        progress(0.5, desc="Загрузка...")
    или:
        progress(0.5, "Загрузка...")

    Совместим с:
        - gr.Progress (Gradio)
        - _JobProgressAdapter (Desktop backend)
        - ConsoleProgress (CLI)
        - None (когда прогресс не нужен)
    """

    def __call__(self, value: float, desc: str = "", **kwargs) -> None: ...


def notify_progress(progress: ProgressCallback | None, value: float, message: str) -> None:
    """Безопасный вызов progress callback.

    Args:
        progress: Callback или None.
        value: Значение прогресса (0.0 — 1.0).
        message: Описание текущего шага.
    """
    if progress is None:
        return
    try:
        progress(value, desc=message)
    except TypeError:
        try:
            progress(value, message)
        except Exception:
            pass


def display_progress(
    percent: float,
    message: str,
    is_print: bool,
    progress: ProgressCallback | None = None,
) -> None:
    """Уведомляет о прогрессе через callback и/или print.

    Логика:
    - is_print=True: всегда печатает в stdout (серверный лог для Gradio/Desktop,
      основной вывод для CLI).
    - progress callback: всегда вызывается (обновляет UI в Gradio, SSE в Desktop).
    - ConsoleProgress: НЕ печатает если is_print=True (избегает дублирования),
      печатает только progress-only сообщения (is_print=False).

    Args:
        percent: Значение прогресса (0.0 — 1.0).
        message: Описание текущего шага.
        is_print: Если True, выводит message в stdout.
        progress: Callback или None.
    """
    if is_print:
        print(message)
        # Помечаем для ConsoleProgress, что сообщение уже напечатано
        if isinstance(progress, ConsoleProgress):
            progress.mark_printed(message)

    notify_progress(progress, percent, message)


class ConsoleProgress:
    """Progress-callback для CLI: печатает сообщения в stdout.

    Избегает дублирования: если display_progress уже напечатал сообщение
    (is_print=True), ConsoleProgress его пропускает.
    """

    def __init__(self) -> None:
        self._already_printed: set[str] = set()

    def __call__(self, value: float, desc: str = "", **kwargs) -> None:
        if desc and desc not in self._already_printed:
            print(desc)

    def mark_printed(self, message: str) -> None:
        """Помечает сообщение как уже напечатанное (вызывается из display_progress)."""
        self._already_printed.add(message)