"""
Laravel Workshop AI - Cleaned up version with AI Agents
Keeps only essential commands, everything else goes through AI Agents
"""

import sublime
import sublime_plugin
import os
import threading
import re
import json

# Import modular components
from .laravel_workshop_api import create_api_client_from_settings
from .context_analyzer import ContextAnalyzer
from .ui_helpers import UIHelpers, TabManager
from .response_processor import ResponseProcessor, StreamingResponseHandler


# ============================================================================
# BASE CLASSES
# ============================================================================

class LaravelWorkshopContextCommandBase(sublime_plugin.TextCommand):
    """Base class for commands that work with current cursor position or selection"""
    
    def get_api_client(self):
        """Get configured API client instance."""
        return create_api_client_from_settings()
    
    def get_context_text(self):
        """Get text from selection or current line/word"""
        selected_text = UIHelpers.get_selected_text(self.view)
        if selected_text.strip():
            return selected_text
        
        # If no selection, get current line
        cursor_pos = self.view.sel()[0].begin()
        line_region = self.view.line(cursor_pos)
        line_text = self.view.substr(line_region)
        
        # If line is empty, get current word
        if not line_text.strip():
            word_region = self.view.word(cursor_pos)
            word_text = self.view.substr(word_region)
            return word_text
        
        return line_text


# ============================================================================
# PHP/LARAVEL COMPLETION (Specialized feature)
# ============================================================================

class LaravelWorkshopPhpCompletionCommand(LaravelWorkshopContextCommandBase):
    """AI-powered PHP/Laravel code completion - specialized autocomplete"""
    
    def __init__(self, view):
        super().__init__(view)
        self.api_client = None
        self.completion_cache = {}
        self.detection_cache = {}
        
        # PHP patterns
        self.php_patterns = {
            'functions': ['array_', 'str_', 'preg_', 'file_', 'json_', 'date_'],
            'classes': ['DateTime', 'PDO', 'Exception', 'ArrayObject', 'SplFileInfo'],
            'keywords': ['public', 'private', 'protected', 'static', 'abstract', 'final'],
            'constructs': ['i', 'else', 'foreach', 'while', 'for', 'switch', 'try', 'catch']
        }
        
        # Laravel patterns
        self.laravel_patterns = {
            'models': ['User', 'Post', 'Comment', 'Category', 'Product'],
            'controllers': ['UserController', 'PostController', 'AuthController'],
            'methods': ['index', 'show', 'create', 'store', 'edit', 'update', 'destroy'],
            'eloquent': ['find', 'where', 'get', 'first', 'create', 'update', 'delete'],
            'blade': ['@extends', '@section', '@yield', '@i', '@foreach', '@include'],
            'facades': ['Route', 'DB', 'Auth', 'Cache', 'Config', 'View', 'Mail']
        }
    
    def run(self, edit):
        """Main completion logic"""
        view = self.view
        cursor_pos = view.sel()[0].begin()
        
        # Detect project type
        project_type = self._detect_project_type()
        
        # Get context
        context = self._get_php_context(cursor_pos, project_type)
        
        # Generate completions
        completions = self._generate_completions(context, project_type)
        
        # Show popup
        self._show_completion_popup(completions, cursor_pos, project_type)
    
    def _detect_project_type(self):
        """Detect if Laravel or native PHP"""
        if 'project_type' in self.detection_cache:
            return self.detection_cache['project_type']
        
        view = self.view
        if not view.window() or not view.window().folders():
            return 'php'
        
        project_root = view.window().folders()[0]
        
        laravel_indicators = [
            'artisan', 'composer.json', 'app/Http/Controllers',
            'app/Models', 'resources/views', 'routes/web.php'
        ]
        
        is_laravel = any(
            os.path.exists(os.path.join(project_root, indicator))
            for indicator in laravel_indicators
        )
        
        project_type = 'laravel' if is_laravel else 'php'
        self.detection_cache['project_type'] = project_type
        return project_type
    
    def _get_php_context(self, cursor_pos, project_type):
        """Extract PHP context"""
        view = self.view
        region = view.line(cursor_pos)
        line_text = view.substr(region)
        
        start_line = max(0, region.begin() - 1000)
        end_line = min(view.size(), region.end() + 1000)
        context_region = sublime.Region(start_line, end_line)
        context = view.substr(context_region)
        
        patterns = self._detect_laravel_patterns(context) if project_type == 'laravel' else self._detect_php_patterns(context)
        
        return {
            'current_line': line_text,
            'context': context,
            'cursor_pos': cursor_pos,
            'patterns': patterns,
            'file_type': self._detect_file_type(),
            'project_type': project_type
        }
    
    def _detect_php_patterns(self, context):
        """Detect native PHP patterns"""
        return {
            'is_class': 'class ' in context,
            'is_function': 'function ' in context,
            'is_array': 'array(' in context or '[' in context,
            'is_object': '->' in context,
            'is_static': '::' in context,
        }
    
    def _detect_laravel_patterns(self, context):
        """Detect Laravel patterns"""
        return {
            'is_model': 'extends.*Model' in context,
            'is_controller': 'Controller' in context,
            'is_migration': 'Schema::' in context,
            'is_route': 'Route::' in context,
            'is_eloquent': '::' in context,
        }
    
    def _detect_file_type(self):
        """Detect file type"""
        filename = self.view.file_name()
        if not filename:
            return 'php'
        
        if 'Controller.php' in filename:
            return 'controller'
        elif 'Model.php' in filename:
            return 'model'
        elif '.blade.php' in filename:
            return 'blade'
        else:
            return 'php'
    
    def _generate_completions(self, context, project_type):
        """Generate completions"""
        cache_key = self._get_cache_key(context)
        if cache_key in self.completion_cache:
            return self.completion_cache[cache_key]
        
        prompt = self._build_prompt(context, project_type)
        
        if not self.api_client:
            self.api_client = self.get_api_client()
        
        try:
            response = self.api_client.make_blocking_request(prompt)
            completions = self._parse_completions(response, context, project_type)
            self.completion_cache[cache_key] = completions
            return completions
        except Exception as e:
            print("Completion error: {0}".format(e))
            return self._get_fallback_completions(context, project_type)
    
    def _build_prompt(self, context, project_type):
        """Build prompt"""
        file_type = context['file_type']
        current_line = context['current_line']
        
        framework = "Laravel" if project_type == 'laravel' else "PHP"
        
        return """You are a {framework} expert. Complete this code:

File type: {file_type}
Current line: {current_line}

Provide 5 {framework}-specific completions. Return only code, one per line."""
    
    def _parse_completions(self, response, context, project_type):
        """Parse completions"""
        try:
            completions = [line.strip() for line in response.split('\n') if line.strip()]
            return completions[:5]
        except:
            return self._get_fallback_completions(context, project_type)
    
    def _get_fallback_completions(self, context, project_type):
        """Fallback completions"""
        if project_type == 'laravel':
            return [
                'public function index() {',
                'return view(\'',
                'public function store(Request $request) {',
                'return redirect()->route(\''
            ]
        return [
            'public function ',
            'private function ',
            'protected function ',
            'if (',
            'foreach ('
        ]
    
    def _show_completion_popup(self, completions, cursor_pos, project_type):
        """Show popup"""
        if not completions:
            return
        
        completion_items = []
        for i, completion in enumerate(completions):
            label = 'Laravel' if project_type == 'laravel' else 'PHP'
            completion_items.append([completion, "{0} {1}".format(label, i+1)])
        
        self.view.show_popup_menu(completion_items, lambda idx: self._on_select(idx, completions))
    
    def _on_select(self, index, completions):
        """Handle selection"""
        if index == -1 or index >= len(completions):
            return
        self.view.run_command('insert', {'characters': completions[index]})
    
    def _get_cache_key(self, context):
        """Generate cache key"""
        import hashlib
        key_data = "{0}_{1}_{2}".format(context['current_line'], context['file_type'], context['project_type'])
        return hashlib.md5(key_data.encode()).hexdigest()


