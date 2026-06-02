from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Literal


ItemType = Literal["directory", "file"]


@dataclass(frozen=True)
class Dependency:
    name: str
    version: str | None = None
    tech_stack_name: str | None = None

    @classmethod
    def from_text(cls, value: str) -> "Dependency":
        if "@" in value:
            name, version = value.split("@", 1)
            return cls(name=name.strip(), version=version.strip() or None)
        return cls(name=value.strip())


@dataclass(frozen=True)
class TechStack:
    name: str
    version: str | None = None


@dataclass(frozen=True)
class ProjectRequest:
    project_id: str
    project_name: str
    description: str
    domains: list[str]
    stacks: list[TechStack]
    dependencies: list[Dependency] = field(default_factory=list)
    requirements: str = ""
    package_name: str = "com.example"


@dataclass(frozen=True)
class GeneratedItem:
    type: ItemType
    path: str
    content: str | None = None

    @property
    def depth(self) -> int:
        return len(PurePosixPath(self.path).parts)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "GeneratedItem":
        item_type = raw.get("type")
        if item_type not in {"directory", "file"}:
            raise ValueError(f"Invalid item type: {item_type}")

        path = raw.get("path")
        if not isinstance(path, str):
            raise ValueError("Item path must be a string")

        content = raw.get("content")
        if item_type == "file" and not isinstance(content, str):
            raise ValueError(f"File content must be a string: {path}")
        if item_type == "directory":
            content = None

        item = cls(type=item_type, path=path, content=content)
        validate_safe_path(item.path)
        if item.type == "file" and not item.content.strip():
            raise ValueError(f"Generated file must not be empty: {item.path}")
        return item


@dataclass(frozen=True)
class GenerationPlan:
    project_id: str
    project_name: str
    directories: list[str]
    required_files: list[str]
    stack_conventions: list[dict[str, Any]]
    stacks: list[TechStack]
    dependencies: list[Dependency]


def validate_safe_path(path: str) -> None:
    if not path or path.strip() != path:
        raise ValueError("Path must not be empty or padded")
    if path.startswith("/") or path.startswith("~"):
        raise ValueError(f"Path must be relative: {path}")
    pure_path = PurePosixPath(path)
    if any(part in {"", ".", ".."} for part in pure_path.parts):
        raise ValueError(f"Path contains an unsafe segment: {path}")
    if "\\" in path:
        raise ValueError(f"Path must use POSIX separators: {path}")
    if str(pure_path) != path:
        raise ValueError(f"Path must use normalized POSIX syntax: {path}")
