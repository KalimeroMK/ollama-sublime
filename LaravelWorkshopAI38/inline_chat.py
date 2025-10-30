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
# Try to import Laravel intelligence helpers; fall back safely if unavailable
try:
    from .laravel_intelligence import get_laravel_analyzer, LaravelContextDetector  # type: ignore
    _HAS_LARAVEL_INTEL = True
except Exception:
    get_laravel_analyzer = None  # type: ignore
    LaravelContextDetector = None  # type: ignore
    _HAS_LARAVEL_INTEL = False

# Import agent framework for Cursor-like analysis
try:
    from .agent_framework import create_agent_workflow, AgentRole, Agent, Task, AgentCrew
    from .agent_tools import create_default_tools
    _HAS_AGENT_FRAMEWORK = True
except Exception:
    _HAS_AGENT_FRAMEWORK = False
    create_agent_workflow = None
    AgentRole = None
    Agent = None
    Task = None
    AgentCrew = None
    create_default_tools = None

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
        self.input_start = None  # type: Optional[int]
        
        # Settings
        self.settings = sublime.load_settings("LaravelWorkshopAI.sublime-settings")
        self.auto_place_right = self.settings.get("inline_chat_auto_place_right", True)
        # Disable inline input mode - use input panel instead (more reliable)
        self.inline_input_mode = False  # Always use input panel
        
        def _on_settings_change():
            self.auto_place_right = self.settings.get("inline_chat_auto_place_right", True)
            self.inline_input_mode = self.settings.get("inline_chat_inline_input", True)
        self.settings.add_on_change("inline_chat_settings", _on_settings_change)
        
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
        """Create or show chat tab in sidebar (Cursor-like)"""
        window = self.current_view.window()
        if not window:
            return
        
        # Check if chat tab already exists
        for view in window.views():
            if view.settings().get('laravel_workshop_chat_tab'):
                self.chat_view = view
                # Ensure placement if requested
                if self.auto_place_right:
                    self._ensure_right_group(window)
                    window.set_view_index(self.chat_view, 1, 0)
                window.focus_view(view)
                self._update_chat_display()
                # Show status message with instructions
                sublime.status_message("💬 AI Chat активен! Користи Cmd+K за нова порака. За sidebar: View → Layout → Columns: 2")
                return
        
        # Create new chat tab
        self.chat_view = window.new_file()
        self.chat_view.set_name("💬 AI Chat")
        self.chat_view.settings().set('laravel_workshop_chat_tab', True)
        self.chat_view.settings().set('word_wrap', True)
        self.chat_view.set_scratch(True)
        self.chat_view.set_read_only(False)  # Make editable to write content
        self.chat_view.set_syntax_file("Packages/Text/Plain text.tmLanguage")
        
        # Auto place to right group if enabled
        if self.auto_place_right:
            self._ensure_right_group(window)
            window.set_view_index(self.chat_view, 1, 0)
        
        # Focus on chat tab so it's visible
        window.focus_view(self.chat_view)
        
        # Initial content
        self._update_chat_display()
        
        # Show instructions
        sublime.status_message("💬 AI Chat активен! Користи Cmd+K за нова порака. За sidebar: View → Layout → Columns: 2")
        
    def _ensure_right_group(self, window):
        """Ensure a 2-column layout and that group 1 (right) exists"""
        try:
            if window.num_groups() < 2:
                # Set 2-column layout explicitly
                window.set_layout({
                    'cols': [0.0, 0.5, 1.0],
                    'rows': [0.0, 1.0],
                    'cells': [[0, 0, 1, 1], [1, 0, 2, 1]]
                })
        except Exception:
            # Best-effort fallback
            try:
                window.run_command('new_pane')
            except Exception:
                pass
    
    def show_input_prompt(self):
        """Show input prompt to user (uses input panel)"""
        print("show_input_prompt called")
        
        # Get window from any available view
        window = None
        if self.current_view and self.current_view.window():
            window = self.current_view.window()
        elif self.chat_view and self.chat_view.window():
            window = self.chat_view.window()
        else:
            try:
                window = sublime.active_window()
            except:
                pass
        
        if not window:
            print("show_input_prompt: No window available")
            sublime.status_message("⚠️ No window available. Please open a file first.")
            return
        
        # Always use input panel (more reliable than inline input)
        try:
            print("Opening input panel...")
            panel = window.show_input_panel(
                "💬 Chat with AI (press Enter to send):",
                "",
                self.on_user_input,
                None,
                self.on_cancel
            )
            print("Input panel opened successfully")
            sublime.status_message("💬 Type your message and press Enter")
        except Exception as e:
            print("Error showing input panel: {0}".format(str(e)))
            import traceback
            traceback.print_exc()
            sublime.status_message("⚠️ Error opening input panel. Try Cmd+K again or use Command Palette → Inline Chat")
    
    def on_user_input(self, user_message):
        """Handle user input"""
        if not user_message.strip():
            return
        
        # Reset inline input marker if any
        self.input_start = None
        
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
        """Get response from AI with streaming - uses agent workers for Cursor-like analysis"""
        api_client = create_api_client_from_settings()
        
        # Get context
        context = self._build_context()
        
        # Show loading
        self.chat_history.append({
            'role': 'assistant',
            'content': '',
            'timestamp': self._get_timestamp()
        })
        self._update_chat_display()
        
        def fetch():
            try:
                # Debug: Print context info
                print("Context debug:")
                print("  - project_root: {0}".format(context.get('project_root')))
                print("  - is_laravel: {0}".format(context.get('is_laravel')))
                print("  - has_agent_framework: {0}".format(_HAS_AGENT_FRAMEWORK))
                
                # Warn if project not detected
                if not context.get('project_root'):
                    if self.chat_history:
                        self.chat_history[-1]['content'] = "⚠️ Warning: Project not detected. Make sure you have a project folder open in Sublime Text (File → Open Folder...). Analyzing without project context..."
                        sublime.set_timeout(lambda: self._update_chat_display(), 0)
                
                # For now, use regular response directly - agents seem to hang
                # We can re-enable agents later when they're more stable
                use_agents = False  # Temporarily disabled due to hanging issues
                
                if use_agents and _HAS_AGENT_FRAMEWORK and context.get('is_laravel') and context.get('project_root'):
                    print("Using agent framework for analysis")
                    # Use agent but with very short timeout (30s) then fallback
                    try:
                        self._get_agent_response_with_timeout(user_message, context, api_client, timeout=30)
                    except:
                        print("Agent failed, using regular response")
                        self._get_regular_response(user_message, context, api_client)
                else:
                    print("Using regular response with context")
                    # Always use regular response - it's more reliable
                    self._get_regular_response(user_message, context, api_client)
                
            except Exception as e:
                print("Error in fetch: {0}".format(str(e)))
                self.chat_history[-1]['content'] = "❌ Error: {0}".format(str(e))
                sublime.set_timeout(lambda: self._update_chat_display(), 0)
                self._save_history()
        
        sublime.set_timeout_async(fetch, 0)
    
    def _get_agent_response(self, user_message, context, api_client):
        """Use agent workers to analyze project deeply (Cursor-like)"""
        # Show loading indicator
        sublime.status_message("🔍 Analyzing project with AI agent...")
        
        try:
            # Determine which agent role to use based on query
            user_lower = user_message.lower()
            
            if any(kw in user_lower for kw in ['n+1', 'query', 'optimize', 'performance', 'slow']):
                agent_role = AgentRole.DEBUGGER  # Use debugger for N+1 and performance issues
            elif any(kw in user_lower for kw in ['refactor', 'improve', 'clean', 'smell']):
                agent_role = AgentRole.REFACTORER
            elif any(kw in user_lower for kw in ['bug', 'error', 'fix', 'debug']):
                agent_role = AgentRole.DEBUGGER
            elif any(kw in user_lower for kw in ['create', 'generate', 'new', 'build']):
                agent_role = AgentRole.CODER
            elif any(kw in user_lower for kw in ['review', 'check', 'verify', 'test']):
                agent_role = AgentRole.REVIEWER
            else:
                agent_role = AgentRole.CODER  # Default to coder for general questions
            
            # Update only status bar to avoid resetting prompt input
            sublime.status_message("🔍 Starting {0} agent analysis...".format(agent_role.value))
            
            # Update chat history message but don't refresh display yet to preserve prompt
            if self.chat_history:
                self.chat_history[-1]['content'] = "🔍 Analyzing project with {0} agent...".format(agent_role.value)
            
            # Create agent with tools
            tools = create_default_tools()
            agent = Agent(
                role=agent_role,
                goal="Provide specific, actionable analysis based on the actual project code",
                backstory="You are an expert {0} who analyzes code line-by-line, like Cursor IDE. You examine actual files, relationships, and provide precise fixes.".format(agent_role.value),
                api_client=api_client,
                tools=tools,
                project_root=context.get('project_root')
            )
            
            # Build comprehensive task with all context
            task_description = self._build_agent_task_description(user_message, context)
            
            # Create task
            task = Task(
                description=task_description,
                agent_role=agent_role,
                context=context
            )
            
            sublime.status_message("🔄 Agent analyzing project...")
            
            # Execute agent task with timeout handling
            print("Executing agent task...")
            crew = AgentCrew(agents=[agent], tasks=[task])
            
            # Try to execute with timeout awareness
            import threading
            result_container = {'result': None, 'exception': None, 'done': False}
            
            def execute_agent():
                try:
                    print("Agent crew.kickoff() starting...")
                    result_container['result'] = crew.kickoff()
                    result_container['done'] = True
                    print("Agent crew.kickoff() completed")
                except Exception as e:
                    print("Agent execution error: {0}".format(str(e)))
                    result_container['exception'] = e
                    result_container['done'] = True
            
            # Run in thread to avoid blocking
            thread = threading.Thread(target=execute_agent)
            thread.daemon = True
            thread.start()
            
            # Show progress while waiting (update every 5 seconds)
            # Use status bar only to avoid resetting prompt input
            elapsed = 0
            while not result_container['done'] and elapsed < 60:
                thread.join(timeout=5.0)
                elapsed += 5
                if not result_container['done']:
                    # Only update status bar, don't touch chat view to preserve prompt input
                    sublime.status_message("🔄 Agent analyzing project ({0}s)...".format(elapsed))
            
            # Final check
            if not result_container['done']:
                thread.join(timeout=1.0)  # One more second
            
            if not result_container['done']:
                print("Agent timeout - falling back to regular response")
                raise TimeoutError("Agent execution timed out")
            
            if result_container['exception']:
                raise result_container['exception']
            
            result = result_container['result']
            
            if not result:
                print("Agent returned no result - falling back")
                raise ValueError("Agent returned no result")
            
            # Extract response from agent result
            agent_response = ""
            for task_desc, task_result in result.get("results", {}).items():
                if task_result:
                    agent_response += str(task_result)
            
            # If response is empty, fall back to regular method
            if not agent_response.strip():
                print("Agent response empty - falling back to regular response")
                sublime.status_message("⚠️ Agent response empty, using regular analysis...")
                self._get_regular_response(user_message, context, api_client)
                return
            
            # Update chat history with agent response
            if self.chat_history:
                self.chat_history[-1]['content'] = agent_response
                self._update_chat_display()
            
            sublime.status_message("✅ Agent analysis complete!")
            
            # Save history
            self._save_history()
            
            # Ask for next input
            sublime.set_timeout(lambda: self.show_input_prompt(), 100)
            
        except TimeoutError:
            print("Agent timeout - using regular response")
            sublime.status_message("⏱️ Agent timeout, using direct analysis...")
            if self.chat_history:
                self.chat_history[-1]['content'] = "⏱️ Agent analysis timed out. Using direct analysis instead..."
                self._update_chat_display()
            self._get_regular_response(user_message, context, api_client)
        except Exception as e:
            # Fallback to regular response if agent fails
            print("Agent response failed: {0}".format(str(e)))
            import traceback
            traceback.print_exc()
            sublime.status_message("⚠️ Agent failed, using direct analysis...")
            if self.chat_history:
                self.chat_history[-1]['content'] = "⚠️ Agent encountered an error. Falling back to direct analysis..."
                self._update_chat_display()
            self._get_regular_response(user_message, context, api_client)
    
    def _build_agent_task_description(self, user_message, context):
        """Build comprehensive task description for agent with full project context"""
        parts = []
        
        parts.append("TASK: {0}".format(user_message))
        parts.append("")
        
        # Add project context
        if context.get('project_root'):
            parts.append("PROJECT ROOT: {0}".format(context['project_root']))
            parts.append("This is a Laravel project.")
        
        # Add file context
        if context.get('file'):
            parts.append("")
            parts.append("CURRENT FILE: {0}".format(context['file']))
            if context.get('file_content'):
                parts.append("")
                parts.append("CURRENT FILE CONTENT:")
                parts.append("```php")
                parts.append(context['file_content'][:2000])  # First 2000 chars
                parts.append("```")
        
        # Add selection
        if context.get('selection'):
            parts.append("")
            parts.append("SELECTED CODE:")
            parts.append("```php")
            parts.append(context['selection'])
            parts.append("```")
        
        # Add Laravel model info
        if context.get('laravel_model'):
            parts.append("")
            parts.append("LARAVEL MODEL: {0}".format(context['laravel_model']))
            if context.get('laravel_properties'):
                props = ", ".join(["{0} ({1})".format(p['name'], p['type']) for p in context['laravel_properties'][:10]])
                parts.append("Model properties: {0}".format(props))
        
        # Add instructions for deep analysis
        parts.append("")
        parts.append("INSTRUCTIONS:")
        parts.append("- Analyze the project structure line-by-line")
        parts.append("- Examine relationships between files")
        parts.append("- Look for specific issues (N+1 queries, code smells, etc.)")
        parts.append("- Provide EXACT fixes with code examples")
        parts.append("- Reference specific files and line numbers when possible")
        parts.append("- Be precise and actionable, like Cursor IDE")
        
        # For N+1 specifically
        if 'n+1' in user_message.lower():
            parts.append("")
            parts.append("N+1 ANALYSIS REQUIRED:")
            parts.append("- Scan controllers for foreach loops with relationships")
            parts.append("- Identify exact lines causing N+1 problems")
            parts.append("- Show before/after code with with() or load()")
            parts.append("- Check model relationships")
            
            # Add relevant controllers for analysis
            if context.get('project_root'):
                controllers = self._find_relevant_controllers(context['project_root'])
                if controllers:
                    parts.append("")
                    parts.append("RELEVANT CONTROLLERS TO ANALYZE:")
                    for ctrl_path, ctrl_content in controllers[:5]:
                        rel_path = os.path.relpath(ctrl_path, context['project_root'])
                        parts.append("")
                        parts.append("FILE: {0}".format(rel_path))
                        parts.append("```php")
                        parts.append(ctrl_content[:1500])  # First 1500 chars per controller
                        parts.append("```")
        
        # Scan project files for general analysis (Cursor-like line-by-line)
        if context.get('project_root') and context.get('is_laravel'):
            # Find relevant PHP files based on query
            relevant_files = self._find_relevant_project_files(user_message, context['project_root'])
            if relevant_files:
                parts.append("")
                parts.append("PROJECT FILES TO ANALYZE:")
                parts.append("Examine these files line-by-line for issues:")
                for file_path, file_content in relevant_files[:3]:  # Limit to 3 files
                    rel_path = os.path.relpath(file_path, context['project_root'])
                    parts.append("")
                    parts.append("FILE: {0}".format(rel_path))
                    parts.append("```php")
                    parts.append(file_content[:1000])  # First 1000 chars per file
                    parts.append("```")
        
        return "\n".join(parts)
    
    def _find_relevant_project_files(self, query, project_root):
        """Find relevant project files based on query keywords"""
        query_lower = query.lower()
        relevant_files = []
        
        # Determine file types to scan based on query
        file_types = []
        if any(kw in query_lower for kw in ['controller', 'route', 'api']):
            file_types.append('Controller.php')
        if any(kw in query_lower for kw in ['model', 'entity', 'database']):
            file_types.append('Model.php')
        if any(kw in query_lower for kw in ['service', 'repository']):
            file_types.extend(['Service.php', 'Repository.php'])
        
        # If no specific type, scan common Laravel files
        if not file_types:
            file_types = ['Controller.php', 'Model.php']
        
        # Scan for files
        scan_dirs = [
            os.path.join(project_root, 'app', 'Http', 'Controllers'),
            os.path.join(project_root, 'app', 'Models'),
            os.path.join(project_root, 'app', 'Services'),
            os.path.join(project_root, 'app'),
        ]
        
        for scan_dir in scan_dirs:
            if not os.path.exists(scan_dir):
                continue
            
            try:
                for root, dirs, files in os.walk(scan_dir):
                    # Skip vendor, node_modules, etc.
                    if any(excluded in root for excluded in ['vendor', 'node_modules', '.git', 'tests']):
                        continue
                    
                    for file in files:
                        if any(file.endswith(ft) for ft in file_types):
                            file_path = os.path.join(root, file)
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    # Only include files with relevant content
                                    if len(content) > 50:  # Skip empty/tiny files
                                        relevant_files.append((file_path, content))
                            except:
                                continue
                    
                    # Limit total files
                    if len(relevant_files) >= 10:
                        break
                    
            except Exception:
                continue
        
        return relevant_files[:10]  # Return max 10 files
    
    def _get_regular_response(self, user_message, context, api_client):
        """Regular prompt-based response with streaming"""
        print("_get_regular_response called with prompt length: {0}".format(len(user_message)))
        
        # Build prompt with context
        full_prompt = self._build_prompt_with_context(user_message, context)
        print("Built prompt, length: {0}".format(len(full_prompt)))
        
        # Ensure assistant placeholder exists
        if not self.chat_history or self.chat_history[-1]['role'] != 'assistant':
            self.chat_history.append({'role': 'assistant', 'content': '', 'timestamp': self._get_timestamp()})
        
        # Show immediate feedback
        if self.chat_history:
            self.chat_history[-1]['content'] = "⏳ Connecting to AI model..."
            sublime.set_timeout(lambda: self._update_chat_display(), 0)
        
        received_any = {'flag': False}
        error_occurred = {'flag': False}
        
        # Streaming callback
        def content_callback(chunk):
            if self.chat_history:
                if not received_any['flag']:
                    # Clear spinner on first chunk
                    self.chat_history[-1]['content'] = ''
                received_any['flag'] = True
                self.chat_history[-1]['content'] += chunk
                sublime.set_timeout(lambda: self._update_chat_display(), 0)
        
        # Run streaming request with timeout protection
        def run_stream():
            try:
                print("Making streaming request to API...")
                api_client.make_streaming_request(full_prompt, content_callback)
                print("Streaming request completed")
            except Exception as e:
                print("Streaming error: {0}".format(str(e)))
                import traceback
                traceback.print_exc()
                error_occurred['flag'] = True
                # Show error in chat
                if self.chat_history:
                    error_msg = "❌ Error: {0}\n\n".format(str(e))
                    error_msg += "Please check:\n"
                    error_msg += "1. Ollama is running: `ollama serve`\n"
                    error_msg += "2. Model is available: `ollama list`\n"
                    error_msg += "3. Settings are correct in Laravel Workshop AI settings"
                    self.chat_history[-1]['content'] = error_msg
                    sublime.set_timeout(lambda: self._update_chat_display(), 0)
            finally:
                # Save history
                self._save_history()
                # Ask for next input after a short delay
                def open_next_input():
                    # Update display first
                    if self.chat_history:
                        self._update_chat_display()
                    # Show status message
                    sublime.status_message("💬 Response complete! Press Cmd+K to continue chatting...")
                    # Then open input panel
                    sublime.set_timeout(lambda: self.show_input_prompt(), 500)
                
                sublime.set_timeout(open_next_input, 300)  # 300ms delay to ensure response is saved
        
        # Start streaming async
        sublime.set_timeout_async(run_stream, 0)
        
        # Watchdog to handle no-stream cases (reduce to 20 seconds)
        def watchdog():
            if not received_any['flag'] and not error_occurred['flag']:
                if self.chat_history and self.chat_history[-1]['role'] == 'assistant':
                    # No chunks after 20s -> show helpful message
                    self.chat_history[-1]['content'] = (
                        "⚠️ No response after 20 seconds.\n\n"
                        "This usually means:\n"
                        "1. Ollama server is not running - run `ollama serve`\n"
                        "2. Model is not available - check `ollama list`\n"
                        "3. Connection timeout - check network/firewall\n"
                        "4. Model is slow - try a smaller model\n\n"
                        "Check console (View → Show Console) for detailed errors."
                    )
                    self._update_chat_display()
                    self._save_history()
                    # Open input panel so user can continue
                    sublime.set_timeout(lambda: self.show_input_prompt(), 200)
        
        sublime.set_timeout(watchdog, 20000)  # 20 seconds timeout
        
    def _show_inline_input(self):
        """Ensure inline input prompt is visible and focus caret for typing"""
        if not self.chat_view:
            return
        self._update_chat_display()
        try:
            window = self.chat_view.window()
            if window:
                window.focus_view(self.chat_view)
        except Exception:
            pass
        # Caret at end so user can type
        try:
            end = self.chat_view.size()
            self.chat_view.sel().clear()
            self.chat_view.sel().add(sublime.Region(end, end))
        except Exception:
            pass
        
    def _build_context(self):
        """Build context from current file and Laravel project"""
        context = {
            'file': None,
            'file_content': None,
            'selection': None,
            'laravel_model': None,
            'laravel_properties': [],
            'project_root': None,
            'is_laravel': False
        }
        
        # Get window - try multiple sources
        window = None
        active_view = None
        
        if self.current_view:
            window = self.current_view.window()
            active_view = self.current_view
        
        # If no window from current_view, try to get from chat_view or active view
        if not window and self.chat_view:
            window = self.chat_view.window()
            if window:
                active_view = window.active_view()
        
        # If still no window, try to get from any view
        if not window:
            try:
                window = sublime.active_window()
                if window:
                    active_view = window.active_view()
            except:
                pass
        
        # Get project root from window folders
        if window and window.folders():
            context['project_root'] = window.folders()[0]
            # Check if Laravel project
            if context['project_root'] and os.path.exists(os.path.join(context['project_root'], 'artisan')):
                context['is_laravel'] = True
                print("✅ Detected Laravel project: {0}".format(context['project_root']))
            elif context['project_root']:
                print("⚠️ Project root found but not Laravel: {0}".format(context['project_root']))
        else:
            print("⚠️ No project root found - window folders: {0}".format(window.folders() if window else "No window"))
        
        # Get file info from active view (not chat view)
        if active_view and active_view != self.chat_view:
            file_name = active_view.file_name()
            if file_name:
                context['file'] = file_name
                # Get file content for better context (first 2000 chars)
                try:
                    full_content = active_view.substr(sublime.Region(0, min(2000, active_view.size())))
                    context['file_content'] = full_content
                except:
                    pass
            
            # Get selection
            selection = active_view.sel()
            if selection and not selection[0].empty():
                context['selection'] = active_view.substr(selection[0])
        
        # Get Laravel context if available (use active_view, not chat view)
        if active_view and active_view != self.chat_view and _HAS_LARAVEL_INTEL and get_laravel_analyzer and LaravelContextDetector:
            try:
                analyzer = get_laravel_analyzer(active_view)
            except Exception:
                analyzer = None
            if analyzer:
                # Check if in model file
                try:
                    model_name = LaravelContextDetector.get_current_model_name(active_view)
                except Exception:
                    model_name = None
                if model_name:
                    context['laravel_model'] = model_name
                    try:
                        context['laravel_properties'] = analyzer.get_model_properties(model_name)
                    except Exception:
                        context['laravel_properties'] = []
                else:
                    # Check if using a model
                    try:
                        cursor_pos = active_view.sel()[0].begin() if active_view.sel() else 0
                        detected_model = LaravelContextDetector.detect_model_context(active_view, cursor_pos)
                    except Exception:
                        detected_model = None
                    if detected_model:
                        context['laravel_model'] = detected_model
                        try:
                            context['laravel_properties'] = analyzer.get_model_properties(detected_model)
                        except Exception:
                            context['laravel_properties'] = []
        
        return context
    
    def _build_prompt_with_context(self, user_message, context):
        """Build prompt with context - optimized for Laravel project analysis"""
        prompt_parts = []
        
        # System instructions for Laravel analysis
        if context.get('is_laravel'):
            prompt_parts.append("""You are an expert Laravel developer analyzing THIS OPEN PROJECT. The user has a Laravel project open in Sublime Text.

CRITICAL: You HAVE access to the project structure and files. DO NOT ask for project details - USE the information provided below.

Provide SPECIFIC, ACTIONABLE answers based on the ACTUAL project code:

When analyzing N+1 problems:
- DO analyze the controllers and models provided below
- DO identify specific foreach loops with relationship queries
- DO provide exact code fixes with with(), load(), or eager loading
- DO show before/after examples
- DO NOT say you don't have access to the project

When analyzing code:
- Reference specific files, methods, and line numbers
- Use the project structure information provided
- Be precise and actionable""")
        
        # Emphasize project is open
        if context.get('project_root'):
            prompt_parts.append("\n🔴 IMPORTANT: A Laravel project is currently open in Sublime Text!")
            prompt_parts.append("Project Root: {0}".format(context['project_root']))
            prompt_parts.append("You MUST analyze the actual project files. DO NOT ask the user to provide project details.")
        
        # Add project info
        if context.get('project_root'):
            prompt_parts.append("\n📍 Project Root: {0}".format(context['project_root']))
            if context.get('is_laravel'):
                prompt_parts.append("✅ Laravel Project Detected")
        
        # Add file context
        if context.get('file'):
            prompt_parts.append("\n📄 Current File: {0}".format(context['file']))
            
            # Add relevant file content for better analysis
            if context.get('file_content'):
                # Extract relevant parts (methods, classes)
                file_content = context['file_content']
                # If it's a Controller, Model, or similar, include more context
                if 'Controller' in context['file'] or 'Model' in context['file'] or context.get('selection'):
                    prompt_parts.append("\nFile Content:\n```php\n{0}\n```".format(file_content[:1500]))
        
        # Add selection if present
        if context.get('selection'):
            prompt_parts.append("\n🔍 Selected Code:\n```php\n{0}\n```".format(context['selection']))
        
        # Add Laravel model info
        if context.get('laravel_model'):
            prompt_parts.append("\n📦 Laravel Model: {0}".format(context['laravel_model']))
            
            if context.get('laravel_properties'):
                props_str = ", ".join(["{0} ({1})".format(p['name'], p['type']) for p in context['laravel_properties'][:10]])
                prompt_parts.append("Model properties: {0}".format(props_str))
        
        # Check for N+1 related queries and add relevant controller/model code
        user_lower = user_message.lower()
        if any(keyword in user_lower for keyword in ['n+1', 'n plus 1', 'eager loading', 'lazy loading', 'queries']):
            prompt_parts.append("\n⚠️ N+1 Query Analysis Requested:")
            prompt_parts.append("For N+1 problems, analyze the code above and:")
            prompt_parts.append("1. Identify loops that query relationships inside")
            prompt_parts.append("2. Show the exact problematic code")
            prompt_parts.append("3. Provide specific fix using with(), load(), or eager loading")
            prompt_parts.append("4. Show before/after code examples")
            
            # If Laravel project, try to find relevant controllers
            if context.get('is_laravel') and context.get('project_root'):
                controllers = self._find_relevant_controllers(context['project_root'])
                if controllers:
                    prompt_parts.append("\n📁 Found Controllers to analyze:")
                    for ctrl_path, ctrl_content in controllers[:3]:  # Limit to 3 for token efficiency
                        rel_path = os.path.relpath(ctrl_path, context['project_root'])
                        prompt_parts.append("\n{}:\n```php\n{}\n```".format(rel_path, ctrl_content[:800]))
        
        # Add conversation history (last 5 messages)
        if len(self.chat_history) > 1:
            prompt_parts.append("\n💬 Conversation History:")
            for msg in self.chat_history[-6:-1]:  # Exclude current message
                if msg['role'] == 'user':
                    prompt_parts.append("User: {0}".format(msg['content']))
                else:
                    prompt_parts.append("Assistant: {0}...".format(msg['content'][:150]))
        
        # Add current message
        prompt_parts.append("\n❓ User Question: {0}".format(user_message))
        prompt_parts.append("\nPlease provide a specific, actionable answer based on the code above.")
        
        return "\n".join(prompt_parts)
    
    def _update_chat_display(self):
        """Update chat display in tab, preserving inline input if enabled"""
        if not self.chat_view:
            return
        
        # Preserve current inline input if any
        existing_input = None
        if self.inline_input_mode and self.input_start is not None:
            try:
                existing_input = self.chat_view.substr(sublime.Region(self.input_start, self.chat_view.size()))
            except Exception:
                existing_input = None
        
        # Build content
        content = self._build_chat_content()
        
        # Update view with messages
        self.chat_view.set_read_only(False)
        self.chat_view.run_command('select_all')
        self.chat_view.run_command('right_delete')
        self.chat_view.run_command('append', {'characters': content})
        
        # If inline input mode, append prompt and restore input
        if self.inline_input_mode:
            prompt = "\n✏️ Prompt: "
            self.chat_view.run_command('append', {'characters': prompt})
            # Record start position for input AFTER appending prompt
            self.input_start = self.chat_view.size()
            print("Setting input_start to: {0} (after appending prompt)".format(self.input_start))
            if existing_input:
                self.chat_view.run_command('append', {'characters': existing_input})
            # Move caret to end
            self.chat_view.sel().clear()
            self.chat_view.sel().add(sublime.Region(self.chat_view.size(), self.chat_view.size()))
            # Keep editable so user can type
            self.chat_view.set_read_only(False)
        else:
            # Make read-only when not in inline input mode
            self.chat_view.set_read_only(True)
        
        # Scroll to bottom
        self.chat_view.show(self.chat_view.size())
    
    def _find_relevant_controllers(self, project_root):
        """Find Laravel controllers to analyze for N+1 problems"""
        controllers = []
        
        # Common controller locations
        controller_dirs = [
            os.path.join(project_root, 'app', 'Http', 'Controllers'),
            os.path.join(project_root, 'app', 'Controllers'),
        ]
        
        for controller_dir in controller_dirs:
            if not os.path.exists(controller_dir):
                continue
            
            try:
                for root, dirs, files in os.walk(controller_dir):
                    # Skip vendor, node_modules, etc.
                    if 'vendor' in root or '.git' in root:
                        continue
                    
                    for file in files:
                        if file.endswith('Controller.php'):
                            file_path = os.path.join(root, file)
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    # Only include controllers that have database queries or relationships
                                    if any(keyword in content for keyword in ['::where', '::find', '->get', '->first', '->load', '::with', 'foreach']):
                                        controllers.append((file_path, content))
                            except:
                                continue
                    
                    # Limit total controllers
                    if len(controllers) >= 5:
                        break
                    
            except Exception:
                continue
        
        return controllers[:5]  # Return max 5 controllers
    
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

