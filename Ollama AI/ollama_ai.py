import sublime
import sublime_plugin
import json
import urllib.request
import os
import re
import threading
import html
import time

# Import modular components
from ollama_api import create_api_client_from_settings
from context_analyzer import ContextAnalyzer, extract_symbol_from_text, get_project_context_for_symbol
from ui_helpers import UIHelpers, TabManager
from response_processor import ResponseProcessor, StreamingResponseHandler, ChatHistoryManager

class OllamaBaseCommand:
    def get_settings(self):
        settings = sublime.load_settings("Ollama.sublime-settings")
        continue_chat = settings.get("continue_chat", True)
        return continue_chat
    
    def get_api_client(self):
        """Get configured API client instance."""
        return create_api_client_from_settings()

class OllamaContextCommandBase(sublime_plugin.TextCommand):
    """Base class for commands that work with current cursor position or selection"""
    def get_settings(self):
        settings = sublime.load_settings("Ollama.sublime-settings")
        continue_chat = settings.get("continue_chat", True)
        return continue_chat
    
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
    
    def run(self, edit):
        # Get context text (selection, line, or word)
        context_text = self.get_context_text()
        if not context_text.strip():
            UIHelpers.show_status_message("Ollama: No text to analyze.")
            return

        # Get settings and API client
        settings = sublime.load_settings("Ollama.sublime-settings")
        api_client = self.get_api_client()

        # Get context-aware information with advanced multi-file analysis
        context_analyzer = ContextAnalyzer.from_view(self.view)
        
        # Get current file path for advanced context
        current_file_path = None
        if self.view and self.view.file_name():
            current_file_path = self.view.file_name()
            if context_analyzer.project_root:
                current_file_path = os.path.relpath(current_file_path, context_analyzer.project_root)
        
        symbol, usage_context = context_analyzer.analyze_text_for_context(context_text, current_file_path)

        # Prepare prompt
        prompt = self.get_prompt(settings).format(code=context_text)
        full_prompt = "{}{}".format(prompt, usage_context)

        # Create output tab
        tab_title = UIHelpers.format_tab_title(
            settings.get("tab_title", "Ollama {selection}"), 
            context_text, 
            max_length=20
        )
        
        tab_manager = TabManager(self.view.window())
        self.output_tab = tab_manager.create_output_tab(
            "selection_output",
            tab_title,
            prompt,
            api_client.model
        )

        # Handle streaming response
        def content_callback(content):
            UIHelpers.append_to_tab(self.output_tab, content)

        def fetch():
            try:
                api_client.make_streaming_request(full_prompt, content_callback)
            except Exception as e:
                UIHelpers.append_to_tab(
                    self.output_tab, 
                    ResponseProcessor.format_error_message(e, "streaming request")
                )

        sublime.set_timeout_async(fetch, 0)

    def get_prompt(self, settings):
        return settings.get("prompt", "Please explain this code:\n{code}\n")

