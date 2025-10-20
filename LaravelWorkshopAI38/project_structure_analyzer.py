"""
Minimal project structure analyzer used by the agent framework.

Public API:
- analyze_project_structure(project_root: str) -> dict with keys:
  - 'primary_pattern': object with attrs (name: str, confidence: float, evidence: list)
  - 'recommendations': dict of booleans and lists
"""

from typing import Dict, Any, List
import os


class _PrimaryPattern:
    def __init__(self, name: str = "Standard Laravel", confidence: float = 1.0, evidence: List[str] = None):
        self.name = name
        self.confidence = confidence
        self.evidence = evidence or []


def analyze_project_structure(project_root: str) -> Dict[str, Any]:
    if not project_root or not os.path.isdir(project_root):
        primary = _PrimaryPattern()
    else:
        primary = _PrimaryPattern(evidence=[f"root: {os.path.basename(project_root)}"])

    return {
        "primary_pattern": primary,
        "recommendations": {
            "use_modules": False,
            "use_domains": False,
            "use_actions": True,
            "use_dtos": True,
            "use_repositories": True,
            "use_services": True,
            "available_modules": [],
            "available_domains": [],
        },
    }
