"""
Minimal Agent Memory implementation (compile-safe).
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List


@dataclass
class MemoryEntry:
    id: str
    content: str
    timestamp: float = field(default_factory=lambda: time.time())
    context: Any = None
    importance: int = 5
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "MemoryEntry":
        return MemoryEntry(
            id=str(data.get("id", "")),
            content=str(data.get("content", "")),
            timestamp=float(data.get("timestamp", time.time())),
            context=data.get("context"),
            importance=int(data.get("importance", 5)),
            tags=list(data.get("tags", [])),
        )


class AgentMemory:
    def __init__(self, storage_path: str) -> None:
        self.storage_path = storage_path
        self.memories: List[MemoryEntry] = []
        self.load()

    def load(self) -> None:
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.memories = [MemoryEntry.from_dict(m) for m in data]
        except Exception:
            self.memories = []

    def save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.storage_path) or ".", exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump([m.to_dict() for m in self.memories], f, indent=2)
        except Exception:
            pass

    def add(self, entry: MemoryEntry) -> None:
        self.memories.append(entry)
        self.save()

    def all(self) -> List[MemoryEntry]:
        return list(self.memories)
