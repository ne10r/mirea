"""Модель виртуальной файловой системы, загружаемой из XML.
"""

from __future__ import annotations

from base64 import b64decode
from dataclasses import dataclass, field
import hashlib
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as element_tree


DIRECTORY_TAGS = frozenset(("directory", "dir", "folder"))


class VfsLoadError(ValueError):
    """Ошибка чтения или проверки XML-файла VFS."""


@dataclass
class VfsNode:
    """Узел дерева VFS с каталогами и байтовым содержимым файлов.
    """

    name: str
    is_directory: bool
    content: bytes = b""
    owner: str = "root"
    group: str = "root"
    children: dict[str, "VfsNode"] = field(default_factory=dict)

    def add_child(self, child: "VfsNode") -> None:
        """Добавляет дочерний узел, отклоняя дубликаты имён.
        """

        if not self.is_directory:
            raise VfsLoadError(
                f"файл не может содержать "
                f"дочерние элементы: {self.name}"
            )
        if child.name in self.children:
            raise VfsLoadError(
                f"дублирующееся имя в каталоге "
                f"{self.name}: {child.name}"
            )
        self.children[child.name] = child


class VirtualFileSystem:
    """Дерево VFS, все операции над которым выполняются только в памяти.
    """

    def __init__(self, name: str, root: VfsNode) -> None:
        self.name = name
        self.root = root
        self.current_path = PurePosixPath("/")

    @classmethod
    def from_xml(cls, path: str | Path) -> "VirtualFileSystem":
        """Загружает VFS из XML, не изменяя исходный файл.
        """

        source = Path(path)
        try:
            document = element_tree.parse(source)
        except OSError as error:
            raise VfsLoadError(
                f"не удалось открыть VFS: {error}"
            ) from error
        except element_tree.ParseError as error:
            raise VfsLoadError(
                f"некорректный XML VFS: {error}"
            ) from error

        xml_root = document.getroot()
        if xml_root.tag not in {"vfs", "filesystem"}:
            raise VfsLoadError(
                "корневой элемент VFS должен иметь имя vfs "
                "или filesystem"
            )

        vfs_name = (xml_root.get("name") or source.stem).strip()
        if not vfs_name:
            raise VfsLoadError(
                "имя VFS не может быть пустым"
            )

        root = VfsNode("/", is_directory=True)
        for element in xml_root:
            root.add_child(cls._parse_node(element))
        return cls(vfs_name, root)

    @classmethod
    def _parse_node(cls, element: element_tree.Element) -> VfsNode:
        """Преобразует XML-элемент в узел VFS."""

        tag = element.tag.lower()
        name = cls._get_node_name(element)
        if tag in DIRECTORY_TAGS:
            return cls._parse_directory(element, name)

        if tag != "file":
            raise VfsLoadError(
                f"неизвестный элемент VFS: <{element.tag}>"
            )

        return cls._parse_file(element, name)

    @staticmethod
    def _get_node_name(element: element_tree.Element) -> str:
        name = element.get("name")
        if not name:
            raise VfsLoadError(
                f"у элемента <{element.tag}> "
                "отсутствует имя"
            )
        if name in {".", "..", "/"} or "/" in name or "\\" in name:
            raise VfsLoadError(
                f"недопустимое имя узла VFS: {name}"
            )
        return name

    @classmethod
    def _parse_directory(
        cls,
        element: element_tree.Element,
        name: str,
    ) -> VfsNode:
        node = VfsNode(
            name,
            is_directory=True,
            owner=element.get("owner", "root"),
            group=element.get("group", "root"),
        )
        if (element.text or "").strip():
            raise VfsLoadError(
                f"каталог содержит текстовые "
                f"данные: {name}"
            )
        for child_element in element:
            node.add_child(cls._parse_node(child_element))
        return node

    @classmethod
    def _parse_file(
        cls,
        element: element_tree.Element,
        name: str,
    ) -> VfsNode:
        content = cls._decode_file_content(element, name)
        if list(element):
            raise VfsLoadError(
                f"файл содержит вложенные "
                f"элементы: {name}"
            )
        return VfsNode(
            name,
            is_directory=False,
            content=content,
            owner=element.get("owner", "root"),
            group=element.get("group", "root"),
        )

    @staticmethod
    def _decode_file_content(
        element: element_tree.Element,
        name: str,
    ) -> bytes:
        encoding = (element.get("encoding") or "utf-8").lower()
        raw_content = element.text or ""
        if encoding == "utf-8":
            return raw_content.encode("utf-8")
        if encoding != "base64":
            raise VfsLoadError(
                f"неподдерживаемая кодировка "
                f"файла: {encoding}"
            )
        try:
            return b64decode("".join(raw_content.split()), validate=True)
        except ValueError as error:
            raise VfsLoadError(
                f"некорректные base64-данные "
                f"файла {name}"
            ) from error

    def _resolve(self, path: str = ".") -> VfsNode:
        """Находит узел по POSIX-пути относительно текущего каталога.
        """

        requested = PurePosixPath(path or ".")
        parts = list(requested.parts)
        node = self.root if requested.is_absolute() else self._current_node()
        for part in parts:
            if part in {"", ".", "/"}:
                continue
            if part == "..":
                node = self._node_for_path(self._parent_path(node))
                continue
            if not node.is_directory or part not in node.children:
                raise VfsLoadError(f"путь не найден: {path}")
            node = node.children[part]
        return node

    def _current_node(self) -> VfsNode:
        return self._node_for_path(self.current_path)

    def _node_for_path(self, path: PurePosixPath) -> VfsNode:
        node = self.root
        for part in path.parts:
            if part == "/":
                continue
            node = node.children[part]
        return node

    def _parent_path(self, node: VfsNode) -> PurePosixPath:
        path = self.path_for(node)
        return path.parent if path != PurePosixPath("/") else path

    def path_for(self, target: VfsNode) -> PurePosixPath:
        """Возвращает абсолютный путь узла в дереве.
        """

        if target is self.root:
            return PurePosixPath("/")

        def search(
            node: VfsNode,
            path: PurePosixPath,
        ) -> PurePosixPath | None:
            for child in node.children.values():
                child_path = path / child.name
                if child is target:
                    return child_path
                if child.is_directory:
                    result = search(child, child_path)
                    if result is not None:
                        return result
            return None

        result = search(self.root, PurePosixPath("/"))
        if result is None:
            raise VfsLoadError("узел отсутствует в VFS")
        return result

    def list_directory(self, path: str = ".") -> list[str]:
        """Возвращает отсортированный список содержимого каталога.
        """

        node = self._resolve(path)
        if not node.is_directory:
            return [node.name]
        return [
            child.name + ("/" if child.is_directory else "")
            for child in sorted(
                node.children.values(),
                key=lambda item: item.name,
            )
        ]

    def change_directory(self, path: str) -> PurePosixPath:
        """Меняет текущий каталог и возвращает новый абсолютный путь.
        """

        node = self._resolve(path)
        if not node.is_directory:
            raise VfsLoadError(
                f"не является каталогом: {path}"
            )
        self.current_path = self.path_for(node)
        return self.current_path

    def change_owner(
        self,
        path: str,
        owner: str,
        group: str | None = None,
    ) -> str:
        """Меняет владельца узла только в объектной модели VFS.
        """

        node = self._resolve(path)
        if not owner or any(char.isspace() for char in owner):
            raise VfsLoadError(
                "имя владельца не может быть пустым или "
                "содержать пробелы"
            )
        if group is not None and (
            not group or any(char.isspace() for char in group)
        ):
            raise VfsLoadError(
                "имя группы не может быть пустым или "
                "содержать пробелы"
            )
        node.owner = owner
        if group is not None:
            node.group = group
        return self.owner_for(path)

    def owner_for(self, path: str = ".") -> str:
        """Возвращает владельца и группу узла по пути.
        """

        node = self._resolve(path)
        return f"{node.owner}:{node.group}"

    def info(self) -> str:
        """Возвращает краткую информацию о подключённой VFS.
        """

        files, directories, total_bytes = self._statistics(self.root)
        return (
            f"VFS: {self.name}\n"
            f"Текущий каталог: {self.current_path}\n"
            f"Каталогов: {directories}, файлов: {files}, "
            f"байт: {total_bytes}"
        )

    def data_sha256(self) -> str:
        """Считает SHA-256 представления дерева VFS.
        """

        digest = hashlib.sha256()

        def visit(node: VfsNode, path: PurePosixPath) -> None:
            children = sorted(
                node.children.values(),
                key=lambda item: item.name,
            )
            for child in children:
                child_path = path / child.name
                digest.update(str(child_path).encode("utf-8"))
                digest.update(b"/" if child.is_directory else b"\0")
                if child.is_directory:
                    visit(child, child_path)
                else:
                    digest.update(child.content)

        visit(self.root, PurePosixPath("/"))
        return digest.hexdigest()

    def _statistics(self, node: VfsNode) -> tuple[int, int, int]:
        files = directories = total_bytes = 0
        for child in node.children.values():
            if child.is_directory:
                directories += 1
                nested = self._statistics(child)
            else:
                files, nested = 1, (0, 0, len(child.content))
            child_files, child_directories, child_bytes = nested
            files += child_files
            directories += child_directories
            total_bytes += child_bytes
        return files, directories, total_bytes
