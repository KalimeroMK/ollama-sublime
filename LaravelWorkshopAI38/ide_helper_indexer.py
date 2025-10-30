from __future__ import annotations

import os
import re
import json
import hashlib
import time
from typing import Dict, Any, List
import sublime

IDE_HELPER_FILES = ["_ide_helper_models.php", "_ide_helper.php"]

PROPERTY_RE = re.compile(r"@property(?:-read)?\s+[^$]*\$(?P<name>[A-Za-z_][A-Za-z0-9_]*)")
RELATION_HINT_RE = re.compile(r"@property(?:-read)?\s+\\?Illuminate\\\\Database\\\\Eloquent\\\\(?:Collection|Relations\\\\[A-Za-z]+)[^$]*\$(?P<name>[A-Za-z_][A-Za-z0-9_]*)")
SCOPE_RE = re.compile(r"@method\s+static\s+[^ ]+\s+scope(?P<name>[A-Za-z_][A-Za-z0-9_]*)\(")
CLASS_RE = re.compile(r"class\s+(?P<cls>[A-Za-z_][A-Za-z0-9_\\]*)")
MODEL_CLASS_RE = re.compile(r"namespace\\s+App\\\\Models|class\s+[A-Za-z_][A-Za-z0-9_]*\s+extends\s+\\?Illuminate\\\\Database\\\\Eloquent\\\\Model")


def _cache_path_for_project(project_root: str) -> str:
    settings = sublime.load_settings("LaravelWorkshopAI.sublime-settings")
    cache_dir = settings.get("cache_directory", os.path.expanduser("~/.sublime_ollama_cache"))
    try:
        cache_dir = os.path.expanduser(cache_dir)
    except Exception:
        pass
    os.makedirs(cache_dir, exist_ok=True)
    h = hashlib.sha1((project_root + "::idehelper").encode("utf-8", errors="ignore")).hexdigest()[:16]
    return os.path.join(cache_dir, f"lwai_ide_{h}.json")


def _load_cache(project_root: str) -> Dict[str, Any]:
    p = _cache_path_for_project(project_root)
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(project_root: str, data: Dict[str, Any]):
    p = _cache_path_for_project(project_root)
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def _parse_ide_helper(content: str) -> Dict[str, Any]:
    models: Dict[str, Dict[str, Any]] = {}
    current_cls: str | None = None
    for line in content.splitlines():
        mcls = CLASS_RE.search(line)
        if mcls:
            cls = mcls.group("cls")
            # Only consider Eloquent-like classes heuristically
            if current_cls is None or cls != current_cls:
                current_cls = cls
                models.setdefault(current_cls, {"properties": [], "relations": [], "scopes": []})
        if not current_cls:
            continue
        mp = PROPERTY_RE.search(line)
        if mp:
            name = mp.group("name")
            arr = models.setdefault(current_cls, {"properties": [], "relations": [], "scopes": []})
            if name not in arr["properties"]:
                arr["properties"].append(name)
        mr = RELATION_HINT_RE.search(line)
        if mr:
            name = mr.group("name")
            arr = models.setdefault(current_cls, {"properties": [], "relations": [], "scopes": []})
            if name not in arr["relations"]:
                arr["relations"].append(name)
        ms = SCOPE_RE.search(line)
        if ms:
            name = ms.group("name")
            # scopes are typically referenced without 'scope' prefix when called as dynamic where
            arr = models.setdefault(current_cls, {"properties": [], "relations": [], "scopes": []})
            if name not in arr["scopes"]:
                arr["scopes"].append(name)
    return {"models": models}


def build_eloquent_index(project_root: str) -> Dict[str, Any]:
    # Cache by mtimes of helper files
    cache = _load_cache(project_root)
    mtimes_old = cache.get("mtimes", {})
    mtimes_new: Dict[str, float] = {}

    aggregated: Dict[str, Any] = {"models": {}}

    changed = False
    for fname in IDE_HELPER_FILES:
        path = os.path.join(project_root, fname)
        if not os.path.exists(path):
            continue
        try:
            mt = os.path.getmtime(path)
        except Exception:
            mt = 0
        mtimes_new[path] = mt
        if str(mt) != str(mtimes_old.get(path)):
            changed = True
        # Parse regardless; simple and safe
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            continue
        parsed = _parse_ide_helper(content)
        for cls, data in parsed.get("models", {}).items():
            agg = aggregated["models"].setdefault(cls, {"properties": [], "relations": [], "scopes": []})
            for k in ("properties", "relations", "scopes"):
                for v in data.get(k, []) or []:
                    if v not in agg[k]:
                        agg[k].append(v)

    out = {
        "models": aggregated["models"],
        "stats": {
            "model_classes": len(aggregated["models"]),
            "properties": sum(len(v.get("properties", [])) for v in aggregated["models"].values()),
            "relations": sum(len(v.get("relations", [])) for v in aggregated["models"].values()),
        },
        "generated_at": int(time.time()),
        "mtimes": mtimes_new,
    }
    try:
        _save_cache(project_root, out)
    except Exception:
        pass
    return out
