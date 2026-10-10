"""REPL и обработчики команд эмулятора."""

from __future__ import annotations

from dataclasses import dataclass
import getpass
from pathlib import Path
import socket
from typing import TextIO

from .parser import CommandParseError, ParsedCommand, parse_command
from .vfs import VfsLoadError, VirtualFileSystem


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


def execute_command(
    command: ParsedCommand,
    vfs: VirtualFileSystem | None = None,
) -> ExecutionResult:
    """Выполняет команды этапов 1–3.

    Без подключённой VFS ``ls`` и ``cd`` сохраняют поведение заглушек этапа 1.
    """

    if command.name == "exit":
        if command.args:
            raise CommandError("команда exit не принимает аргументы")
        raise ExitRequested

    if command.name == "vfs-info":
        if command.args:
            raise CommandError("команда vfs-info не принимает аргументы")
        if vfs is None:
            raise CommandError("VFS не подключена")
        return ExecutionResult(vfs.info())

    if command.name == "clear":
        if command.args:
            raise CommandError("команда clear не принимает аргументы")
        return ExecutionResult("\033[2J\033[H")

    if command.name == "pwd":
        if command.args:
            raise CommandError("команда pwd не принимает аргументы")
        if vfs is None:
            raise CommandError("VFS не подключена")
        return ExecutionResult(str(vfs.current_path))

    if command.name == "chown":
        if len(command.args) != 2:
            raise CommandError("использование: chown ВЛАДЕЛЕЦ[:ГРУППА] ПУТЬ")
        if vfs is None:
            raise CommandError("VFS не подключена")
        identity, path = command.args
        owner, separator, group = identity.partition(":")
        try:
            changed_owner = vfs.change_owner(path, owner, group if separator else None)
        except VfsLoadError as error:
            raise CommandError(str(error)) from error
        return ExecutionResult(f"Владелец {path}: {changed_owner}")

    if command.name in {"ls", "cd"} and vfs is None:
        arguments = " ".join(command.args)
        suffix = f" {arguments}" if arguments else ""
        return ExecutionResult(f"{command.name}{suffix}")

    if command.name == "ls":
        if len(command.args) > 1:
            raise CommandError("команда ls принимает не более одного пути")
        try:
            entries = vfs.list_directory(command.args[0] if command.args else ".")
        except VfsLoadError as error:
            raise CommandError(str(error)) from error
        return ExecutionResult("\n".join(entries) or "(пусто)")

    if command.name == "cd":
        if len(command.args) > 1:
            raise CommandError("команда cd принимает не более одного пути")
        try:
            path = vfs.change_directory(command.args[0] if command.args else ".")
        except VfsLoadError as error:
            raise CommandError(str(error)) from error
        return ExecutionResult(f"Текущий каталог: {path}")

    raise CommandError(f"неизвестная команда: {command.name}")


def execute_line(
    line: str,
    vfs: VirtualFileSystem | None = None,
) -> ExecutionResult:
    """Разбирает и выполняет одну строку."""

    try:
        command = parse_command(line)
    except CommandParseError:
        raise

    if command is None:
        return ExecutionResult()
    return execute_command(command, vfs)


def run_startup_script(
    script_path: str | Path,
    output: TextIO,
    prompt_factory=make_prompt,
    vfs: VirtualFileSystem | None = None,
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
            result = execute_line(line, vfs)
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
    vfs: VirtualFileSystem | None = None,
) -> int:
    """Запускает интерактивный цикл REPL."""

    while True:
        print(prompt_factory(), end=" ", file=output, flush=True)
        line = input_stream.readline()
        if line == "":
            print(file=output)
            return 0

        try:
            result = execute_line(line.rstrip("\n"), vfs)
        except ExitRequested:
            return 0
        except (CommandError, CommandParseError) as error:
            print(f"Ошибка: {error}", file=output)
            continue

        if result.output:
            print(result.output, file=output)
