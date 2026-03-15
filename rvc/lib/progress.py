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

    Пытается вызвать как progress(value, desc=message),
    при ошибке — как progress(value, message).
    Если progress is None — ничего не делает.

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

    Args:
        percent: Значение прогресса (0.0 — 1.0).
        message: Описание текущего шага.
        is_print: Если True, выводит message в stdout.
        progress: Callback или None.
    """
    if is_print:
        print(message)
    notify_progress(progress, percent, message)


class ConsoleProgress:
    """Progress-callback для CLI: просто печатает сообщения в stdout."""

    def __call__(self, value: float, desc: str = "", **kwargs) -> None:
        if desc:
            print(desc)