# ============================================================================
# CREATE FILE (Utility command)
# ============================================================================

class LaravelWorkshopCreateFileCommand(sublime_plugin.WindowCommand):
    """Create a new file based on a prompt (old version - use Generate Files instead)"""
    
    def run(self):
        # Redirect to modern generate files command
        sublime.status_message("💡 Use 'Laravel Workshop AI: Generate Files' instead for automatic file creation!")
        # Still allow old way for backwards compatibility
        UIHelpers.show_input_panel(
            self.window, 
            "Describe what you want to create (will auto-create files):", 
            "", 
            self.on_description
        )

    def on_description(self, description):
        if not description.strip():
            return
            
        # Use the new automatic generation instead
        # Get project root
        project_root = UIHelpers.ensure_project_folder(self.window)
        if not project_root:
            return
        
        # Create progress tab
        progress_tab = UIHelpers.create_progress_tab(
            self.window,
            "🤖 Generating Files...",
            "Analyzing and creating files...\n"
        )
        
        # Use the same logic as Generate Files command
        api_client = create_api_client_from_settings()
        prompt = self._build_generation_prompt(description, project_root)
        
        handler = StreamingResponseHandler()
        
        def content_callback(content):
            UIHelpers.append_to_tab(progress_tab, content)
            handler.handle_chunk(content)
        
        def fetch():
            try:
                api_client.make_streaming_request(prompt, content_callback)
                response = handler.get_accumulated_content()
                
                # Parse and create files (same as Generate Files)
                self._create_files_from_ai_response(response, project_root, progress_tab)
                
            except Exception as e:
                UIHelpers.append_to_tab(progress_tab, "\n\n❌ Error: {}".format(str(e)))
        
        threading.Thread(target=fetch).start()
    
    def _build_generation_prompt(self, user_input, project_root):
        """Build AI prompt with project analysis"""
        project_info = self._analyze_project_for_create(project_root)
        
        # Read project files for better context
        readme_info = ""
        composer_info = ""
        
        try:
            # Read composer.json if exists
            composer_path = os.path.join(project_root, 'composer.json')
            if os.path.exists(composer_path):
                import json
                with open(composer_path, 'r') as f:
                    composer_data = json.load(f)
                    name = composer_data.get('name', '')
                    require = composer_data.get('require', {})
                    composer_info = "\nComposer project: {}\nDependencies: {}".format(name, list(require.keys())[:5])
            
            # Read README if exists
            for readme in ['README.md', 'readme.txt', 'README.txt']:
                readme_path = os.path.join(project_root, readme)
                if os.path.exists(readme_path):
                    with open(readme_path, 'r') as f:
                        readme_content = f.read(500)  # First 500 chars
                        if 'php' in readme_content.lower() or 'laravel' in readme_content.lower():
                            readme_info = "\nREADME mentions: PHP/Laravel"
                        elif 'node' in readme_content.lower() or 'javascript' in readme_content.lower():
                            readme_info = "\nREADME mentions: Node.js/JavaScript"
                    break
        except:
            pass
        
        return """You are an expert developer. Analyze the project and create ALL necessary files.

REQUEST: {user_input}

PROJECT ANALYSIS:
{project_info}{composer_info}{readme_info}

IMPORTANT: 
1. Check the project type from the analysis above
2. If you see "Laravel PHP" or "composer.json" → create PHP/Laravel files
3. If you see "Node.js" or "package.json" → create Node.js files  
4. ONLY create files that match the project type!

Return ONLY valid JSON (NO markdown, NO explanations):
{{
  "files": [{{"path": "file.ext", "content": "Full content with \\n for newlines"}}],
  "instructions": "How to use/run what was created"
}}""".format(user_input=user_input, project_info=project_info, composer_info=composer_info, readme_info=readme_info)
    
    def _analyze_project_for_create(self, project_root):
        """Quick project analysis"""
        try:
            analysis = []
            
            # Check for Laravel
            if os.path.exists(os.path.join(project_root, 'artisan')):
                analysis.append("⚙️ FRAMEWORK: Laravel PHP")
            # Check for PHP (composer.json usually means PHP)
            elif os.path.exists(os.path.join(project_root, 'composer.json')):
                analysis.append("⚙️ FRAMEWORK: PHP (composer.json detected)")
            # Check for Node.js
            elif os.path.exists(os.path.join(project_root, 'package.json')):
                analysis.append("⚙️ FRAMEWORK: Node.js (package.json detected)")
            else:
                analysis.append("⚙️ FRAMEWORK: Unknown")
            
            # List key files
            key_files = []
            for file in ['composer.json', 'package.json', 'requirements.txt', 'Gemfile']:
                if os.path.exists(os.path.join(project_root, file)):
                    key_files.append(file)
            
            if key_files:
                analysis.append("📦 Key files: {}".format(", ".join(key_files)))
            
            return "\n".join(analysis)
        except Exception as e:
            return "Error analyzing: {}".format(str(e))
    
    def _create_files_from_ai_response(self, response, project_root, progress_tab):
        """Parse AI response and create files (shared with Generate Files)"""
        import json
        import re
        
        UIHelpers.append_to_tab(progress_tab, "\n📝 Parsing response...\n")
        
        try:
            # Extract JSON using balanced braces method
            json_text = None
            brace_count = 0
            start_idx = -1
            end_idx = -1
            
            for i, char in enumerate(response):
                if char == '{':
                    if brace_count == 0:
                        start_idx = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_idx != -1:
                        end_idx = i + 1
                        json_text = response[start_idx:end_idx]
                        if '"files"' in json_text:
                            break
            
            if not json_text:
                UIHelpers.append_to_tab(progress_tab, "\n❌ No JSON found")
                return
            
            # Parse JSON
            data = json.loads(json_text)
            files = data.get('files', [])
            
            # Create files
            created_count = 0
            for file_info in files:
                path = file_info.get('path')
                content = file_info.get('content')
                
                if not path or not content:
                    continue
                
                # Build full path
                full_path = os.path.join(project_root, path)
                
                # Create file
                if UIHelpers.create_file_safely(full_path, content):
                    created_count += 1
                    UIHelpers.append_to_tab(progress_tab, "\n✅ Created: {}".format(path))
            
            if created_count > 0:
                sublime.status_message("✅ Created {} file(s)".format(created_count))
                
        except Exception as e:
            UIHelpers.append_to_tab(progress_tab, "\n❌ Error: {}".format(str(e)))


