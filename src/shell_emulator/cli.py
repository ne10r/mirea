"""Точка входа приложения."""

from __future__ import annotations

import sys

from .config import format_debug_config, parse_args
from .repl import run_interactive, run_startup_script
from .vfs import VfsLoadError, VirtualFileSystem


def main(argv: list[str] | None = None) -> int:
    """Запускает эмулятор в интерактивном или скриптовом режиме."""

    config = parse_args(argv)
    print(format_debug_config(config))

    vfs = None
    if config.vfs_path:
        try:
            vfs = VirtualFileSystem.from_xml(config.vfs_path)
        except VfsLoadError as error:
            print(f"Ошибка загрузки VFS: {error}", file=sys.stderr)
            return 1

    if config.startup_script:
        return run_startup_script(config.startup_script, sys.stdout, vfs=vfs)

    return run_interactive(sys.stdin, sys.stdout, vfs=vfs)
