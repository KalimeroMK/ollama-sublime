"""
Laravel Autocomplete - Smart autocomplete for Laravel models
Reads model properties, relationships, and IDE helper
"""

import sublime
import sublime_plugin
import re
from typing import List, Tuple

from laravel_intelligence import get_laravel_analyzer, LaravelContextDetector


class LaravelWorkshopLaravelAutocompleteCommand(sublime_plugin.EventListener):
    """Provides Laravel-aware autocomplete"""
    
    def __init__(self):
        self.completions_cache = {}
        self.last_completion_time = 0
        
    def on_query_completions(self, view, prefix, locations):
        """Provide completions"""
        # Only for PHP files
        if not view.match_selector(locations[0], "source.php"):
            return None
        
        # Get Laravel analyzer
        analyzer = get_laravel_analyzer(view)
        if not analyzer:
            return None
        
        # Detect context
        cursor_pos = locations[0]
        model_name = self._detect_model_at_cursor(view, cursor_pos)
        
        if not model_name:
            return None
        
        # Get completions for this model
        completions = self._get_model_completions(analyzer, model_name, prefix)
        
        if not completions:
            return None
        
        # Return completions
        return (
            completions,
            sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS
        )
    
    def _detect_model_at_cursor(self, view, cursor_pos):
        """Detect which model is being accessed"""
        # Get current line
        line_region = view.line(cursor_pos)
        line_text = view.substr(line_region)
        
        # Get text before cursor
        line_start = line_region.begin()
        text_before_cursor = view.substr(sublime.Region(line_start, cursor_pos))
        
        # Pattern 1: $model->|
        match = re.search(r'\$(\w+)->', text_before_cursor)
        if match = match.group(1)
            # Try to find variable type
            model_name = self._find_variable_type(view, var_name, cursor_pos)
            if model_name:
                return model_name
        
        # Pattern 2: Model::|
        match = re.search(r'(\w+)::', text_before_cursor)
        if match = match.group(1)
            if potential_model[0].isupper():  # PascalCase = likely a model
                return potential_model
        
        # Pattern 3: In model file
        if LaravelContextDetector.is_in_model_file(view):
            # Check if typing $this->
            if '$this->' in text_before_cursor:
                return LaravelContextDetector.get_current_model_name(view)
        
        return None
    
    def _find_variable_type(self, view, var_name, cursor_pos):
        """Try to find the type of a variable"""
        # Search backwards for variable assignment
        search_region = sublime.Region(max(0, cursor_pos - 5000), cursor_pos)
        search_text = view.substr(search_region)
        
        # Pattern: $var = Model::...
        pattern = r'\${0}\s*=\s*(\w+)::'.format(var_name)
        match = re.search(pattern, search_text)
        if match:
            return match.group(1)
        
        # Pattern: $var = new Model(
        pattern = r'\${0}\s*=\s*new\s+(\w+)\('.format(var_name)
        match = re.search(pattern, search_text)
        if match:
            return match.group(1)
        
        # Pattern: function method(Model $var)
        pattern = r'(\w+)\s+\${0}\)'.format(var_name)
        match = re.search(pattern, search_text)
        if match:
            return match.group(1)
        
        # Pattern: @var Model $var (PHPDoc)
        pattern = r'@var\s+(\w+)\s+\${0}'.format(var_name)
        match = re.search(pattern, search_text)
        if match:
            return match.group(1)
        
        return None
    
    def _get_model_completions(self, analyzer, model_name, prefix):
        """Get completions for a model"""
        cache_key = "{0}_{1}".format(model_name, prefix)
        
        # Check cache
        if cache_key in self.completions_cache:
            return self.completions_cache[cache_key]
        
        # Get completions from analyzer
        completions = analyzer.get_model_completions(model_name, prefix)
        
        # Cache results
        self.completions_cache[cache_key] = completions
        
        return completions


