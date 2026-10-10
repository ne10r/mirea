from io import StringIO
from pathlib import Path
import tempfile
import unittest

from shell_emulator.repl import (
    CommandError,
    ExitRequested,
    execute_command,
    execute_line,
    make_prompt,
    run_interactive,
    run_startup_script,
)
from shell_emulator.parser import ParsedCommand
from shell_emulator.vfs import VirtualFileSystem


class ReplTests(unittest.TestCase):
    def test_prompt_contains_username_and_hostname(self):
        prompt = make_prompt()

        self.assertIn("@", prompt)
        self.assertTrue(prompt.endswith(":~$"))

    def test_ls_is_a_stub(self):
        result = execute_line('ls "folder name"')

        self.assertEqual(result.output, "ls folder name")

    def test_cd_is_a_stub(self):
        result = execute_line("cd /tmp")

        self.assertEqual(result.output, "cd /tmp")

    def test_unknown_command_is_an_error(self):
        with self.assertRaisesRegex(CommandError, "неизвестная команда"):
            execute_line("whoami")

    def test_exit_raises_signal(self):
        with self.assertRaises(ExitRequested):
            execute_command(ParsedCommand("exit", ()))

    def test_interactive_mode_stops_on_exit(self):
        output = StringIO()

        code = run_interactive(
            StringIO("ls\nexit\n"),
            output,
            prompt_factory=lambda: "user@host:~$",
        )

        self.assertEqual(code, 0)
        self.assertIn("user@host:~$ ls", output.getvalue())
        self.assertIn("ls", output.getvalue())

    def test_startup_script_skips_errors(self):
        output = StringIO()
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "startup.txt"
            script.write_text("ls\nunknown\ncd \"docs\"\n", encoding="utf-8")

            code = run_startup_script(
                script,
                output,
                prompt_factory=lambda: "user@host:~$",
            )

        text = output.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("ls", text)
        self.assertIn("Ошибка в строке 2", text)
        self.assertIn("cd docs", text)

    def test_missing_startup_script_returns_error(self):
        output = StringIO()

        code = run_startup_script("missing-startup.txt", output)

        self.assertEqual(code, 1)
        self.assertIn("Ошибка чтения стартового скрипта", output.getvalue())

    def test_ls_and_cd_use_connected_vfs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vfs.xml"
            path.write_text(
                '<vfs name="demo"><directory name="docs">'
                '<file name="guide.txt">text</file></directory></vfs>',
                encoding="utf-8",
            )
            vfs = VirtualFileSystem.from_xml(path)

        self.assertEqual(execute_line("ls", vfs).output, "docs/")
        self.assertEqual(
            execute_line("cd docs", vfs).output,
            "Текущий каталог: /docs",
        )
        self.assertEqual(execute_line("ls", vfs).output, "guide.txt")

    def test_vfs_command_reports_path_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vfs.xml"
            path.write_text('<vfs><directory name="docs" /></vfs>', encoding="utf-8")
            vfs = VirtualFileSystem.from_xml(path)

        with self.assertRaisesRegex(CommandError, "путь не найден"):
            execute_line("cd missing", vfs)

    def test_stage_four_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vfs.xml"
            path.write_text('<vfs><directory name="docs" /></vfs>', encoding="utf-8")
            vfs = VirtualFileSystem.from_xml(path)

        self.assertEqual(execute_line("pwd", vfs).output, "/")
        self.assertEqual(execute_line("cd docs", vfs).output, "Текущий каталог: /docs")
        self.assertEqual(execute_line("pwd", vfs).output, "/docs")
        self.assertEqual(execute_line("clear").output, "\033[2J\033[H")

        with self.assertRaisesRegex(CommandError, "не принимает аргументы"):
            execute_line("pwd extra", vfs)

    def test_chown_changes_only_in_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vfs.xml"
            path.write_text(
                '<vfs><file name="notes.txt" owner="root" /></vfs>',
                encoding="utf-8",
            )
            vfs = VirtualFileSystem.from_xml(path)
            self.assertEqual(
                execute_line("chown alice:staff notes.txt", vfs).output,
                "Владелец notes.txt: alice:staff",
            )
            self.assertEqual(vfs.owner_for("notes.txt"), "alice:staff")
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                '<vfs><file name="notes.txt" owner="root" /></vfs>',
            )

    def test_chown_reports_invalid_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vfs.xml"
            path.write_text('<vfs><file name="notes.txt" /></vfs>', encoding="utf-8")
            vfs = VirtualFileSystem.from_xml(path)

        with self.assertRaisesRegex(CommandError, "использование"):
            execute_line("chown alice", vfs)
        with self.assertRaisesRegex(CommandError, "имя группы"):
            execute_line("chown alice: notes.txt", vfs)
