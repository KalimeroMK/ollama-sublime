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

# Import ollama_ai and its classes
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


class TestOllamaPromptCommand(unittest.TestCase):
    """Test cases for OllamaPromptCommand."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.command = OllamaPromptCommand()
        self.command.window = Mock()
        
        # Mock API client
        self.mock_api_client = Mock()
        self.mock_api_client.make_blocking_request.return_value = "AI response content"
        
        # Mock chat history manager
        self.mock_chat_history_manager = Mock()
        self.mock_chat_history_manager.get_messages_for_api.return_value = []
    
    @patch('ollama_ai.UIHelpers')
    @patch('ollama_ai.create_api_client_from_settings')
    @patch('ollama_ai.ChatHistoryManager')
    def test_run_shows_input_panel(self, mock_chat_manager, mock_create_api, mock_ui):
        """Test that run() shows input panel."""
        mock_chat_manager.return_value = self.mock_chat_history_manager
        
        self.command.run()
        
        mock_ui.show_input_panel.assert_called_once_with(
            self.command.window,
            "Enter your prompt:",
            "",
            self.command.on_done
        )
    
    @patch('ollama_ai.UIHelpers')
    @patch('ollama_ai.ContextAnalyzer')
    @patch('ollama_ai.create_api_client_from_settings')
    @patch('ollama_ai.sublime.set_timeout_async')
    def test_on_done_with_valid_input(self, mock_set_timeout, mock_create_api, mock_context, mock_ui):
        """Test on_done with valid user input."""
        # Setup mocks
        mock_create_api.return_value = self.mock_api_client
        mock_context_analyzer = Mock()
        mock_context_analyzer.analyze_text_for_context.return_value = ("TestSymbol", " context info")
        mock_context.from_view.return_value = mock_context_analyzer
        
        mock_tab = Mock()
        mock_ui.create_output_tab.return_value = mock_tab
        
        # Mock settings
        with patch('ollama_ai.sublime.load_settings') as mock_settings:
            mock_settings.return_value.get.return_value = True  # continue_chat
            
            self.command.chat_history_manager = self.mock_chat_history_manager
            self.command.on_done("Test user input")
            
            # Verify output tab creation
            mock_ui.create_output_tab.assert_called_once_with(
                self.command.window,
                "Ollama Custom Prompt",
                "\n> Test user input\n"
            )
            
            # Verify async fetch is scheduled
            mock_set_timeout.assert_called()
    
    @patch('ollama_ai.UIHelpers')
    def test_on_done_with_empty_input(self, mock_ui):
        """Test on_done with empty user input."""
        self.command.on_done("")
        
        # Should not create any tabs or make API calls
        mock_ui.create_output_tab.assert_not_called()
    
    @patch('ollama_ai.sublime.load_settings')
    def test_get_settings(self, mock_load_settings):
        """Test getting settings."""
        mock_settings = Mock()
        mock_settings.get.return_value = False
        mock_load_settings.return_value = mock_settings
        
        result = self.command.get_settings()
        
        self.assertFalse(result)
        mock_settings.get.assert_called_once_with("continue_chat", True)


class TestOllamaSelectionCommandBase(unittest.TestCase):
    """Test cases for selection-based commands."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.command = OllamaExplainSelectionCommand()
        self.command.view = Mock()
        
        # Mock selected text
        mock_region = Mock()
        mock_region.empty.return_value = False
        self.command.view.sel.return_value = [mock_region]
        self.command.view.substr.return_value = "selected code"
        
        # Mock window
        mock_window = Mock()
        self.command.view.window.return_value = mock_window
        
        # Mock API client
        self.mock_api_client = Mock()
        self.mock_api_client.model = "test-model"
    
    @patch('ollama_ai.UIHelpers')
    @patch('ollama_ai.ContextAnalyzer')
    @patch('ollama_ai.TabManager')
    @patch('ollama_ai.create_api_client_from_settings')
    @patch('ollama_ai.sublime.set_timeout_async')
    def test_run_with_selection(self, mock_set_timeout, mock_create_api, mock_tab_manager, mock_context, mock_ui):
        """Test run with valid text selection."""
        # Setup mocks
        mock_create_api.return_value = self.mock_api_client
        mock_ui.get_selected_text.return_value = "selected code"
        
        mock_context_analyzer = Mock()
        mock_context_analyzer.analyze_text_for_context.return_value = ("TestClass", " context")
        mock_context.from_view.return_value = mock_context_analyzer
        
        mock_tab_mgr = Mock()
        mock_output_tab = Mock()
        mock_tab_mgr.create_output_tab.return_value = mock_output_tab
        mock_tab_manager.return_value = mock_tab_mgr
        
        # Mock settings
        with patch('ollama_ai.sublime.load_settings') as mock_settings:
            mock_settings_obj = Mock()
            mock_settings_obj.get.side_effect = lambda key, default: {
                "tab_title": "Ollama {selection}",
                "explain_prompt": "Explain: {code}"
            }.get(key, default)
            mock_settings.return_value = mock_settings_obj
            
            # Run the command
            self.command.run(Mock())
            
            # Verify context analysis
            mock_context_analyzer.analyze_text_for_context.assert_called_once_with("selected code")
            
            # Verify tab creation
            mock_tab_mgr.create_output_tab.assert_called_once_with(
                "selection_output",
                "Ollama selected code",
                "Explain: selected code",
                "test-model"
            )
            
            # Verify async fetch is scheduled
            mock_set_timeout.assert_called_once()
    
    @patch('ollama_ai.UIHelpers')
    def test_run_without_selection(self, mock_ui):
        """Test run without text selection."""
        mock_ui.get_selected_text.return_value = ""
        
        self.command.run(Mock())
        
        mock_ui.show_status_message.assert_called_once_with("Ollama: No text selected.")
    
    def test_get_prompt_explain(self):
        """Test getting explain prompt."""
        settings = Mock()
        settings.get.return_value = "Custom explain prompt: {code}"
        
        result = self.command.get_prompt(settings)
        
        self.assertEqual(result, "Custom explain prompt: {code}")
        settings.get.assert_called_once_with(
            "explain_prompt", 
            "Explain the following code in a concise and clear way, assuming a professional Laravel PHP developer audience. Focus on the code's purpose, its role in the system, and any non-obvious logic.\n\n---\n\n{code}"
        )


