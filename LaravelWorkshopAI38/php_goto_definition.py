from __future__ import annotations

import os
import re
import sublime
import sublime_plugin

from .context_analyzer import ContextAnalyzer
from .project_indexer import build_project_index

CLASS_NAME_RE = re.compile(r"^[A-Z][A-Za-z0-9_]*$")
ASSIGN_CLASS_RE_TMPL = r"\${var}\s*=\s*([A-Za-z_\\\\][A-Za-z0-9_\\\\]*)::"
TYPEHINT_VAR_TMPL = r"([A-Za-z_\\\\][A-Za-z0-9_\\\\]*)\s+\${var}\b"
USE_LINE_RE = re.compile(r"^use\s+([A-Za-z_\\\\][A-Za-z0-9_\\\\]*)\\\\([A-Za-z_][A-Za-z0-9_]*)\s*;\s*$", re.MULTILINE)
FULLY_QUALIFIED_RE = re.compile(r"^[A-Za-z_\\\\][A-Za-z0-9_\\\\]*$")
ROUTE_CALL_RE = re.compile(r"route\(\s*['\"]([^'\"]+)['\"]")
VIEW_CALL_RE = re.compile(r"view\(\s*['\"]([^'\"]+)['\"]")
INCLUDE_CALL_RE = re.compile(r"@include(?:If|When)?\(\s*['\"]([^'\"]+)['\"]")
COMPONENT_CALL_RE = re.compile(r"@component\(\s*['\"]([^'\"]+)['\"]")
EACH_CALL_RE = re.compile(r"@each\(\s*['\"]([^'\"]+)['\"]")
X_COMPONENT_RE = re.compile(r"<x-([a-z0-9_.\-:]+)")

SEARCH_PATHS = [
    os.path.join("app", "Models"),
    os.path.join("app", "Http", "Controllers"),
    os.path.join("app", "DTOs"),
    os.path.join("app", "Data"),
    os.path.join("app", "DataTransferObjects"),
    os.path.join("app", "ValueObjects"),
    "app",
]
EXCLUDE_DIRS = {"vendor", "node_modules", ".git", "storage"}


def _resolve_blade_view_path(project_root: str, view_name: str) -> str | None:
    # Namespaced: vendor::path.name
    if "::" in view_name:
        ns, v = view_name.split("::", 1)
        vpath = v.replace('.', os.sep)
        candidate = os.path.join(project_root, "resources", "views", "vendor", ns, vpath + ".blade.php")
        return candidate if os.path.exists(candidate) else None
    # App views: path.name
    vpath = view_name.replace('.', os.sep)
    candidate = os.path.join(project_root, "resources", "views", vpath + ".blade.php")
    return candidate if os.path.exists(candidate) else None


def _find_project_root(view: sublime.View) -> str | None:
    ctx = ContextAnalyzer.from_view(view)
    if ctx and ctx.project_root:
        return ctx.project_root
    win = view.window()
    if win:
        folders = win.folders()
        if folders:
            return folders[0]
    return None


def _resolve_class_to_path(project_root: str, fqcn: str) -> str | None:
    # Normalize backslashes
    parts = [p for p in fqcn.split("\\") if p]
    if not parts:
        return None
    short = parts[-1]
    # Heuristic: prefer app/Models/<Class>.php when namespace contains Models
    candidates = []
    if "Models" in parts:
        candidates.append(os.path.join(project_root, "app", "Models", short + ".php"))
    # Try PSR-4 default
    candidates.append(os.path.join(project_root, "app", short + ".php"))
    # Also try Controllers
    candidates.append(os.path.join(project_root, "app", "Http", "Controllers", short + ".php"))
    for c in candidates:
        if os.path.exists(c):
            return c
    # Fallback: scan common dirs
    for rel in SEARCH_PATHS:
        p = os.path.join(project_root, rel, short + ".php")
        if os.path.exists(p):
            return p
    # Last resort: scan the project for Class.php excluding vendors
    target = short + ".php"
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        if target in files:
            return os.path.join(root, target)
    return None


