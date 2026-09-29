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