class TestOllamaCreateFileCommand(unittest.TestCase):
    """Test cases for OllamaCreateFileCommand."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.command = OllamaCreateFileCommand()
        self.command.window = Mock()
        
        # Mock API client
        self.mock_api_client = Mock()
    
    @patch('ollama_ai.UIHelpers')
    def test_run_shows_input_panel(self, mock_ui):
        """Test that run() shows input panel for file description."""
        self.command.run()
        
        mock_ui.show_input_panel.assert_called_once_with(
            self.command.window,
            "Describe the file you want to create:",
            "",
            self.command.on_description
        )
    
    @patch('ollama_ai.UIHelpers')
    def test_on_description(self, mock_ui):
        """Test on_description method."""
        self.command.on_description("Test file description")
        
        self.assertEqual(self.command.description, "Test file description")
        mock_ui.show_input_panel.assert_called_once_with(
            self.command.window,
            "Enter the file path (relative to project):",
            "",
            self.command.on_path
        )
    
    @patch('ollama_ai.UIHelpers')
    @patch('ollama_ai.ContextAnalyzer')
    @patch('ollama_ai.create_api_client_from_settings')
    @patch('ollama_ai.threading.Thread')
    def test_on_path_success(self, mock_thread, mock_create_api, mock_context, mock_ui):
        """Test on_path with valid path."""
        # Setup mocks
        mock_ui.ensure_project_folder.return_value = "/project/root"
        mock_create_api.return_value = self.mock_api_client
        
        mock_context_analyzer = Mock()
        mock_context_analyzer.analyze_text_for_context.return_value = ("TestClass", " context")
        mock_context.from_view.return_value = mock_context_analyzer
        
        mock_progress_tab = Mock()
        mock_ui.create_progress_tab.return_value = mock_progress_tab
        
        # Set description
        self.command.description = "Test file description"
        
        # Run on_path
        self.command.on_path("app/Test.php")
        
        # Verify file path is set
        self.assertEqual(self.command.file_path, "/project/root/app/Test.php")
        
        # Verify progress tab creation
        mock_ui.create_progress_tab.assert_called_once_with(
            self.command.window,
            "Creating File",
            "Creating file at /project/root/app/Test.php\n"
        )
        
        # Verify thread is started
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()
    
    @patch('ollama_ai.UIHelpers')
    def test_on_path_no_project(self, mock_ui):
        """Test on_path when no project folder is open."""
        mock_ui.ensure_project_folder.return_value = None
        
        self.command.on_path("test.php")
        
        # Should not create progress tab or start thread
        mock_ui.create_progress_tab.assert_not_called()


class TestOllamaInlineRefactorCommand(unittest.TestCase):
    """Test cases for OllamaInlineRefactorCommand."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.command = OllamaInlineRefactorCommand()
        self.command.view = Mock()
        
        # Mock selection
        mock_region = Mock()
        mock_region.empty.return_value = False
        mock_region.begin.return_value = 10
        mock_region.end.return_value = 20
        self.command.view.sel.return_value = [mock_region]
        self.command.view.substr.return_value = "selected code"
        
        # Mock phantom set
        with patch('ollama_ai.sublime.PhantomSet') as mock_phantom_set:
            self.mock_phantom_set = Mock()
            mock_phantom_set.return_value = self.mock_phantom_set
    
    @patch('ollama_ai.UIHelpers')
    @patch('ollama_ai.ContextAnalyzer')
    @patch('ollama_ai.create_api_client_from_settings')
    @patch('ollama_ai.threading.Thread')
    @patch('ollama_ai.sublime.PhantomSet')
    def test_run_with_selection(self, mock_phantom_set, mock_thread, mock_create_api, mock_context, mock_ui):
        """Test run with valid selection."""
        # Setup mocks
        mock_ui.get_selected_text.return_value = "selected code"
        mock_create_api.return_value = Mock()
        
        mock_context_analyzer = Mock()
        mock_context_analyzer.analyze_text_for_context.return_value = ("TestClass", " context")
        mock_context.from_view.return_value = mock_context_analyzer
        
        mock_phantom_set.return_value = self.mock_phantom_set
        
        # Mock settings
        with patch('ollama_ai.sublime.load_settings') as mock_settings:
            mock_settings_obj = Mock()
            mock_settings_obj.get.return_value = "Refactor: {code}"
            mock_settings.return_value = mock_settings_obj
            
            # Run the command
            self.command.run(Mock())
            
            # Verify selected text is stored
            self.assertEqual(self.command.selected_text, "selected code")
            
            # Verify phantom set is created
            mock_phantom_set.assert_called_once_with(self.command.view, "ollama_inline_refactor")
            
            # Verify thread is started
            mock_thread.assert_called_once()
            mock_thread.return_value.start.assert_called_once()
    
    @patch('ollama_ai.UIHelpers')
    def test_run_without_selection(self, mock_ui):
        """Test run without text selection."""
        mock_ui.get_selected_text.return_value = ""
        
        self.command.run(Mock())
        
        mock_ui.show_status_message.assert_called_once_with("Ollama: No text selected.")
    
    @patch('ollama_ai.sublime.Phantom')
    def test_show_inline_suggestion(self, mock_phantom):
        """Test showing inline suggestion."""
        # Setup phantom set
        self.command.phantom_set = Mock()
        self.command.selection_region = Mock()
        
        # Mock phantom
        mock_phantom_instance = Mock()
        mock_phantom.return_value = mock_phantom_instance
        
        self.command.show_inline_suggestion("refactored code")
        
        # Verify suggestion is stored
        self.assertEqual(self.command.suggestion, "refactored code")
        
        # Verify phantom is created and updated
        mock_phantom.assert_called_once()
        self.command.phantom_set.update.assert_called_once_with([mock_phantom_instance])
    
    def test_on_phantom_navigate_approve(self):
        """Test phantom navigation with approve action."""
        self.command.suggestion = "refactored code"
        self.command.selection_region = Mock()
        self.command.selection_region.begin.return_value = 10
        self.command.selection_region.end.return_value = 20
        self.command.phantom_set = Mock()
        
        self.command.on_phantom_navigate("approve")
        
        # Verify replace text command is called
        self.command.view.run_command.assert_called_once_with(
            "ollama_replace_text",
            {
                "region_start": 10,
                "region_end": 20,
                "text": "refactored code"
            }
        )
        
        # Verify phantoms are cleared
        self.command.phantom_set.update.assert_called_once_with([])
    
    def test_on_phantom_navigate_dismiss(self):
        """Test phantom navigation with dismiss action."""
        self.command.phantom_set = Mock()
        
        self.command.on_phantom_navigate("dismiss")
        
        # Verify phantoms are cleared
        self.command.phantom_set.update.assert_called_once_with([])


