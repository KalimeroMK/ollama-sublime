"""
Laravel Workshop AI - AI-powered code assistance for Sublime Text
Powered by local Ollama LLMs for privacy and performance.

This package provides intelligent code analysis, refactoring suggestions,
multi-file feature generation, and architectural insights for Laravel PHP development.

NEW: AI Agent Framework - Autonomous code generation with multi-agent workflows!
NEW: Laravel Intelligence - Smart autocomplete with model properties and IDE helper!
NEW: Inline Chat - Cursor/Windsurf-like chat interface!
"""

__version__ = "2.1.0"
__author__ = "KalimeroMK"
__package_name__ = "Laravel Workshop AI"

# Import agent commands to register them
# Temporarily disabled due to agent_framework syntax errors
# from .agent_commands import (
#     OllamaAgentGenerateFeatureCommand,
#     OllamaAgentDebugCommand,
#     OllamaAgentRefactorCommand,
#     OllamaAgentCustomTaskCommand,
#     OllamaAgentChatCommand
# )

# Import Laravel intelligence commands
from .inline_chat import (
    LaravelWorkshopInlineChatCommand,
    LaravelWorkshopCloseChatCommand,
    LaravelWorkshopClearChatHistoryCommand
)

# Temporarily disabled due to laravel_autocomplete syntax errors
# from .laravel_autocomplete import (
#     OllamaLaravelAutocompleteCommand,
#     OllamaShowModelInfoCommand,
#     OllamaGenerateIdeHelperCommand
# )

# Import basic working commands
from .laravel_workshop_commands import (
    LaravelWorkshopPhpCompletionCommand,
    LaravelWorkshopCreateFileCommand,
    LaravelWorkshopCacheManagerCommand,
    LaravelWorkshopEditSettingsCommand,
    LaravelWorkshopAiPromptCommand,
    LaravelWorkshopAiSmartCompletionCommand,
    LaravelWorkshopAiGenerateFilesCommand,
    LaravelWorkshopCodeSmellFinderCommand,
    LaravelWorkshopOptimizeProjectCommand
)

# Event listener for settings auto-save
import sublime
import sublime_plugin

class LaravelWorkshopSettingsSaveListener(sublime_plugin.EventListener):
    """Auto-save settings view content to actual settings file"""
    
    def on_pre_save(self, view):
        settings_file_path = view.settings().get('settings_file_path')
        if settings_file_path:
            # Prevent saving the scratch view itself, redirect to actual file
            # Get content from view
            content = view.substr(sublime.Region(0, view.size()))
            
            # Save to actual file
            try:
                import os
                os.makedirs(os.path.dirname(settings_file_path), exist_ok=True)
                with open(settings_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                sublime.status_message("✅ Settings saved to: " + os.path.basename(settings_file_path))
                
                # Clear the modified flag since we saved to the actual file
                view.set_scratch(True)  # Mark as scratch to prevent normal save dialog
                sublime.set_timeout(lambda: view.set_scratch(False), 100)
            except Exception as e:
                sublime.error_message("Error saving settings: " + str(e))
