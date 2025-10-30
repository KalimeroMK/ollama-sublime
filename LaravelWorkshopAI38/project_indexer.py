from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Iterable, Tuple
import json
import hashlib
import time
import sublime

DEFAULT_EXCLUDES = {"vendor", "node_modules", ".git", "storage", "bootstrap", "build", "dist"}

# Relations detection in Eloquent models (heuristic)
RELATION_CALL_RE = re.compile(
    r"return\s*\$this->\s*(hasOne|hasMany|belongsTo|belongsToMany|morphOne|morphMany|morphTo|morphToMany)\s*\(",
    re.IGNORECASE,
)
CLASS_MODEL_RE = re.compile(r"class\s+([A-Za-z_][A-Za-z0-9_]*)\s+extends\s+Model\b")
METHOD_DEF_RE = re.compile(r"public\s+function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")

# Routes detection (controllers & closures)
ROUTE_FILE_CANDIDATES = [
    ("routes", "web.php"),
    ("routes", "api.php"),
]
ROUTE_ARRAY_CONTROLLER_RE = re.compile(
    r"Route::(get|post|put|patch|delete|options)\s*\(.*?,\s*\[\s*([^\]]+?)::class\s*,\s*'([A-Za-z_][A-Za-z0-9_]*)'\s*\]\s*\)\s*;",
    re.IGNORECASE | re.DOTALL,
)
ROUTE_STRING_CONTROLLER_RE = re.compile(
    r"Route::(get|post|put|patch|delete|options)\s*\(.*?,\s*['\"]([A-Za-z0-9_\\\\]+)@([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\)\s*;",
    re.IGNORECASE | re.DOTALL,
)
ROUTE_NAME_RE = re.compile(r"->\s*name\s*\(\s*['\"]([^'\"]+)['\"]\s*\)")


def _list_php_files(root: str, subdir: str, excludes: Iterable[str]) -> List[str]:
    target_dir = os.path.join(root, subdir)
    out: List[str] = []
    for r, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in excludes]
        for f in files:
            if f.endswith(".php"):
                out.append(os.path.join(r, f))
    return out


def _extract_method_bodies(lines: List[str]) -> Dict[str, Tuple[int, int]]:
    """Return mapping method_name -> (start_line_index, end_line_index) inclusive, best-effort by brace counting."""
    bodies: Dict[str, Tuple[int, int]] = {}
    current = None
    depth = 0
    for i, ln in enumerate(lines):
        m = METHOD_DEF_RE.search(ln)
        if m and current is None:
            current = m.group(1)
            # body likely starts at next '{'
            # include current line in search for braces
            # reset depth when we hit first '{'
            # crude but works for normal formatting
            # find first '{' after method def
            pass
        # Track braces
        depth += ln.count('{')
        depth -= ln.count('}')
        if current is not None and depth == 0 and '{' in ln:
            # close body when depth returns to zero after having opened
            bodies[current] = (bodies.get(current, (i, i))[0], i)
            current = None
        elif current is not None and current not in bodies:
            bodies[current] = (i, i)
        elif current is not None:
            start, _ = bodies[current]
            bodies[current] = (start, i)
    return bodies


def _parse_relation_target(snippet: str) -> str | None:
    # Try to find Foo::class within the snippet
    m = re.search(r"([A-Za-z_][A-Za-z0-9_\\\\]+)::class", snippet)
    if m:
        return m.group(1).split('\\')[-1]
    return None


