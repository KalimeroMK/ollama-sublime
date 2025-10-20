"""
Minimal Laravel Autocomplete stub (compile-safe).
"""
from __future__ import annotations

import sublime
import sublime_plugin


class LaravelWorkshopAutocompleteStub(sublime_plugin.WindowCommand):
    def run(self) -> None:
        sublime.status_message("Laravel Workshop Autocomplete (stub)")
