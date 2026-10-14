import unittest

from shell_emulator.config import format_debug_config, parse_args


class ConfigTests(unittest.TestCase):
    def test_parses_supported_parameters(self):
        config = parse_args(
            ["--vfs-path", "vfs.xml", "--startup-script", "demo.txt"]
        )

        self.assertEqual(config.vfs_path, "vfs.xml")
        self.assertEqual(config.startup_script, "demo.txt")

    def test_debug_output_contains_all_parameters(self):
        config = parse_args(
            ["--vfs-path", "vfs.xml", "--startup-script", "demo.txt"]
        )

        text = format_debug_config(config)

        self.assertIn("vfs.xml", text)
        self.assertIn("demo.txt", text)

    def test_debug_output_marks_missing_parameters(self):
        text = format_debug_config(parse_args([]))

        self.assertEqual(text.count("<не указан>"), 2)
