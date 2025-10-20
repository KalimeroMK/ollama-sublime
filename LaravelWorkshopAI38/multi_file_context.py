"""
Minimal Multi-file Context provider (compile-safe).
"""
from __future__ import annotations

from typing import Dict


class MultiFileContext:
    def __init__(self) -> None:
        self.cache_index: Dict[str, str] = {}

    def get_context_for(self, key: str) -> str:
        return self.cache_index.get(key, "")

    def set_context_for(self, key: str, value: str) -> None:
        self.cache_index[key] = value