class TestOllamaGenerateFeatureCommand(unittest.TestCase):
    """Test cases for OllamaGenerateFeatureCommand."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.command = OllamaGenerateFeatureCommand()
        self.command.window = Mock()
        
        # Mock API client
        self.mock_api_client = Mock()
    
    def test_run_shows_input_panel(self):
        """Test that run() shows input panel for feature description."""
        self.command.run()
        
        self.command.window.show_input_panel.assert_called_once_with(
            "Enter a description for the new feature:",
            "",
            self.command.on_done,
            None,
            None
        )
    
    @patch('ollama_ai.threading.Thread')
    def test_on_done_with_description(self, mock_thread):
        """Test on_done with valid description."""
        self.command.on_done("Test feature description")
        
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()
    
    def test_on_done_without_description(self):
        """Test on_done with empty description."""
        with patch('ollama_ai.threading.Thread') as mock_thread:
            self.command.on_done("")
            
            mock_thread.assert_not_called()
    
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
        
        # Mock view for status updates
        mock_view = Mock()
        self.command.window.active_view.return_value = mock_view
        
        self.command.generate_feature("Test feature")
        
        # Verify API call was made
        self.mock_api_client.make_blocking_request.assert_called_once()
        
        # Verify show_plan_for_approval is called
        mock_set_timeout.assert_called()
    
    def test_show_plan_for_approval(self):
        """Test showing plan for user approval."""
        files = [
            {"path": "app/Test.php", "description": "Test controller"},
            {"path": "tests/TestTest.php", "description": "Test file"}
        ]
        
        self.command.show_plan_for_approval(files)
        
        # Verify files are stored
        self.assertEqual(self.command.files_to_create, files)
        
        # Verify quick panel is shown
        expected_items = [
            "[✅ Approve and Create Files]",
            "[❌ Cancel]",
            "- app/Test.php",
            "- tests/TestTest.php"
        ]
        self.command.window.show_quick_panel.assert_called_once_with(
            expected_items,
            self.command.on_plan_selection
        )
    
    @patch('ollama_ai.threading.Thread')
    def test_on_plan_selection_approve(self, mock_thread):
        """Test plan selection with approve (index 0)."""
        self.command.on_plan_selection(0)
        
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()
    
    @patch('ollama_ai.sublime.status_message')
    def test_on_plan_selection_cancel(self, mock_status):
        """Test plan selection with cancel (index 1)."""
        self.command.on_plan_selection(1)
        
        mock_status.assert_called_once_with("Ollama: Feature generation cancelled.")
    
    @patch('ollama_ai.sublime.status_message')
    def test_on_plan_selection_escape(self, mock_status):
        """Test plan selection with escape (index -1)."""
        self.command.on_plan_selection(-1)
        
        mock_status.assert_called_once_with("Ollama: Feature generation cancelled.")


class TestOllamaReplaceTextCommand(unittest.TestCase):
    """Test cases for OllamaReplaceTextCommand."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.command = OllamaReplaceTextCommand()
        self.command.view = Mock()
    
    @patch('ollama_ai.sublime.Region')
    def test_run(self, mock_region):
        """Test replace text command."""
        mock_region_instance = Mock()
        mock_region.return_value = mock_region_instance
        
        edit = Mock()
        
        self.command.run(edit, 10, 20, "replacement text")
        
        # Verify region is created correctly
        mock_region.assert_called_once_with(10, 20)
        
        # Verify replace is called
        self.command.view.replace.assert_called_once_with(edit, mock_region_instance, "replacement text")