# ============================================================================
# CACHE MANAGER (Utility command)
# ============================================================================

class LaravelWorkshopCacheManagerCommand(sublime_plugin.WindowCommand):
    """Manage Laravel Workshop AI cache"""
    
    def run(self):
        options = [
            ["Clear All Cache", "Remove all cached data"],
            ["Clear Context Cache", "Clear project context cache"],
            ["Clear Completion Cache", "Clear PHP completion cache"],
            ["View Cache Stats", "Show cache statistics"]
        ]
        
        self.window.show_quick_panel(options, self.on_select)
    
    def on_select(self, index):
        if index == -1:
            return
        
        if index == 0:
            self.clear_all_cache()
        elif index == 1:
            self.clear_context_cache()
        elif index == 2:
            self.clear_completion_cache()
        elif index == 3:
            self.show_cache_stats()
    
    def clear_all_cache(self):
        try:
            cache_dir = os.path.join(sublime.packages_path(), 'User', 'LaravelWorkshopAI', 'cache')
            if os.path.exists(cache_dir):
                import shutil
                shutil.rmtree(cache_dir)
                os.makedirs(cache_dir)
            sublime.status_message("✅ All cache cleared")
        except Exception as e:
            sublime.error_message("Failed to clear cache: {0}".format(str(e)))
    
    def clear_context_cache(self):
        sublime.status_message("✅ Context cache cleared")
    
    def clear_completion_cache(self):
        sublime.status_message("✅ Completion cache cleared")
    
    def show_cache_stats(self):
        sublime.message_dialog("Cache Stats:\n\nContext cache: 0 items\nCompletion cache: 0 items")


# ============================================================================
# SETTINGS (Utility command)
# ============================================================================

