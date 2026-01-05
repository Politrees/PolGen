import os
import re

VERSION_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "VERSION")


def get_version() -> str:
    """Получает версию проекта из файла VERSION.

    Поддерживает форматы:
    - 1.3.0
    - 1.3.0-beta.1
    - 1.3.0-alpha
    - 1.3.0-rc.2
    - v1.3.0 (префикс v удаляется)
    """
    try:
        with open(VERSION_FILE, encoding="utf-8") as f:
            version = f.read().strip()
            # Удаляем префикс 'v' если есть
            version = version.removeprefix("v")
            return version
    except FileNotFoundError:
        return "unknown"


def get_version_info() -> dict:
    """Парсит версию и возвращает её компоненты.

    Returns:
        dict: {
            'full': '1.3.8-beta.8',
            'major': 1,
            'minor': 3,
            'patch': 8,
            'prerelease': 'beta.8',
            'is_prerelease': True
        }

    """
    version = get_version()

    # Паттерн для парсинга семантической версии с пре-релизом
    pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$"
    match = re.match(pattern, version)

    if match:
        return {
            "full": version,
            "major": int(match.group(1)),
            "minor": int(match.group(2)),
            "patch": int(match.group(3)),
            "prerelease": match.group(4) or "",
            "is_prerelease": bool(match.group(4)),
        }

    return {
        "full": version,
        "major": 0,
        "minor": 0,
        "patch": 0,
        "prerelease": "",
        "is_prerelease": False,
    }


__version__ = get_version()
__version_info__ = get_version_info()