class OllamaPhpCompletionCommand(OllamaContextCommandBase):
    """AI-powered PHP/Laravel code completion - works for both Laravel and native PHP"""
    
    def __init__(self):
        super().__init__()
        self.api_client = None
        self.completion_cache = {}
        self.detection_cache = {}
        
        # PHP patterns (работи за чист PHP)
        self.php_patterns = {
            'functions': ['array_', 'str_', 'preg_', 'file_', 'json_', 'date_'],
            'classes': ['DateTime', 'PDO', 'Exception', 'ArrayObject', 'SplFileInfo'],
            'keywords': ['public', 'private', 'protected', 'static', 'abstract', 'final'],
            'constructs': ['if', 'else', 'foreach', 'while', 'for', 'switch', 'try', 'catch']
        }
        
        # Laravel patterns (дополнителни за Laravel)
        self.laravel_patterns = {
            'models': ['User', 'Post', 'Comment', 'Category', 'Product'],
            'controllers': ['UserController', 'PostController', 'AuthController'],
            'methods': ['index', 'show', 'create', 'store', 'edit', 'update', 'destroy'],
            'eloquent': ['find', 'where', 'get', 'first', 'create', 'update', 'delete'],
            'blade': ['@extends', '@section', '@yield', '@if', '@foreach', '@include'],
            'facades': ['Route', 'DB', 'Auth', 'Cache', 'Config', 'View', 'Mail']
        }
    
    def run(self, edit):
        """Main completion logic - works for both PHP and Laravel"""
        view = self.view
        cursor_pos = view.sel()[0].begin()
        
        # Detect if we're in Laravel or native PHP
        project_type = self._detect_project_type()
        
        # Get appropriate context
        context = self._get_php_context(cursor_pos, project_type)
        
        # Generate completions based on project type
        completions = self._generate_completions(context, project_type)
        
        # Show completion popup
        self._show_completion_popup(completions, cursor_pos, project_type)
    
    def _detect_project_type(self):
        """Detect if we're working with Laravel or native PHP"""
        # Check cache first
        if 'project_type' in self.detection_cache:
            return self.detection_cache['project_type']
        
        # Get project root
        view = self.view
        if not view.window() or not view.window().folders():
            return 'php'  # Default to PHP if no project
        
        project_root = view.window().folders()[0]
        
        # Check for Laravel indicators
        laravel_indicators = [
            'artisan',
            'composer.json',
            'app/Http/Controllers',
            'app/Models',
            'resources/views',
            'routes/web.php',
            'vendor/laravel'
        ]
        
        is_laravel = any(
            os.path.exists(os.path.join(project_root, indicator))
            for indicator in laravel_indicators
        )
        
        project_type = 'laravel' if is_laravel else 'php'
        self.detection_cache['project_type'] = project_type
        
        return project_type
    
    def _get_php_context(self, cursor_pos, project_type):
        """Extract PHP context - works for both Laravel and native PHP"""
        view = self.view
        region = view.line(cursor_pos)
        line_text = view.substr(region)
        
        # Get surrounding context
        start_line = max(0, region.begin() - 1000)
        end_line = min(view.size(), region.end() + 1000)
        context_region = sublime.Region(start_line, end_line)
        context = view.substr(context_region)
        
        # Detect patterns based on project type
        if project_type == 'laravel':
            patterns = self._detect_laravel_patterns(context)
        else:
            patterns = self._detect_php_patterns(context)
        
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
            'is_string': '"' in context or "'" in context,
            'is_object': '->' in context,
            'is_static': '::' in context,
            'is_namespace': 'namespace ' in context,
            'is_use': 'use ' in context
        }
    
    def _detect_laravel_patterns(self, context):
        """Detect Laravel-specific patterns"""
        return {
            'is_model': 'class.*extends.*Model' in context,
            'is_controller': 'class.*Controller' in context,
            'is_migration': 'Schema::' in context,
            'is_blade': '@' in context and '.blade.php' in (self.view.file_name() or ''),
            'is_route': 'Route::' in context,
            'is_middleware': 'middleware' in context.lower(),
            'is_eloquent': '::' in context and any(model in context for model in self.laravel_patterns['models']),
            'is_facade': any(facade in context for facade in self.laravel_patterns['facades'])
        }
    
    def _detect_file_type(self):
        """Detect PHP file type"""
        filename = self.view.file_name()
        if not filename:
            return 'php'
        
        if 'Controller.php' in filename:
            return 'controller'
        elif 'Model.php' in filename:
            return 'model'
        elif 'migration' in filename:
            return 'migration'
        elif '.blade.php' in filename:
            return 'blade'
        elif 'routes' in filename:
            return 'routes'
        elif 'config' in filename:
            return 'config'
        else:
            return 'php'
    
    def _generate_completions(self, context, project_type):
        """Generate completions based on project type"""
        # Check cache first
        cache_key = self._get_cache_key(context)
        if cache_key in self.completion_cache:
            return self.completion_cache[cache_key]
        
        # Build appropriate prompt
        if project_type == 'laravel':
            prompt = self._build_laravel_prompt(context)
        else:
            prompt = self._build_php_prompt(context)
        
        # Get API client
        if not self.api_client:
            self.api_client = self.get_api_client()
        
        try:
            response = self.api_client.make_blocking_request(
                model=self._get_model(),
                prompt=prompt,
                max_tokens=150,
                temperature=0.2
            )
            
            completions = self._parse_completions(response, context, project_type)
            
            # Cache results
            self.completion_cache[cache_key] = completions
            
            return completions
            
        except Exception as e:
            print(f"Completion error: {e}")
            return self._get_fallback_completions(context, project_type)
    
    def _build_php_prompt(self, context):
        """Build prompt for native PHP completion"""
        file_type = context['file_type']
        current_line = context['current_line']
        patterns = context['patterns']
        
        prompt = f"""You are a PHP expert. Complete the following code:

File type: {file_type}
Current line: {current_line}
Context patterns: {patterns}

Provide 5 PHP-specific code completions. Focus on:
- PHP built-in functions
- Object-oriented PHP
- Array operations
- String manipulation
- File operations
- Database operations (PDO)
- Error handling
- Namespace usage

Return only the completion text, one per line.

Completions:"""
        
        return prompt
    
    def _build_laravel_prompt(self, context):
        """Build prompt for Laravel completion"""
        file_type = context['file_type']
        current_line = context['current_line']
        patterns = context['patterns']
        
        prompt = f"""You are a Laravel/PHP expert. Complete the following code:

File type: {file_type}
Current line: {current_line}
Laravel patterns: {patterns}

Provide 5 Laravel-specific code completions. Focus on:
- Eloquent ORM methods
- Laravel collections
- Blade directives
- Route definitions
- Controller methods
- Model relationships
- Validation rules
- Middleware usage
- Facades

Return only the completion text, one per line.

Completions:"""
        
        return prompt
    
    def _parse_completions(self, response, context, project_type):
        """Parse LLM response for completions"""
        try:
            response = response.strip()
            completions = [line.strip() for line in response.split('\n') if line.strip()]
            
            # Filter completions based on project type
            valid_completions = []
            for completion in completions:
                if self._is_valid_completion(completion, context, project_type):
                    valid_completions.append(completion)
            
            return valid_completions[:5]
            
        except Exception as e:
            print(f"Parse error: {e}")
            return self._get_fallback_completions(context, project_type)
    
    def _is_valid_completion(self, completion, context, project_type):
        """Validate completion based on project type"""
        if len(completion) < 2 or len(completion) > 100:
            return False
        
        # Common PHP patterns (работи за двете)
        common_patterns = [
            r'^[a-zA-Z_][a-zA-Z0-9_]*\(',  # Function calls
            r'^\$[a-zA-Z_][a-zA-Z0-9_]*->',  # Object methods
            r'^[a-zA-Z_][a-zA-Z0-9_]*::',  # Static methods
            r'^\s*[{}();]',  # Syntax completion
            r'^use\s+',  # Use statements
            r'^namespace\s+',  # Namespace
            r'^class\s+',  # Class definition
            r'^function\s+',  # Function definition
            r'^[a-zA-Z_][a-zA-Z0-9_]*\[',  # Array access
        ]
        
        # Laravel-specific patterns
        if project_type == 'laravel':
            laravel_patterns = [
                r'^@[a-zA-Z_][a-zA-Z0-9_]*',  # Blade directives
                r'^Route::',  # Route definitions
                r'^DB::',  # Database facade
                r'^Auth::',  # Auth facade
                r'^Cache::',  # Cache facade
                r'^Config::',  # Config facade
                r'^View::',  # View facade
                r'^Mail::',  # Mail facade
            ]
            common_patterns.extend(laravel_patterns)
        
        import re
        for pattern in common_patterns:
            if re.match(pattern, completion):
                return True
        
        return False
    
    def _get_fallback_completions(self, context, project_type):
        """Get fallback completions based on project type"""
        file_type = context['file_type']
        
        if project_type == 'laravel':
            return self._get_laravel_fallbacks(file_type)
        else:
            return self._get_php_fallbacks(file_type)
    
    def _get_php_fallbacks(self, file_type):
        """Get fallback completions for native PHP"""
        return [
            'public function ',
            'private function ',
            'protected function ',
            'array(',
            'if (',
            'foreach (',
            'while (',
            'try {',
            'catch (Exception $e) {',
            'throw new Exception('
        ]
    
    def _get_laravel_fallbacks(self, file_type):
        """Get fallback completions for Laravel"""
        fallbacks = {
            'model': [
                'protected $fillable = [',
                'public function user() {',
                'return $this->belongsTo(User::class);',
                'public function posts() {',
                'return $this->hasMany(Post::class);'
            ],
            'controller': [
                'public function index() {',
                'return view(\'',
                'public function store(Request $request) {',
                'public function show($id) {',
                'return redirect()->route(\''
            ],
            'blade': [
                '@extends(\'layouts.app\')',
                '@section(\'content\')',
                '@yield(\'content\')',
                '@if($condition)',
                '@foreach($items as $item)'
            ],
            'routes': [
                'Route::get(\'/\', function () {',
                'Route::resource(\'posts\', PostController::class);',
                'Route::middleware([\'auth\'])->group(function () {',
                'Route::get(\'/dashboard\', [DashboardController::class, \'index\']);'
            ]
        }
        
        return fallbacks.get(file_type, [
            'public function ',
            'private function ',
            'protected function ',
            'use Illuminate\\',
            'return view(\''
        ])
    
    def _show_completion_popup(self, completions, cursor_pos, project_type):
        """Show completion popup with appropriate icons"""
        if not completions:
            return
        
        # Create completion items with appropriate icons
        completion_items = []
        for i, completion in enumerate(completions):
            icon = self._get_completion_icon(completion, project_type)
            project_label = 'Laravel' if project_type == 'laravel' else 'PHP'
            completion_items.append([
                completion,
                f"{project_label} {icon} {i+1}",
                f"AI-generated {project_label} completion"
            ])
        
        # Show popup
        self.view.show_popup_menu(completion_items, self._on_completion_select)
    
    def _get_completion_icon(self, completion, project_type):
        """Get appropriate icon for completion"""
        if '::' in completion:
            return '⚡'  # Static method
        elif '->' in completion:
            return '🔗'  # Object method
        elif completion.startswith('@'):
            return '🎨'  # Blade directive
        elif 'Route::' in completion:
            return '🛣️'  # Route
        elif 'Model::' in completion:
            return '🗃️'  # Model
        elif project_type == 'laravel':
            return '🚀'  # Laravel
        else:
            return '🐘'  # PHP
    
    def _on_completion_select(self, index):
        """Handle completion selection"""
        if index == -1:
            return
        
        completions = self.completion_cache.get(self._get_current_cache_key(), [])
        if index < len(completions):
            completion = completions[index]
            
            # Insert completion with proper indentation
            cursor_pos = self.view.sel()[0].begin()
            self.view.run_command('insert', {'characters': completion})
    
    def _get_cache_key(self, context):
        """Generate cache key for context"""
        import hashlib
        key_data = f"{context['current_line']}_{context['file_type']}_{context['project_type']}_{context['cursor_pos']}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_current_cache_key(self):
        """Get current cache key"""
        cursor_pos = self.view.sel()[0].begin()
        project_type = self._detect_project_type()
        context = self._get_php_context(cursor_pos, project_type)
        return self._get_cache_key(context)
    
    def _get_model(self):
        """Get model for completion"""
        settings = sublime.load_settings('OllamaAI.sublime-settings')
        return settings.get('model', 'llama2')
    
    def get_api_client(self):
        """Get API client for making requests"""
        return create_api_client_from_settings()

class OllamaPromptCommand(sublime_plugin.WindowCommand):
    def get_settings(self):
        settings = sublime.load_settings("Ollama.sublime-settings")
        continue_chat = settings.get("continue_chat", True)
        return continue_chat
    
    def get_api_client(self):
        """Get configured API client instance."""
        return create_api_client_from_settings()
    def run(self):
        self.chat_history_manager = ChatHistoryManager()
        UIHelpers.show_input_panel(
            self.window,
            "Enter your prompt:",
            "",
            self.on_done
        )

    def on_done(self, user_input):
        if not user_input:
            return

        continue_chat = self.get_settings()
        api_client = self.get_api_client()

        # Get context-aware information with advanced multi-file analysis
        view = self.window.active_view()
        context_analyzer = ContextAnalyzer.from_view(view)
        
        # Get current file path for advanced context
        current_file_path = None
        if view and view.file_name():
            current_file_path = view.file_name()
            if context_analyzer.project_root:
                current_file_path = os.path.relpath(current_file_path, context_analyzer.project_root)
        
        symbol, usage_context = context_analyzer.analyze_text_for_context(user_input, current_file_path)
        full_prompt = "{}{}".format(user_input, usage_context)

        # Create output tab
        tab = UIHelpers.create_output_tab(
            self.window, 
            "Ollama Custom Prompt",
            "\n> " + user_input + "\n"
        )

        def fetch():
            try:
                # Prepare messages for API call
                messages = None
                if continue_chat and hasattr(self, 'chat_history_manager'):
                    messages = self.chat_history_manager.get_messages_for_api()
                    self.chat_history_manager.add_user_message(full_prompt)
                
                # Make API request
                content = api_client.make_blocking_request(full_prompt, messages)
                
                if content:
                    is_valid, validated_content = ResponseProcessor.validate_response_content(content)
                    if is_valid:
                        UIHelpers.append_to_tab(tab, validated_content)
                        
                        # Update chat history if continue_chat is enabled
                        if continue_chat and hasattr(self, 'chat_history_manager'):
                            self.chat_history_manager.add_assistant_message(validated_content)
                    else:
                        UIHelpers.append_to_tab(tab, ResponseProcessor.format_debug_message(
                            "Received empty or invalid response", content
                        ))
                else:
                    UIHelpers.append_to_tab(tab, ResponseProcessor.format_error_message(
                        "No response received from API", "API request"
                    ))
                    
            except Exception as e:
                UIHelpers.append_to_tab(tab, ResponseProcessor.format_error_message(e, "API request"))

        sublime.set_timeout_async(fetch, 0)

        # If continue_chat is enabled, prompt for next input automatically
        if getattr(self, 'continue_chat_panel', None):
            try:
                self.continue_chat_panel.close()
            except Exception:
                pass
                
        if continue_chat:
            def ask_next():
                UIHelpers.show_input_panel(
                    self.window,
                    "Continue chat (leave blank to end):",
                    "",
                    self.on_done
                )
            self.continue_chat_panel = sublime.set_timeout_async(ask_next, 500)