class LaravelWorkshopEditSettingsCommand(sublime_plugin.WindowCommand):
    """Opens the Laravel Workshop AI settings files in split view"""
    
    def run(self):
        # Get paths
        packages_path = sublime.packages_path()
        default_settings_path = os.path.join(packages_path, "LaravelWorkshopAI38", "LaravelWorkshopAI.sublime-settings")
        user_settings_path = os.path.join(packages_path, "User", "LaravelWorkshopAI.sublime-settings")
        
        # Try multiple paths for default settings
        default_content = ""
        
        # Try 1: Packages/LaravelWorkshopAI38/
        if os.path.exists(default_settings_path):
            try:
                with open(default_settings_path, 'r', encoding='utf-8') as f:
                    default_content = f.read()
                print("✅ Loaded default settings from: {}".format(default_settings_path))
            except Exception as e:
                print("❌ Error reading default settings from file: {}".format(e))
        
        # Try 2: Load from settings resource if file doesn't exist
        if not default_content:
            try:
                # Try to load from package
                resource = sublime.load_resource("Packages/LaravelWorkshopAI38/LaravelWorkshopAI.sublime-settings")
                default_content = resource
                print("✅ Loaded default settings from resource")
            except Exception as e:
                print("❌ Error loading default settings from resource: {}".format(e))
        
        # Try 3: Read from symlink target if it's a symlink
        if not default_content and os.path.exists(default_settings_path):
            try:
                real_path = os.path.realpath(default_settings_path)
                if real_path != default_settings_path and os.path.exists(real_path):
                    with open(real_path, 'r', encoding='utf-8') as f:
                        default_content = f.read()
                    print("✅ Loaded default settings from symlink target: {}".format(real_path))
            except Exception as e:
                print("❌ Error reading default settings from symlink: {}".format(e))
        
        # Try 4: Load from the plugin directory within this workspace (development mode)
        if not default_content:
            try:
                plugin_dir = os.path.dirname(__file__)
                workspace_default = os.path.join(plugin_dir, 'LaravelWorkshopAI.sublime-settings')
                if os.path.exists(workspace_default):
                    with open(workspace_default, 'r', encoding='utf-8') as f:
                        default_content = f.read()
                    print("✅ Loaded default settings from workspace: {}".format(workspace_default))
            except Exception as e:
                print("❌ Error reading default settings from workspace: {}".format(e))
        
        if not default_content:
            print("⚠️ WARNING: Could not load default settings. Path tried: {}".format(default_settings_path))
        
        # Create/read user settings - only show what's different from default
        user_content = ""
        default_dict = {}
        user_dict = {}
        
        # Parse default settings
        if default_content:
            try:
                # Remove comments for parsing
                cleaned_default = re.sub(r'//.*?$', '', default_content, flags=re.MULTILINE)
                cleaned_default = re.sub(r'/\*.*?\*/', '', cleaned_default, flags=re.DOTALL)
                default_dict = json.loads(cleaned_default)
            except:
                pass
        
        # Read user settings
        if os.path.exists(user_settings_path):
            try:
                with open(user_settings_path, 'r', encoding='utf-8') as f:
                    user_content_raw = f.read()
                    
                # Parse user settings
                cleaned_user = re.sub(r'//.*?$', '', user_content_raw, flags=re.MULTILINE)
                cleaned_user = re.sub(r'/\*.*?\*/', '', cleaned_user, flags=re.DOTALL)
                user_dict = json.loads(cleaned_user)
            except:
                user_content = user_content_raw  # If can't parse, show as-is
        else:
            # Create empty user settings
            user_content = """{
    // ============================================
    // Your Custom Settings
    // ============================================
    // Only add values that differ from default (left side)
    // Values here override default settings
    
}"""
            
            # Write empty user settings file
            os.makedirs(os.path.dirname(user_settings_path), exist_ok=True)
            with open(user_settings_path, 'w', encoding='utf-8') as f:
                f.write(user_content)
        
        # Store original user content for editing
        user_content_for_edit = user_content if user_content else ""
        
        # If we have both parsed, show only differences for display
        # But keep full user content for editing
        if default_dict and user_dict:
            differences = self._find_settings_differences(default_dict, user_dict)
            if differences:
                # Format differences nicely
                formatted_diff = json.dumps(differences, indent=4, ensure_ascii=False)
                user_content_display = "{\n    // ============================================\n"
                user_content_display += "    // Your Custom Overrides (differs from default)\n"
                user_content_display += "    // ============================================\n"
                user_content_display += "    // Only settings that differ are shown here\n"
                user_content_display += "    // See left panel for all available settings\n\n"
                user_content_display += formatted_diff[1:]  # Remove opening brace (already added)
                user_content_display = user_content_display.rstrip() + "\n}"
            else:
                user_content_display = """{
    // ============================================
    // Your Custom Settings
    // ============================================
    // No custom overrides - all using defaults
    // Add settings here to override defaults (see left panel)
    
}"""
        else:
            # Use original content if parsing failed or no default
            user_content_display = user_content if user_content else """{
    // Your custom settings here
    // Values here override defaults from left panel
}"""
        
        # For editing, use the actual file content (full), not just differences
        # This way user can add/remove any setting
        if not user_content_for_edit and os.path.exists(user_settings_path):
            # Read it again to be sure
            try:
                with open(user_settings_path, 'r', encoding='utf-8') as f:
                    user_content_for_edit = f.read()
            except:
                user_content_for_edit = user_content_display
        
        # Create a temporary view for default settings (left side)
        default_view = self.window.new_file()
        default_view.set_name("📋 Default Settings (Пример - Read Only)")
        default_view.set_syntax_file("Packages/JavaScript/JSON.sublime-syntax")
        default_view.set_scratch(True)
        default_view.set_read_only(True)
        # Normalize indentation/visuals for consistent rendering
        dv_settings = default_view.settings()
        dv_settings.set('detect_indentation', False)
        dv_settings.set('auto_indent', False)
        dv_settings.set('smart_indent', False)
        dv_settings.set('tab_size', 4)
        dv_settings.set('translate_tabs_to_spaces', False)
        dv_settings.set('word_wrap', False)
        
        # Wait a bit for view to be ready, then append content
        def populate_default_view():
            if not default_view or not default_view.is_valid():
                return
                
            if default_content:
                # Clear and populate with default content
                default_view.set_read_only(False)
                default_view.run_command('select_all')
                default_view.run_command('right_delete')
                # Use insert instead of append to ensure content appears
                def do_insert():
                    if default_view and default_view.is_valid():
                        default_view.run_command('insert', {'characters': default_content})
                        default_view.set_read_only(True)
                sublime.set_timeout(do_insert, 50)
            else:
                # Show helpful message with path info
                error_msg = "// ===========================================\n"
                error_msg += "// Default Settings file not found\n"
                error_msg += "// ===========================================\n\n"
                error_msg += "Expected path: {}\n\n".format(default_settings_path)
                error_msg += "Packages path: {}\n\n".format(packages_path)
                error_msg += "File exists: {}\n\n".format(os.path.exists(default_settings_path))
                error_msg += "Please check if the file exists in:\n"
                error_msg += "  Packages/LaravelWorkshopAI38/LaravelWorkshopAI.sublime-settings\n\n"
                error_msg += "// Example minimal config:\n{\n"
                error_msg += '    "ai_provider": "ollama",\n'
                error_msg += '    "ollama": {\n'
                error_msg += '        "model": "qwen2.5-coder:latest"\n'
                error_msg += '    }\n'
                error_msg += "}\n"
                default_view.set_read_only(False)
                default_view.run_command('select_all')
                default_view.run_command('right_delete')
                def do_insert_err():
                    if default_view and default_view.is_valid():
                        default_view.run_command('insert', {'characters': error_msg})
                        default_view.set_read_only(True)
                sublime.set_timeout(do_insert_err, 50)
        
        # Create a view showing only differences (right side)
        # This view shows only overrides and saves to user_settings_path
        user_diff_view = self.window.new_file()
        user_diff_view.set_name("✏️ Your Settings (Edit Overrides Only)")
        user_diff_view.set_syntax_file("Packages/JavaScript/JSON.sublime-syntax")
        # Not scratch - so it can be saved (but we redirect save to actual file via listener)
        user_diff_view.set_scratch(False)
        # Normalize indentation/visuals for consistent rendering
        ud_settings = user_diff_view.settings()
        ud_settings.set('detect_indentation', False)
        ud_settings.set('auto_indent', False)
        ud_settings.set('smart_indent', False)
        ud_settings.set('tab_size', 4)
        ud_settings.set('translate_tabs_to_spaces', False)
        ud_settings.set('word_wrap', False)
        
        def populate_user_diff_view():
            if default_dict and user_dict:
                differences = self._find_settings_differences(default_dict, user_dict)
                if differences:
                    formatted = json.dumps(differences, indent=4, ensure_ascii=False)
                    content = "{\n    // ============================================\n"
                    content += "    // Your Custom Overrides\n"
                    content += "    // ============================================\n"
                    content += "    // Only settings that differ from default (left)\n"
                    content += "    // See left panel for all available settings\n\n"
                    content += formatted[1:]  # Skip opening brace
                    content = content.rstrip() + "\n}"
                    user_diff_view.run_command('append', {'characters': content})
                    
                    # Store path for saving
                    user_diff_view.settings().set('settings_file_path', user_settings_path)
                else:
                    content = """{
    // ============================================
    // Your Custom Settings
    // ============================================
    // No overrides - all using defaults
    // Add settings here to override defaults
    // (see left panel for available options)
    
}"""
                    user_diff_view.run_command('append', {'characters': content})
                    user_diff_view.settings().set('settings_file_path', user_settings_path)
            else:
                # Fallback if parsing failed - show empty, user can add overrides
                # Don't show full content here, only what they want to override
                content = """{
    // ============================================
    // Your Custom Settings
    // ============================================
    // Parsing failed or no defaults loaded
    // Add only settings you want to override
    // See left panel for all available settings
    
}"""
                user_diff_view.run_command('append', {'characters': content})
                user_diff_view.settings().set('settings_file_path', user_settings_path)
        
        # Set up content and layout with longer delays for view initialization
        sublime.set_timeout(lambda: populate_default_view(), 200)
        sublime.set_timeout(lambda: populate_user_diff_view(), 400)
        sublime.set_timeout(lambda: self._setup_split_view(default_view, user_diff_view), 600)
    
    def _find_settings_differences(self, default_dict, user_dict):
        """Find only settings that differ from default"""
        differences = {}
        
        def compare_values(key, default_val, user_val):
            """Recursively compare values"""
            if isinstance(default_val, dict) and isinstance(user_val, dict):
                # Both are dicts, compare recursively
                nested_diff = {}
                for k in user_val:
                    if k in default_val:
                        nested_result = compare_values(k, default_val[k], user_val[k])
                        if nested_result is not None:
                            nested_diff[k] = nested_result
                    else:
                        # New key in user settings
                        nested_diff[k] = user_val[k]
                
                # Note: We don't handle removed keys explicitly
                # If user wants to remove a setting, they can delete it manually
                
                return nested_diff if nested_diff else None
            elif default_val != user_val:
                # Values differ
                return user_val
            else:
                # Values are the same
                return None
        
        # Compare all user keys
        for key in user_dict:
            if key in default_dict:
                result = compare_values(key, default_dict[key], user_dict[key])
                if result is not None:
                    differences[key] = result
            else:
                # New key not in default
                differences[key] = user_dict[key]
        
        return differences
    
    def _setup_split_view(self, default_view, user_view):
        """Setup split view with default on left, user on right"""
        try:
            window = self.window
            if not window or not default_view or not user_view:
                return
            
            # Set 2-column layout
            window.set_layout({
                'cols': [0.0, 0.5, 1.0],
                'rows': [0.0, 1.0],
                'cells': [[0, 0, 1, 1], [1, 0, 2, 1]]
            })
            
            # Move views to respective groups
            window.set_view_index(default_view, 0, 0)
            window.set_view_index(user_view, 1, 0)
            
            # Focus on user settings (right side)
            window.focus_view(user_view)
            
            sublime.status_message("💡 Лево: Пример Settings | Десно: Твои Settings (овде пишувај)")
        except Exception as e:
            print("Could not setup split view: {}".format(e))


