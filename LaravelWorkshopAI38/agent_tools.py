"""
Minimal safe tools utilities for the Agent framework.
"""
from __future__ import annotations

import os
from typing import Optional


class FileSystemTools:
    @staticmethod
    def read_file(file_path: str) -> Optional[str]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None

    @staticmethod
    def write_file(file_path: str, content: str) -> bool:
        try:
            os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception:
            return False


def create_default_tools():
    """Return a default empty tool list.

    agent_commands imports this symbol. Keeping it minimal and compile-safe
    is sufficient; advanced tool wiring can be added later.
    """
    return []
