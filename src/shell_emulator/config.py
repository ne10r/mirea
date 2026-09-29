"""Обработка параметров запуска эмулятора."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace


def build_argument_parser() -> ArgumentParser:
    """Создаёт парсер параметров CLI."""

    parser = ArgumentParser(
        description="Эмулятор командной оболочки UNIX-подобной ОС"
    )
    parser.add_argument(
        "--vfs-path",
        metavar="PATH",
        help="путь к физическому расположению VFS",
    )
    parser.add_argument(
        "--startup-script",
        metavar="PATH",
        help="путь к стартовому скрипту",
    )
    return parser


def parse_args(args: list[str] | None = None) -> Namespace:
    """Разбирает переданный список аргументов или аргументы процесса."""

    return build_argument_parser().parse_args(args)


def format_debug_config(config: Namespace) -> str:
    """Формирует отладочный вывод всех поддерживаемых параметров."""

    vfs_path = config.vfs_path or "<не указан>"
    startup_script = config.startup_script or "<не указан>"
    return (
        "Параметры запуска:\n"
        f"  Путь к VFS: {vfs_path}\n"
        f"  Стартовый скрипт: {startup_script}"
    )