# ============================================================================
# INLINE CHAT (Cursor-like feature)
# ============================================================================

class LaravelWorkshopAiPromptCommand(sublime_plugin.WindowCommand):
    """Cursor-like inline chat interface with file creation capability"""
    
    def run(self):
        UIHelpers.show_input_panel(
            self.window,
            "💬 Ask AI (use 'create: ' prefix to auto-generate files):",
            "",
            self.on_done
        )
    
    def on_done(self, user_input):
        if not user_input.strip():
            return
        
        api_client = create_api_client_from_settings()
        
        view = self.window.active_view()
        context_analyzer = ContextAnalyzer.from_view(view)
        usage_context = ""
        
        current_file_path = None
        if view and view.file_name():
            current_file_path = view.file_name()
            if context_analyzer and context_analyzer.project_root:
                relative_path = os.path.relpath(current_file_path, context_analyzer.project_root)
                try:
                    symbol, usage_context = context_analyzer.analyze_text_for_context(user_input, current_file_path)
                except Exception:
                    usage_context = ""
        
        # Check if this is a file creation request
        is_file_creation = user_input.lower().startswith('create: ')
        if is_file_creation:
            user_input = user_input.replace('create: ', '', 1).strip()
        
        full_prompt = "{0}{1}".format(user_input, usage_context)
        
        # Enhanced prompt for file creation
        if is_file_creation:
            full_prompt = self._build_file_creation_prompt(user_input, context_analyzer, current_file_path)

        tab = UIHelpers.create_output_tab(
            self.window, 
            "AI Chat",
            "\n> {0}\n\n".format(user_input)
        )

        def fetch():
            try:
                content = api_client.make_blocking_request(full_prompt)
                if content:
                    UIHelpers.append_to_tab(tab, content)
                    
                    # If it's a file creation request, parse and create files
                    if is_file_creation:
                        self._create_files_from_response(content, context_analyzer.project_root)
                else:
                    UIHelpers.append_to_tab(tab, "No response received")
            except Exception as e:
                UIHelpers.append_to_tab(tab, "Error: {0}".format(str(e)))

        sublime.set_timeout_async(fetch, 0)
    
    def _build_file_creation_prompt(self, user_input, context_analyzer, current_file_path):
        """Build enhanced prompt for file creation with project analysis"""
        
        project_root = context_analyzer.project_root if context_analyzer else None
        
        # Analyze project structure
        project_info = ""
        if project_root:
            project_info = self._analyze_project_structure(project_root)
        
        # Build comprehensive prompt
        prompt = """You are an expert Laravel/PHP developer. Analyze the project and create the requested files.

USER REQUEST: {user_input}

PROJECT INFO:
{project_info}

INSTRUCTIONS:
1. Analyze what files are needed based on the request
2. Return a JSON structure with this format:
{{
  "files": [
    {{
      "path": "app/Http/Controllers/ExampleController.php",
      "content": "<?php\\n\\nnamespace App\\\\Http\\\\Controllers;\\n\\n// Full file content here"
    }}
  ]
}}

RETURN ONLY VALID JSON, NO MARKDOWN OR EXPLANATIONS."""
        
        return prompt.format(user_input=user_input, project_info=project_info)
    
    def _analyze_project_structure(self, project_root):
        """Analyze project structure and return summary"""
        try:
            analysis = []
            
            # Check for Laravel structure
            if os.path.exists(os.path.join(project_root, 'artisan')):
                analysis.append("- Framework: Laravel")
            else:
                analysis.append("- Framework: PHP (vanilla)")
            
            # List directories
            common_dirs = ['app', 'config', 'database', 'resources', 'routes', 'tests', 'vendor']
            existing_dirs = [d for d in common_dirs if os.path.exists(os.path.join(project_root, d))]
            if existing_dirs:
                analysis.append("- Directories: {}".format(", ".join(existing_dirs)))
            
            # Check for composer.json
            if os.path.exists(os.path.join(project_root, 'composer.json')):
                try:
                    with open(os.path.join(project_root, 'composer.json'), 'r') as f:
                        import json
                        composer_data = json.load(f)
                        ns = composer_data.get('autoload', {}).get('psr-4', {})
                        if ns:
                            analysis.append("- Namespaces: {}".format(", ".join(ns.keys())))
                except:
                    pass
            
            return "\n".join(analysis) if analysis else "Standard PHP/Laravel project"
            
        except Exception as e:
            return "Error analyzing project: {}".format(e)
    
    def _create_files_from_response(self, response, project_root):
        """Parse AI response and create files"""
        import json
        import re
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*"files".*\}', response, re.DOTALL)
            if not json_match:
                # Try to find code blocks that might contain JSON
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
                if json_match:
                    json_text = json_match.group(1)
                else:
                    sublime.error_message("Could not parse AI response as JSON. Please check the response format.")
                    return
            else:
                json_text = json_match.group(0)
            
            # Parse JSON
            data = json.loads(json_text)
            files = data.get('files', [])
            
            if not files:
                sublime.status_message("No files specified in AI response")
                return
            
            # Create files
            created_count = 0
            for file_info in files:
                path = file_info.get('path')
                content = file_info.get('content')
                
                if not path or not content:
                    continue
                
                # Build full path
                full_path = os.path.join(project_root, path)
                
                # Create file
                if UIHelpers.create_file_safely(full_path, content):
                    created_count += 1
                    UIHelpers.show_status_message("✅ Created: {}".format(path), 2000)
                    
                    # Open the file
                    UIHelpers.open_file_in_window(self.window, full_path, 500)
            
            if created_count > 0:
                sublime.status_message("✅ Created {} file(s)".format(created_count))
            else:
                sublime.status_message("No files were created")
                
        except json.JSONDecodeError as e:
            sublime.error_message("Could not parse JSON response: {}".format(str(e)))
        except Exception as e:
            sublime.error_message("Error creating files: {}".format(str(e)))


# ============================================================================
# SMART COMPLETION (Cursor-like feature)
# ============================================================================

