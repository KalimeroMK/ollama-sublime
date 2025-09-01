#!/usr/bin/env python3
"""
Unit tests for ui_helpers.py module.
Tests the UIHelpers class and TabManager class.
"""

import unittest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock, call
import sys

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock sublime module before importing
sys.modules['sublime'] = Mock()

from ui_helpers import UIHelpers, TabManager


class TestUIHelpers(unittest.TestCase):
    """Test cases for UIHelpers class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_window = Mock()
        self.mock_view = Mock()
        self.mock_tab = Mock()
        
        # Configure mock tab
        self.mock_tab.is_valid.return_value = True
        self.mock_window.new_file.return_value = self.mock_tab
    
    def test_create_output_tab_basic(self):
        """Test basic output tab creation."""
        result = UIHelpers.create_output_tab(self.mock_window, "Test Title")
        
        self.mock_window.new_file.assert_called_once()
        self.mock_tab.set_name.assert_called_once_with("Test Title")
        self.mock_tab.set_scratch.assert_called_once_with(True)
        self.assertEqual(result, self.mock_tab)
    
    def test_create_output_tab_with_content(self):
        """Test output tab creation with initial content."""
        UIHelpers.create_output_tab(self.mock_window, "Test Title", "Initial content")
        
        self.mock_tab.run_command.assert_called_once_with("append", {"characters": "Initial content"})
    
    def test_create_progress_tab(self):
        """Test progress tab creation."""
        result = UIHelpers.create_progress_tab(self.mock_window, "Progress", "Description text")
        
        self.mock_window.new_file.assert_called_once()
        self.mock_tab.set_name.assert_called_once_with("Progress")
        self.mock_tab.set_scratch.assert_called_once_with(True)
        self.mock_tab.run_command.assert_called_once_with("append", {"characters": "Description text\n"})
        self.assertEqual(result, self.mock_tab)
    
    def test_create_progress_tab_no_description(self):
        """Test progress tab creation without description."""
        UIHelpers.create_progress_tab(self.mock_window, "Progress")
        
        # Should not call append when no description
        self.mock_tab.run_command.assert_not_called()
    
    def test_append_to_tab_valid(self):
        """Test appending content to valid tab."""
        UIHelpers.append_to_tab(self.mock_tab, "test content")
        
        self.mock_tab.is_valid.assert_called_once()
        self.mock_tab.run_command.assert_called_once_with("append", {"characters": "test content"})
    
    def test_append_to_tab_invalid(self):
        """Test appending content to invalid tab."""
        self.mock_tab.is_valid.return_value = False
        
        UIHelpers.append_to_tab(self.mock_tab, "test content")
        
        self.mock_tab.is_valid.assert_called_once()
        self.mock_tab.run_command.assert_not_called()
    
    def test_append_to_tab_none(self):
        """Test appending content to None tab."""
        UIHelpers.append_to_tab(None, "test content")
        # Should not crash
    
    def test_get_selected_text_single_selection(self):
        """Test getting selected text with single selection."""
        mock_region = Mock()
        mock_region.empty.return_value = False
        self.mock_view.sel.return_value = [mock_region]
        self.mock_view.substr.return_value = "selected text"
        
        result = UIHelpers.get_selected_text(self.mock_view)
        
        self.assertEqual(result, "selected text")
        self.mock_view.substr.assert_called_once_with(mock_region)
    
    def test_get_selected_text_multiple_selections(self):
        """Test getting selected text with multiple selections."""
        mock_region1 = Mock()
        mock_region1.empty.return_value = False
        mock_region2 = Mock()
        mock_region2.empty.return_value = False
        
        self.mock_view.sel.return_value = [mock_region1, mock_region2]
        self.mock_view.substr.side_effect = ["first", "second"]
        
        result = UIHelpers.get_selected_text(self.mock_view)
        
        self.assertEqual(result, "firstsecond")
        self.assertEqual(self.mock_view.substr.call_count, 2)
    
    def test_get_selected_text_empty_selection(self):
        """Test getting selected text with empty selection."""
        mock_region = Mock()
        mock_region.empty.return_value = True
        self.mock_view.sel.return_value = [mock_region]
        
        result = UIHelpers.get_selected_text(self.mock_view)
        
        self.assertEqual(result, "")
        self.mock_view.substr.assert_not_called()
    
    def test_has_selection_true(self):
        """Test has_selection when view has selection."""
        mock_region = Mock()
        mock_region.empty.return_value = False
        self.mock_view.sel.return_value = [mock_region]
        
        result = UIHelpers.has_selection(self.mock_view)
        self.assertTrue(result)
    
    def test_has_selection_false(self):
        """Test has_selection when view has no selection."""
        mock_region = Mock()
        mock_region.empty.return_value = True
        self.mock_view.sel.return_value = [mock_region]
        
        result = UIHelpers.has_selection(self.mock_view)
        self.assertFalse(result)
    
    @patch('sublime.status_message')
    @patch('sublime.set_timeout')
    def test_show_status_message_with_timeout(self, mock_set_timeout, mock_status_message):
        """Test showing status message with timeout."""
        UIHelpers.show_status_message("Test message", 3000)
        
        mock_status_message.assert_called_once_with("Test message")
        mock_set_timeout.assert_called_once()
    
    @patch('sublime.status_message')
    @patch('sublime.set_timeout')
    def test_show_status_message_no_timeout(self, mock_set_timeout, mock_status_message):
        """Test showing status message without timeout."""
        UIHelpers.show_status_message("Test message", 0)
        
        mock_status_message.assert_called_once_with("Test message")
        mock_set_timeout.assert_not_called()
    
    @patch('sublime.error_message')
    def test_show_error_message(self, mock_error_message):
        """Test showing error message."""
        UIHelpers.show_error_message("Error message")
        mock_error_message.assert_called_once_with("Error message")
    
    @patch('sublime.message_dialog')
    def test_show_info_message(self, mock_message_dialog):
        """Test showing info message."""
        UIHelpers.show_info_message("Info message")
        mock_message_dialog.assert_called_once_with("Info message")
    
    def test_format_tab_title_short_selection(self):
        """Test formatting tab title with short selection."""
        template = "Ollama: {selection}"
        result = UIHelpers.format_tab_title(template, "short text", max_length=50)
        self.assertEqual(result, "Ollama: short text")
    
    def test_format_tab_title_long_selection(self):
        """Test formatting tab title with long selection."""
        template = "Ollama: {selection}"
        long_text = "a" * 100
        result = UIHelpers.format_tab_title(template, long_text, max_length=20)
        expected = "Ollama: " + "a" * 9 + "..."
        self.assertEqual(result, expected)
    
    def test_format_tab_title_empty_selection(self):
        """Test formatting tab title with empty selection."""
        template = "Ollama: {selection}"
        result = UIHelpers.format_tab_title(template, "", max_length=50)
        self.assertEqual(result, "Ollama: ")
    
    def test_ensure_project_folder_success(self):
        """Test ensuring project folder when folders exist."""
        self.mock_window.folders.return_value = ["/project/root", "/other/project"]
        
        result = UIHelpers.ensure_project_folder(self.mock_window)
        self.assertEqual(result, "/project/root")
    
    @patch.object(UIHelpers, 'show_error_message')
    def test_ensure_project_folder_no_folders(self, mock_show_error):
        """Test ensuring project folder when no folders exist."""
        self.mock_window.folders.return_value = []
        
        result = UIHelpers.ensure_project_folder(self.mock_window)
        
        self.assertIsNone(result)
        mock_show_error.assert_called_once_with("No project folders open. Please open a project first.")
    
    def test_create_file_safely_success(self):
        """Test successful file creation."""
        # Use temporary directory
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "test_file.txt")
        content = "Test content"
        
        try:
            result = UIHelpers.create_file_safely(file_path, content)
            
            self.assertTrue(result)
            self.assertTrue(os.path.exists(file_path))
            
            with open(file_path, 'r', encoding='utf-8') as f:
                self.assertEqual(f.read(), content)
        finally:
            import shutil
            shutil.rmtree(temp_dir)
    
    def test_create_file_safely_with_directories(self):
        """Test file creation with nested directories."""
        # Use temporary directory
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "nested", "dir", "test_file.txt")
        content = "Test content"
        
        try:
            result = UIHelpers.create_file_safely(file_path, content)
            
            self.assertTrue(result)
            self.assertTrue(os.path.exists(file_path))
            self.assertTrue(os.path.exists(os.path.dirname(file_path)))
        finally:
            import shutil
            shutil.rmtree(temp_dir)
    
    @patch.object(UIHelpers, 'show_error_message')
    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    def test_create_file_safely_permission_error(self, mock_open, mock_show_error):
        """Test file creation with permission error."""
        result = UIHelpers.create_file_safely("/invalid/path/file.txt", "content")
        
        self.assertFalse(result)
        mock_show_error.assert_called_once()
    
    @patch('sublime.set_timeout')
    def test_open_file_in_window_with_delay(self, mock_set_timeout):
        """Test opening file with delay."""
        UIHelpers.open_file_in_window(self.mock_window, "/path/to/file.txt", 1000)
        
        mock_set_timeout.assert_called_once()
        # Verify the timeout function would call window.open_file
        timeout_func = mock_set_timeout.call_args[0][0]
        timeout_func()
        self.mock_window.open_file.assert_called_once_with("/path/to/file.txt")
    
    def test_open_file_in_window_no_delay(self):
        """Test opening file without delay."""
        UIHelpers.open_file_in_window(self.mock_window, "/path/to/file.txt", 0)
        
        self.mock_window.open_file.assert_called_once_with("/path/to/file.txt")
    
    @patch('sublime.set_timeout')
    def test_close_tab_delayed_valid(self, mock_set_timeout):
        """Test closing valid tab with delay."""
        UIHelpers.close_tab_delayed(self.mock_tab, 1000)
        
        mock_set_timeout.assert_called_once_with(unittest.mock.ANY, 1000)
    
    def test_close_tab_delayed_none(self):
        """Test closing None tab."""
        # Should not crash
        UIHelpers.close_tab_delayed(None, 1000)
    
    def test_show_input_panel(self):
        """Test showing input panel."""
        on_done = Mock()
        on_change = Mock()
        on_cancel = Mock()
        
        UIHelpers.show_input_panel(
            self.mock_window, 
            "Test caption", 
            "initial text", 
            on_done, 
            on_change, 
            on_cancel
        )
        
        self.mock_window.show_input_panel.assert_called_once_with(
            "Test caption",
            "initial text", 
            on_done,
            on_change,
            on_cancel
        )
    
    def test_show_input_panel_minimal(self):
        """Test showing input panel with minimal parameters."""
        on_done = Mock()
        
        UIHelpers.show_input_panel(self.mock_window, "Caption", "text", on_done)
        
        self.mock_window.show_input_panel.assert_called_once_with(
            "Caption",
            "text",
            on_done,
            None,
            None
        )
    
    def test_get_project_relative_path_success(self):
        """Test getting relative path within project."""
        file_path = "/project/root/app/Controllers/UserController.php"
        project_root = "/project/root"
        
        result = UIHelpers.get_project_relative_path(file_path, project_root)
        self.assertEqual(result, "app/Controllers/UserController.php")
    
    def test_get_project_relative_path_outside_project(self):
        """Test getting relative path for file outside project."""
        file_path = "/other/location/file.php"
        project_root = "/project/root"
        
        result = UIHelpers.get_project_relative_path(file_path, project_root)
        self.assertEqual(result, file_path)  # Should return original path
    
    def test_get_project_relative_path_same_path(self):
        """Test getting relative path when file is project root."""
        project_root = "/project/root"
        
        result = UIHelpers.get_project_relative_path(project_root, project_root)
        self.assertEqual(result, ".")


class TestTabManager(unittest.TestCase):
    """Test cases for TabManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_window = Mock()
        self.mock_tab = Mock()
        self.mock_tab.is_valid.return_value = True
        
        # Mock UIHelpers.create_output_tab
        self.patcher = patch.object(UIHelpers, 'create_output_tab', return_value=self.mock_tab)
        self.mock_create_tab = self.patcher.start()
        
        self.tab_manager = TabManager(self.mock_window)
    
    def tearDown(self):
        """Clean up patches."""
        self.patcher.stop()
    
    def test_init(self):
        """Test TabManager initialization."""
        self.assertEqual(self.tab_manager.window, self.mock_window)
        self.assertEqual(self.tab_manager.tabs, {})
    
    def test_create_output_tab_basic(self):
        """Test creating output tab without extra content."""
        result = self.tab_manager.create_output_tab("test_key", "Test Title")
        
        self.mock_create_tab.assert_called_once_with(self.mock_window, "Test Title")
        self.assertEqual(self.tab_manager.tabs["test_key"], self.mock_tab)
        self.assertEqual(result, self.mock_tab)
    
    @patch.object(UIHelpers, 'append_to_tab')
    def test_create_output_tab_with_prompt_and_model(self, mock_append):
        """Test creating output tab with prompt and model information."""
        result = self.tab_manager.create_output_tab(
            "test_key", 
            "Test Title", 
            "Test prompt", 
            "test-model"
        )
        
        # Should append header with prompt and model info
        expected_header = "Prompt: Test prompt\nModel: test-model\n\n---\n\n"
        mock_append.assert_called_once_with(self.mock_tab, expected_header)
        self.assertEqual(result, self.mock_tab)
    
    @patch.object(UIHelpers, 'append_to_tab')
    def test_create_output_tab_with_prompt_only(self, mock_append):
        """Test creating output tab with prompt only."""
        self.tab_manager.create_output_tab("test_key", "Test Title", "Test prompt", "")
        
        expected_header = "Prompt: Test prompt\n\n---\n\n"
        mock_append.assert_called_once_with(self.mock_tab, expected_header)
    
    @patch.object(UIHelpers, 'append_to_tab')
    def test_create_output_tab_with_model_only(self, mock_append):
        """Test creating output tab with model only."""
        self.tab_manager.create_output_tab("test_key", "Test Title", "", "test-model")
        
        expected_header = "Model: test-model\n\n---\n\n"
        mock_append.assert_called_once_with(self.mock_tab, expected_header)
    
    def test_get_tab_existing(self):
        """Test getting existing tab."""
        self.tab_manager.tabs["test_key"] = self.mock_tab
        
        result = self.tab_manager.get_tab("test_key")
        self.assertEqual(result, self.mock_tab)
    
    def test_get_tab_non_existing(self):
        """Test getting non-existing tab."""
        result = self.tab_manager.get_tab("non_existing")
        self.assertIsNone(result)
    
    @patch.object(UIHelpers, 'append_to_tab')
    def test_append_to_tab_existing(self, mock_append):
        """Test appending to existing tab."""
        self.tab_manager.tabs["test_key"] = self.mock_tab
        
        self.tab_manager.append_to_tab("test_key", "test content")
        
        mock_append.assert_called_once_with(self.mock_tab, "test content")
    
    @patch.object(UIHelpers, 'append_to_tab')
    def test_append_to_tab_non_existing(self, mock_append):
        """Test appending to non-existing tab."""
        self.tab_manager.append_to_tab("non_existing", "test content")
        
        mock_append.assert_not_called()
    
    def test_close_tab_no_delay(self):
        """Test closing tab without delay."""
        self.tab_manager.tabs["test_key"] = self.mock_tab
        
        self.tab_manager.close_tab("test_key", delay=0)
        
        self.assertNotIn("test_key", self.tab_manager.tabs)
        self.mock_tab.close.assert_called_once()
    
    @patch.object(UIHelpers, 'close_tab_delayed')
    def test_close_tab_with_delay(self, mock_close_delayed):
        """Test closing tab with delay."""
        self.tab_manager.tabs["test_key"] = self.mock_tab
        
        self.tab_manager.close_tab("test_key", delay=1000)
        
        self.assertNotIn("test_key", self.tab_manager.tabs)
        mock_close_delayed.assert_called_once_with(self.mock_tab, 1000)
    
    def test_close_tab_non_existing(self):
        """Test closing non-existing tab."""
        # Should not crash
        self.tab_manager.close_tab("non_existing")
    
    def test_close_tab_invalid_tab(self):
        """Test closing invalid tab."""
        invalid_tab = Mock()
        invalid_tab.is_valid.return_value = False
        self.tab_manager.tabs["test_key"] = invalid_tab
        
        self.tab_manager.close_tab("test_key", delay=0)
        
        self.assertNotIn("test_key", self.tab_manager.tabs)
        # Should not call close on invalid tab
        invalid_tab.close.assert_not_called()
    
    def test_cleanup(self):
        """Test cleaning up all tabs."""
        # Add multiple tabs
        tab1 = Mock()
        tab1.is_valid.return_value = True
        tab2 = Mock() 
        tab2.is_valid.return_value = True
        
        self.tab_manager.tabs["key1"] = tab1
        self.tab_manager.tabs["key2"] = tab2
        
        self.tab_manager.cleanup()
        
        # All tabs should be removed
        self.assertEqual(self.tab_manager.tabs, {})
        tab1.close.assert_called_once()
        tab2.close.assert_called_once()


class TestFileOperationsIntegration(unittest.TestCase):
    """Integration tests for file operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_create_file_safely_real_filesystem(self):
        """Test file creation on real filesystem."""
        file_path = os.path.join(self.temp_dir, "real_test.txt")
        content = "Real file content\nwith multiple lines"
        
        result = UIHelpers.create_file_safely(file_path, content)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(file_path))
        
        with open(file_path, 'r', encoding='utf-8') as f:
            self.assertEqual(f.read(), content)
    
    def test_create_nested_directories(self):
        """Test creating file with nested directory structure."""
        file_path = os.path.join(self.temp_dir, "level1", "level2", "level3", "deep_file.txt")
        content = "Deep nested file"
        
        result = UIHelpers.create_file_safely(file_path, content)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(file_path))
        self.assertTrue(os.path.exists(os.path.dirname(file_path)))


if __name__ == '__main__':
    print("🧪 Running UI Helpers Tests...")
    print("=" * 50)
    
    # Run the tests
    unittest.main(verbosity=2, exit=False)
    
    print("\n" + "=" * 50)
    print("✅ UI Helpers tests completed!")