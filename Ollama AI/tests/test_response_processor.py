#!/usr/bin/env python3
"""
Unit tests for response_processor.py module.
Tests the ResponseProcessor, StreamingResponseHandler, and ChatHistoryManager classes.
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock sublime module before importing (not needed for response_processor but for consistency)
sys.modules['sublime'] = Mock()

from response_processor import ResponseProcessor, StreamingResponseHandler, ChatHistoryManager


class TestResponseProcessor(unittest.TestCase):
    """Test cases for ResponseProcessor class."""
    
    def test_clean_markdown_fences_php(self):
        """Test cleaning markdown fences with PHP code."""
        content = "```php\n<?php\nclass Test {}\n```"
        result = ResponseProcessor.clean_markdown_fences(content, "php")
        self.assertEqual(result, "<?php\nclass Test {}")
    
    def test_clean_markdown_fences_generic(self):
        """Test cleaning markdown fences with generic language."""
        content = "```javascript\nconst x = 1;\n```"
        result = ResponseProcessor.clean_markdown_fences(content, "php")
        self.assertEqual(result, "const x = 1;")
    
    def test_clean_markdown_fences_no_language(self):
        """Test cleaning markdown fences without language specifier."""
        content = "```\nsome code here\n```"
        result = ResponseProcessor.clean_markdown_fences(content)
        self.assertEqual(result, "some code here")
    
    def test_clean_markdown_fences_multiple_blocks(self):
        """Test cleaning content with multiple code blocks."""
        content = "```php\ncode1\n```\nsome text\n```\ncode2\n```"
        result = ResponseProcessor.clean_markdown_fences(content, "php")
        self.assertEqual(result, "code1\nsome text\ncode2")
    
    def test_clean_markdown_fences_empty_content(self):
        """Test cleaning empty or None content."""
        self.assertEqual(ResponseProcessor.clean_markdown_fences(""), "")
        self.assertEqual(ResponseProcessor.clean_markdown_fences(None), None)
    
    def test_clean_markdown_fences_no_fences(self):
        """Test cleaning content without markdown fences."""
        content = "just plain text with no fences"
        result = ResponseProcessor.clean_markdown_fences(content)
        self.assertEqual(result, content)
    
    def test_extract_code_from_response_single_block(self):
        """Test extracting code from response with single code block."""
        content = "Here's the code:\n```php\n<?php echo 'test';\n```\nThat's it!"
        result = ResponseProcessor.extract_code_from_response(content)
        self.assertEqual(result, "<?php echo 'test';")
    
    def test_extract_code_from_response_multiple_blocks(self):
        """Test extracting code from response with multiple blocks (returns first)."""
        content = "```php\nfirst block\n```\nsome text\n```js\nsecond block\n```"
        result = ResponseProcessor.extract_code_from_response(content)
        self.assertEqual(result, "first block")
    
    def test_extract_code_from_response_no_blocks(self):
        """Test extracting code when no code blocks present."""
        content = "Just regular text without code blocks"
        result = ResponseProcessor.extract_code_from_response(content)
        self.assertEqual(result, content)
    
    def test_extract_code_from_response_empty(self):
        """Test extracting code from empty content."""
        self.assertEqual(ResponseProcessor.extract_code_from_response(""), "")
        self.assertEqual(ResponseProcessor.extract_code_from_response(None), None)
    
    def test_validate_response_content_valid(self):
        """Test validating valid response content."""
        content = "This is valid content"
        is_valid, cleaned = ResponseProcessor.validate_response_content(content)
        self.assertTrue(is_valid)
        self.assertEqual(cleaned, "This is valid content")
    
    def test_validate_response_content_empty_string(self):
        """Test validating empty string."""
        is_valid, cleaned = ResponseProcessor.validate_response_content("")
        self.assertFalse(is_valid)
        self.assertEqual(cleaned, "")
    
    def test_validate_response_content_none(self):
        """Test validating None content."""
        is_valid, cleaned = ResponseProcessor.validate_response_content(None)
        self.assertFalse(is_valid)
        self.assertEqual(cleaned, "")
    
    def test_validate_response_content_whitespace_only(self):
        """Test validating whitespace-only content."""
        is_valid, cleaned = ResponseProcessor.validate_response_content("   \n\t  ")
        self.assertFalse(is_valid)
        self.assertEqual(cleaned, "")
    
    def test_validate_response_content_empty_indicators(self):
        """Test validating content with empty indicators."""
        empty_indicators = ["no response", "empty response", "null", "undefined"]
        
        for indicator in empty_indicators:
            is_valid, cleaned = ResponseProcessor.validate_response_content(indicator)
            self.assertFalse(is_valid)
            self.assertEqual(cleaned, indicator)
            
            # Test case insensitive
            is_valid, cleaned = ResponseProcessor.validate_response_content(indicator.upper())
            self.assertFalse(is_valid)
            self.assertEqual(cleaned, indicator.upper())
    
    def test_format_error_message_default_context(self):
        """Test formatting error message with default context."""
        error = Exception("Test error")
        result = ResponseProcessor.format_error_message(error)
        self.assertEqual(result, "\nERROR (API request): Test error")
    
    def test_format_error_message_custom_context(self):
        """Test formatting error message with custom context."""
        error = "Custom error message"
        result = ResponseProcessor.format_error_message(error, "file operation")
        self.assertEqual(result, "\nERROR (file operation): Custom error message")
    
    def test_format_debug_message_with_data(self):
        """Test formatting debug message with data."""
        result = ResponseProcessor.format_debug_message("Test message", {"key": "value"})
        self.assertEqual(result, "\n[DEBUG] Test message: {'key': 'value'}")
    
    def test_format_debug_message_without_data(self):
        """Test formatting debug message without data."""
        result = ResponseProcessor.format_debug_message("Test message")
        self.assertEqual(result, "\n[DEBUG] Test message")
    
    def test_unescape_html(self):
        """Test unescaping HTML entities."""
        content = "&lt;div&gt;Hello &amp; welcome&lt;/div&gt;"
        result = ResponseProcessor.unescape_html(content)
        self.assertEqual(result, "<div>Hello & welcome</div>")
    
    def test_unescape_html_empty(self):
        """Test unescaping empty content."""
        self.assertEqual(ResponseProcessor.unescape_html(""), "")
        self.assertEqual(ResponseProcessor.unescape_html(None), None)
    
    def test_normalize_line_endings_crlf(self):
        """Test normalizing CRLF line endings."""
        content = "line1\r\nline2\r\nline3"
        result = ResponseProcessor.normalize_line_endings(content)
        self.assertEqual(result, "line1\nline2\nline3")
    
    def test_normalize_line_endings_cr(self):
        """Test normalizing CR line endings."""
        content = "line1\rline2\rline3"
        result = ResponseProcessor.normalize_line_endings(content)
        self.assertEqual(result, "line1\nline2\nline3")
    
    def test_normalize_line_endings_mixed(self):
        """Test normalizing mixed line endings."""
        content = "line1\r\nline2\rline3\nline4"
        result = ResponseProcessor.normalize_line_endings(content)
        self.assertEqual(result, "line1\nline2\nline3\nline4")
    
    def test_normalize_line_endings_empty(self):
        """Test normalizing empty content."""
        self.assertEqual(ResponseProcessor.normalize_line_endings(""), "")
        self.assertEqual(ResponseProcessor.normalize_line_endings(None), None)
    
    def test_truncate_for_display_short(self):
        """Test truncating short content."""
        content = "Short text"
        result = ResponseProcessor.truncate_for_display(content, 50)
        self.assertEqual(result, "Short text")
    
    def test_truncate_for_display_long(self):
        """Test truncating long content."""
        content = "This is a very long text that should be truncated"
        result = ResponseProcessor.truncate_for_display(content, 20)
        self.assertEqual(result, "This is a very lo...")
    
    def test_truncate_for_display_exact_length(self):
        """Test truncating content at exact max length."""
        content = "12345678901234567890"  # 20 characters
        result = ResponseProcessor.truncate_for_display(content, 20)
        self.assertEqual(result, content)  # Should not truncate
    
    def test_truncate_for_display_empty(self):
        """Test truncating empty content."""
        self.assertEqual(ResponseProcessor.truncate_for_display(""), "")
        self.assertEqual(ResponseProcessor.truncate_for_display(None), None)


class TestStreamingResponseHandler(unittest.TestCase):
    """Test cases for StreamingResponseHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.callback = Mock()
        self.handler = StreamingResponseHandler(self.callback)
    
    def test_init_with_callback(self):
        """Test initialization with callback."""
        self.assertEqual(self.handler.callback, self.callback)
        self.assertEqual(self.handler.accumulated_content, "")
        self.assertFalse(self.handler.is_complete)
    
    def test_init_without_callback(self):
        """Test initialization without callback."""
        handler = StreamingResponseHandler()
        self.assertIsNone(handler.callback)
        self.assertEqual(handler.accumulated_content, "")
        self.assertFalse(handler.is_complete)
    
    def test_handle_chunk_with_callback(self):
        """Test handling chunk with callback."""
        self.handler.handle_chunk("test content")
        
        self.assertEqual(self.handler.accumulated_content, "test content")
        self.callback.assert_called_once_with("test content")
    
    def test_handle_chunk_without_callback(self):
        """Test handling chunk without callback."""
        handler = StreamingResponseHandler()
        handler.handle_chunk("test content")
        
        self.assertEqual(handler.accumulated_content, "test content")
    
    def test_handle_chunk_empty_content(self):
        """Test handling empty chunk."""
        self.handler.handle_chunk("")
        
        self.assertEqual(self.handler.accumulated_content, "")
        self.callback.assert_not_called()
    
    def test_handle_chunk_none_content(self):
        """Test handling None chunk."""
        self.handler.handle_chunk(None)
        
        self.assertEqual(self.handler.accumulated_content, "")
        self.callback.assert_not_called()
    
    def test_handle_multiple_chunks(self):
        """Test handling multiple chunks."""
        chunks = ["chunk1", "chunk2", "chunk3"]
        
        for chunk in chunks:
            self.handler.handle_chunk(chunk)
        
        self.assertEqual(self.handler.accumulated_content, "chunk1chunk2chunk3")
        self.assertEqual(self.callback.call_count, 3)
    
    def test_handle_completion(self):
        """Test handling completion."""
        self.handler.handle_completion()
        self.assertTrue(self.handler.is_complete)
    
    def test_get_accumulated_content(self):
        """Test getting accumulated content."""
        self.handler.handle_chunk("part1")
        self.handler.handle_chunk("part2")
        
        result = self.handler.get_accumulated_content()
        self.assertEqual(result, "part1part2")
    
    def test_reset(self):
        """Test resetting handler."""
        self.handler.handle_chunk("some content")
        self.handler.handle_completion()
        
        self.handler.reset()
        
        self.assertEqual(self.handler.accumulated_content, "")
        self.assertFalse(self.handler.is_complete)