class OllamaSelectionCommandBase(sublime_plugin.TextCommand):
    def get_settings(self):
        settings = sublime.load_settings("Ollama.sublime-settings")
        continue_chat = settings.get("continue_chat", True)
        return continue_chat
    
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
    
    def run(self, edit):
        # Get context text (selection, line, or word)
        context_text = self.get_context_text()
        if not context_text.strip():
            UIHelpers.show_status_message("Ollama: No text to analyze.")
            return

        # Get settings and API client
        settings = sublime.load_settings("Ollama.sublime-settings")
        api_client = self.get_api_client()


class OllamaExplainSelectionCommand(OllamaContextCommandBase):
    def get_prompt(self, settings):
        return settings.get("explain_prompt", "Explain the following code in a concise and clear way, assuming a professional Laravel PHP developer audience. Focus on the code's purpose, its role in the system, and any non-obvious logic.\n\n---\n\n{code}")


class OllamaOptimizeSelectionCommand(OllamaContextCommandBase):
    def get_prompt(self, settings):
        return settings.get("optimize_prompt", "Optimize the following code, keeping in mind the conventions of modern Laravel PHP development. Return only the optimized code, without any extra explanations or markdown formatting.\n\n---\n\n{code}")


class OllamaCodeSmellFinderCommand(OllamaContextCommandBase):
    """
    Analyzes the selected code for code smells, suggests optimizations,
    and identifies potentially unused code.
    """
    def get_prompt(self, settings):
        return settings.get("code_smell_prompt", """
Analyze the following code for potential code smells, such as poor design choices, bugs, or non-optimal code.
Provide specific, actionable suggestions for improvement.
Based on the provided usage context, also determine if this code appears to be unused. If it is unused, explicitly state that it can likely be deleted.

Code to analyze:
{code}
""")


class OllamaSelectionPromptCommand(OllamaContextCommandBase):
    """
    A command that prompts the user for input and combines it with the selected text
    """
    def run(self, edit):
        # Get context text (selection, line, or word)
        self.context_text = self.get_context_text()
        if not self.context_text.strip():
            UIHelpers.show_status_message("Ollama: No text to analyze.")
            return

        # Show input panel for user prompt
        UIHelpers.show_input_panel(
            self.view.window(),
            "Enter prompt for selected code:",
            "",
            self.on_done
        )

    def on_done(self, user_prompt):
        if not user_prompt.strip():
            return

        # Get API client
        api_client = self.get_api_client()

        # Get context-aware information with advanced multi-file analysis
        context_analyzer = ContextAnalyzer.from_view(self.view)
        
        # Get current file path for advanced context
        current_file_path = None
        if self.view and self.view.file_name():
            current_file_path = self.view.file_name()
            if context_analyzer.project_root:
                current_file_path = os.path.relpath(current_file_path, context_analyzer.project_root)
        
        symbol, usage_context = context_analyzer.analyze_text_for_context(self.context_text, current_file_path)

        # Combine user prompt with context text and context
        full_prompt = "{}\n\n---\n\n{}{}".format(user_prompt, self.context_text, usage_context)

        # Create output tab
        tab_manager = TabManager(self.view.window())
        self.output_tab = tab_manager.create_output_tab(
            "custom_prompt",
            "Ollama Custom Prompt",
            user_prompt,
            api_client.model
        )

        # Handle streaming response
        def content_callback(content):
            UIHelpers.append_to_tab(self.output_tab, content)

        def fetch():
            try:
                api_client.make_streaming_request(full_prompt, content_callback)
            except Exception as e:
                UIHelpers.append_to_tab(
                    self.output_tab, 
                    ResponseProcessor.format_error_message(e, "custom prompt request")
                )

        sublime.set_timeout_async(fetch, 0)

    def is_visible(self):
        return UIHelpers.has_selection(self.view)


class OllamaCreateFileCommand(sublime_plugin.WindowCommand):
    """
    Create a new file based on a prompt
    """
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
        # Ensure project folder is available
        project_root = UIHelpers.ensure_project_folder(self.window)
        if not project_root:
            return

        # Determine the full file path
        full_path = os.path.join(project_root, path)
        self.file_path = full_path

        # Get file extension to determine language
        _, ext = os.path.splitext(full_path)
        language = ext[1:] if ext else "text"

        # Get API client
        api_client = create_api_client_from_settings()

        # Create a progress view
        progress_view = UIHelpers.create_progress_tab(
            self.window,
            "Creating File", 
            "Creating file at {}\n".format(full_path)
        )

        # Generate the prompt for file creation
        prompt = """You are a professional developer. Create a new {} file based on this description:
{}
File should be created at: {}

Generate only the file content, with no additional explanations or markdown formatting.
""".format(language, self.description, full_path)

        # Get context-aware information with advanced multi-file analysis
        context_analyzer = ContextAnalyzer.from_view(self.window.active_view())
        
        # Get current file path for advanced context (use target file path if available)
        current_file_path = None
        active_view = self.window.active_view()
        if active_view and active_view.file_name():
            current_file_path = active_view.file_name()
            if context_analyzer.project_root:
                current_file_path = os.path.relpath(current_file_path, context_analyzer.project_root)
        
        # If we don't have a current file, use the target file path for architectural context
        if not current_file_path and hasattr(self, 'file_path'):
            target_relative_path = os.path.relpath(self.file_path, project_root)
            current_file_path = target_relative_path
        
        symbol, usage_context = context_analyzer.analyze_text_for_context(self.description, current_file_path)
        full_prompt = "{}{}".format(prompt, usage_context)

        # Use streaming response handler to accumulate content
        handler = StreamingResponseHandler()
        
        def content_callback(content):
            UIHelpers.append_to_tab(progress_view, content)
            handler.handle_chunk(content)

        def fetch():
            try:
                # Make streaming request
                api_client.make_streaming_request(full_prompt, content_callback)
                
                # Get accumulated content and create file
                file_content = handler.get_accumulated_content()
                if UIHelpers.create_file_safely(full_path, file_content):
                    # Close progress view and open the new file
                    UIHelpers.close_tab_delayed(progress_view, 500)
                    UIHelpers.open_file_in_window(self.window, full_path, 1000)
                else:
                    UIHelpers.append_to_tab(progress_view, 
                        ResponseProcessor.format_error_message("Failed to create file", "file creation"))
                    
            except Exception as e:
                UIHelpers.append_to_tab(progress_view, 
                    ResponseProcessor.format_error_message(e, "file generation"))

        threading.Thread(target=fetch).start()


