import re
import html


class ResponseProcessor:
    """
    Handles processing and formatting of responses from Ollama API.
    Centralizes response cleaning, formatting, and validation logic.
    """
    
    @staticmethod
    def clean_markdown_fences(content, language_hint="php"):
        """
        Remove markdown code fences from response content.
        Supports various fence formats and languages.
        """
        if not content:
            return content
            
        cleaned = content.strip()
        
        # Remove opening fences with language specifiers
        fence_patterns = [
            r'^```' + re.escape(language_hint) + r'\s*\n',
            r'^```[a-zA-Z]*\s*\n',
            r'^```\s*\n'
        ]
        
        for pattern in fence_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE)
        
        # Remove closing fences
        cleaned = re.sub(r'\n```\s*$', '', cleaned)
        cleaned = re.sub(r'^```\s*$', '', cleaned, flags=re.MULTILINE)
        
        return cleaned.strip()
    
    @staticmethod
    def extract_code_from_response(content):
        """
        Extract code blocks from markdown response, preserving the cleanest code.
        """
        if not content:
            return content
            
        # Look for code blocks within triple backticks
        code_block_pattern = r'```(?:[a-zA-Z]*\n)?(.*?)```'
        matches = re.findall(code_block_pattern, content, re.DOTALL)
        
        if matches:
            # Return the first (usually largest) code block
            return matches[0].strip()
        
        # If no code blocks found, try to clean existing content
        return ResponseProcessor.clean_markdown_fences(content)
    
    @staticmethod
    def validate_response_content(content):
        """
        Validate that response content is not empty and meaningful.
        Returns tuple of (is_valid, cleaned_content).
        """
        if not content:
            return False, ""
            
        cleaned = content.strip()
        if not cleaned:
            return False, ""
            
        # Check for common empty responses
        empty_indicators = [
            "no response",
            "empty response", 
            "null",
            "undefined"
        ]
        
        if cleaned.lower() in empty_indicators:
            return False, cleaned
            
        return True, cleaned
    
    @staticmethod
    def format_error_message(error, context="API request"):
        """Format error messages consistently."""
        return "\nERROR ({}): {}".format(context, str(error))
    
    @staticmethod
    def format_debug_message(message, data=None):
        """Format debug messages consistently."""
        if data:
            return "\n[DEBUG] {}: {}".format(message, data)
        return "\n[DEBUG] {}".format(message)
    
    @staticmethod
    def unescape_html(content):
        """Unescape HTML entities in response content."""
        if not content:
            return content
        return html.unescape(content)
    
    @staticmethod
    def normalize_line_endings(content):
        """Normalize line endings to system default."""
        if not content:
            return content
        return content.replace('\r\n', '\n').replace('\r', '\n')
    
    @staticmethod
    def truncate_for_display(content, max_length=100):
        """Truncate content for display purposes with ellipsis."""
        if not content or len(content) <= max_length:
            return content
        return content[:max_length-3] + "..."


class StreamingResponseHandler:
    """
    Handles streaming responses from Ollama API.
    Manages state and content accumulation during streaming.
    """
    
    def __init__(self, callback=None):
        self.callback = callback
        self.accumulated_content = ""
        self.is_complete = False
    
    def handle_chunk(self, content):
        """Handle a single chunk of streaming content."""
        if content:
            self.accumulated_content += content
            if self.callback:
                self.callback(content)
    
    def handle_completion(self):
        """Handle completion of streaming response."""
        self.is_complete = True
    
    def get_accumulated_content(self):
        """Get the complete accumulated content."""
        return self.accumulated_content
    
    def reset(self):
        """Reset the handler for reuse."""
        self.accumulated_content = ""
        self.is_complete = False


class ChatHistoryManager:
    """
    Manages chat history for conversation continuity.
    Handles message formatting and history maintenance.
    """
    
    def __init__(self):
        self.history = []
        self.max_history_length = 20  # Keep last 20 messages
    
    def add_system_message(self, content):
        """Add a system message to history."""
        self.history.append({"role": "system", "content": content})
        self._trim_history()
    
    def add_user_message(self, content):
        """Add a user message to history."""
        self.history.append({"role": "user", "content": content})
        self._trim_history()
    
    def add_assistant_message(self, content):
        """Add an assistant message to history."""
        self.history.append({"role": "assistant", "content": content})
        self._trim_history()
    
    def get_messages_for_api(self):
        """Get messages formatted for API request."""
        return self.history.copy()
    
    def get_conversation_messages_only(self):
        """Get only user and assistant messages (excluding system)."""
        return [msg for msg in self.history if msg["role"] in ["user", "assistant"]]
    
    def clear_history(self):
        """Clear all chat history."""
        self.history = []
    
    def _trim_history(self):
        """Trim history to maximum length, preserving system messages."""
        if len(self.history) <= self.max_history_length:
            return
            
        # Separate system messages from conversation
        system_messages = [msg for msg in self.history if msg["role"] == "system"]
        conversation_messages = [msg for msg in self.history if msg["role"] != "system"]
        
        # Keep only the most recent conversation messages
        recent_conversation = conversation_messages[-(self.max_history_length - len(system_messages)):]
        
        # Rebuild history with system messages first
        self.history = system_messages + recent_conversation