"""Точка входа приложения."""

from __future__ import annotations

import sys

from .config import format_debug_config, parse_args
from .repl import run_interactive, run_startup_script


def main(argv: list[str] | None = None) -> int:
    """Запускает эмулятор в интерактивном или скриптовом режиме."""

    config = parse_args(argv)
    print(format_debug_config(config))

    if config.startup_script:
        return run_startup_script(config.startup_script, sys.stdout)

    return run_interactive(sys.stdin, sys.stdout)
