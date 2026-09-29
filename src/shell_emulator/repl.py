"""REPL и обработчики команд эмулятора."""

from __future__ import annotations

from dataclasses import dataclass
import getpass
from pathlib import Path
import socket
from typing import TextIO

from .parser import CommandParseError, ParsedCommand, parse_command


class CommandError(RuntimeError):
    """Ошибка выполнения команды."""


class ExitRequested(Exception):
    """Сигнал завершения REPL или стартового скрипта."""


@dataclass(frozen=True)
class ExecutionResult:
    """Результат выполнения одной команды."""

    output: str = ""


def make_prompt() -> str:
    """Возвращает приглашение на основе реальных данных ОС."""

    username = getpass.getuser()
    hostname = socket.gethostname() or "localhost"
    return f"{username}@{hostname}:~$"


def execute_command(command: ParsedCommand) -> ExecutionResult:
    """Выполняет команды этапа 1–2.

    Команды ``ls`` и ``cd`` пока являются заглушками и не меняют VFS.
    """

    if command.name == "exit":
        if command.args:
            raise CommandError("команда exit не принимает аргументы")
        raise ExitRequested

    if command.name in {"ls", "cd"}:
        arguments = " ".join(command.args)
        suffix = f" {arguments}" if arguments else ""
        return ExecutionResult(f"{command.name}{suffix}")

    raise CommandError(f"неизвестная команда: {command.name}")


def execute_line(line: str) -> ExecutionResult:
    """Разбирает и выполняет одну строку."""

    try:
        command = parse_command(line)
    except CommandParseError:
        raise

    if command is None:
        return ExecutionResult()
    return execute_command(command)


def run_startup_script(
    script_path: str | Path,
    output: TextIO,
    prompt_factory=make_prompt,
) -> int:
    """Выполняет команды скрипта, пропуская строки с ошибками."""

    path = Path(script_path)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        print(f"Ошибка чтения стартового скрипта: {error}", file=output)
        return 1

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue

        print(f"{prompt_factory()} {line}", file=output)
        try:
            result = execute_line(line)
        except ExitRequested:
            print("Сеанс завершён.", file=output)
            return 0
        except (CommandError, CommandParseError) as error:
            print(f"Ошибка в строке {line_number}: {error}", file=output)
            continue

        if result.output:
            print(result.output, file=output)

    return 0


def run_interactive(
    input_stream: TextIO,
    output: TextIO,
    prompt_factory=make_prompt,
) -> int:
    """Запускает интерактивный цикл REPL."""

    while True:
        print(prompt_factory(), end=" ", file=output, flush=True)
        line = input_stream.readline()
        if line == "":
            print(file=output)
            return 0

        try:
            result = execute_line(line.rstrip("\n"))
        except ExitRequested:
            return 0
        except (CommandError, CommandParseError) as error:
            print(f"Ошибка: {error}", file=output)
            continue

        if result.output:
            print(result.output, file=output)
