"""Точка входа приложения."""

from __future__ import annotations

import sys

from .repl import run_interactive


def main(argv: list[str] | None = None) -> int:
    """Запускает интерактивный эмулятор."""

    return run_interactive(sys.stdin, sys.stdout)