class LaravelWorkshopAiSmartCompletionCommand(LaravelWorkshopContextCommandBase):
    """Cursor-like smart code completion"""
    
    def run(self, edit):
        context_text = self.get_context_text()
        if not context_text.strip():
            sublime.status_message("No context for completion")
            return

        api_client = self.get_api_client()
        
        prompt = """Complete this code intelligently:

{context_text}

Provide a smart completion that makes sense in context. Return only the completion code."""

        def fetch():
            try:
                completion = api_client.make_blocking_request(prompt)
                if completion:
                    # Show completion in popup
                    self.view.show_popup(
                        "<div style='padding: 10px;'><pre>{0}</pre></div>".format(completion),
                        max_width=600,
                        max_height=400
                    )
            except Exception as e:
                sublime.status_message("Completion failed: {0}".format(str(e)))

        sublime.set_timeout_async(fetch, 0)


# ============================================================================
# AI FILE GENERATION (New feature)
# ============================================================================

class LaravelWorkshopAiGenerateFilesCommand(sublime_plugin.WindowCommand):
    """Generate files based on AI analysis of project needs"""
    
    def run(self):
        UIHelpers.show_input_panel(
            self.window,
            "✨ Describe what you want to create:",
            "",
            self.on_input
        )
    
    def on_input(self, user_input):
        if not user_input.strip():
            return
        
        # Get project root
        project_root = UIHelpers.ensure_project_folder(self.window)
        if not project_root:
            return
        
        # Create progress tab
        progress_tab = UIHelpers.create_progress_tab(
            self.window,
            "🤖 Generating Files...",
            "Analyzing project structure and generating files...\n"
        )
        
        # Create API client
        api_client = create_api_client_from_settings()
        
        # Build comprehensive prompt
        prompt = self._build_generation_prompt(user_input, project_root)
        
        handler = StreamingResponseHandler()
        
        def content_callback(content):
            UIHelpers.append_to_tab(progress_tab, content)
            handler.handle_chunk(content)
        
        def fetch():
            try:
                api_client.make_streaming_request(prompt, content_callback)
                
                response = handler.get_accumulated_content()
                
                # Parse and create files
                self._create_files_from_ai_response(response, project_root, progress_tab)
                
            except Exception as e:
                UIHelpers.append_to_tab(progress_tab, "\n\n❌ Error: {}".format(str(e)))
        
        threading.Thread(target=fetch).start()
    
    def _build_generation_prompt(self, user_input, project_root):
        """Build AI prompt with project analysis"""
        
        project_info = self._analyze_project_fully(project_root)
        
        return """You are an expert full-stack developer. Analyze the project and create ALL necessary files for the requested feature.

USER REQUEST: {user_input}

PROJECT ANALYSIS:
{project_info}

CRITICAL REQUIREMENTS:
1. **CHECK THE PROJECT TYPE FIRST!** Look at the PROJECT ANALYSIS above
2. If you see "Laravel" or "PHP" → create PHP/Laravel files ONLY
3. If you see "Node.js" → create Node.js files ONLY
4. **DO NOT create Node.js Docker for PHP projects!**
5. **DO NOT create PHP files for Node.js projects!**

Return ONLY valid JSON (NO markdown, NO explanations):
{{
  "files": [
    {{
      "path": "relative/path/to/file.ext",
      "content": "Full file content with \\n for newlines"
    }}
  ],
  "instructions": "How to use/run what was created"
}}

EXAMPLES:
- PHP/Laravel project → create PHP Dockerfile with PHP-FPM, PHP, MySQL
- Node.js project → create Node.js Dockerfile with Node, npm

CRITICAL: Return ONLY the JSON object. No ```json```, no markdown fences.""".format(user_input=user_input, project_info=project_info)
    
    def _analyze_project_fully(self, project_root):
        """Perform comprehensive project analysis"""
        analysis_parts = []
        
        try:
            # Detect framework - be more specific
            if os.path.exists(os.path.join(project_root, 'artisan')):
                analysis_parts.append("⚙️ FRAMEWORK: Laravel PHP")
                analysis_parts.append("✅ CONFIRMED: This is a PHP Laravel project!")
            elif os.path.exists(os.path.join(project_root, 'composer.json')):
                analysis_parts.append("⚙️ FRAMEWORK: PHP (composer.json detected)")
                analysis_parts.append("✅ CONFIRMED: This is a PHP project!")
            elif os.path.exists(os.path.join(project_root, 'package.json')):
                analysis_parts.append("⚙️ FRAMEWORK: Node.js")
                analysis_parts.append("✅ CONFIRMED: This is a Node.js project!")
            else:
                analysis_parts.append("⚙️ FRAMEWORK: Unknown")
            
            # Check what files exist to better identify project type
            key_files = []
            for file in ['composer.json', 'package.json', 'requirements.txt', 'Gemfile', 'artisan', 'package-lock.json']:
                if os.path.exists(os.path.join(project_root, file)):
                    key_files.append(file)
            
            if key_files:
                analysis_parts.append("📁 Key files found: {}".format(", ".join(key_files)))
            
            # Existing structure
            existing_dirs = []
            common_dirs = {
                'app': 'Application code',
                'config': 'Configuration',
                'database': 'Database migrations',
                'resources/views': 'Views',
                'routes': 'Routes',
                'tests': 'Tests',
                'vendor': 'Dependencies',
                'node_modules': 'Node.js dependencies'
            }
            
            for dir_name, description in common_dirs.items():
                dir_path = os.path.join(project_root, dir_name)
                if os.path.exists(dir_path):
                    existing_dirs.append("✓ {}/ - {}".format(dir_name, description))
            
            if existing_dirs:
                analysis_parts.append("EXISTING STRUCTURE:")
                analysis_parts.extend(existing_dirs)
            
            # Read composer.json for namespaces
            composer_path = os.path.join(project_root, 'composer.json')
            if os.path.exists(composer_path):
                try:
                    with open(composer_path, 'r') as f:
                        import json
                        composer_data = json.load(f)
                        name = composer_data.get('name', '')
                        require = composer_data.get('require', {})
                        analysis_parts.append("COMPOSER INFO:")
                        analysis_parts.append("  Project: {}".format(name))
                        analysis_parts.append("  Main deps: {}".format(list(require.keys())[:3]))
                        
                        autoload = composer_data.get('autoload', {})
                        psr4 = autoload.get('psr-4', {})
                        if psr4:
                            analysis_parts.append("PSR-4 NAMESPACES:")
                            for ns, path in psr4.items():
                                analysis_parts.append("  - {} maps to {}".format(ns.rstrip('\\'), path))
                except:
                    pass
            
            return "\n".join(analysis_parts)
            
        except Exception as e:
            return "Error analyzing project: {}".format(e)
    
    def _fix_nested_json_content(self, json_text):
        """Fix nested JSON in content fields by properly escaping nested quotes"""
        import re
        
        # Simple regex approach: find "content": "..." and fix nested quotes
        # We'll find the content field and replace unescaped quotes inside
        
        def fix_content_field(m):
            prefix = m.group(1)  # "content" : "
            content = m.group(2)  # The actual content value
            suffix = m.group(3)  # " (closing quote)
            
            # Escape quotes that aren't already escaped
            # But preserve escaped sequences like \"
            fixed_content = []
            i = 0
            while i < len(content):
                if content[i] == '\\' and i + 1 < len(content):
                    # Preserve escape sequences
                    fixed_content.append(content[i:i+2])
                    i += 2
                elif content[i] == '"':
                    # This quote needs escaping if it's not at start/end
                    fixed_content.append('\\"')
                    i += 1
                else:
                    fixed_content.append(content[i])
                    i += 1
            
            # Also escape newlines properly
            fixed = ''.join(fixed_content)
            fixed = fixed.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
            
            return prefix + fixed + suffix
        
        # Pattern to match content fields: "content": "value"
        # This handles multi-line strings too
        pattern = r'("content"\s*:\s*")(.*?)("(?:\s*[,}\]]))'
        
        # Use DOTALL to match across newlines
        fixed_json = re.sub(pattern, fix_content_field, json_text, flags=re.DOTALL)
        
        return fixed_json
    
    def _create_files_from_ai_response(self, response, project_root, progress_tab):
        """Parse AI response and create files"""
        import json
        import re
        
        UIHelpers.append_to_tab(progress_tab, "\n\n📝 Parsing AI response...\n")
        
        try:
            # Try to extract JSON from response
            json_text = None
            
            # Method 1: Try to find complete JSON with balanced braces
            # Use a more robust approach - find the complete JSON object
            brace_count = 0
            start_idx = -1
            end_idx = -1
            
            for i, char in enumerate(response):
                if char == '{':
                    if brace_count == 0:
                        start_idx = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_idx != -1:
                        end_idx = i + 1
                        json_text = response[start_idx:end_idx]
                        # Check if it contains "files" key
                        if '"files"' in json_text:
                            break
            
            # Method 2: Find in code blocks if no complete JSON found
            if not json_text:
                json_block = re.search(r'```json\s*(.*?)```', response, re.DOTALL)
                if json_block:
                    json_text = json_block.group(1).strip()
                else:
                    # Try without json tag
                    json_block = re.search(r'```\s*(.*?)```', response, re.DOTALL)
                    if json_block and '"files"' in json_block.group(1):
                        json_text = json_block.group(1).strip()
            
            if not json_text:
                UIHelpers.append_to_tab(progress_tab, "\n❌ Could not find JSON in AI response")
                UIHelpers.append_to_tab(progress_tab, "\nRaw response preview:\n{}".format(response[:1000]))
                return
            
            UIHelpers.append_to_tab(progress_tab, "✓ Found JSON structure\n")
            
            # Parse JSON - handle nested JSON in content fields
            try:
                data = json.loads(json_text)
            except json.JSONDecodeError as e:
                # Try to fix common JSON issues - nested JSON in content
                UIHelpers.append_to_tab(progress_tab, "⚠️ JSON parse error, attempting to fix...\n")
                
                # Try to manually parse and fix content fields
                try:
                    # Replace unescaped quotes in content strings
                    # This is a simple fix for nested JSON
                    fixed_json = self._fix_nested_json_content(json_text)
                    data = json.loads(fixed_json)
                except Exception as fix_error:
                    UIHelpers.append_to_tab(progress_tab, "❌ Could not fix JSON: {}\n".format(str(fix_error)))
                    UIHelpers.append_to_tab(progress_tab, "Problematic JSON preview:\n{}...\n".format(json_text[max(0, e.pos-100):e.pos+100]))
                    return
            
            files = data.get('files', [])
            instructions = data.get('instructions', '')
            
            if not files:
                UIHelpers.append_to_tab(progress_tab, "\n⚠️ No files found in AI response")
                return
            
            # Create files
            created_count = 0
            for i, file_info in enumerate(files, 1):
                path = file_info.get('path')
                content = file_info.get('content')
                
                if not path or not content:
                    UIHelpers.append_to_tab(progress_tab, "\n⚠️ File {}: Missing path or content".format(i))
                    continue
                
                # Process content - handle escaped characters
                # JSON already decodes escaped sequences automatically
                # But we need to handle if they're double-escaped
                if isinstance(content, str):
                    # Replace double-escaped sequences if they exist
                    if '\\n' in content and '\n' not in content:
                        content = content.replace('\\n', '\n')
                        content = content.replace('\\t', '\t')
                        content = content.replace('\\"', '"')
                        content = content.replace("\\'", "'")
                
                # Build full path
                full_path = os.path.join(project_root, path)
                
                # Create file
                if UIHelpers.create_file_safely(full_path, content):
                    created_count += 1
                    status_msg = "✅ [{}] Created: {}".format(created_count, path)
                    UIHelpers.append_to_tab(progress_tab, "\n{}".format(status_msg))
                    
                    # Open the last file
                    if i == len(files):
                        UIHelpers.open_file_in_window(self.window, full_path, 300)
                else:
                    UIHelpers.append_to_tab(progress_tab, "\n❌ Failed to create: {}".format(path))
            
            # Show instructions if provided
            if instructions:
                UIHelpers.append_to_tab(progress_tab, "\n\n📋 Instructions:")
                UIHelpers.append_to_tab(progress_tab, "\n" + instructions)
            
            # Summary
            UIHelpers.append_to_tab(progress_tab, "\n\n" + "="*50)
            UIHelpers.append_to_tab(progress_tab, "\n✅ Successfully created {} file(s)".format(created_count))
            UIHelpers.append_to_tab(progress_tab, "\n" + "="*50)
            
            sublime.status_message("✅ Created {} file(s)".format(created_count))
                
        except json.JSONDecodeError as e:
            UIHelpers.append_to_tab(progress_tab, "\n\n❌ JSON Parse Error: {}".format(str(e)))
            UIHelpers.append_to_tab(progress_tab, "\nAttempted to parse:\n{}".format(json_text[:500] if json_text else ""))
        except Exception as e:
            UIHelpers.append_to_tab(progress_tab, "\n\n❌ Error: {}".format(str(e)))