class OllamaInlineRefactorCommand(OllamaContextCommandBase):
    def get_settings(self):
        settings = sublime.load_settings("Ollama.sublime-settings")
        continue_chat = settings.get("continue_chat", True)
        return continue_chat
    
    def get_api_client(self):
        """Get configured API client instance."""
        return create_api_client_from_settings()
    """
    Shows an inline phantom with a refactoring suggestion for the selected code.
    The user can then approve or dismiss the suggestion.
    """
    def run(self, edit):
        # Check if there's any selected text
        self.context_text = self.get_context_text()
        self.selection_region = None
        
        # Persist the phantom set on the instance to prevent garbage collection
        self.phantom_set = sublime.PhantomSet(self.view, "ollama_inline_refactor")

        # Get the first selection region
        for region in self.view.sel():
            if not region.empty():
                self.selection_region = region
                break

        if not self.context_text.strip():
            UIHelpers.show_status_message("Ollama: No text selected.")
            return

        # Get API client and settings
        api_client = self.get_api_client()
        settings = sublime.load_settings("Ollama.sublime-settings")

        # Get context-aware information with advanced multi-file analysis
        context_analyzer = ContextAnalyzer.from_view(self.view)
        
        # Get current file path for advanced context
        current_file_path = None
        if self.view and self.view.file_name():
            current_file_path = self.view.file_name()
            if context_analyzer.project_root:
                current_file_path = os.path.relpath(current_file_path, context_analyzer.project_root)
        
        symbol, usage_context = context_analyzer.analyze_text_for_context(self.context_text, current_file_path)

        # Prepare prompt
        prompt_template = settings.get("refactor_prompt", "Refactor this code: {code}")
        full_prompt = prompt_template.format(code=self.context_text, context=usage_context)

        def do_request():
            try:
                # Make blocking request for inline refactor
                suggestion = api_client.make_blocking_request(full_prompt)
                
                if suggestion:
                    # Clean markdown and validate content
                    cleaned_suggestion = ResponseProcessor.clean_markdown_fences(suggestion, "php")
                    is_valid, validated_suggestion = ResponseProcessor.validate_response_content(cleaned_suggestion)
                    
                    if is_valid:
                        sublime.set_timeout(lambda: self.show_inline_suggestion(validated_suggestion), 0)
                    else:
                        UIHelpers.show_status_message("Ollama: Received an empty suggestion.")
                else:
                    UIHelpers.show_status_message("Ollama: No response received from API.")
                    
            except Exception as e:
                UIHelpers.show_status_message("Ollama: Refactor error: {}".format(e))

        thread = threading.Thread(target=do_request)
        thread.start()

    def show_inline_suggestion(self, suggestion):
        self.suggestion = suggestion  # Store suggestion for the 'approve' action
        escaped_suggestion = html.escape(self.suggestion, quote=False)

        # Restore the original, styled HTML
        phantom_content = """
            <body id="ollama-inline-refactor">
                <style>
                    body {
                        font-family: sans-serif;
                        margin: 0;
                        padding: 8px;
                        border-radius: 4px;
                        background-color: var(--background);
                        color: var(--foreground);
                        border: 1px solid var(--border);
                    }
                    .header {
                        font-weight: bold;
                        margin-bottom: 8px;
                        padding-bottom: 4px;
                        border-bottom: 1px solid var(--border);
                    }
                    pre {
                        margin: 0;
                        padding: 8px;
                        border-radius: 4px;
                        background-color: var(--background_light);
                        white-space: pre-wrap;
                        word-wrap: break-word;
                    }
                    .buttons {
                        margin-top: 8px;
                        text-align: right;
                    }
                    a {
                        text-decoration: none;
                        padding: 4px 8px;
                        border-radius: 4px;
                        background-color: var(--button_background);
                        color: var(--button_foreground);
                        margin-left: 4px;
                    }
                    a.approve {
                        background-color: var(--greenish);
                    }
                </style>
                <div class="header">AI Refactoring Suggestion</div>
                <pre><code>""" + escaped_suggestion + """</code></pre>
                <div class="buttons">
                    <a href="approve" class="approve">Approve</a>
                    <a href="dismiss">Dismiss</a>
                </div>
            </body>
        """

        phantom = sublime.Phantom(
            self.selection_region,
            phantom_content,
            sublime.LAYOUT_BLOCK,
            on_navigate=self.on_phantom_navigate
        )
        self.phantom_set.update([phantom])


    def on_phantom_navigate(self, href):
        if href == "approve":
            if hasattr(self, 'suggestion') and self.suggestion:
                self.view.run_command("ollama_replace_text", {"region_start": self.selection_region.begin(), "region_end": self.selection_region.end(), "text": self.suggestion})
        
        # Erase phantoms by updating the set with an empty list
        if hasattr(self, 'phantom_set'):
            self.phantom_set.update([])

    def is_visible(self):
        for region in self.view.sel():
            if not region.empty():
                return True
        return False


class OllamaReplaceTextCommand(OllamaContextCommandBase):
    def run(self, edit, region_start, region_end, text):
        region = sublime.Region(region_start, region_end)
        self.view.replace(edit, region, text)


class OllamaEditSettingsCommand(sublime_plugin.WindowCommand):
    """
    Opens the Ollama settings file for editing
    """
    def run(self):
        settings_file = "Packages/User/Ollama.sublime-settings"
        self.window.run_command("open_file", {"file": "${packages}/" + settings_file})


class OllamaEditSystemPromptsCommand(sublime_plugin.WindowCommand):
    """
    Opens the Ollama settings file for editing system prompts
    """
    def run(self):
        settings_file = "Packages/User/Ollama.sublime-settings"
        # Open the settings file
        view = self.window.run_command("open_file", {"file": "${packages}/" + settings_file})
        # We could add logic here to jump to system prompt section if needed


class OllamaGenerateFeatureCommand(sublime_plugin.WindowCommand):
    def get_settings(self):
        settings = sublime.load_settings("Ollama.sublime-settings")
        continue_chat = settings.get("continue_chat", True)
        return continue_chat
    
    def get_api_client(self):
        """Get configured API client instance."""
        return create_api_client_from_settings()
    """
    Generates multiple files for a new feature based on a high-level description.
    Uses a two-step process: Architect AI for planning and Coder AI for implementation.
    """
    def run(self):
        self.window.show_input_panel(
            "Enter a description for the new feature:",
            "",
            self.on_done,
            None,
            None
        )

    def on_done(self, description):
        if not description:
            return

        thread = threading.Thread(target=self.generate_feature, args=(description,))
        thread.start()

    def generate_feature(self, description):
        try:
            sublime.set_timeout(lambda: self.window.active_view().set_status("ollama_status", "Ollama: Asking Architect AI to create a plan..."), 0)

            # Step 1: Get the plan from the Architect AI
            architect_prompt = sublime.load_settings("Ollama.sublime-settings").get("feature_architect_prompt", "Create a JSON plan for this feature: {prompt}")
            full_architect_prompt = architect_prompt.format(prompt=description)
            plan_json_str = self._make_blocking_ollama_request(full_architect_prompt)

            if not plan_json_str:
                raise Exception("Architect AI returned an empty plan.")

            # Clean up the response to ensure it's valid JSON
            plan_json_str = ResponseProcessor.clean_markdown_fences(plan_json_str, "json")

            plan = json.loads(plan_json_str)
            files_to_create = plan.get("files", [])

            if not files_to_create:
                raise Exception("Architect AI did not specify any files to create.")

            sublime.set_timeout(lambda: self.window.active_view().set_status("ollama_status", ""), 0)
            sublime.set_timeout(lambda: self.show_plan_for_approval(files_to_create), 0)

        except Exception as e:
            sublime.set_timeout(lambda: sublime.error_message("Ollama Feature Generation Error: {}\n\nCheck the console for more details.".format(e)), 0)
            print("Ollama Error: Failed to generate feature plan. Raw response from AI was:")
            print(plan_json_str)

    def show_plan_for_approval(self, files_to_create):
        self.files_to_create = files_to_create
        plan_items = ["[✅ Approve and Create Files]", "[❌ Cancel]"] + ["- " + f["path"] for f in files_to_create]

        self.window.show_quick_panel(plan_items, self.on_plan_selection)

    def on_plan_selection(self, index):
        if index == -1 or index == 1:
            sublime.status_message("Ollama: Feature generation cancelled.")
            return

        if index == 0:
            thread = threading.Thread(target=self.create_files)
            thread.start()

    def create_files(self):
        try:
            project_root = self.window.folders()[0]
            coder_prompt_template = sublime.load_settings("Ollama.sublime-settings").get("feature_coder_prompt", "Create this file: {path} - {description}")

            for i, file_info in enumerate(self.files_to_create):
                path = file_info["path"]
                description = file_info["description"]
                progress_msg = "Ollama: ({}/{}) Asking Coder AI to write {}...".format(i + 1, len(self.files_to_create), path)
                sublime.set_timeout(lambda: self.window.active_view().set_status("ollama_status", progress_msg), 0)

                # Step 2: Get the code from the Coder AI
                full_coder_prompt = coder_prompt_template.format(path=path, description=description)
                file_content = self._make_blocking_ollama_request(full_coder_prompt)

                if not file_content:
                    print("Ollama Warning: Coder AI returned empty content for {}. Skipping.".format(path))
                    continue

                # Create the file
                file_path = os.path.join(project_root, path)
                if UIHelpers.create_file_safely(file_path, file_content):
                    # Open the newly created file
                    UIHelpers.open_file_in_window(self.window, file_path, 0)
                else:
                    print("Ollama Warning: Failed to create file {}. Skipping.".format(path))

            sublime.set_timeout(lambda: self.window.active_view().set_status("ollama_status", "Ollama: Feature generation complete!"), 0)

        except Exception as e:
            sublime.set_timeout(lambda: sublime.error_message("Ollama File Creation Error: {}".format(e)), 0)

    def _make_blocking_ollama_request(self, prompt):
        """Make a blocking request using the extracted API client."""
        api_client = self.get_api_client()
        return api_client.make_blocking_request(prompt)


