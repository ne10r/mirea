"""REPL и обработчики команд эмулятора."""

from __future__ import annotations

from dataclasses import dataclass
import getpass
from pathlib import Path
import socket
from typing import TextIO

from .parser import CommandParseError, ParsedCommand, parse_command
from .vfs import VfsLoadError, VirtualFileSystem


MAX_PATH_ARGUMENTS = 1
CHOWN_ARGUMENT_COUNT = 2


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


def _reject_arguments(command: ParsedCommand) -> None:
    if command.args:
        raise CommandError(
            f"команда {command.name} не принимает аргументы"
        )


def _require_vfs(vfs: VirtualFileSystem | None) -> VirtualFileSystem:
    if vfs is None:
        raise CommandError("VFS не подключена")
    return vfs


def _execute_exit(
    command: ParsedCommand,
    vfs: VirtualFileSystem | None,
) -> ExecutionResult:
    _reject_arguments(command)
    raise ExitRequested


def _execute_vfs_info(
    command: ParsedCommand,
    vfs: VirtualFileSystem | None,
) -> ExecutionResult:
    _reject_arguments(command)
    return ExecutionResult(_require_vfs(vfs).info())


def _execute_clear(
    command: ParsedCommand,
    vfs: VirtualFileSystem | None,
) -> ExecutionResult:
    _reject_arguments(command)
    return ExecutionResult("\033[2J\033[H")


def _execute_pwd(
    command: ParsedCommand,
    vfs: VirtualFileSystem | None,
) -> ExecutionResult:
    _reject_arguments(command)
    return ExecutionResult(str(_require_vfs(vfs).current_path))


def _execute_chown(
    command: ParsedCommand,
    vfs: VirtualFileSystem | None,
) -> ExecutionResult:
    if len(command.args) != CHOWN_ARGUMENT_COUNT:
        raise CommandError(
            "использование: chown ВЛАДЕЛЕЦ[:ГРУППА] ПУТЬ"
        )

    connected_vfs = _require_vfs(vfs)
    identity, path = command.args
    owner, separator, group = identity.partition(":")
    try:
        changed_owner = connected_vfs.change_owner(
            path,
            owner,
            group if separator else None,
        )
    except VfsLoadError as error:
        raise CommandError(str(error)) from error
    return ExecutionResult(f"Владелец {path}: {changed_owner}")


def _stub_command(command: ParsedCommand) -> ExecutionResult:
    arguments = " ".join(command.args)
    suffix = f" {arguments}" if arguments else ""
    return ExecutionResult(f"{command.name}{suffix}")


def _path_argument(command: ParsedCommand) -> str:
    if len(command.args) > MAX_PATH_ARGUMENTS:
        raise CommandError(
            f"команда {command.name} принимает "
            "не более одного пути"
        )
    return command.args[0] if command.args else "."


def _execute_ls(
    command: ParsedCommand,
    vfs: VirtualFileSystem | None,
) -> ExecutionResult:
    path = _path_argument(command)
    try:
        entries = _require_vfs(vfs).list_directory(path)
    except VfsLoadError as error:
        raise CommandError(str(error)) from error
    return ExecutionResult("\n".join(entries) or "(пусто)")


def _execute_cd(
    command: ParsedCommand,
    vfs: VirtualFileSystem | None,
) -> ExecutionResult:
    path = _path_argument(command)
    try:
        new_path = _require_vfs(vfs).change_directory(path)
    except VfsLoadError as error:
        raise CommandError(str(error)) from error
    return ExecutionResult(f"Текущий каталог: {new_path}")


def execute_command(
    command: ParsedCommand,
    vfs: VirtualFileSystem | None = None,
) -> ExecutionResult:
    """Выполняет команды этапов 1–5."""

    if command.name in {"ls", "cd"} and vfs is None:
        return _stub_command(command)

    handlers = {
        "exit": _execute_exit,
        "vfs-info": _execute_vfs_info,
        "clear": _execute_clear,
        "pwd": _execute_pwd,
        "chown": _execute_chown,
        "ls": _execute_ls,
        "cd": _execute_cd,
    }
    handler = handlers.get(command.name)
    if handler is None:
        raise CommandError(f"неизвестная команда: {command.name}")
    return handler(command, vfs)


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