class TestChatHistoryManager(unittest.TestCase):
    """Test cases for ChatHistoryManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = ChatHistoryManager()
    
    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.manager.history, [])
        self.assertEqual(self.manager.max_history_length, 20)
    
    def test_add_system_message(self):
        """Test adding system message."""
        self.manager.add_system_message("System prompt")
        
        expected = [{"role": "system", "content": "System prompt"}]
        self.assertEqual(self.manager.history, expected)
    
    def test_add_user_message(self):
        """Test adding user message."""
        self.manager.add_user_message("User input")
        
        expected = [{"role": "user", "content": "User input"}]
        self.assertEqual(self.manager.history, expected)
    
    def test_add_assistant_message(self):
        """Test adding assistant message."""
        self.manager.add_assistant_message("Assistant response")
        
        expected = [{"role": "assistant", "content": "Assistant response"}]
        self.assertEqual(self.manager.history, expected)
    
    def test_conversation_flow(self):
        """Test full conversation flow."""
        self.manager.add_system_message("You are helpful")
        self.manager.add_user_message("Hello")
        self.manager.add_assistant_message("Hi there!")
        self.manager.add_user_message("How are you?")
        self.manager.add_assistant_message("I'm doing well!")
        
        expected = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "I'm doing well!"}
        ]
        self.assertEqual(self.manager.history, expected)
    
    def test_get_messages_for_api(self):
        """Test getting messages for API call."""
        self.manager.add_system_message("System")
        self.manager.add_user_message("User")
        
        result = self.manager.get_messages_for_api()
        
        # Should return a copy of the history
        expected = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "User"}
        ]
        self.assertEqual(result, expected)
        # Verify it's a copy (modifying result shouldn't affect history)
        result.append({"role": "test", "content": "test"})
        self.assertEqual(len(self.manager.history), 2)
    
    def test_get_conversation_messages_only(self):
        """Test getting only conversation messages (excluding system)."""
        self.manager.add_system_message("System prompt")
        self.manager.add_user_message("User input")
        self.manager.add_assistant_message("Assistant response")
        self.manager.add_system_message("Another system message")
        
        result = self.manager.get_conversation_messages_only()
        
        expected = [
            {"role": "user", "content": "User input"},
            {"role": "assistant", "content": "Assistant response"}
        ]
        self.assertEqual(result, expected)
    
    def test_clear_history(self):
        """Test clearing chat history."""
        self.manager.add_system_message("System")
        self.manager.add_user_message("User")
        
        self.manager.clear_history()
        self.assertEqual(self.manager.history, [])
    
    def test_trim_history_under_limit(self):
        """Test that history under limit is not trimmed."""
        # Add messages under the limit
        for i in range(5):
            self.manager.add_user_message(f"Message {i}")
        
        self.assertEqual(len(self.manager.history), 5)
    
    def test_trim_history_over_limit(self):
        """Test trimming history when over limit."""
        # Set a smaller limit for testing
        self.manager.max_history_length = 5
        
        # Add system message
        self.manager.add_system_message("System prompt")
        
        # Add more conversation messages than the limit allows
        for i in range(8):
            self.manager.add_user_message(f"User {i}")
            self.manager.add_assistant_message(f"Assistant {i}")
        
        # Should keep system message plus most recent conversation messages
        self.assertEqual(len(self.manager.history), 5)
        
        # First message should be system message
        self.assertEqual(self.manager.history[0]["role"], "system")
        self.assertEqual(self.manager.history[0]["content"], "System prompt")
        
        # Remaining should be most recent conversation messages
        self.assertIn("User 6", [msg["content"] for msg in self.manager.history])
        self.assertIn("User 7", [msg["content"] for msg in self.manager.history])
        self.assertNotIn("User 0", [msg["content"] for msg in self.manager.history])
    
    def test_trim_history_multiple_system_messages(self):
        """Test trimming with multiple system messages."""
        self.manager.max_history_length = 6
        
        # Add multiple system messages
        self.manager.add_system_message("System 1")
        self.manager.add_system_message("System 2")
        
        # Add conversation messages
        for i in range(8):
            self.manager.add_user_message(f"User {i}")
        
        # Should preserve all system messages and most recent conversation
        self.assertEqual(len(self.manager.history), 6)
        
        system_count = sum(1 for msg in self.manager.history if msg["role"] == "system")
        self.assertEqual(system_count, 2)
        
        # Should keep most recent user messages
        self.assertIn("User 6", [msg["content"] for msg in self.manager.history])
        self.assertIn("User 7", [msg["content"] for msg in self.manager.history])
        self.assertNotIn("User 0", [msg["content"] for msg in self.manager.history])
    
    def test_trim_history_only_system_messages(self):
        """Test trimming when only system messages exist."""
        self.manager.max_history_length = 3
        
        for i in range(5):
            self.manager.add_system_message(f"System {i}")
        
        # All system messages should be preserved even if over limit
        self.assertEqual(len(self.manager.history), 5)
        for i, msg in enumerate(self.manager.history):
            self.assertEqual(msg["role"], "system")
            self.assertEqual(msg["content"], f"System {i}")


class TestResponseProcessorEdgeCases(unittest.TestCase):
    """Test edge cases and complex scenarios for ResponseProcessor."""
    
    def test_clean_markdown_fences_nested_backticks(self):
        """Test cleaning content with nested backticks."""
        content = "```php\n$code = `ls -la`;\necho `date`;\n```"
        result = ResponseProcessor.clean_markdown_fences(content, "php")
        self.assertEqual(result, "$code = `ls -la`;\necho `date`;")
    
    def test_clean_markdown_fences_incomplete_blocks(self):
        """Test cleaning content with incomplete markdown blocks."""
        content = "```php\nsome code here\n(no closing fence)"
        result = ResponseProcessor.clean_markdown_fences(content, "php")
        self.assertEqual(result, "some code here\n(no closing fence)")
    
    def test_extract_code_complex_response(self):
        """Test extracting code from complex AI response."""
        content = """Here's the solution:

