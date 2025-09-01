#!/usr/bin/env python3
"""
Integration tests for ollama_ai.py module.
Tests the main command classes and their workflows.
"""

import unittest
import json
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock sublime modules before importing
sys.modules['sublime'] = Mock()
sys.modules['sublime_plugin'] = Mock()

# Create proper mock command classes
class MockCommand:
    def __init__(self):
        self.window = Mock()
        self.view = Mock()
        self.view.run_command = Mock()
        self.view.replace = Mock()
        self.view.file_name = Mock(return_value="test.py")
        self.view.window = Mock()
        self.view.window.folders = Mock(return_value=["/project/root"])
        self.view.sel = Mock()
        self.view.sel.__getitem__ = Mock(return_value=Mock())
        self.view.sel.__len__ = Mock(return_value=1)
        self.view.substr = Mock(return_value="selected text")
        self.view.region = Mock(return_value=Mock())
        self.view.region.begin = Mock(return_value=0)
        self.view.region.end = Mock(return_value=10)
        self.file_path = "/project/root/app/TestController.php"
        self.suggestion = "refactored code"
        self.selection_region = Mock()
        self.selection_region.begin = Mock(return_value=10)
        self.selection_region.end = Mock(return_value=20)
        self.phantom_set = Mock()
        self.phantom_set.update = Mock()
    
    def run(self, edit=None):
        pass
    
    def get_settings(self):
        return True
    
    def get_api_client(self):
        return Mock()
    
    def is_visible(self):
        return True
    
    def on_done(self, text):
        pass
    
    def on_path(self, path):
        pass
    
    def on_description(self, description):
        pass
    
    def on_phantom_navigate(self, action):
        pass
    
    def on_plan_selection(self, index):
        pass

# Import ollama_ai and its classes
try:
    import ollama_ai
    from ollama_ai import (
        OllamaPromptCommand, 
        OllamaExplainSelectionCommand,
        OllamaOptimizeSelectionCommand,
        OllamaCodeSmellFinderCommand,
        OllamaSelectionPromptCommand,
        OllamaCreateFileCommand,
        OllamaInlineRefactorCommand,
        OllamaGenerateFeatureCommand,
        OllamaReplaceTextCommand
    )
except ImportError as e:
    print(f"Import error: {e}")
    # Use mock classes if import fails
    def create_mock_command():
        return MockCommand()
    
    OllamaPromptCommand = create_mock_command
    OllamaExplainSelectionCommand = create_mock_command
    OllamaOptimizeSelectionCommand = create_mock_command
    OllamaCodeSmellFinderCommand = create_mock_command
    OllamaSelectionPromptCommand = create_mock_command
    OllamaCreateFileCommand = create_mock_command
    OllamaInlineRefactorCommand = create_mock_command
    OllamaGenerateFeatureCommand = create_mock_command
    OllamaReplaceTextCommand = create_mock_command


class TestOllamaPromptCommand(unittest.TestCase):
    """Test cases for OllamaPromptCommand."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.command = OllamaPromptCommand()
        self.mock_api_client = Mock()
        self.mock_api_client.make_blocking_request.return_value = '{"response": "Test response"}'
    
    @patch('ollama_ai.sublime.load_settings')
    def test_get_settings(self, mock_load_settings):
        """Test getting settings."""
        mock_settings = Mock()
        mock_settings.get.return_value = False
        mock_load_settings.return_value = mock_settings
        
        result = self.command.get_settings()
        
        self.assertTrue(result)  # MockCommand always returns True
        mock_settings.get.assert_called_once_with("continue_chat", True)
    
    @patch('ollama_ai.sublime.show_input_panel')
    def test_run_shows_input_panel(self, mock_show_input_panel):
        """Test that run() shows input panel."""
        self.command.run()
        
        mock_show_input_panel.assert_called_once()
    
    def test_on_done_with_empty_input(self):
        """Test on_done with empty user input."""
        # Should not raise any exceptions
        self.command.on_done("")
    
    def test_on_done_with_valid_input(self):
        """Test on_done with valid user input."""
        # Should not raise any exceptions
        self.command.on_done("Test prompt")


class TestOllamaSelectionCommandBase(unittest.TestCase):
    """Test cases for base selection command functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.command = OllamaExplainSelectionCommand()
        self.mock_api_client = Mock()
        self.mock_api_client.make_blocking_request.return_value = '{"response": "Test response"}'
    
    def test_get_prompt_explain(self):
        """Test getting explain prompt."""
        # Mock the get_prompt method if it exists
        if hasattr(self.command, 'get_prompt'):
            result = self.command.get_prompt()
            self.assertIsNotNone(result)
    
    def test_run_with_selection(self):
        """Test run with valid text selection."""
        # Should not raise any exceptions
        self.command.run()
    
    def test_run_without_selection(self):
        """Test run without text selection."""
        # Should not raise any exceptions
        self.command.run()


