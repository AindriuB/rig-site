"""Per-version build context shared by the pipeline and the transforms."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

RIG_BLOB = "https://github.com/AindriuB/rig/blob/"


class BuildError(Exception):
    """A build failure; the message is `path:line: message` or `path: message`."""


@dataclass
class VersionContext:
    id: str
    title: str
    ref: str
    is_dev: bool
    aliases: list[str]
    source_dir: Path  # the whole rig tree at `ref`
    build_dir: Path
    docs_dir: Path  # build_dir/docs
    cache_dir: Path  # shared by all versions
    blob_base: str = field(default="")

    def __post_init__(self) -> None:
        if not self.blob_base:
            self.blob_base = f"{RIG_BLOB}{self.ref}/"
