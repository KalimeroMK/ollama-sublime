"""
Minimal Laravel Intelligence stubs (compile-safe).
"""
from __future__ import annotations

from typing import Any


class LaravelContextDetector:
    def detect(self, view: Any) -> str:
        return ""


def get_laravel_analyzer() -> Any:
    class _Analyzer:
        def analyze_model(self, model_path: str) -> dict:
            return {"model": model_path, "properties": []}
    return _Analyzer()
