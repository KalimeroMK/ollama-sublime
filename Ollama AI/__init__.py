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
from .agent_commands import (
    OllamaAgentGenerateFeatureCommand,
    OllamaAgentDebugCommand,
    OllamaAgentRefactorCommand,
    OllamaAgentCustomTaskCommand,
    OllamaAgentChatCommand
)

# Import Laravel intelligence commands
from .inline_chat import (
    OllamaInlineChatCommand,
    OllamaCloseChatCommand,
    OllamaClearChatHistoryCommand
)

from .laravel_autocomplete import (
    OllamaLaravelAutocompleteCommand,
    OllamaShowModelInfoCommand,
    OllamaGenerateIdeHelperCommand
)