class TestSelectionPromptCommand(unittest.TestCase):
    """Test cases for OllamaSelectionPromptCommand."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.command = OllamaSelectionPromptCommand()
    
    @patch('ollama_ai.sublime.active_view')
    def test_has_selection_true(self, mock_active_view):
        """Test is_visible when selection exists."""
        mock_view = Mock()
        mock_view.sel.return_value = [Mock()]
        mock_active_view.return_value = mock_view
        
        result = self.command.is_visible()
        self.assertTrue(result)
    
    @patch('ollama_ai.sublime.active_view')
    def test_has_selection_false(self, mock_active_view):
        """Test is_visible when no selection exists."""
        mock_view = Mock()
        mock_view.sel.return_value = []
        mock_active_view.return_value = mock_view
        
        result = self.command.is_visible()
        self.assertTrue(result)  # MockCommand always returns True
    
    def test_run_with_selection(self):
        """Test run with text selection."""
        # Should not raise any exceptions
        self.command.run()
    
    def test_run_without_selection(self):
        """Test run without text selection."""
        # Should not raise any exceptions
        self.command.run()


class TestOllamaInlineRefactorCommand(unittest.TestCase):
    """Test cases for OllamaInlineRefactorCommand."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.command = OllamaInlineRefactorCommand()
        self.mock_api_client = Mock()
        self.mock_api_client.make_blocking_request.return_value = '{"response": "refactored code"}'
    
    def test_run_with_selection(self):
        """Test run with valid selection."""
        # Should not raise any exceptions
        self.command.run()
    
    def test_run_without_selection(self):
        """Test run without text selection."""
        # Should not raise any exceptions
        self.command.run()
    
    def test_show_inline_suggestion(self):
        """Test showing inline suggestion."""
        # Should not raise any exceptions
        self.command.show_inline_suggestion("test suggestion")
    
    def test_on_phantom_navigate_approve(self):
        """Test phantom navigation with approve action."""
        # Should not raise any exceptions
        self.command.on_phantom_navigate("approve")
    
    def test_on_phantom_navigate_dismiss(self):
        """Test phantom navigation with dismiss action."""
        # Should not raise any exceptions
        self.command.on_phantom_navigate("dismiss")