def _index_model_file(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return {}
    mclass = CLASS_MODEL_RE.search(content)
    if not mclass:
        return {}
    model = mclass.group(1)
    relations: List[str] = []
    relations_detail: Dict[str, Dict[str, Any]] = {}
    lines = content.splitlines()
    bodies = _extract_method_bodies(lines)
    current_method = None
    for i, ln in enumerate(lines):
        mm = METHOD_DEF_RE.search(ln)
        if mm:
            current_method = mm.group(1)
        if RELATION_CALL_RE.search(ln) and current_method:
            relations.append(current_method)
            target = _parse_relation_target(ln)
            if not target and current_method in bodies:
                start, end = bodies[current_method]
                body_text = "\n".join(lines[start:end+1])
                target = _parse_relation_target(body_text)
            relations_detail[current_method] = {"target": target}
    return {"model": model, "file": path, "relations": relations, "relations_detail": relations_detail}


def _index_routes(root: str) -> Dict[str, Any]:
    routes: List[Dict[str, str]] = []
    for d, f in ROUTE_FILE_CANDIDATES:
        p = os.path.join(root, d, f)
        if not os.path.exists(p):
            continue
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except Exception:
            continue
        for m in ROUTE_ARRAY_CONTROLLER_RE.finditer(content):
            ctrl = m.group(2)
            method = m.group(3)
            # extract snippet until semicolon to catch chained ->name()
            start = m.start()
            semi = content.find(';', start)
            snippet = content[start:semi + 1] if semi != -1 else content[start:]
            name = None
            mn = ROUTE_NAME_RE.search(snippet)
            if mn:
                name = mn.group(1)
            routes.append({"file": p, "controller": ctrl, "method": method, "name": name})
        for m in ROUTE_STRING_CONTROLLER_RE.finditer(content):
            ctrl = m.group(2)
            method = m.group(3)
            start = m.start()
            semi = content.find(';', start)
            snippet = content[start:semi + 1] if semi != -1 else content[start:]
            name = None
            mn = ROUTE_NAME_RE.search(snippet)
            if mn:
                name = mn.group(1)
            routes.append({"file": p, "controller_action": f"{ctrl}@{method}", "controller": ctrl, "method": method, "name": name})
    return {"count": len(routes), "routes": routes}


def _cache_path_for_project(project_root: str) -> str:
    settings = sublime.load_settings("LaravelWorkshopAI.sublime-settings")
    cache_dir = settings.get("cache_directory", os.path.expanduser("~/.sublime_ollama_cache"))
    try:
        cache_dir = os.path.expanduser(cache_dir)
    except Exception:
        pass
    os.makedirs(cache_dir, exist_ok=True)
    h = hashlib.sha1(project_root.encode("utf-8", errors="ignore")).hexdigest()[:16]
    return os.path.join(cache_dir, f"lwai_index_{h}.json")


def _load_cache(project_root: str) -> Dict[str, Any]:
    path = _cache_path_for_project(project_root)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(project_root: str, data: Dict[str, Any]):
    path = _cache_path_for_project(project_root)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def build_project_index(project_root: str, max_workers: int = 8, excludes: Iterable[str] = None) -> Dict[str, Any]:
    excludes = set(excludes or DEFAULT_EXCLUDES)

    # Load cache
    cache = _load_cache(project_root)
    cached_models = {m.get("file"): m for m in cache.get("models", [])}
    cached_mtimes = cache.get("mtimes", {})

    # Models relations
    model_files = _list_php_files(project_root, os.path.join("app", "Models"), excludes)
    to_index = []
    model_index: List[Dict[str, Any]] = []
    new_mtimes: Dict[str, float] = {}
    for p in model_files:
        try:
            mt = os.path.getmtime(p)
        except Exception:
            mt = 0
        new_mtimes[p] = mt
        if str(mt) == str(cached_mtimes.get(p)) and p in cached_models:
            model_index.append(cached_models[p])
        else:
            to_index.append(p)

    if to_index:
        with ThreadPoolExecutor(max_workers=max_workers or 4) as ex:
            futs = {ex.submit(_index_model_file, p): p for p in to_index}
            for fut in as_completed(futs):
                res = fut.result()
                if res:
                    model_index.append(res)

    # Routes (no mtime cache for simplicity; route files are few)
    routes_index = _index_routes(project_root)

    # Quick maps
    relations_map = {m["model"]: m.get("relations", []) for m in model_index}
    relations_detail_map = {m["model"]: m.get("relations_detail", {}) for m in model_index}

    out = {
        "models": model_index,
        "routes": routes_index,
        "relations_map": relations_map,
        "relations_detail": relations_detail_map,
        "stats": {
            "models": len(model_index),
            "routes": routes_index.get("count", 0),
        },
        "generated_at": int(time.time()),
    }

    # Save cache
    try:
        cache_out = {"models": model_index, "mtimes": new_mtimes}
        _save_cache(project_root, cache_out)
    except Exception:
        pass

    return out