💡 To use sidebar (like Cursor):
  View → Layout → Columns: 2

Type your question and press Enter!
"""
        
        lines = []
        lines.append("╔═══════════════════════════════════════╗")
        lines.append("║         💬 AI Chat Assistant         ║")
        lines.append("╚═══════════════════════════════════════╝")
        lines.append("")
        
        for msg in self.chat_history:
            role = msg['role']
            content = msg['content']
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
        
        # Add continuation message if last message was from assistant
        if self.chat_history and self.chat_history[-1]['role'] == 'assistant':
            lines.append("")
            lines.append("💡 Press Cmd+K to continue chatting...")
            lines.append("")
        
        lines.append("───────────────────────────────────────")
        lines.append("💬 To continue the conversation:")
        lines.append("   Press Cmd+K to open input panel")
        lines.append("   Or: Command Palette → 'Inline Chat'")
        lines.append("")
        lines.append("🗑️  Press Cmd+Shift+K to clear history")
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


class LaravelWorkshopInlineChatCommand(sublime_plugin.WindowCommand):
    """Start inline chat (Cursor/Windsurf-like)"""
    
    def run(self):
        global _chat_manager
        
        if _chat_manager.is_active:
            # Continue existing chat - open input panel
            _chat_manager.show_input_prompt()
        else:
            # Start new chat - get active view or any view
            view = self.window.active_view()
            if not view:
                # Try to get any view from window
                views = self.window.views()
                if views:
                    view = views[0]
                else:
                    sublime.status_message("⚠️ Please open a file first")
                    return
            
            _chat_manager.start_chat(view)


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


class LaravelWorkshopSubmitInlineChatCommand(sublime_plugin.TextCommand):
    """Submit inline input from the chat view"""

    def run(self, edit):
        global _chat_manager
        # Ensure we're in the chat view
        if not _chat_manager.chat_view or self.view.id() != _chat_manager.chat_view.id():
            sublime.status_message("Not in AI Chat view")
            return
        
        # Retrieve input text from the stored start position
        if _chat_manager.input_start is None:
            # Fallback: try to find the last prompt marker
            full_text = self.view.substr(sublime.Region(0, self.view.size()))
            marker = "\n✏️ Prompt: "
            idx = full_text.rfind(marker)
            if idx != -1:
                _chat_manager.input_start = idx + len(marker)
                print("Submit: Found prompt marker at position: {0}".format(_chat_manager.input_start))
        
        if _chat_manager.input_start is None:
            # Last resort: try to find prompt anywhere in the file
            full_text = self.view.substr(sublime.Region(0, self.view.size()))
            marker = "✏️ Prompt: "
            idx = full_text.rfind(marker)
            if idx != -1:
                _chat_manager.input_start = idx + len(marker)
                print("Submit: Found prompt marker (no newline) at position: {0}".format(_chat_manager.input_start))
        
        if _chat_manager.input_start is None:
            sublime.status_message("⚠️ No prompt input found - try typing in the prompt field")
            print("Submit failed: input_start is None")
            return
        
        region = sublime.Region(_chat_manager.input_start, self.view.size())
        user_message = self.view.substr(region).strip()
        
        print("Submit: Extracted message: '{0}'".format(user_message[:50]))
        
        if not user_message:
            sublime.status_message("Type a prompt to send")
            return
        
        # Lock view during submission to prevent edits mid-send
        try:
            self.view.set_read_only(True)
        except Exception:
            pass
        
        # Submit and let manager handle display/streaming
        _chat_manager.on_user_input(user_message)
        
        # Focus back to code view if available
        try:
            if _chat_manager.current_view and _chat_manager.current_view.window():
                _chat_manager.current_view.window().focus_view(_chat_manager.current_view)
        except Exception:
            pass


class InlineChatKeyHandler(sublime_plugin.EventListener):
    """Handle Enter key to submit inline chat prompts"""
    
    def on_query_context(self, view, key, operator, operand, match_all):
        """Provide context for key bindings"""
        global _chat_manager
        
        # Only handle our custom context key
        if key != 'in_chat_prompt_area':
            return None
        
        # Check if this is the chat view
        if not _chat_manager.chat_view or view.id() != _chat_manager.chat_view.id():
            return False
        
        # Check if we're in inline input mode
        if not _chat_manager.inline_input_mode:
            return False
        
        # Check if caret is in the prompt input area
        if _chat_manager.input_start is None:
            return False
        
        caret_pos = view.sel()[0].begin() if view.sel() else 0
        is_in_prompt_area = caret_pos >= _chat_manager.input_start
        
        # Return boolean based on operator
        if operator == sublime.OP_EQUAL:
            return is_in_prompt_area == operand
        elif operator == sublime.OP_NOT_EQUAL:
            return is_in_prompt_area != operand
        
        return is_in_prompt_area
    
    def on_text_command(self, view, command_name, args):
        """Intercept insert commands to detect Enter key"""
        global _chat_manager
        
        # Check if this is the chat view
        if not _chat_manager.chat_view or view.id() != _chat_manager.chat_view.id():
            return None
        
        # Check if we're in inline input mode
        if not _chat_manager.inline_input_mode:
            return None
        
        # Check if this is an insert command with Enter (newline)
        if command_name == 'insert' and 'characters' in args:
            text = args['characters']
            # Detect Enter key (newline)
            if text == '\n':
                # If input_start is None, try to find it
                if _chat_manager.input_start is None:
                    full_text = view.substr(sublime.Region(0, view.size()))
                    marker = "\n✏️ Prompt: "
                    idx = full_text.rfind(marker)
                    if idx != -1:
                        _chat_manager.input_start = idx + len(marker)
                        print("Found prompt marker at position: {0}".format(_chat_manager.input_start))
                
                # Check if caret is in the prompt input area (after "✏️ Prompt: ")
                caret_pos = view.sel()[0].begin() if view.sel() else 0
                print("Enter pressed - caret_pos: {0}, input_start: {1}".format(caret_pos, _chat_manager.input_start))
                
                if _chat_manager.input_start is not None and caret_pos >= _chat_manager.input_start:
                    # We're in the input area - submit instead of inserting newline
                    print("Submitting prompt...")
                    sublime.set_timeout(lambda: view.run_command('laravel_workshop_submit_inline_chat'), 0)
                    # Return a no-op command to prevent the newline
                    return ('noop', {})
        
        return None
