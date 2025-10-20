"""
Inline Chat - Cursor/Windsurf-like chat interface
Shows a sidebar tab where you can chat with AI
Persistent history and context across sessions
"""

import sublime
import sublime_plugin
import html
import json
import os
from typing import List, Dict, Optional

from .laravel_workshop_api import create_api_client_from_settings
from .context_analyzer import ContextAnalyzer
# Temporarily disabled - laravel_intelligence has syntax errors
# from .laravel_intelligence import get_laravel_analyzer, LaravelContextDetector
from .ui_helpers import UIHelpers


class InlineChatManager:
    """Manages inline chat sessions with persistent history"""
    
    def __init__(self):
        self.chat_history = []
        self.current_view: Optional[sublime.View] = None
        self.chat_view: Optional[sublime.View] = None
        self.is_active = False
        self.context_cache = {}
        self.history_file = None
        
        # Load history on init
        self._load_history()
        
    def _get_history_file(self, view: sublime.View):
        """Get history file path for current project"""
        window = view.window()
        if not window or not window.folders():
            # Use global history
            cache_dir = os.path.join(sublime.packages_path(), 'User', 'LaravelWorkshopAI', 'chat_history')
            os.makedirs(cache_dir, exist_ok=True)
            return os.path.join(cache_dir, 'global_chat.json')
        
        # Use project-specific history
        project_root = window.folders()[0]
        project_name = os.path.basename(project_root)
        cache_dir = os.path.join(sublime.packages_path(), 'User', 'LaravelWorkshopAI', 'chat_history')
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, '{0}_chat.json'.format(project_name))
    
    def _load_history(self):
        """Load chat history from file"""
        if not self.current_view:
            return
        
        self.history_file = self._get_history_file(self.current_view)
        
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.chat_history = data.get('history', [])
                    self.context_cache = data.get('context', {})
            except Exception as e:
                print("Error loading chat history: {0}".format(e))
                self.chat_history = []
    
    def _save_history(self):
        """Save chat history to file"""
        if not self.history_file:
            return
        
        try:
            data = {
                'history': self.chat_history[-100:],  # Keep last 100 messages
                'context': self.context_cache
            }
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Error saving chat history: {0}".format(e))
    
    def start_chat(self, view: sublime.View):
        """Start a new chat session in sidebar"""
        self.current_view = view
        self.is_active = True
        
        # Load history for this project
        self.history_file = self._get_history_file(view)
        self._load_history()
        
        # Create or show chat tab
        self._create_chat_tab()
        
        # Show input prompt
        self.show_input_prompt()
    
    def _create_chat_tab(self):
        """Create or show chat tab in sidebar"""
        window = self.current_view.window()
        if not window:
            return
        
        # Check if chat tab already exists
        for view in window.views():
            if view.settings().get('laravel_workshop_chat_tab'):
                self.chat_view = view
                window.focus_view(view)
                self._update_chat_display()
                return
        
        # Create new chat tab
        self.chat_view = window.new_file()
        self.chat_view.set_name("💬 AI Chat")
        self.chat_view.settings().set('laravel_workshop_chat_tab', True)
        self.chat_view.settings().set('word_wrap', True)
        self.chat_view.set_scratch(True)
        self.chat_view.set_read_only(True)
        
        # Move to right side
        window.set_view_index(self.chat_view, 1, 0)
        
        # Initial content
        self._update_chat_display()
    
    def show_input_prompt(self):
        """Show input prompt to user"""
        if not self.current_view:
            return
        
        # Show input panel
        window = self.current_view.window()
        if window:
            window.show_input_panel(
                "💬 Chat with AI:",
                "",
                self.on_user_input,
                None,
                self.on_cancel
            )
    
    def on_user_input(self, user_message):
        """Handle user input"""
        if not user_message.strip():
            return
        
        # Add to history
        self.chat_history.append({
            'role': 'user',
            'content': user_message,
            'timestamp': self._get_timestamp()
        })
        
        # Save history
        self._save_history()
        
        # Show user message
        self._update_chat_display()
        
        # Get AI response
        self._get_ai_response(user_message)
    
    def _get_timestamp(self):
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M")
    
    def _get_ai_response(self, user_message):
        """Get response from AI with streaming"""
        api_client = create_api_client_from_settings()
        
        # Get context
        context = self._build_context()
        
        # Build prompt with context
        full_prompt = self._build_prompt_with_context(user_message, context)
        
        # Show loading
        self.chat_history.append({
            'role': 'assistant',
            'content': '',
            'timestamp': self._get_timestamp()
        })
        self._update_chat_display()
        
        # Streaming callback
        def content_callback(chunk):
            if self.chat_history:
                self.chat_history[-1]['content'] += chunk
                sublime.set_timeout(lambda: self._update_chat_display(), 0)
        
        def fetch():
            try:
                # Use streaming for better UX
                api_client.make_streaming_request(full_prompt, content_callback)
                
                # Save history
                self._save_history()
                
                # Ask for next input
                sublime.set_timeout(lambda: self.show_input_prompt(), 100)
                
            except Exception as e:
                self.chat_history[-1]['content'] = "❌ Error: {0}".format(str(e))
                sublime.set_timeout(lambda: self._update_chat_display(), 0)
                self._save_history()
        
        sublime.set_timeout_async(fetch, 0)
    
    def _build_context(self):
        """Build context from current file and Laravel project"""
        context = {
            'file': None,
            'selection': None,
            'laravel_model': None,
            'laravel_properties': []
        }
        
        if not self.current_view:
            return context
        
        # Get file info
        file_name = self.current_view.file_name()
        if file_name:
            context['file'] = file_name
        
        # Get selection
        selection = self.current_view.sel()
        if selection and not selection[0].empty():
            context['selection'] = self.current_view.substr(selection[0])
        
        # Get Laravel context
        analyzer = get_laravel_analyzer(self.current_view)
        if analyzer:
            # Check if in model file
            model_name = LaravelContextDetector.get_current_model_name(self.current_view)
            if model_name:
                context['laravel_model'] = model_name
                context['laravel_properties'] = analyzer.get_model_properties(model_name)
            else:
                # Check if using a model
                cursor_pos = self.current_view.sel()[0].begin()
                detected_model = LaravelContextDetector.detect_model_context(self.current_view, cursor_pos)
                if detected_model:
                    context['laravel_model'] = detected_model
                    context['laravel_properties'] = analyzer.get_model_properties(detected_model)
        
        return context
    
    def _build_prompt_with_context(self, user_message, context):
        """Build prompt with context"""
        prompt_parts = []
        
        # Add context
        if context['file']:
            prompt_parts.append("Current file: {0}".format(context['file']))
        
        if context['selection']:
            prompt_parts.append("Selected code:\n```\n{0}\n```".format(context['selection']))
        
        if context['laravel_model']:
            prompt_parts.append("\nLaravel Model: {0}".format(context['laravel_model']))
            
            if context['laravel_properties']:
                props_str = ", ".join(["{0} ({1})".format(p['name'], p['type']) for p in context['laravel_properties'][:10]])
                prompt_parts.append("Model properties: {0}".format(props_str))
        
        # Add conversation history (last 5 messages)
        if len(self.chat_history) > 1:
            prompt_parts.append("\nConversation history:")
            for msg in self.chat_history[-6:-1]:  # Exclude current message
                if msg['role'] == 'user':
                    prompt_parts.append("User: {0}".format(msg['content']))
                else:
                    prompt_parts.append("Assistant: {0}...".format(msg['content'][:100]))
        
        # Add current message
        prompt_parts.append("\nUser: {0}".format(user_message))
        
        return "\n".join(prompt_parts)
    
    def _update_chat_display(self):
        """Update chat display in tab"""
        if not self.chat_view:
            return
        
        # Build content
        content = self._build_chat_content()
        
        # Update view
        self.chat_view.set_read_only(False)
        self.chat_view.run_command('select_all')
        self.chat_view.run_command('right_delete')
        self.chat_view.run_command('append', {'characters': content})
        self.chat_view.set_read_only(True)
        
        # Scroll to bottom
        self.chat_view.show(self.chat_view.size())
    
    def _build_chat_content(self):
        """Build chat content for display"""
        if not self.chat_history:
            return """╔═══════════════════════════════════════╗
║         💬 AI Chat Assistant         ║
╚═══════════════════════════════════════╝

Welcome! Press Cmd+K to start chatting.

Features:
• Context-aware responses
• Laravel model detection
• Persistent history
• Streaming responses

Type your question and press Enter!
"""
        
        lines = []
        lines.append("╔═══════════════════════════════════════╗")
        lines.append("║         💬 AI Chat Assistant         ║")
        lines.append("╚═══════════════════════════════════════╝")
        lines.append("")
        
        for msg in self.chat_history:

        
            msg['role'] = content = msg['content']
            timestamp = msg.get('timestamp', '')
            
            if role == 'user':
                lines.append("┌─ 👤 You [{0}]".format(timestamp))
                lines.append("│")
                for line in content.split('\n'):
                    lines.append("│  {0}".format(line))
                lines.append("└─")
                lines.append("")
            else:
                lines.append("┌─ 🤖 AI [{0}]".format(timestamp))
                lines.append("│")
                for line in content.split('\n'):
                    lines.append("│  {0}".format(line))
                lines.append("└─")
                lines.append("")
        
        lines.append("───────────────────────────────────────")
        lines.append("Press Cmd+K to continue chatting")
        lines.append("Press Cmd+Shift+K to clear history")
        lines.append("")
        
        return "\n".join(lines)
    
    def _create_input_html(self):
        """Create HTML for input prompt (not used anymore)"""
        return """
        <body id="ollama-chat">
            <style>
                body {
                    font-family: system-ui;
                    padding: 10px;
                    background-color: var(--background);
                    border: 1px solid var(--bluish);
                    border-radius: 4px;
                    margin: 5px 0;
                }
                .prompt {
                    color: var(--foreground);
                    font-size: 0.9rem;
                }
            </style>
            <div class="prompt">💬 Type your message in the input panel below...</div>
        </body>
        """
    
    def _create_chat_html(self):
        """Create HTML for chat display"""
        messages_html = []
        
        for msg in self.chat_history[-10:]:  # Show last 10 messages
            role = msg['role']
            content = html.escape(msg['content'])
            
            if role == 'user':
                messages_html.append("""
                <div class="message user-message">
                    <div class="message-header">👤 You</div>
                    <div class="message-content">{content}</div>
                </div>
                """)
            else:
                messages_html.append("""
                <div class="message ai-message">
                    <div class="message-header">🤖 AI</div>
                    <div class="message-content">{content}</div>
                </div>
                """)
        
        return """
        <body id="ollama-chat">
            <style>
                body {{
                    font-family: system-ui;
                    padding: 10px;
                    background-color: var(--background);
                    border: 1px solid var(--bluish);
                    border-radius: 4px;
                    margin: 5px 0;
                    max-width: 600px;
                }}
                .message {{
                    margin: 10px 0;
                    padding: 8px;
                    border-radius: 4px;
                }}
                .user-message {{
                    background-color: color(var(--bluish) alpha(0.1));
                    border-left: 3px solid var(--bluish);
                }}
                .ai-message {{
                    background-color: color(var(--greenish) alpha(0.1));
                    border-left: 3px solid var(--greenish);
                }}
                .message-header {{
                    font-weight: bold;
                    font-size: 0.85rem;
                    margin-bottom: 4px;
                    color: var(--foreground);
                }}
                .message-content {{
                    color: var(--foreground);
                    font-size: 0.9rem;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }}
                .actions {{
                    margin-top: 10px;
                    padding-top: 10px;
                    border-top: 1px solid var(--bluish);
                }}
                .action-link {{
                    color: var(--bluish);
                    text-decoration: none;
                    margin-right: 15px;
                    font-size: 0.85rem;
                }}
                .action-link:hover {{
                    text-decoration: underline;
                }}
            </style>
            <div class="chat-messages">
                {''.join(messages_html)}
            </div>
            <div class="actions">
                <a href="continue" class="action-link">↩️ Continue</a>
                <a href="clear" class="action-link">🗑️ Clear</a>
                <a href="close" class="action-link">❌ Close</a>
            </div>
        </body>
        """
    
    def clear_history(self):
        """Clear chat history"""
        self.chat_history = []
        self._save_history()
        self._update_chat_display()
        sublime.status_message("Chat history cleared")
    
    def _handle_navigation(self, href):
        """Handle link clicks in phantom (not used anymore)"""
        if href == 'continue':
            self.show_input_prompt()
        elif href == 'clear':
            self.clear_history()
        elif href == 'close':
            self.close_chat()
    
    def on_cancel(self):
        """Handle cancel"""
        # Don't close chat, just wait
        pass
    
    def close_chat(self):
        """Close chat tab"""
        if self.chat_view:
            window = self.chat_view.window()
            if window:
                window.focus_view(self.chat_view)
                window.run_command('close_file')
        
        self.is_active = False
        self.chat_view = None


# Global chat manager
_chat_manager = InlineChatManager()


class LaravelWorkshopInlineChatCommand(sublime_plugin.TextCommand):
    """Start inline chat (Cursor/Windsurf-like)"""
    
    def run(self, edit):
        global _chat_manager
        
        if _chat_manager.is_active:
            # Continue existing chat
            _chat_manager.show_input_prompt()
        else:
            # Start new chat
            _chat_manager.start_chat(self.view)


class LaravelWorkshopCloseChatCommand(sublime_plugin.TextCommand):
    """Close inline chat"""
    
    def run(self, edit):
        global _chat_manager
        _chat_manager.close_chat()


class LaravelWorkshopClearChatHistoryCommand(sublime_plugin.TextCommand):
    """Clear chat history"""
    
    def run(self, edit):
        global _chat_manager
        _chat_manager.clear_history()
