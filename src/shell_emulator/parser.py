"""Разбор команд интерактивного режима и стартовых скриптов."""

from __future__ import annotations

from dataclasses import dataclass
import shlex


class CommandParseError(ValueError):
    """Возникает, если строку команды нельзя разобрать."""


@dataclass(frozen=True)
class ParsedCommand:
    """Команда с именем и позиционными аргументами."""

    name: str
    args: tuple[str, ...]


def parse_command(line: str) -> ParsedCommand | None:
    """Разбирает строку, сохраняя аргументы в кавычках единым значением."""

    try:
        parts = shlex.split(line, posix=True)
    except ValueError as error:
        raise CommandParseError(f"ошибка разбора команды: {error}") from error

    if not parts:
        return None

    return ParsedCommand(parts[0], tuple(parts[1:]))