# ============================================================================
# CODE SMELL FINDER (Project-wide analysis)
# ============================================================================

class LaravelWorkshopCodeSmellFinderCommand(sublime_plugin.WindowCommand):
    """Find code smells across the entire project"""
    
    def run(self):
        project_root = UIHelpers.ensure_project_folder(self.window)
        if not project_root:
            return
        
        # Check if feature is enabled
        settings = sublime.load_settings("LaravelWorkshopAI.sublime-settings")
        if not settings.get("enable_code_smell_finder", True):
            sublime.status_message("Code Smell Finder is disabled in settings")
            return
        
        progress_tab = UIHelpers.create_progress_tab(
            self.window,
            "🔍 Finding Code Smells...",
            "Scanning project for code smells...\n"
        )
        
        api_client = create_api_client_from_settings()
        
        def analyze():
            try:
                # Scan project for PHP files
                php_files = self._scan_php_files(project_root)
                UIHelpers.append_to_tab(progress_tab, "Found {} PHP files\n".format(len(php_files)))
                UIHelpers.append_to_tab(progress_tab, "Analyzing...\n\n")
                
                # Analyze each file
                all_issues = []
                for file_path in php_files[:50]:  # Limit to 50 files for performance
                    issues = self._analyze_file(file_path, api_client, progress_tab)
                    if issues:
                        all_issues.extend(issues)
                
                # Display results
                self._display_results(progress_tab, all_issues)
                
            except Exception as e:
                UIHelpers.append_to_tab(progress_tab, "\n❌ Error: {}".format(str(e)))
        
        threading.Thread(target=analyze).start()
    
    def _scan_php_files(self, project_root):
        """Scan project for PHP files"""
        php_files = []
        for root, dirs, files in os.walk(project_root):
            # Skip vendor, node_modules, etc.
            if 'vendor' in root or 'node_modules' in root or '.git' in root:
                continue
            
            for file in files:
                if file.endswith('.php'):
                    php_files.append(os.path.join(root, file))
        
        return php_files
    
    def _analyze_file(self, file_path, api_client, progress_tab):
        """Analyze a single file for code smells"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            return []
        
        settings = sublime.load_settings("LaravelWorkshopAI.sublime-settings")
        prompt_template = settings.get("code_smell_prompt", "")
        
        # Get context for the file
        project_root = UIHelpers.ensure_project_folder(self.window)
        context_analyzer = ContextAnalyzer(project_root)
        
        # Build context
        context = ""
        try:
            symbol, usage_context = context_analyzer.analyze_text_for_context(content[:500], file_path)
            context = usage_context
        except:
            pass
        
        prompt = prompt_template.format(code=content[:2000], context=context[:1000])
        
        try:
            response = api_client.make_blocking_request(prompt)
            if response:
                return [{"file": file_path, "issues": response}]
        except:
            pass
        
        return []
    
    def _display_results(self, progress_tab, all_issues):
        """Display code smell results"""
        if not all_issues:
            UIHelpers.append_to_tab(progress_tab, "\n✅ No code smells found!\n")
            return
        
        UIHelpers.append_to_tab(progress_tab, "\n" + "="*60 + "\n")
        UIHelpers.append_to_tab(progress_tab, "🔍 CODE SMELLS FOUND: {}\n".format(len(all_issues)))
        UIHelpers.append_to_tab(progress_tab, "="*60 + "\n\n")
        
        for issue in all_issues:
            rel_path = os.path.relpath(issue['file'], UIHelpers.ensure_project_folder(self.window))
            UIHelpers.append_to_tab(progress_tab, "📄 {}\n".format(rel_path))
            UIHelpers.append_to_tab(progress_tab, "{}\n\n".format(issue['issues']))


# ============================================================================
# OPTIMIZE PROJECT (Project-wide optimization)
# ============================================================================

class LaravelWorkshopOptimizeProjectCommand(sublime_plugin.WindowCommand):
    """Optimize methods across the entire project"""
    
    def run(self):
        project_root = UIHelpers.ensure_project_folder(self.window)
        if not project_root:
            return
        
        progress_tab = UIHelpers.create_progress_tab(
            self.window,
            "⚡ Optimizing Project...",
            "Scanning project for optimization opportunities...\n"
        )
        
        api_client = create_api_client_from_settings()
        
        def analyze():
            try:
                # Scan for PHP files
                php_files = self._scan_php_files(project_root)
                UIHelpers.append_to_tab(progress_tab, "Found {} PHP files\n".format(len(php_files)))
                UIHelpers.append_to_tab(progress_tab, "Analyzing methods...\n\n")
                
                # Find methods in each file
                all_optimizations = []
                for file_path in php_files[:50]:
                    optimizations = self._find_optimizations(file_path, api_client, progress_tab)
                    if optimizations:
                        all_optimizations.extend(optimizations)
                
                # Display results
                self._display_optimizations(progress_tab, all_optimizations)
                
            except Exception as e:
                UIHelpers.append_to_tab(progress_tab, "\n❌ Error: {}".format(str(e)))
        
        threading.Thread(target=analyze).start()
    
    def _scan_php_files(self, project_root):
        """Scan project for PHP files"""
        php_files = []
        for root, dirs, files in os.walk(project_root):
            if 'vendor' in root or 'node_modules' in root or '.git' in root:
                continue
            for file in files:
                if file.endswith('.php'):
                    php_files.append(os.path.join(root, file))
        return php_files
    
    def _find_optimizations(self, file_path, api_client, progress_tab):
        """Find methods that can be optimized"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            return []
        
        # Extract methods using regex - find methods with balanced braces
        import re
        
        # Better pattern that handles nested braces
        methods = []
        method_pattern = r'(?:public|private|protected)\s+function\s+\w+\s*\([^)]*\)\s*'
        
        for match in re.finditer(method_pattern, content):
            start = match.end()
            brace_count = 0
            method_start = start
            
            # Find opening brace
            while method_start < len(content) and content[method_start] not in '{':
                method_start += 1
            
            if method_start >= len(content):
                continue
            
            brace_count = 1
            method_end = method_start + 1
            
            # Find closing brace with balanced braces
            while method_end < len(content) and brace_count > 0:
                if content[method_end] == '{':
                    brace_count += 1
                elif content[method_end] == '}':
                    brace_count -= 1
                method_end += 1
            
            if brace_count == 0:
                method_code = content[match.start():method_end]
                methods.append(method_code)
        
        if not methods:
            return []
        
        settings = sublime.load_settings("LaravelWorkshopAI.sublime-settings")
        prompt_template = settings.get("optimize_prompt", "")
        
        optimizations = []
        for method in methods[:5]:  # Limit per file
            prompt = prompt_template.format(code=method)
            
            try:
                response = api_client.make_blocking_request(prompt)
                if response and response.strip() != method.strip():
                    optimizations.append({
                        "file": file_path,
                        "method": method[:100] + "...",
                        "optimized": response
                    })
            except:
                pass
        
        return optimizations
    
    def _display_optimizations(self, progress_tab, optimizations):
        """Display optimization results"""
        if not optimizations:
            UIHelpers.append_to_tab(progress_tab, "\n✅ No optimizations found!\n")
            return
        
        UIHelpers.append_to_tab(progress_tab, "\n" + "="*60 + "\n")
        UIHelpers.append_to_tab(progress_tab, "⚡ OPTIMIZATION OPPORTUNITIES: {}\n".format(len(optimizations)))
        UIHelpers.append_to_tab(progress_tab, "="*60 + "\n\n")
        
        for opt in optimizations:
            rel_path = os.path.relpath(opt['file'], UIHelpers.ensure_project_folder(self.window))
            UIHelpers.append_to_tab(progress_tab, "📄 {}\n".format(rel_path))
            UIHelpers.append_to_tab(progress_tab, "Method: {}\n".format(opt['method']))
            UIHelpers.append_to_tab(progress_tab, "Optimized:\n{}\n\n".format(opt['optimized']))