```php
<?php
class UserController {
    public function index() {
        return view('users');
    }
}
```

This code creates a controller that handles user listing. You can also use:

```javascript
const users = await fetch('/api/users');
```

Both approaches work well."""
        
        result = ResponseProcessor.extract_code_from_response(content)
        expected = "<?php\nclass UserController {\n    public function index() {\n        return view('users');\n    }\n}"
        self.assertEqual(result, expected)
    
    def test_validate_response_content_with_whitespace(self):
        """Test validating content that has meaningful content after stripping."""
        content = "  \n  Valid content with surrounding whitespace  \n  "
        is_valid, cleaned = ResponseProcessor.validate_response_content(content)
        self.assertTrue(is_valid)
        self.assertEqual(cleaned, "Valid content with surrounding whitespace")


class TestStreamingResponseHandlerIntegration(unittest.TestCase):
    """Integration tests for StreamingResponseHandler."""
    
    def test_complete_streaming_simulation(self):
        """Test complete streaming response simulation."""
        collected_chunks = []
        
        def collector(content):
            collected_chunks.append(content)
        
        handler = StreamingResponseHandler(collector)
        
        # Simulate streaming chunks
        chunks = ["Hello", " ", "world", "!", " How", " are", " you?"]
        for chunk in chunks:
            handler.handle_chunk(chunk)
        
        handler.handle_completion()
        
        # Verify callback was called for each chunk
        self.assertEqual(collected_chunks, chunks)
        
        # Verify accumulated content
        self.assertEqual(handler.get_accumulated_content(), "Hello world! How are you?")
        self.assertTrue(handler.is_complete)
    
    def test_handler_reuse(self):
        """Test reusing handler after reset."""
        handler = StreamingResponseHandler()
        
        # First use
        handler.handle_chunk("first use")
        handler.handle_completion()
        
        # Reset and reuse
        handler.reset()
        handler.handle_chunk("second use")
        
        self.assertEqual(handler.get_accumulated_content(), "second use")
        self.assertFalse(handler.is_complete)


if __name__ == '__main__':
    print("🧪 Running Response Processor Tests...")
    print("=" * 50)
    
    # Run the tests
    unittest.main(verbosity=2, exit=False)
    
    print("\n" + "=" * 50)
    print("✅ Response Processor tests completed!")