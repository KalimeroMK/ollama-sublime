from __future__ import annotations

import os
import re
from typing import List, Tuple

import sublime
import sublime_plugin

from .context_analyzer import ContextAnalyzer
from .ide_helper_indexer import build_eloquent_index

PHP_VAR_PROP_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)->[A-Za-z_0-9]*$")
PHP_VAR_ANNOT_RE = re.compile(r"@var\s+([A-Za-z_\\\\][A-Za-z0-9_\\\\]*)\s*\$([A-Za-z_][A-Za-z0-9_]*)")


class EloquentAutocompleteListener(sublime_plugin.EventListener):
    def on_query_completions(self, view: sublime.View, prefix: str, locations: List[int]):
        try:
            settings = sublime.load_settings("LaravelWorkshopAI.sublime-settings")
            if not settings.get("enable_eloquent_autocomplete", True):
                return None

            # Only PHP files
            fname = view.file_name() or ""
            if not fname.endswith(".php"):
                return None

            # Determine if we are after `$var->`
            pt = locations[0]
            line_region = view.line(pt)
            line_text = view.substr(sublime.Region(line_region.begin(), pt))
            m = PHP_VAR_PROP_RE.search(line_text)
            if not m:
                return None

            var_name = m.group(1)

            # Find project root
            context = ContextAnalyzer.from_view(view)
            project_root = context.project_root if context else None
            if not project_root:
                # fallback to first folder
                folders = view.window().folders() if view.window() else []
                project_root = folders[0] if folders else None
            if not project_root:
                return None

            # Build/load IDE helper index
            idx = build_eloquent_index(project_root)

            # Attempt to infer class from @var annotations in the buffer (search recent 3000 chars)
            search_region = sublime.Region(max(0, line_region.begin() - 3000), pt)
            context_text = view.substr(search_region)
            inferred_cls = None
            for am in PHP_VAR_ANNOT_RE.finditer(context_text):
                cls, var = am.group(1), am.group(2)
                if var == var_name:
                    inferred_cls = cls
            # Simple fallback: App\Models\<Ucfirst(var)>
            if not inferred_cls:
                candidate = var_name[:1].upper() + var_name[1:]
                inferred_cls = f"App\\Models\\{candidate}"

            model_data = idx.get("models", {}).get(inferred_cls) or {}
            props = model_data.get("properties", [])
            rels = model_data.get("relations", [])
            scopes = model_data.get("scopes", [])

            completions: List[Tuple[str, str]] = []
            for p in sorted(props):
                completions.append((f"{p}\tproperty", p))
            for r in sorted(rels):
                completions.append((f"{r}()\trelation", f"{r}()"))
            for s in sorted(scopes):
                # scopes are typically referenced as where/with modifiers, we still expose for discoverability
                completions.append((f"{s}\tscope", s))

            flags = sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS
            return (completions, flags) if completions else None
        except Exception:
            return None
