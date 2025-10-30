from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Iterable

from .n_plus_one_scanner import scan_file_for_n_plus_one

DEFAULT_EXCLUDES = {"vendor", "node_modules", ".git", "storage", "bootstrap", "build", "dist"}
SUPPORTED_EXTENSIONS = {".php", ".blade.php"}


def _should_skip(path: str, project_root: str, excludes: Iterable[str]) -> bool:
    rel = os.path.relpath(path, project_root)
    parts = rel.split(os.sep)
    for p in parts:
        if p in excludes:
            return True
    return False


def _is_supported_file(filename: str) -> bool:
    if filename.endswith(".blade.php"):
        return True
    _, ext = os.path.splitext(filename)
    return ext in {".php"}


def _collect_files(project_root: str, excludes: Iterable[str]) -> List[str]:
    files: List[str] = []
    for root, dirs, filenames in os.walk(project_root):
        # Prune excluded dirs in-place for performance
        dirs[:] = [d for d in dirs if d not in excludes]
        for fname in filenames:
            if not _is_supported_file(fname):
                continue
            full = os.path.join(root, fname)
            if _should_skip(full, project_root, excludes):
                continue
            files.append(full)
    return files


def scan_project(project_root: str, max_workers: int = 8, excludes: Iterable[str] = None, known_relations: List[str] | None = None) -> Dict[str, Any]:
    excludes = set(excludes or DEFAULT_EXCLUDES)
    targets = _collect_files(project_root, excludes)

    results: List[Dict[str, Any]] = []

    def _scan_one(path: str) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return scan_file_for_n_plus_one(path, content, known_relations=known_relations)
        except Exception:
            return {"file": path, "issues_found": False, "diffs": [], "relations": []}

    with ThreadPoolExecutor(max_workers=max_workers or 4) as ex:
        futs = {ex.submit(_scan_one, p): p for p in targets}
        for fut in as_completed(futs):
            res = fut.result()
            results.append(res)

    diffs: List[Dict[str, Any]] = []
    for r in results:
        for d in r.get("diffs", []) or []:
            diffs.append(d)

    problematic_files = [r["file"] for r in results if r.get("issues_found")]

    summary = {
        "total_files": len(targets),
        "problem_files": len(problematic_files),
        "problematic_files": problematic_files,
        "diffs": diffs,
        "results": results,
    }
    return summary


def apply_fixes(diffs: List[Dict[str, Any]]) -> Dict[str, Any]:
    applied = 0
    errors: List[str] = []
    for d in diffs:
        file_path = d.get("file")
        new_content = d.get("new_content")
        if not file_path or new_content is None:
            continue
        try:
            # Backup
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    old = f.read()
                backup_path = file_path + ".bak"
                with open(backup_path, "w", encoding="utf-8") as bf:
                    bf.write(old)
            except Exception:
                pass

            with open(file_path, "w", encoding="utf-8") as w:
                w.write(new_content)
            applied += 1
        except Exception as e:
            errors.append(f"{file_path}: {e}")
    return {"applied": applied, "errors": errors}