class TestSelectionPromptCommand(unittest.TestCase):
    """Test cases for OllamaSelectionPromptCommand."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.command = OllamaSelectionPromptCommand()
        self.command.view = Mock()
        
        # Mock window
        mock_window = Mock()
        self.command.view.window.return_value = mock_window
    
    @patch('ollama_ai.UIHelpers')
    def test_run_with_selection(self, mock_ui):
        """Test run with text selection."""
        mock_ui.get_selected_text.return_value = "selected code"
        
        self.command.run(Mock())
        
        # Verify selected text is stored
        self.assertEqual(self.command.selected_text, "selected code")
        
        # Verify input panel is shown
        mock_ui.show_input_panel.assert_called_once_with(
            self.command.view.window(),
            "Enter prompt for selected code:",
            "",
            self.command.on_done
        )
    
    @patch('ollama_ai.UIHelpers')
    def test_run_without_selection(self, mock_ui):
        """Test run without text selection."""
        mock_ui.get_selected_text.return_value = ""
        
        self.command.run(Mock())
        
        mock_ui.show_status_message.assert_called_once_with("Ollama: No text selected.")
        mock_ui.show_input_panel.assert_not_called()
    
    @patch('ollama_ai.UIHelpers')
    def test_has_selection_true(self, mock_ui):
        """Test is_visible when selection exists."""
        mock_ui.has_selection.return_value = True
        
        result = self.command.is_visible()
        
        self.assertTrue(result)
        mock_ui.has_selection.assert_called_once_with(self.command.view)
    
    @patch('ollama_ai.UIHelpers')
    def test_has_selection_false(self, mock_ui):
        """Test is_visible when no selection exists."""
        mock_ui.has_selection.return_value = False
        
        result = self.command.is_visible()
        
        self.assertFalse(result)


class TestCommandIntegrationScenarios(unittest.TestCase):
    """Test integration scenarios combining multiple components."""
    
    @patch('ollama_ai.sublime')
    @patch('ollama_ai.UIHelpers')
    @patch('ollama_ai.ContextAnalyzer')
    @patch('ollama_ai.ResponseProcessor')
    @patch('ollama_ai.create_api_client_from_settings')
    def test_explain_command_full_workflow(self, mock_create_api, mock_processor, mock_context, mock_ui, mock_sublime):
        """Test complete workflow for explain command."""
        # Setup command
        command = OllamaExplainSelectionCommand()
        command.view = Mock()
        
        # Mock selected text
        mock_ui.get_selected_text.return_value = "class TestController {}"
        
        # Mock API client
        mock_api_client = Mock()
        mock_api_client.model = "test-model"
        mock_api_client.make_streaming_request = Mock()
        mock_create_api.return_value = mock_api_client
        
        # Mock context analyzer
        mock_analyzer = Mock()
        mock_analyzer.analyze_text_for_context.return_value = ("TestController", " context info")
        mock_context.from_view.return_value = mock_analyzer
        
        # Mock tab manager
        with patch('ollama_ai.TabManager') as mock_tab_manager:
            mock_tab_mgr = Mock()
            mock_output_tab = Mock()
            mock_tab_mgr.create_output_tab.return_value = mock_output_tab
            mock_tab_manager.return_value = mock_tab_mgr
            
            # Mock settings
            with patch('ollama_ai.sublime.load_settings') as mock_settings:
                mock_settings_obj = Mock()
                mock_settings_obj.get.side_effect = lambda key, default: {
                    "tab_title": "Ollama {selection}",
                    "explain_prompt": "Explain: {code}"
                }.get(key, default)
                mock_settings.return_value = mock_settings_obj
                
                # Mock window
                command.view.window.return_value = Mock()
                
                # Run command
                command.run(Mock())
                
                # Verify the full workflow
                mock_ui.get_selected_text.assert_called_once_with(command.view)
                mock_analyzer.analyze_text_for_context.assert_called_once_with("class TestController {}")
                mock_tab_mgr.create_output_tab.assert_called_once()
                mock_sublime.set_timeout_async.assert_called_once()
    
    @patch('ollama_ai.sublime')
    @patch('ollama_ai.UIHelpers')
    @patch('ollama_ai.ContextAnalyzer')
    def test_create_file_command_workflow(self, mock_context, mock_ui, mock_sublime):
        """Test create file command workflow."""
        # Setup command
        command = OllamaCreateFileCommand()
        command.window = Mock()
        command.description = "Test controller"
        
        # Mock project folder
        mock_ui.ensure_project_folder.return_value = "/project/root"
        
        # Mock context analyzer
        mock_analyzer = Mock()
        mock_analyzer.analyze_text_for_context.return_value = ("Controller", " context")
        mock_context.from_view.return_value = mock_analyzer
        
        # Mock progress tab
        mock_progress_tab = Mock()
        mock_ui.create_progress_tab.return_value = mock_progress_tab
        
        with patch('ollama_ai.threading.Thread') as mock_thread:
            command.on_path("app/TestController.php")
            
            # Verify file path is set correctly
            self.assertEqual(command.file_path, "/project/root/app/TestController.php")
            
            # Verify progress tab creation
            mock_ui.create_progress_tab.assert_called_once()
            
            # Verify context analysis
            mock_analyzer.analyze_text_for_context.assert_called_once_with("Test controller")
            
            # Verify thread is started
            mock_thread.assert_called_once()


if __name__ == '__main__':
    print("🧪 Running Ollama AI Integration Tests...")
    print("=" * 50)
    
    # Run the tests
    unittest.main(verbosity=2, exit=False)
    
    print("\n" + "=" * 50)
    print("✅ Ollama AI integration tests completed!")