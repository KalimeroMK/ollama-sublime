from __future__ import annotations

import os
import re
from typing import Dict, List, Any, Set


CLASS_RE = re.compile(r"class\s+([A-Za-z_][A-Za-z0-9_]*)Controller\b")

PHP_TEMPLATE = """<?php

namespace App\\Http\\Requests;

use Illuminate\\Foundation\\Http\\FormRequest;

class {class_name} extends FormRequest
{{
    public function authorize(): bool
    {{
        return true;
    }}

    public function rules(): array
    {{
        return {rules};
    }}
}}
"""


def _ensure_requests_dir(project_root: str) -> str:
    requests_dir = os.path.join(project_root, "app", "Http", "Requests")
    os.makedirs(requests_dir, exist_ok=True)
    return requests_dir


def _infer_controller_name(content: str) -> str | None:
    m = CLASS_RE.search(content or "")
    return m.group(1) if m else None


def _unique_name(base: str, used: Set[str]) -> str:
    name = base
    i = 2
    while name in used:
        name = f"{base}{i}"
        i += 1
    used.add(name)
    return name


def generate_form_requests(project_root: str, validation_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create FormRequest class files based on controller validation findings.
    Returns {created: [paths], skipped: [paths], errors: [str]}
    """
    requests_dir = _ensure_requests_dir(project_root)
    created: List[str] = []
    skipped: List[str] = []
    errors: List[str] = []

    planned_names: Set[str] = set()

    results = validation_summary.get("results", []) if validation_summary else []

    for r in results:
        if not r.get("issues_found"):
            continue
        file_path = r.get("file")
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            errors.append(f"Read error {file_path}: {e}")
            continue

        controller = _infer_controller_name(content) or "Unnamed"

        # If scanner provided methods per hit, generate per-method; else per-controller
        hits = r.get("inline_validation", []) or []
        method_names = []
        for h in hits:
            m = h.get("method")
            if m and m not in method_names:
                method_names.append(m)

        target_classes: List[str] = []
        if method_names:
            for mname in method_names:
                base = f"{mname[0].upper()}{mname[1:]}Request"
                target_classes.append(base)
        else:
            base = f"{controller}Request"
            target_classes.append(base)

        # Build a map method->rules_raw for convenience
        rules_by_method = {}
        for h in hits:
            if h.get("method") and h.get("rules_raw"):
                rules_by_method[h.get("method")] = h.get("rules_raw")

        for cls in target_classes:
            cls_unique = _unique_name(cls, planned_names)
            target_path = os.path.join(requests_dir, f"{cls_unique}.php")
            if os.path.exists(target_path):
                skipped.append(target_path)
                continue
            # Determine rules for this class
            rules = "[]"
            # If this class came from a specific method, try to grab its rules
            if cls.endswith("Request"):
                base = cls[:-7]  # class base name without 'Request'
                for mname, rr in rules_by_method.items():
                    if mname and base.lower() == (mname or '').lower():
                        rules = rr or "[]"
                        break
            # Fallback to first available rules_raw
            if rules == "[]" and hits:
                any_rr = next((h.get("rules_raw") for h in hits if h.get("rules_raw")), None)
                if any_rr:
                    rules = any_rr

            content = PHP_TEMPLATE.format(class_name=cls_unique, rules=rules)
            try:
                with open(target_path, "w", encoding="utf-8") as w:
                    w.write(content)
                created.append(target_path)
            except Exception as e:
                errors.append(f"Write error {target_path}: {e}")

    return {"created": created, "skipped": skipped, "errors": errors}