class OllamaArchitectureAnalysisCommand(sublime_plugin.WindowCommand):
    def get_settings(self):
        settings = sublime.load_settings("Ollama.sublime-settings")
        continue_chat = settings.get("continue_chat", True)
        return continue_chat
    
    def get_api_client(self):
        """Get configured API client instance."""
        return create_api_client_from_settings()
    """
    Analyze the project's multi-file architecture and provide insights about
    patterns, relationships, and potential improvements.
    """
    
    def run(self):
        # Get API client
        api_client = self.get_api_client()
        
        # Get advanced context analyzer
        from multi_file_context import AdvancedContextAnalyzer
        
        try:
            context_analyzer = AdvancedContextAnalyzer.from_view(self.window.active_view())
            
            # Create analysis tab
            tab = UIHelpers.create_output_tab(
                self.window, 
                "Architecture Analysis",
                "🏗️ Analyzing project architecture...\n\n"
            )
            
            def fetch():
                try:
                    # Build comprehensive architecture report
                    report = self._build_architecture_report(context_analyzer)
                    
                    # Create AI prompt for analysis
                    prompt = """Analyze this Laravel project architecture and provide insights:

{}

Please provide:
1. Architecture overview and patterns identified
2. Code organization assessment
3. Potential improvements and refactoring suggestions
4. Dependency analysis and any circular dependencies
5. Recommendations for better structure

Be specific and actionable in your recommendations.""".format(report)
                    
                    # Get AI analysis
                    ai_analysis = api_client.make_blocking_request(prompt)
                    
                    if ai_analysis:
                        is_valid, validated_content = ResponseProcessor.validate_response_content(ai_analysis)
                        if is_valid:
                            UIHelpers.append_to_tab(tab, "🤖 AI Architecture Analysis:\n\n")
                            UIHelpers.append_to_tab(tab, validated_content)
                        else:
                            UIHelpers.append_to_tab(tab, "⚠️ Received invalid AI response")
                    else:
                        UIHelpers.append_to_tab(tab, "⚠️ No AI analysis received")
                        
                except Exception as e:
                    UIHelpers.append_to_tab(tab, ResponseProcessor.format_error_message(e, "architecture analysis"))
            
            sublime.set_timeout_async(fetch, 0)
            
        except Exception as e:
            UIHelpers.show_error_message(f"Error initializing architecture analysis: {e}")
    
    def _build_architecture_report(self, context_analyzer):
        """Build a comprehensive architecture report."""
        report = "📊 PROJECT ARCHITECTURE REPORT\n"
        report += "=" * 50 + "\n\n"
        
        # File statistics
        total_files = len(context_analyzer._file_cache)
        report += f"📁 Total Files: {total_files}\n"
        
        # File types breakdown
        extensions = {}
        for file_path, file_info in context_analyzer._file_cache.items():
            ext = file_info['extension']
            extensions[ext] = extensions.get(ext, 0) + 1
        
        report += "\n📋 File Types:\n"
        for ext, count in sorted(extensions.items()):
            report += f"  • {ext}: {count} files\n"
        
        # Architectural patterns
        if context_analyzer._architectural_patterns:
            report += "\n🏗️ Architectural Patterns Detected:\n"
            for pattern in context_analyzer._architectural_patterns:
                report += f"  • {pattern.pattern_type.upper()}: {pattern.description} ({len(pattern.files)} files)\n"
        
        # File roles distribution
        roles = {}
        for file_path, role in context_analyzer._file_roles.items():
            roles[role] = roles.get(role, 0) + 1
        
        report += "\n🎭 File Roles Distribution:\n"
        for role, count in sorted(roles.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                report += f"  • {role.title()}: {count} files\n"
        
        # Dependency analysis
        dependency_count = sum(len(deps) for deps in context_analyzer._dependency_graph.values())
        report += f"\n🔗 Total Dependencies: {dependency_count}\n"
        
        # Top files by dependency count
        file_dep_counts = [(file, len(deps)) for file, deps in context_analyzer._dependency_graph.items()]
        file_dep_counts.sort(key=lambda x: x[1], reverse=True)
        
        if file_dep_counts:
            report += "\n📈 Files with Most Dependencies:\n"
            for file_path, dep_count in file_dep_counts[:5]:
                role = context_analyzer._file_roles.get(file_path, 'unknown')
                report += f"  • {file_path} [{role}]: {dep_count} dependencies\n"
        
        # Top files by dependent count (reverse dependencies)
        file_dependent_counts = [(file, len(deps)) for file, deps in context_analyzer._reverse_dependency_graph.items()]
        file_dependent_counts.sort(key=lambda x: x[1], reverse=True)
        
        if file_dependent_counts:
            report += "\n📉 Most Depended Upon Files:\n"
            for file_path, dependent_count in file_dependent_counts[:5]:
                role = context_analyzer._file_roles.get(file_path, 'unknown')
                report += f"  • {file_path} [{role}]: {dependent_count} dependents\n"
        
        return report


class OllamaRelatedFilesCommand(OllamaContextCommandBase):
    def get_settings(self):
        settings = sublime.load_settings("Ollama.sublime-settings")
        continue_chat = settings.get("continue_chat", True)
        return continue_chat
    
    def get_api_client(self):
        """Get configured API client instance."""
        return create_api_client_from_settings()
    """
    Show related files for the current file based on advanced multi-file analysis.
    """
    
    def run(self, edit):
        if not self.view.file_name():
            UIHelpers.show_status_message("Ollama: No file currently open.")
            return
        
        from multi_file_context import AdvancedContextAnalyzer
        
        try:
            context_analyzer = AdvancedContextAnalyzer.from_view(self.view)
            
            # Get current file relative path
            current_file_path = self.view.file_name()
            if context_analyzer.project_root:
                current_file_path = os.path.relpath(current_file_path, context_analyzer.project_root)
            
            # Get related files
            related_files = context_analyzer.get_related_files(current_file_path, max_depth=2)
            
            if not related_files:
                UIHelpers.show_status_message("Ollama: No related files found.")
                return
            
            # Create analysis tab
            tab = UIHelpers.create_output_tab(
                self.view.window(), 
                f"Related Files: {os.path.basename(current_file_path)}",
                f"🔗 Files related to {current_file_path}:\n\n"
            )
            
            # Group files by role
            files_by_role = {}
            for file_path in related_files:
                role = context_analyzer._file_roles.get(file_path, 'unknown')
                if role not in files_by_role:
                    files_by_role[role] = []
                files_by_role[role].append(file_path)
            
            # Display files grouped by role
            for role, files in sorted(files_by_role.items()):
                UIHelpers.append_to_tab(tab, f"📁 {role.upper()} FILES:\n")
                for file_path in files:
                    # Get relationship info
                    relationship_info = self._get_relationship_info(context_analyzer, current_file_path, file_path)
                    UIHelpers.append_to_tab(tab, f"  • {file_path} {relationship_info}\n")
                UIHelpers.append_to_tab(tab, "\n")
            
            # Add architectural context
            arch_context = context_analyzer.get_architectural_context(current_file_path)
            if arch_context:
                UIHelpers.append_to_tab(tab, arch_context)
                
        except Exception as e:
            UIHelpers.show_error_message(f"Error analyzing related files: {e}")
    
    def _get_relationship_info(self, context_analyzer, source_file, target_file):
        """Get relationship information between two files."""
        relationships = []
        
        # Check direct dependencies
        for relationship in context_analyzer._dependency_graph.get(source_file, []):
            if relationship.target_file == target_file:
                relationships.append(f"→{relationship.relationship_type}")
        
        # Check reverse dependencies
        for relationship in context_analyzer._reverse_dependency_graph.get(source_file, []):
            if relationship.source_file == target_file:
                relationships.append(f"←{relationship.relationship_type}")
        
        if relationships:
            return f"[{', '.join(relationships)}]"
        return "[related]"


class OllamaImpactAnalysisCommand(OllamaContextCommandBase):
    def get_settings(self):
        settings = sublime.load_settings("Ollama.sublime-settings")
        continue_chat = settings.get("continue_chat", True)
        return continue_chat
    
    def get_api_client(self):
        """Get configured API client instance."""
        return create_api_client_from_settings()
    """
    Analyze the potential impact of changes to the current file.
    """
    
    def run(self, edit):
        if not self.view.file_name():
            UIHelpers.show_status_message("Ollama: No file currently open.")
            return
        
        # Get API client
        api_client = self.get_api_client()
        
        from multi_file_context import AdvancedContextAnalyzer
        
        try:
            context_analyzer = AdvancedContextAnalyzer.from_view(self.view)
            
            # Get current file relative path
            current_file_path = self.view.file_name()
            if context_analyzer.project_root:
                current_file_path = os.path.relpath(current_file_path, context_analyzer.project_root)
            
            # Create analysis tab
            tab = UIHelpers.create_output_tab(
                self.view.window(), 
                f"Impact Analysis: {os.path.basename(current_file_path)}",
                f"🎯 Analyzing potential impact of changes to {current_file_path}...\n\n"
            )
            
            def fetch():
                try:
                    # Build impact report
                    impact_report = self._build_impact_report(context_analyzer, current_file_path)
                    
                    # Create AI prompt for impact analysis
                    prompt = f"""Analyze the potential impact of modifying this file in a Laravel project:

{impact_report}

Please provide:
1. Risk assessment (High/Medium/Low) for changes to this file
2. Recommended testing strategy
3. Areas that require special attention when modifying this file
4. Suggested deployment considerations
5. Potential breaking changes to watch out for

Be specific about the impact on different parts of the application."""
                    
                    # Get AI analysis
                    ai_analysis = api_client.make_blocking_request(prompt)
                    
                    if ai_analysis:
                        is_valid, validated_content = ResponseProcessor.validate_response_content(ai_analysis)
                        if is_valid:
                            UIHelpers.append_to_tab(tab, "🤖 AI Impact Assessment:\n\n")
                            UIHelpers.append_to_tab(tab, validated_content)
                        else:
                            UIHelpers.append_to_tab(tab, "⚠️ Received invalid AI response")
                    else:
                        UIHelpers.append_to_tab(tab, "⚠️ No AI analysis received")
                        
                except Exception as e:
                    UIHelpers.append_to_tab(tab, ResponseProcessor.format_error_message(e, "impact analysis"))
            
            sublime.set_timeout_async(fetch, 0)
            
        except Exception as e:
            UIHelpers.show_error_message(f"Error analyzing impact: {e}")
    
    def _build_impact_report(self, context_analyzer, file_path):
        """Build a comprehensive impact analysis report."""
        report = f"📊 IMPACT ANALYSIS REPORT FOR: {file_path}\n"
        report += "=" * 60 + "\n\n"
        
        # File role and basic info
        role = context_analyzer._file_roles.get(file_path, 'unknown')
        file_info = context_analyzer._file_cache.get(file_path, {})
        
        report += f"📁 File Role: {role.title()}\n"
        report += f"📏 File Size: {file_info.get('size', 0)} characters\n"
        report += f"📂 Directory: {file_info.get('directory', 'N/A')}\n\n"
        
        # Dependencies analysis
        dependencies = context_analyzer.get_file_dependencies(file_path)
        dependents = context_analyzer.get_file_dependents(file_path)
        
        report += f"🔗 Direct Dependencies: {len(dependencies)}\n"
        if dependencies:
            for dep in dependencies[:5]:
                dep_role = context_analyzer._file_roles.get(dep, 'unknown')
                report += f"  • {dep} [{dep_role}]\n"
            if len(dependencies) > 5:
                report += f"  • ... and {len(dependencies) - 5} more\n"
        
        report += f"\n📈 Files Depending on This: {len(dependents)}\n"
        if dependents:
            for dep in dependents[:5]:
                dep_role = context_analyzer._file_roles.get(dep, 'unknown')
                report += f"  • {dep} [{dep_role}]\n"
            if len(dependents) > 5:
                report += f"  • ... and {len(dependents) - 5} more\n"
        
        # Risk assessment based on dependencies
        risk_level = "Low"
        if len(dependents) > 10:
            risk_level = "High"
        elif len(dependents) > 5:
            risk_level = "Medium"
        
        report += f"\n⚠️ Estimated Risk Level: {risk_level}\n"
        
        # Architectural patterns this file participates in
        participating_patterns = [p for p in context_analyzer._architectural_patterns if file_path in p.files]
        if participating_patterns:
            report += "\n🏗️ Architectural Patterns:\n"
            for pattern in participating_patterns:
                report += f"  • {pattern.pattern_type.upper()}: {pattern.description}\n"
        
        # Related files for broader context
        related_files = context_analyzer.get_related_files(file_path, max_depth=1)
        if related_files:
            report += f"\n🔄 Related Files ({len(related_files)}):\n"
            for related in related_files[:5]:
                related_role = context_analyzer._file_roles.get(related, 'unknown')
                report += f"  • {related} [{related_role}]\n"
        
        return report


class OllamaCacheManagerCommand(sublime_plugin.WindowCommand):
    def get_settings(self):
        settings = sublime.load_settings("Ollama.sublime-settings")
        continue_chat = settings.get("continue_chat", True)
        return continue_chat
    
    def get_api_client(self):
        """Get configured API client instance."""
        return create_api_client_from_settings()
    """Command to manage Ollama AI cache and performance settings."""
    
    def run(self):
        """Show cache management options."""
        items = [
            ["🗑️ Clear All Cache", "Clear all cached context analysis data"],
            ["📊 Show Cache Statistics", "Display cache hit/miss statistics"],
            ["⚡ Performance Report", "Show performance metrics and recommendations"],
            ["🔧 Cache Settings", "Open cache configuration settings"],
            ["📈 Reset Performance Metrics", "Reset all performance tracking data"]
        ]
        
        self.window.show_quick_panel(
            items,
            self.on_cache_option_selected
        )
    
    def on_cache_option_selected(self, index):
        """Handle cache management option selection."""
        if index == 0:
            self.clear_cache()
        elif index == 1:
            self.show_cache_stats()
        elif index == 2:
            self.show_performance_report()
        elif index == 3:
            self.open_cache_settings()
        elif index == 4:
            self.reset_performance_metrics()
    
    def clear_cache(self):
        """Clear all cached data."""
        try:
            # Get the context analyzer to access cache
            view = self.window.active_view()
            if view:
                context_analyzer = ContextAnalyzer.from_view(view)
                if hasattr(context_analyzer, 'cache'):
                    context_analyzer.cache.clear()
                    UIHelpers.show_status_message("✅ All cache cleared successfully!", 3000)
                else:
                    UIHelpers.show_status_message("⚠️ Cache system not available", 3000)
            else:
                UIHelpers.show_status_message("⚠️ No active view to access cache", 3000)
        except Exception as e:
            UIHelpers.show_error_message(f"Failed to clear cache: {str(e)}")
    
    def show_cache_stats(self):
        """Display cache statistics."""
        try:
            view = self.window.active_view()
            if view:
                context_analyzer = ContextAnalyzer.from_view(view)
                if hasattr(context_analyzer, 'cache'):
                    stats = context_analyzer.cache.get_stats()
                    
                    stats_text = f"""# 📊 Cache Statistics

## Cache Performance
- **Cache Size**: {stats['size']} entries
- **Cache Hits**: {stats['hits']}
- **Cache Misses**: {stats['misses']}
- **Hit Rate**: {hit_rate:.1f}%

## Recommendations
"""
                    
                    if stats['hits'] + stats['misses'] > 0:
                        hit_rate = (stats['hits'] / (stats['hits'] + stats['misses'])) * 100
                        if hit_rate < 50:
                            stats_text += "- ⚠️ Low cache hit rate - consider increasing cache size\n"
                        elif hit_rate > 80:
                            stats_text += "- ✅ Excellent cache performance\n"
                        else:
                            stats_text += "- 🔶 Moderate cache performance\n"
                    
                    stats_text += f"- **Cache Directory**: ~/.sublime_ollama_cache\n"
                    stats_text += f"- **Max Cache Size**: 100 entries\n"
                    stats_text += f"- **Cache TTL**: 1 hour\n"
                    
                    # Create stats tab
                    tab = UIHelpers.create_output_tab(
                        self.window,
                        "Ollama AI Cache Statistics",
                        stats_text
                    )
                    
                    # Set markdown syntax
                    tab.set_syntax_file("Packages/Markdown/Markdown.sublime-syntax")
                    
                else:
                    UIHelpers.show_status_message("⚠️ Cache system not available", 3000)
            else:
                UIHelpers.show_status_message("⚠️ No active view to access cache", 3000)
        except Exception as e:
            UIHelpers.show_error_message(f"Failed to show cache stats: {str(e)}")
    
    def show_performance_report(self):
        """Show comprehensive performance report."""
        try:
            view = self.window.active_view()
            if view:
                context_analyzer = ContextAnalyzer.from_view(view)
                
                report_text = f"""# ⚡ Performance Report

## Context Analysis Performance
- **Files Scanned**: {len(getattr(context_analyzer, '_file_cache', {}))}
- **Dependencies Tracked**: {len(getattr(context_analyzer, '_dependency_graph', {}))}
- **Architectural Patterns**: {len(getattr(context_analyzer, '_architectural_patterns', []))}

## Cache Performance
"""
                
                if hasattr(context_analyzer, 'cache'):
                    stats = context_analyzer.cache.get_stats()
                    if stats['hits'] + stats['misses'] > 0:
                        hit_rate = (stats['hits'] / (stats['hits'] + stats['misses'])) * 100
                        report_text += f"- **Cache Hit Rate**: {hit_rate:.1f}%\n"
                    else:
                        report_text += "- **Cache Hit Rate**: 0.0%\n"
                    report_text += f"- **Cache Size**: {stats['size']} entries\n"
                
                report_text += f"""
## Performance Recommendations
- **For Large Projects**: Enable background processing
- **For Better Cache**: Increase cache size if memory allows
- **For Faster Scans**: Adjust file size limits and scan timeouts

## Current Settings
- **Max Files to Scan**: 1000
- **File Size Limit**: 1MB
- **Scan Timeout**: 30 seconds
- **Batch Processing**: 50 files per batch
"""
                
                # Create performance report tab
                tab = UIHelpers.create_output_tab(
                    self.window,
                    "Ollama AI Performance Report",
                    report_text
                )
                
                # Set markdown syntax
                tab.set_syntax_file("Packages/Markdown/Markdown.sublime-syntax")
                
            else:
                UIHelpers.show_status_message("⚠️ No active view to analyze", 3000)
        except Exception as e:
            UIHelpers.show_error_message(f"Failed to generate performance report: {str(e)}")
    
    def open_cache_settings(self):
        """Open cache configuration settings."""
        try:
            settings_file = "Ollama AI/Ollama.sublime-settings"
            self.window.open_file(settings_file)
            UIHelpers.show_status_message("🔧 Cache settings opened", 2000)
        except Exception as e:
            UIHelpers.show_error_message(f"Failed to open cache settings: {str(e)}")
    
    def reset_performance_metrics(self):
        """Reset all performance tracking data."""
        try:
            # Reset cache statistics
            view = self.window.active_view()
            if view:
                context_analyzer = ContextAnalyzer.from_view(view)
                if hasattr(context_analyzer, 'cache'):
                    context_analyzer.cache.clear()
                    
                    # Reset stats
                    context_analyzer.cache.cache_stats = {"hits": 0, "misses": 0, "size": 0}
                    
                    UIHelpers.show_status_message("✅ Performance metrics reset successfully!", 3000)
                else:
                    UIHelpers.show_status_message("⚠️ Cache system not available", 3000)
            else:
                UIHelpers.show_status_message("⚠️ No active view to access cache", 3000)
        except Exception as e:
            UIHelpers.show_error_message(f"Failed to reset performance metrics: {str(e)}")

class OllamaAiPromptCommand(sublime_plugin.WindowCommand):
    """Enhanced prompt command with Cursor-like inline interface."""
    
    def run(self):
        """Show enhanced inline prompt interface."""
        view = self.window.active_view()
        if not view:
            sublime.error_message("No active view found")
            return
            
        # Create inline chat interface
        self.show_inline_chat(view)
    
    def show_inline_chat(self, view):
        """Show Cursor-like inline chat interface."""
        # Create a phantom overlay for the chat
        phantom_set = sublime.PhantomSet(view, "ollama_inline_chat")
        
        # Get current cursor position
        cursor_pos = view.sel()[0].end() if view.sel() else 0
        
        # Create chat HTML
        chat_html = self._create_chat_html()
        
        # Create phantom
        phantom = sublime.Phantom(
            sublime.Region(cursor_pos, cursor_pos),
            chat_html,
            sublime.LAYOUT_BLOCK,
            self._on_chat_phantom_click
        )
        
        phantom_set.update([phantom])
        self.phantom_set = phantom_set
        
        # Store view reference
        self.chat_view = view
    
    def _create_chat_html(self):
        """Create Cursor-like chat interface HTML."""
        return """
        <div style="background: #1e1e1e; border: 1px solid #3c3c3c; border-radius: 8px; padding: 16px; margin: 8px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3); font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;">
            <div style="display: flex; align-items: center; margin-bottom: 12px;">
                <div style="background: #007acc; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px;"></div>
                <span style="color: #cccccc; font-size: 14px; font-weight: 500;">AI Assistant</span>
            </div>
            
            <div style="background: #2d2d30; border-radius: 6px; padding: 12px; margin-bottom: 12px;">
                <textarea id="chat-input" placeholder="Ask me anything about your code..." style="width: 100%; background: transparent; border: none; color: #cccccc; font-family: inherit; font-size: 13px; resize: none; outline: none;" rows="3"></textarea>
            </div>
            
            <div style="display: flex; gap: 8px; justify-content: flex-end;">
                <button onclick="sendMessage()" style="background: #007acc; color: white; border: none; padding: 8px 16px; border-radius: 4px; font-size: 12px; cursor: pointer; font-weight: 500;">Send</button>
                <button onclick="dismissChat()" style="background: #3c3c3c; color: #cccccc; border: none; padding: 8px 16px; border-radius: 4px; font-size: 12px; cursor: pointer;">Cancel</button>
            </div>
            
            <div id="chat-history" style="margin-top: 12px; max-height: 200px; overflow-y: auto;"></div>
        </div>
        
        <script>
        function sendMessage() {
            const input = document.getElementById('chat-input');
            const message = input.value.trim();
            if (message) {
                // Send message to Sublime Text
                window.location.href = 'sublime://ollama-chat?message=' + encodeURIComponent(message);
                input.value = '';
            }
        }
        
        function dismissChat() {
            window.location.href = 'sublime://ollama-chat?action=dismiss';
        }
        
        // Auto-focus input
        document.getElementById('chat-input').focus();
        </script>
        """
    
    def _on_chat_phantom_click(self, href):
        """Handle chat phantom interactions."""
        if href.startswith('ollama-chat'):
            # Parse the message
            if 'message=' in href:
                message = href.split('message=')[1]
                self._process_chat_message(message)
            elif 'action=dismiss' in href:
                self._dismiss_chat()
    
    def _process_chat_message(self, message):
        """Process chat message and show response."""
        # Show typing indicator
        self._show_typing_indicator()
        
        # Get API client and make request
        api_client = create_api_client_from_settings()
        if not api_client:
            self._show_error("Failed to create API client")
            return
        
        # Make request
        response = api_client.make_blocking_request(message)
        if response:
            self._show_chat_response(message, response)
        else:
            self._show_error("Failed to get response from AI")
    
    def _show_typing_indicator(self):
        """Show typing indicator in chat."""
        if hasattr(self, 'phantom_set'):
            typing_html = """
            <div style="background: #1e1e1e; border: 1px solid #3c3c3c; border-radius: 8px; padding: 12px; margin: 8px; color: #cccccc; font-size: 13px;">
                <div style="display: flex; align-items: center;">
                    <div style="background: #007acc; width: 6px; height: 6px; border-radius: 50%; margin-right: 8px; animation: pulse 1.5s infinite;"></div>
                    AI is thinking...
                </div>
            </div>
            <style>
            @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
            </style>
            """
            
            # Add typing indicator to chat history
            if hasattr(self, 'chat_view'):
                typing_phantom = sublime.Phantom(
                    sublime.Region(0, 0),
                    typing_html,
                    sublime.LAYOUT_BLOCK
                )
                self.phantom_set.update([typing_phantom])
    
    def _show_chat_response(self, question, answer):
        """Show AI response in chat interface."""
        response_html = f"""
        <div style="background: #1e1e1e; border: 1px solid #3c3c3c; border-radius: 8px; padding: 12px; margin: 8px;">
            <div style="color: #cccccc; font-size: 12px; margin-bottom: 8px; opacity: 0.7;">{question}</div>
            <div style="background: #2d2d30; border-radius: 4px; padding: 8px; color: #cccccc; font-size: 13px; white-space: pre-wrap;">{answer}</div>
        </div>
        """
        
        # Update chat with response
        if hasattr(self, 'phantom_set'):
            response_phantom = sublime.Phantom(
                sublime.Region(0, 0),
                response_html,
                sublime.LAYOUT_BLOCK
            )
            self.phantom_set.update([response_phantom])
    
    def _show_error(self, error_message):
        """Show error message in chat."""
        error_html = f"""
        <div style="background: #1e1e1e; border: 1px solid #e74c3c; border-radius: 8px; padding: 12px; margin: 8px; color: #e74c3c; font-size: 13px;">
            ❌ {error_message}
        </div>
        """
        
        if hasattr(self, 'phantom_set'):
            error_phantom = sublime.Phantom(
                sublime.Region(0, 0),
                error_html,
                sublime.LAYOUT_BLOCK
            )
            self.phantom_set.update([error_phantom])
    
    def _dismiss_chat(self):
        """Dismiss the chat interface."""
        if hasattr(self, 'phantom_set'):
            self.phantom_set.update([])
        if hasattr(self, 'chat_view'):
            self.chat_view = None


class OllamaAiSmartCompletionCommand(OllamaContextCommandBase):
    """Cursor-like smart code completion with AI suggestions."""
    
    def run(self, edit):
        """Show smart completion suggestions."""
        view = self.view
        cursor_pos = view.sel()[0].end()
        
        # Get context around cursor
        context = self._get_context_around_cursor(view, cursor_pos)
        
        # Show completion popup
        self._show_completion_popup(view, context, cursor_pos)
    
    def _get_context_around_cursor(self, view, cursor_pos):
        """Get code context around cursor position."""
        # Get line content
        line_region = view.line(cursor_pos)
        line_content = view.substr(line_region)
        
        # Get previous few lines for context
        start_line = max(0, line_region.begin() - 200)
        context_region = sublime.Region(start_line, cursor_pos)
        context = view.substr(context_region)
        
        return {
            'current_line': line_content,
            'context': context,
            'cursor_pos': cursor_pos - start_line
        }
    
    def _show_completion_popup(self, view, context, cursor_pos):
        """Show AI-powered completion suggestions."""
        # Create completion items
        items = [
            ["💡 Complete this line", "Complete the current line of code"],
            ["🔧 Suggest improvements", "Get optimization suggestions"],
            ["📝 Add documentation", "Add comments and documentation"],
            ["🧪 Add tests", "Generate test cases"],
            ["🔍 Explain this code", "Get detailed explanation"]
        ]
        
        def on_completion_selected(index):
            if index >= 0:
                self._execute_completion(view, context, items[index][0], cursor_pos)
        
        # Show quick panel
        view.window().show_quick_panel(items, on_completion_selected)
    
    def _execute_completion(self, view, context, action, cursor_pos):
        """Execute the selected completion action."""
        if "Complete this line" in action:
            self._complete_current_line(view, context)
        elif "Suggest improvements" in action:
            self._suggest_improvements(view, context)
        elif "Add documentation" in action:
            self._add_documentation(view, context)
        elif "Add tests" in action:
            self._add_tests(view, context)
        elif "Explain this code" in action:
            self._explain_code(view, context)
    
    def _complete_current_line(self, view, context):
        """Complete the current line of code."""
        # Get API client
        api_client = create_api_client_from_settings()
        if not api_client:
            sublime.error_message("Failed to create API client")
            return
        
        # Create completion prompt
        prompt = f"Complete this line of code:\n\n{context['current_line']}\n\nProvide only the completed line, nothing else."
        
        # Get completion
        response = api_client.make_blocking_request(prompt)
        if response:
            # Insert completion at cursor
            cursor_pos = view.sel()[0].end()
            view.run_command("insert", {"characters": response.strip()})
        else:
            sublime.error_message("Failed to get completion from AI")
    
    def _suggest_improvements(self, view, context):
        """Suggest code improvements."""
        api_client = create_api_client_from_settings()
        if not api_client:
            return
        
        prompt = f"Suggest improvements for this code:\n\n{context['context']}\n\nProvide specific, actionable improvements."
        response = api_client.make_blocking_request(prompt)
        
        if response:
            # Show improvements in new tab
            window = view.window()
            tab = window.new_file()
            tab.set_name("AI Improvements")
            tab.run_command("insert", {"characters": response})
            tab.set_syntax_file("Packages/Markdown/Markdown.sublime-syntax")
    
    def _add_documentation(self, view, context):
        """Add documentation to code."""
        api_client = create_api_client_from_settings()
        if not api_client:
            return
        
        prompt = f"Add comprehensive documentation to this code:\n\n{context['context']}\n\nInclude comments explaining what the code does."
        response = api_client.make_blocking_request(prompt)
        
        if response:
            # Show documented code in new tab
            window = view.window()
            tab = window.new_file()
            tab.set_name("Documented Code")
            tab.run_command("insert", {"characters": response})
            tab.set_syntax_file(view.settings().get("syntax"))
    
    def _add_tests(self, view, context):
        """Generate test cases for code."""
        api_client = create_api_client_from_settings()
        if not api_client:
            return
        
        prompt = f"Generate comprehensive test cases for this code:\n\n{context['context']}\n\nCreate unit tests that cover all scenarios."
        response = api_client.make_blocking_request(prompt)
        
        if response:
            # Show tests in new tab
            window = view.window()
            tab = window.new_file()
            tab.set_name("Generated Tests")
            tab.run_command("insert", {"characters": response})
            tab.set_syntax_file("Packages/PHP/PHP.sublime-syntax")
    
    def _explain_code(self, view, context):
        """Explain the code in detail."""
        api_client = create_api_client_from_settings()
        if not api_client:
            return
        
        prompt = f"Explain this code in detail:\n\n{context['context']}\n\nProvide a clear, comprehensive explanation."
        response = api_client.make_blocking_request(prompt)
        
        if response:
            # Show explanation in new tab
            window = view.window()
            tab = window.new_file()
            tab.set_name("Code Explanation")
            tab.run_command("insert", {"characters": response})
            tab.set_syntax_file("Packages/Markdown/Markdown.sublime-syntax")


class OllamaAiRealTimeSuggestionsCommand(sublime_plugin.EventListener):
    """Real-time AI suggestions as you type (Cursor-like feature)."""
    
    def on_selection_modified(self, view):
        """Show real-time suggestions when selection changes."""
        # Only activate for certain file types
        if not self._should_activate(view):
            return
        
        # Check if we should show suggestions
        if self._should_show_suggestions(view):
            self._show_real_time_suggestions(view)
    
    def _should_activate(self, view):
        """Check if real-time suggestions should be activated."""
        # Only for code files
        syntax = view.settings().get("syntax", "")
        code_syntaxes = ["PHP", "JavaScript", "Python", "Laravel"]
        return any(syn in syntax for syn in code_syntaxes)
    
    def _should_show_suggestions(self, view):
        """Check if we should show suggestions now."""
        # Show suggestions every few seconds
        current_time = time.time()
        if not hasattr(view, 'last_suggestion_time'):
            view.last_suggestion_time = 0
        
        if current_time - view.last_suggestion_time > 5:  # 5 seconds
            view.last_suggestion_time = current_time
            return True
        return False
    
    def _show_real_time_suggestions(self, view):
        """Show real-time AI suggestions."""
        # Get current context
        cursor_pos = view.sel()[0].end() if view.sel() else 0
        context = self._get_context_for_suggestions(view, cursor_pos)
        
        # Show suggestion popup
        self._show_suggestion_popup(view, context)
    
    def _get_context_for_suggestions(self, view, cursor_pos):
        """Get context for real-time suggestions."""
        # Get surrounding code
        start_pos = max(0, cursor_pos - 500)
        end_pos = min(view.size(), cursor_pos + 500)
        context_region = sublime.Region(start_pos, end_pos)
        context = view.substr(context_region)
        
        return {
            'context': context,
            'cursor_pos': cursor_pos - start_pos
        }
    
    def _show_suggestion_popup(self, view, context):
        """Show suggestion popup."""
        # Create suggestion items
        suggestions = [
            "💡 This code could be optimized",
            "🔧 Consider using a design pattern here",
            "📝 Add error handling",
            "🧪 This would benefit from unit tests"
        ]
        
        # Show popup
        view.show_popup_menu(suggestions, self._on_suggestion_selected)
    
    def _on_suggestion_selected(self, index):
        """Handle suggestion selection."""
        # This would trigger the specific suggestion action
        pass