class LaravelWorkshopGotoDefinitionCommand(sublime_plugin.TextCommand):
    def run(self, edit, event=None):
        try:
            view = self.view
            # Support both mouse event and keyboard invocation
            if event and isinstance(event, dict) and "x" in event and "y" in event:
                pt = view.window_to_text((event.get("x"), event.get("y")))
            else:
                pt = view.sel()[0].begin()
            # Normalize selection to a single caret at click point to avoid multi-cursor
            try:
                sels = view.sel()
                sels.clear()
                sels.add(sublime.Region(pt, pt))
            except Exception:
                pass
            word_region = view.word(pt)
            token = view.substr(word_region)
            if not token:
                return
            project_root = _find_project_root(view)
            if not project_root:
                return

            # Surrounding context (line) for Blade/view/route patterns
            line = view.line(pt)
            line_text = view.substr(line)

            # Case 0: route('name') in PHP or Blade
            mr = ROUTE_CALL_RE.search(line_text)
            if mr:
                rname = mr.group(1)
                idx = build_project_index(project_root, max_workers=2, excludes=EXCLUDE_DIRS)
                for r in idx.get("routes", {}).get("routes", []):
                    if r.get("name") == rname:
                        # open controller file
                        ctrl = r.get("controller") or ""
                        path = _resolve_class_to_path(project_root, ctrl)
                        if path:
                            self._open_file(path)
                            return

            # Case 0b: view()/@include('view.name') in PHP/Blade → open resources/views/view/name.blade.php
            mv = VIEW_CALL_RE.search(line_text) or INCLUDE_CALL_RE.search(line_text) or COMPONENT_CALL_RE.search(line_text) or EACH_CALL_RE.search(line_text)
            if mv:
                view_name = mv.group(1)
                candidate = _resolve_blade_view_path(project_root, view_name)
                if candidate:
                    self._open_file(candidate)
                    return

            # Case 0c: Blade x-components: <x-foo.bar>
            if view.file_name() and view.file_name().endswith('.blade.php'):
                mx = X_COMPONENT_RE.search(line_text)
                if mx:
                    raw = mx.group(1)
                    if '::' in raw:
                        ns, comp = raw.split('::', 1)
                        comp_path = comp.replace('.', os.sep).replace('-', os.sep)
                        candidate = os.path.join(project_root, "resources", "views", "vendor", ns, "components", comp_path + ".blade.php")
                    else:
                        comp = raw
                        comp_path = comp.replace('.', os.sep).replace('-', os.sep)
                        candidate = os.path.join(project_root, "resources", "views", "components", comp_path + ".blade.php")
                    if os.path.exists(candidate):
                        self._open_file(candidate)
                        return

            # Case 1: Token looks like ClassName → resolve via use lines or PSR-4
            if CLASS_NAME_RE.match(token):
                # Try resolve via use statements
                content = view.substr(sublime.Region(0, view.size()))
                for m in USE_LINE_RE.finditer(content):
                    ns, short = m.group(1), m.group(2)
                    if short == token:
                        path = _resolve_class_to_path(project_root, ns + "\\" + short)
                        if path:
                            self._open_file(path)
                            return
                # Try resolve directly under app/Models or app
                for rel in SEARCH_PATHS:
                    p = os.path.join(project_root, rel, token + ".php")
                    if os.path.exists(p):
                        self._open_file(p)
                        return
                # Try project-wide search
                anyp = _resolve_class_to_path(project_root, token)
                if anyp:
                    self._open_file(anyp)
                    return

            # Case 2: Token is variable like $user → infer from assignment `$user = Class::...`
            if token.startswith("$"):
                var = token[1:]
                # Search recent region
                line = view.line(pt)
                search_region = sublime.Region(max(0, line.begin() - 8000), line.begin())
                ctx = view.substr(search_region)
                m = re.search(ASSIGN_CLASS_RE_TMPL.format(var=re.escape(var)), ctx)
                if m:
                    fqcn = m.group(1).replace("\\\\", "\\")
                    path = _resolve_class_to_path(project_root, fqcn)
                    if path:
                        self._open_file(path)
                        return
                # Try type-hinted parameter or local annotation
                m2 = re.search(TYPEHINT_VAR_TMPL.format(var=re.escape(var)), ctx)
                if m2:
                    fqcn = m2.group(1).replace("\\\\", "\\")
                    path = _resolve_class_to_path(project_root, fqcn)
                    if path:
                        self._open_file(path)
                        return
                # Fallback: Uppercase guess App\Models\Var
                guess = f"App\\Models\\{var[:1].upper() + var[1:]}"
                path = _resolve_class_to_path(project_root, guess)
                if path:
                    self._open_file(path)
                    return
            # Not found: try LSP fallback (e.g., LSP-intelephense)
            try:
                view.run_command("lsp_symbol_definition")
                return
            except Exception:
                pass
            # Still not found: status message for debugging
            sublime.status_message("Go To Definition: not found for '{0}'".format(token))
        except Exception:
            pass

    def _open_file(self, path: str):
        win = self.view.window()
        if win:
            win.open_file(path)

    def is_enabled(self, event=None):
        # Enable in PHP and Blade files
        fname = self.view.file_name() or ""
        return fname.endswith(".php") or fname.endswith(".blade.php")

    def want_event(self):
        # Necessary to receive mouse event coordinates from mousemap
        return True
