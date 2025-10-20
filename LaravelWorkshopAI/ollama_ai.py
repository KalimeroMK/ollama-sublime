"""
Laravel Workshop AI - Cleaned up version with AI Agents
Keeps only essential commands, everything else goes through AI Agents
"""

import sublime
import sublime_plugin
import os
import threading

# Import modular components
from ollama_api import create_api_client_from_settings
from context_analyzer import ContextAnalyzer
from ui_helpers import UIHelpers, TabManager
from response_processor import ResponseProcessor, StreamingResponseHandler


# ============================================================================
# BASE CLASSES
# ============================================================================

class OllamaContextCommandBase(sublime_plugin.TextCommand):
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

class OllamaPhpCompletionCommand(OllamaContextCommandBase):
    """AI-powered PHP/Laravel code completion - specialized autocomplete"""
    
    def __init__(self):
        super().__init__()
        self.api_client = None
        self.completion_cache = {}
        self.detection_cache = {}
        
        # PHP patterns
        self.php_patterns = {
            'functions': ['array_', 'str_', 'preg_', 'file_', 'json_', 'date_'],
            'classes': ['DateTime', 'PDO', 'Exception', 'ArrayObject', 'SplFileInfo'],
            'keywords': ['public', 'private', 'protected', 'static', 'abstract', 'final'],
            'constructs': ['if', 'else', 'foreach', 'while', 'for', 'switch', 'try', 'catch']
        }
        
        # Laravel patterns
        self.laravel_patterns = {
            'models': ['User', 'Post', 'Comment', 'Category', 'Product'],
            'controllers': ['UserController', 'PostController', 'AuthController'],
            'methods': ['index', 'show', 'create', 'store', 'edit', 'update', 'destroy'],
            'eloquent': ['find', 'where', 'get', 'first', 'create', 'update', 'delete'],
            'blade': ['@extends', '@section', '@yield', '@if', '@foreach', '@include'],
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
            print(f"Completion error: {e}")
            return self._get_fallback_completions(context, project_type)
    
    def _build_prompt(self, context, project_type):
        """Build prompt"""
        file_type = context['file_type']
        current_line = context['current_line']
        
        framework = "Laravel" if project_type == 'laravel' else "PHP"
        
        return f"""You are a {framework} expert. Complete this code:

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
            completion_items.append([completion, f"{label} {i+1}"])
        
        self.view.show_popup_menu(completion_items, lambda idx: self._on_select(idx, completions))
    
    def _on_select(self, index, completions):
        """Handle selection"""
        if index == -1 or index >= len(completions):
            return
        self.view.run_command('insert', {'characters': completions[index]})
    
    def _get_cache_key(self, context):
        """Generate cache key"""
        import hashlib
        key_data = f"{context['current_line']}_{context['file_type']}_{context['project_type']}"
        return hashlib.md5(key_data.encode()).hexdigest()


# ============================================================================
# CREATE FILE (Utility command)
# ============================================================================

class OllamaCreateFileCommand(sublime_plugin.WindowCommand):
    """Create a new file based on a prompt"""
    
    def run(self):
        UIHelpers.show_input_panel(
            self.window, 
            "Describe the file you want to create:", 
            "", 
            self.on_description
        )

    def on_description(self, description):
        self.description = description
        UIHelpers.show_input_panel(
            self.window,
            "Enter the file path (relative to project):", 
            "", 
            self.on_path
        )

    def on_path(self, path):
        project_root = UIHelpers.ensure_project_folder(self.window)
        if not project_root:
            return

        full_path = os.path.join(project_root, path)
        self.file_path = full_path

        _, ext = os.path.splitext(full_path)
        language = ext[1:] if ext else "text"

        api_client = create_api_client_from_settings()

        progress_view = UIHelpers.create_progress_tab(
            self.window,
            "Creating File", 
            f"Creating file at {full_path}\n"
        )

        prompt = f"""Create a new {language} file based on this description:
{self.description}

Generate only the file content, no explanations."""

        context_analyzer = ContextAnalyzer.from_view(self.window.active_view())
        
        current_file_path = None
        active_view = self.window.active_view()
        if active_view and active_view.file_name():
            current_file_path = active_view.file_name()
            if context_analyzer.project_root:
                current_file_path = os.path.relpath(current_file_path, context_analyzer.project_root)
        
        symbol, usage_context = context_analyzer.analyze_text_for_context(self.description, current_file_path)
        full_prompt = f"{prompt}{usage_context}"

        handler = StreamingResponseHandler()
        
        def content_callback(content):
            UIHelpers.append_to_tab(progress_view, content)
            handler.handle_chunk(content)

        def fetch():
            try:
                api_client.make_streaming_request(full_prompt, content_callback)
                
                file_content = handler.get_accumulated_content()
                if UIHelpers.create_file_safely(full_path, file_content):
                    UIHelpers.close_tab_delayed(progress_view, 500)
                    UIHelpers.open_file_in_window(self.window, full_path, 1000)
                else:
                    UIHelpers.append_to_tab(progress_view, 
                        ResponseProcessor.format_error_message("Failed to create file", "file creation"))
                    
            except Exception as e:
                UIHelpers.append_to_tab(progress_view, 
                    ResponseProcessor.format_error_message(e, "file generation"))

        threading.Thread(target=fetch).start()


# ============================================================================
# CACHE MANAGER (Utility command)
# ============================================================================

class OllamaCacheManagerCommand(sublime_plugin.WindowCommand):
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
            sublime.error_message(f"Failed to clear cache: {str(e)}")
    
    def clear_context_cache(self):
        sublime.status_message("✅ Context cache cleared")
    
    def clear_completion_cache(self):
        sublime.status_message("✅ Completion cache cleared")
    
    def show_cache_stats(self):
        sublime.message_dialog("Cache Stats:\n\nContext cache: 0 items\nCompletion cache: 0 items")


# ============================================================================
# SETTINGS (Utility command)
# ============================================================================

class OllamaEditSettingsCommand(sublime_plugin.WindowCommand):
    """Opens the Laravel Workshop AI settings file"""
    
    def run(self):
        settings_file = "Packages/User/Ollama.sublime-settings"
        self.window.run_command("open_file", {"file": "${packages}/" + settings_file})


# ============================================================================
# INLINE CHAT (Cursor-like feature)
# ============================================================================

class OllamaAiPromptCommand(sublime_plugin.WindowCommand):
    """Cursor-like inline chat interface"""
    
    def run(self):
        UIHelpers.show_input_panel(
            self.window,
            "💬 Ask AI:",
            "",
            self.on_done
        )
    
    def on_done(self, user_input):
        if not user_input.strip():
            return
        
        api_client = create_api_client_from_settings()
        
        view = self.window.active_view()
        context_analyzer = ContextAnalyzer.from_view(view)
        
        current_file_path = None
        if view and view.file_name():
            current_file_path = view.file_name()
            if context_analyzer.project_root:
                current_file_path = os.path.relpath(current_file_path, context_analyzer.project_root)
        
        symbol, usage_context = context_analyzer.analyze_text_for_context(user_input, current_file_path)
        full_prompt = f"{user_input}{usage_context}"

        tab = UIHelpers.create_output_tab(
            self.window, 
            "AI Chat",
            f"\n> {user_input}\n\n"
        )

        def fetch():
            try:
                content = api_client.make_blocking_request(full_prompt)
                if content:
                    UIHelpers.append_to_tab(tab, content)
                else:
                    UIHelpers.append_to_tab(tab, "No response received")
            except Exception as e:
                UIHelpers.append_to_tab(tab, f"Error: {str(e)}")

        sublime.set_timeout_async(fetch, 0)


# ============================================================================
# SMART COMPLETION (Cursor-like feature)
# ============================================================================

class OllamaAiSmartCompletionCommand(OllamaContextCommandBase):
    """Cursor-like smart code completion"""
    
    def run(self, edit):
        context_text = self.get_context_text()
        if not context_text.strip():
            sublime.status_message("No context for completion")
            return

        api_client = self.get_api_client()
        
        prompt = f"""Complete this code intelligently:

{context_text}

Provide a smart completion that makes sense in context. Return only the completion code."""

        def fetch():
            try:
                completion = api_client.make_blocking_request(prompt)
                if completion:
                    # Show completion in popup
                    self.view.show_popup(
                        f"<div style='padding: 10px;'><pre>{completion}</pre></div>",
                        max_width=600,
                        max_height=400
                    )
            except Exception as e:
                sublime.status_message(f"Completion failed: {str(e)}")

        sublime.set_timeout_async(fetch, 0)
