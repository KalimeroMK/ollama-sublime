from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Iterable

DEFAULT_EXCLUDES = {"vendor", "node_modules", ".git", "storage", "bootstrap", "build", "dist"}

# Heuristics:
# - Flag controller methods that call $request->validate([...]) or Validator::make(...)
# - Recommend using dedicated FormRequest classes (type-hinted in action method)
# - Report file and line numbers where inline validation is found

REQUEST_VALIDATE_RE = re.compile(r"\$request\s*->\s*validate\s*\(", re.IGNORECASE)
VALIDATOR_MAKE_RE = re.compile(r"Validator\s*::\s*make\s*\(", re.IGNORECASE)
CONTROLLER_CLASS_RE = re.compile(r"class\s+[A-Za-z_][A-Za-z0-9_]*Controller\b")
METHOD_SIG_RE = re.compile(r"function\s+[A-Za-z_][A-Za-z0-9_]*\s*\((?P<params>[^)]*)\)")
FORM_REQUEST_HINT_RE = re.compile(r"\\?App\\\\Http\\\\Requests\\\\[A-Za-z_][A-Za-z0-9_]*Request|[A-Za-z_][A-Za-z0-9_]*Request\b")


def _collect_controller_files(project_root: str, excludes: Iterable[str]) -> List[str]:
    targets: List[str] = []
    controllers_dir = os.path.join(project_root, "app", "Http", "Controllers")
    for root, dirs, files in os.walk(controllers_dir):
        dirs[:] = [d for d in dirs if d not in excludes]
        for f in files:
            if f.endswith(".php"):
                targets.append(os.path.join(root, f))
    return targets


def _infer_method_name(signature_line: str | None) -> str | None:
    if not signature_line:
        return None
    m = re.search(r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", signature_line)
    return m.group(1) if m else None


def _extract_rules_around(lines: List[str], start_index: int) -> str:
    """Best-effort extraction of array rules from inline validation starting at start_index (0-based)."""
    buf = ""
    open_paren = 0
    started = False
    for j in range(start_index, min(len(lines), start_index + 50)):
        ln = lines[j]
        for ch in ln:
            if ch == '(':
                open_paren += 1
                started = True
            elif ch == ')':
                open_paren -= 1 if open_paren > 0 else 0
        buf += ln + "\n"
        if started and open_paren == 0:
            break
    # Try to find the first array literal
    m = re.search(r"\[([\s\S]*?)\]", buf)
    if not m:
        return ""
    return "[" + m.group(1).strip() + "]"


def _file_report(path: str, content: str) -> Dict[str, Any]:
    lines = content.splitlines()
    inline_hits: List[Dict[str, Any]] = []

    current_method = None
    for i, line in enumerate(lines, start=1):
        m = METHOD_SIG_RE.search(line)
        if m:
            current_method = line
        if REQUEST_VALIDATE_RE.search(line) or VALIDATOR_MAKE_RE.search(line):
            rules_raw = _extract_rules_around(lines, i - 1)
            inline_hits.append({
                "line": i,
                "snippet": line.strip()[:200],
                "method": _infer_method_name(current_method) if current_method else None,
                "rules_raw": rules_raw,
            })

    has_controller = bool(CONTROLLER_CLASS_RE.search(content))

    # Check for any method signature that hints FormRequest usage
    form_request_hinted = False
    for m in METHOD_SIG_RE.finditer(content):
        params = m.group("params") or ""
        if FORM_REQUEST_HINT_RE.search(params):
            form_request_hinted = True
            break

    return {
        "file": path,
        "is_controller": has_controller,
        "inline_validation": inline_hits,
        "uses_form_request": form_request_hinted,
        "issues_found": bool(inline_hits) and not form_request_hinted,
    }


message = """
This report flags controller methods that use inline validation ($request->validate or Validator::make)
and recommends extracting to a dedicated FormRequest class type-hinted in the controller method.
"""


def scan_project_for_controller_validation(project_root: str, max_workers: int = 8, excludes: Iterable[str] = None) -> Dict[str, Any]:
    excludes = set(excludes or DEFAULT_EXCLUDES)
    files = _collect_controller_files(project_root, excludes)

    results: List[Dict[str, Any]] = []

    def _scan(path: str) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return _file_report(path, f.read())
        except Exception:
            return {"file": path, "issues_found": False, "inline_validation": [], "uses_form_request": False}

    with ThreadPoolExecutor(max_workers=max_workers or 4) as ex:
        futs = {ex.submit(_scan, p): p for p in files}
        for fut in as_completed(futs):
            results.append(fut.result())

    problematic = [r for r in results if r.get("issues_found")]
    return {
        "total_controllers": len(files),
        "problem_files": len(problematic),
        "problematic_files": [r.get("file") for r in problematic],
        "results": results,
        "message": message.strip(),
    }
