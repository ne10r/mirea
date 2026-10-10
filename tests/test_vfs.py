import tempfile
from pathlib import Path
import unittest

from shell_emulator.vfs import VfsLoadError, VirtualFileSystem


class VirtualFileSystemTests(unittest.TestCase):
    def write_xml(self, directory: str, content: str) -> Path:
        path = Path(directory) / "vfs.xml"
        path.write_text(content, encoding="utf-8")
        return path

    def test_loads_nested_text_and_base64_files_in_memory(self):
        xml = """
        <vfs name="test">
          <directory name="docs">
            <file name="guide.txt">hello</file>
            <file name="data.bin" encoding="base64">AAEC</file>
          </directory>
        </vfs>
        """
        with tempfile.TemporaryDirectory() as directory:
            vfs = VirtualFileSystem.from_xml(self.write_xml(directory, xml))

        self.assertEqual(vfs.name, "test")
        self.assertEqual(vfs.list_directory(), ["docs/"])
        self.assertEqual(vfs.change_directory("docs"), Path("/docs"))
        self.assertEqual(vfs.list_directory(), ["data.bin", "guide.txt"])
        self.assertEqual(len(vfs.data_sha256()), 64)

    def test_rejects_invalid_xml(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_xml(directory, "<vfs><file name='broken'>")

            with self.assertRaises(VfsLoadError):
                VirtualFileSystem.from_xml(path)

    def test_rejects_duplicate_names(self):
        xml = '<vfs><file name="same" /><file name="same" /></vfs>'
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(VfsLoadError, "дублирующееся имя"):
                VirtualFileSystem.from_xml(self.write_xml(directory, xml))

    def test_does_not_allow_leaving_root(self):
        with tempfile.TemporaryDirectory() as directory:
            vfs = VirtualFileSystem.from_xml(
                self.write_xml(directory, '<vfs><directory name="docs" /></vfs>')
            )

        self.assertEqual(vfs.change_directory(".."), Path("/"))
        self.assertEqual(vfs.change_directory("../docs"), Path("/docs"))
        self.assertEqual(vfs.change_directory("/"), Path("/"))