class LaravelWorkshopShowModelInfoCommand(sublime_plugin.TextCommand):
    """Show model information in popup"""
    
    def run(self, edit):
        analyzer = get_laravel_analyzer(self.view)
        if not analyzer:
            sublime.status_message("Not a Laravel project")
            return
        
        # Detect model at cursor
        cursor_pos = self.view.sel()[0].begin()
        model_name = LaravelContextDetector.detect_model_context(self.view, cursor_pos)
        
        if not model_name = LaravelContextDetector.get_current_model_name(self.view)
        
        if not model_name:
            sublime.status_message("No model detected")
            return
        
        # Get model info
        model_path = analyzer._find_model_file(model_name)
        if not model_path:
            sublime.status_message("Model {0} not found".format(model_name))
            return
        
        model_info = analyzer.analyze_model(model_path)
        properties = analyzer.get_model_properties(model_name)
        
        # Build HTML
        html = self._build_model_info_html(model_name, model_info, properties)
        
        # Show popup
        self.view.show_popup(
            html,
            flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
            max_width=600,
            max_height=400
        )
    
    def _build_model_info_html(self, model_name, model_info, properties):
        """Build HTML for model info"""
        html_parts = [
            "<h2>📦 {0}</h2>".format(model_name),
            "<p><b>Table:</b> {0}</p>".format(model_info.get('table', 'N/A'))
        ]
        
        # Properties
        if properties:
            html_parts.append("<h3>Properties:</h3><ul>")
            for prop in properties[:15]:  # Limit to 15
                html_parts.append("<li><code>{0}</code> : {1} <i>({2})</i></li>".format(prop['name'], prop['type'], prop['source']))
            if len(properties) > 15:
                html_parts.append("<li><i>... and {0} more</i></li>".format(len(properties) - 15))
            html_parts.append("</ul>")
        
        # Relationships
        relationships = model_info.get('relationships', [])
        if relationships:
            html_parts.append("<h3>Relationships:</h3><ul>")
            for rel in relationships[:10]:
                html_parts.append("<li><code>{0}()</code> : {1} → {2}</li>".format(rel['name'], rel['type'], rel['related']))
            html_parts.append("</ul>")
        
        # Scopes
        scopes = model_info.get('scopes', [])
        if scopes:
            html_parts.append("<h3>Scopes:</h3><ul>")
            for scope in scopes[:10]:
                html_parts.append("<li><code>scope{0}()</code></li>".format(scope))
            html_parts.append("</ul>")
        
        return """
        <body id="model-info">
            <style>
                body {{
                    font-family: system-ui;
                    padding: 10px;
                }}
                h2 {{ margin-top: 0; color: var(--bluish); }}
                h3 {{ color: var(--greenish); font-size: 0.9rem; margin-bottom: 5px; }}
                ul {{ margin: 5px 0; padding-left: 20px; }}
                li {{ margin: 3px 0; font-size: 0.85rem; }}
                code {{ background-color: color(var(--bluish) alpha(0.1)); padding: 2px 4px; border-radius: 2px; }}
            </style>
            {''.join(html_parts)}
        </body>
        """
    
    def is_visible(self):
        """Show only in PHP files"""
        return self.view.match_selector(0, "source.php")


class LaravelWorkshopGenerateIdeHelperCommand(sublime_plugin.WindowCommand):
    """Generate IDE helper for Laravel models"""
    
    def run(self):
        analyzer = get_laravel_analyzer(self.window.active_view())
        if not analyzer:
            sublime.error_message("Not a Laravel project")
            return
        
        # Run artisan command
        import subprocess
        import os
        
        project_root = self.window.folders()[0]
        
        try:
            # Check if ide-helper is installed
            composer_json = os.path.join(project_root, 'composer.json')
            if os.path.exists(composer_json):
                with open(composer_json, 'r') as f:
                    import json
                    data = json.load(f)
                    if 'barryvdh/laravel-ide-helper' not in str(data):
                        sublime.error_message("Laravel IDE Helper not installed.\n\nInstall with:\ncomposer require --dev barryvdh/laravel-ide-helper")
                        return
            
            # Run command
            result = subprocess.run(
                ['php', 'artisan', 'ide-helper:models', '--write'],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                sublime.message_dialog("✅ IDE Helper generated successfully!\n\nRestart Sublime Text to see updated completions.")
                # Clear cache
                analyzer.ide_helper_cache = None
            else:
                sublime.error_message("Failed to generate IDE Helper:\n\n{0}".format(result.stderr))
                
        except Exception as e:
            sublime.error_message("Error: {0}".format(str(e)))
    
    def is_visible(self):
        """Show only in Laravel projects"""
        view = self.window.active_view()
        if not view:
            return False
        return get_laravel_analyzer(view) is not None
