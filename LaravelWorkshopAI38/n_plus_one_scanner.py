from __future__ import annotations

import re
from typing import Dict, List, Any, Tuple

# Simple Laravel N+1 heuristics scanner
# - Detects foreach loops that access relations like $item->user->... or $item->relation()
# - Suggests adding ->with(['relation']) to obvious upstream queries ending with ->get()


RELATION_ACCESS_RE = re.compile(r"\$(?P<var>[a-zA-Z_][a-zA-Z0-9_]*)\s*->\s*(?P<rel>[a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\(|->)")
FOREACH_RE = re.compile(r"@?foreach\s*\((?P<expr>[^)]*)\)|foreach\s*\((?P<expr2>[^)]*)\)")
GET_QUERY_RE = re.compile(r"->\s*get\s*\(\s*\)")
PAGINATE_QUERY_RE = re.compile(r"(->\s*paginate\s*\(.*?\))")
WITH_RE = re.compile(r"->\s*with\s*\(")


def _extract_relations_in_loops(content: str) -> List[str]:
    relations: List[str] = []
    for m in FOREACH_RE.finditer(content):
        start = m.end()
        # lookahead small window after foreach for relation access lines
        window = content[start:start + 800]
        for rm in RELATION_ACCESS_RE.finditer(window):
            rel = rm.group("rel")
            # ignore common scalar props
            if rel in {"id", "name", "title", "created_at", "updated_at", "pivot", "attributes"}:
                continue
            if rel not in relations:
                relations.append(rel)
    return relations


def _suggest_with_injection(lines: List[str], relations: List[str]) -> List[Tuple[int, str]]:
    """
    Return list of (line_index, new_line) suggestions where ->get() is replaced with ->with([...])->get()
    Only if the line contains ->get() and no ->with( already in recent chain.
    """
    suggestions: List[Tuple[int, str]] = []
    if not relations:
        return suggestions
    with_arg = ", ".join([f"'{r}'" for r in relations[:3]])
    with_clause = f"->with([{with_arg}])"

    builder_tokens = [
        '::query(', '::where', '->where', '::with', '->with', '::select', '->select',
        '::join', '->join', '::orderBy', '->orderBy', '::latest', '->latest', '::oldest', '->oldest'
    ]
    service_tokens = ['->execute(', 'Action->', 'Service->']

    for idx, line in enumerate(lines):
        # Heuristic: likely builder if any builder token present and no obvious service/action chaining
        is_builder = any(tok in line for tok in builder_tokens) and not any(tok in line for tok in service_tokens)
        # get()
        if GET_QUERY_RE.search(line) and not WITH_RE.search(line):
            # Heuristic: Avoid touching lines that look like raw DB::table
            if "DB::table(" in line or "->select(" in line:
                continue
            if not is_builder:
                continue
            new_line = GET_QUERY_RE.sub(with_clause + "->get()", line)
            if new_line != line:
                suggestions.append((idx, new_line))
            continue
        # paginate()
        if PAGINATE_QUERY_RE.search(line) and not WITH_RE.search(line):
            if "DB::table(" in line or "->select(" in line:
                continue
            if not is_builder:
                continue
            new_line = PAGINATE_QUERY_RE.sub(lambda m: with_clause + m.group(1), line)
            if new_line != line:
                suggestions.append((idx, new_line))
    return suggestions


def scan_file_for_n_plus_one(file_path: str, content: str, known_relations: List[str] | None = None) -> Dict[str, Any]:
    try:
        relations = _extract_relations_in_loops(content)
        if known_relations:
            # Merge and deduplicate, keep a small cap for suggestion clarity
            merged = []
            seen = set()
            for r in (relations + list(known_relations)):
                if r and r not in seen:
                    seen.add(r)
                    merged.append(r)
            relations = merged[:6]
        lines = content.splitlines(keepends=True)
        suggestions = _suggest_with_injection(lines, relations)

        diffs: List[Dict[str, Any]] = []
        if suggestions:
            new_lines = lines[:]
            for idx, new_line in suggestions:
                new_lines[idx] = new_line
            new_content = "".join(new_lines)
            diffs.append({
                "file": file_path,
                "relations": relations,
                "changes": [(idx, lines[idx], new_line) for idx, new_line in suggestions],
                "new_content": new_content,
            })

        return {
            "file": file_path,
            "relations": relations,
            "issues_found": len(suggestions) > 0,
            "diffs": diffs,
        }
    except Exception:
        return {"file": file_path, "relations": [], "issues_found": False, "diffs": []}
