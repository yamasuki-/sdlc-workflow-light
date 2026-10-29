"""形式別アダプタの登録。形式を追加するときは、モジュールを作り EXTENSIONS に登録するだけでよい。

各アダプタは `convert(path: Path, assets_dir: Path, rel_assets: str) -> list[Fragment]` を提供する。
"""
from __future__ import annotations

from importlib import import_module

from .base import Fragment  # noqa: F401

EXTENSIONS = {
    ".xlsx": "xlsx",
    ".xlsm": "xlsx",
    ".docx": "docx",
    ".pptx": "pptx",
    ".pdf": "pdf",
    ".md": "md",
    ".markdown": "md",
}


def get(ext: str):
    name = EXTENSIONS.get(ext.lower())
    if name is None:
        raise ValueError(f"未対応の形式です: {ext}（対応: {', '.join(sorted(EXTENSIONS))}）")
    return import_module(f"{__name__}.{name}")
