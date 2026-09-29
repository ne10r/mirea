import unittest

from shell_emulator.parser import CommandParseError, parse_command


class ParserTests(unittest.TestCase):
    def test_parses_quoted_argument(self):
        command = parse_command('cd "my documents"')

        self.assertIsNotNone(command)
        self.assertEqual(command.name, "cd")
        self.assertEqual(command.args, ("my documents",))

    def test_parses_multiple_arguments(self):
        command = parse_command('ls "folder name" --details')

        self.assertEqual(command.args, ("folder name", "--details"))

    def test_empty_line(self):
        self.assertIsNone(parse_command("   "))

    def test_reports_unclosed_quotes(self):
        with self.assertRaises(CommandParseError):
            parse_command('cd "unclosed')