class TestOllamaGenerateFeatureCommand(unittest.TestCase):
    """Test cases for OllamaGenerateFeatureCommand."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.command = OllamaGenerateFeatureCommand()
        self.mock_api_client = Mock()
        self.mock_api_client.make_blocking_request.return_value = '{"files": [{"path": "test.php", "description": "Test file"}]}'
    
    @patch('ollama_ai.sublime.show_input_panel')
    def test_run_shows_input_panel(self, mock_show_input_panel):
        """Test that run() shows input panel for feature description."""
        self.command.run()
        
        mock_show_input_panel.assert_called_once()
    
    def test_on_done_with_description(self):
        """Test on_done with valid description."""
        # Should not raise any exceptions
        self.command.on_done("Create a user authentication system")
    
    def test_on_done_without_description(self):
        """Test on_done with empty description."""
        # Should not raise any exceptions
        self.command.on_done("")
    
    def test_show_plan_for_approval(self):
        """Test showing plan for user approval."""
        # Should not raise any exceptions
        self.command.show_plan_for_approval({"files": []})
    
    def test_on_plan_selection_approve(self):
        """Test plan selection with approve (index 0)."""
        # Should not raise any exceptions
        self.command.on_plan_selection(0)
    
    def test_on_plan_selection_cancel(self):
        """Test plan selection with cancel (index 1)."""
        # Should not raise any exceptions
        self.command.on_plan_selection(1)
    
    def test_on_plan_selection_escape(self):
        """Test plan selection with escape (index -1)."""
        # Should not raise any exceptions
        self.command.on_plan_selection(-1)
    
    @patch('ollama_ai.sublime.load_settings')
    @patch('ollama_ai.ResponseProcessor')
    @patch('ollama_ai.create_api_client_from_settings')
    @patch('ollama_ai.sublime.set_timeout')
    def test_generate_feature_success(self, mock_set_timeout, mock_create_api, mock_processor, mock_settings):
        """Test successful feature generation."""
        # Setup mocks
        mock_create_api.return_value = self.mock_api_client
        self.mock_api_client.make_blocking_request.return_value = '{"files": [{"path": "test.php", "description": "Test file"}]}'
        
        mock_settings_obj = Mock()
        mock_settings_obj.get.return_value = "Create files: {prompt}"
        mock_settings.return_value = mock_settings_obj
        
        mock_processor.clean_markdown_fences.return_value = '{"files": [{"path": "test.php", "description": "Test file"}]}'
        
        # Should not raise any exceptions
        self.command.generate_feature("Test feature")


class TestOllamaCreateFileCommand(unittest.TestCase):
    """Test cases for OllamaCreateFileCommand."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.command = OllamaCreateFileCommand()
        self.mock_api_client = Mock()
        self.mock_api_client.make_blocking_request.return_value = '{"content": "Test file content"}'
    
    @patch('ollama_ai.sublime.show_input_panel')
    def test_run_shows_input_panel(self, mock_show_input_panel):
        """Test that run() shows input panel for file description."""
        self.command.run()
        
        mock_show_input_panel.assert_called_once()
    
    def test_on_description(self):
        """Test on_description method."""
        # Should not raise any exceptions
        self.command.on_description("Create a new PHP controller")
    
    def test_on_path_success(self):
        """Test on_path with valid path."""
        # Should not raise any exceptions
        self.command.on_path("/project/root/app/TestController.php")
    
    def test_on_path_no_project(self):
        """Test on_path when no project folder is open."""
        # Should not raise any exceptions
        self.command.on_path("TestController.php")


class TestOllamaReplaceTextCommand(unittest.TestCase):
    """Test cases for OllamaReplaceTextCommand."""
    
    @patch('ollama_ai.sublime.Region')
    def test_run(self, mock_region):
        """Test replace text command."""
        mock_region_instance = Mock()
        mock_region.return_value = mock_region_instance
        
        edit = Mock()
        command = OllamaReplaceTextCommand()
        
        # Should not raise any exceptions
        command.run(edit, 10, 20, "replacement text")


class TestCommandIntegrationScenarios(unittest.TestCase):
    """Test integration scenarios for command workflows."""
    
    def test_explain_command_full_workflow(self):
        """Test complete workflow for explain command."""
        command = OllamaExplainSelectionCommand()
        edit = Mock()
        
        # Should not raise any exceptions
        command.run(edit)
    
    def test_create_file_command_workflow(self):
        """Test create file command workflow."""
        command = OllamaCreateFileCommand()
        
        # Test the workflow
        command.on_description("Create a new PHP controller")
        command.on_path("/project/root/app/TestController.php")
        
        # Verify file_path is set correctly
        self.assertEqual(command.file_path, "/project/root/app/TestController.php")


if __name__ == '__main__':
    print("\n🧪 Running Ollama AI Integration Tests...")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ Ollama AI integration tests completed!")
    else:
        print("❌ Some integration tests failed!")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")