#!/usr/bin/env python3
"""
Unit tests for context_analyzer.py module.
Tests the ContextAnalyzer class and its methods.
"""

import unittest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
import sys

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock sublime module before importing
sys.modules['sublime'] = Mock()

from context_analyzer import ContextAnalyzer, extract_symbol_from_text, get_project_context_for_symbol


class TestContextAnalyzer(unittest.TestCase):
    """Test cases for ContextAnalyzer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = ContextAnalyzer(
            project_root="/test/project",
            code_file_extensions=[".php", ".js", ".py"]
        )
        
        # Create temporary directory for file tests
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_init_default(self):
        """Test initialization with default parameters."""
        analyzer = ContextAnalyzer()
        self.assertIsNone(analyzer.project_root)
        self.assertEqual(analyzer.code_file_extensions, [".php", ".js", ".py"])
    
    def test_init_custom(self):
        """Test initialization with custom parameters."""
        self.assertEqual(self.analyzer.project_root, "/test/project")
        self.assertEqual(self.analyzer.code_file_extensions, [".php", ".js", ".py"])
    
    @patch('sublime.load_settings')
    def test_from_view_with_view(self, mock_load_settings):
        """Test creating analyzer from view with project folder."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.get.return_value = [".php", ".blade.php", ".js"]
        mock_load_settings.return_value = mock_settings
        
        # Mock view and window
        mock_view = Mock()
        mock_window = Mock()
        mock_window.folders.return_value = ["/project/root"]
        mock_view.window.return_value = mock_window
        
        analyzer = ContextAnalyzer.from_view(mock_view)
        
        self.assertEqual(analyzer.project_root, "/project/root")
        self.assertEqual(analyzer.code_file_extensions, [".php", ".blade.php", ".js"])
    
    @patch('sublime.load_settings')
    def test_from_view_no_folders(self, mock_load_settings):
        """Test creating analyzer from view without project folders."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.get.return_value = [".php", ".js"]
        mock_load_settings.return_value = mock_settings
        
        # Mock view and window with no folders
        mock_view = Mock()
        mock_window = Mock()
        mock_window.folders.return_value = []
        mock_view.window.return_value = mock_window
        
        analyzer = ContextAnalyzer.from_view(mock_view)
        
        self.assertIsNone(analyzer.project_root)
        self.assertEqual(analyzer.code_file_extensions, [".php", ".js"])
    
    def test_from_view_none(self):
        """Test creating analyzer from None view."""
        analyzer = ContextAnalyzer.from_view(None)
        self.assertIsNone(analyzer.project_root)
        self.assertEqual(analyzer.code_file_extensions, [".php", ".js", ".py"])
    
    def test_extract_symbol_from_text_class(self):
        """Test extracting class symbol from text."""
        text = "class UserController extends Controller {"
        symbol = self.analyzer.extract_symbol_from_text(text)
        self.assertEqual(symbol, "UserController")
    
    def test_extract_symbol_from_text_function(self):
        """Test extracting function symbol from text."""
        text = "function calculateTotal($items) {"
        symbol = self.analyzer.extract_symbol_from_text(text)
        self.assertEqual(symbol, "calculateTotal")
    
    def test_extract_symbol_from_text_interface(self):
        """Test extracting interface symbol from text."""
        text = "interface PaymentProcessor {"
        symbol = self.analyzer.extract_symbol_from_text(text)
        self.assertEqual(symbol, "PaymentProcessor")
    
    def test_extract_symbol_from_text_trait(self):
        """Test extracting trait symbol from text."""
        text = "trait Cacheable {"
        symbol = self.analyzer.extract_symbol_from_text(text)
        self.assertEqual(symbol, "Cacheable")
    
    def test_extract_symbol_from_text_capitalized_word(self):
        """Test extracting capitalized word as symbol."""
        text = "new UserModel() instance"
        symbol = self.analyzer.extract_symbol_from_text(text)
        self.assertEqual(symbol, "UserModel")
    
    def test_extract_symbol_from_text_empty(self):
        """Test extracting symbol from empty text."""
        symbol = self.analyzer.extract_symbol_from_text("")
        self.assertIsNone(symbol)
    
    def test_extract_symbol_from_text_none(self):
        """Test extracting symbol from None."""
        symbol = self.analyzer.extract_symbol_from_text(None)
        self.assertIsNone(symbol)
    
    def test_extract_symbol_from_text_no_match(self):
        """Test extracting symbol when no pattern matches."""
        text = "some lowercase text with no symbols"
        symbol = self.analyzer.extract_symbol_from_text(text)
        self.assertIsNone(symbol)
    
    def test_find_symbol_usages_no_symbol(self):
        """Test finding usages when no symbol provided."""
        result = self.analyzer.find_symbol_usages(None)
        self.assertEqual(result, "")
        
        result = self.analyzer.find_symbol_usages("")
        self.assertEqual(result, "")
    
    def test_find_symbol_usages_no_project_root(self):
        """Test finding usages when no project root."""
        analyzer = ContextAnalyzer(project_root=None)
        result = analyzer.find_symbol_usages("TestSymbol")
        self.assertEqual(result, "")
    
    def test_find_symbol_usages_with_files(self):
        """Test finding symbol usages across project files."""
        # Create test files in temp directory
        test_file1 = os.path.join(self.temp_dir, "test1.php")
        test_file2 = os.path.join(self.temp_dir, "test2.js")
        test_file3 = os.path.join(self.temp_dir, "test3.txt")  # Should be ignored
        
        with open(test_file1, 'w', encoding='utf-8') as f:
            f.write("<?php\nclass UserController {\n    public function index() {\n        return view('users');\n    }\n}\n")
        
        with open(test_file2, 'w', encoding='utf-8') as f:
            f.write("// JavaScript file\nconst UserController = require('./UserController');\nUserController.init();\n")
        
        with open(test_file3, 'w', encoding='utf-8') as f:
            f.write("This file should be ignored due to extension")
        
        # Create analyzer with temp directory
        analyzer = ContextAnalyzer(
            project_root=self.temp_dir,
            code_file_extensions=[".php", ".js"]
        )
        
        result = analyzer.find_symbol_usages("UserController")
        
        # Verify the result contains expected information
        self.assertIn("UserController", result)
        self.assertIn("test1.php", result)
        self.assertIn("test2.js", result)
        self.assertNotIn("test3.txt", result)
        self.assertIn("class UserController", result)
        self.assertIn("const UserController", result)
    
    def test_find_symbol_usages_no_matches(self):
        """Test finding usages when symbol doesn't exist in project."""
        # Create test file without the symbol
        test_file = os.path.join(self.temp_dir, "test.php")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("<?php\nclass SomeOtherClass {\n}\n")
        
        analyzer = ContextAnalyzer(
            project_root=self.temp_dir,
            code_file_extensions=[".php"]
        )
        
        result = analyzer.find_symbol_usages("NonExistentSymbol")
        self.assertEqual(result, "")
    
    def test_get_project_context_for_symbol(self):
        """Test getting project context for symbol."""
        with patch.object(self.analyzer, 'find_symbol_usages', return_value="test context"):
            result = self.analyzer.get_project_context_for_symbol("TestSymbol")
            self.assertEqual(result, "test context")
    
    def test_get_project_context_for_symbol_empty(self):
        """Test getting project context for empty symbol."""
        result = self.analyzer.get_project_context_for_symbol("")
        self.assertEqual(result, "")
        
        result = self.analyzer.get_project_context_for_symbol(None)
        self.assertEqual(result, "")
    
    def test_analyze_text_for_context(self):
        """Test analyzing text for context."""
        with patch.object(self.analyzer, 'extract_symbol_from_text', return_value="TestClass"):
            with patch.object(self.analyzer, 'get_project_context_for_symbol', return_value="context info"):
                symbol, context = self.analyzer.analyze_text_for_context("class TestClass {}")
                self.assertEqual(symbol, "TestClass")
                self.assertEqual(context, "context info")
    
    def test_analyze_text_for_context_no_symbol(self):
        """Test analyzing text when no symbol found."""
        with patch.object(self.analyzer, 'extract_symbol_from_text', return_value=None):
            with patch.object(self.analyzer, 'get_project_context_for_symbol', return_value=""):
                symbol, context = self.analyzer.analyze_text_for_context("some random text")
                self.assertIsNone(symbol)
                self.assertEqual(context, "")


class TestLegacyFunctions(unittest.TestCase):
    """Test cases for legacy helper functions."""
    
    def test_extract_symbol_from_text_function(self):
        """Test legacy extract_symbol_from_text function."""
        result = extract_symbol_from_text("function testFunction() {}")
        self.assertEqual(result, "testFunction")
    
    def test_extract_symbol_from_text_class(self):
        """Test legacy extract_symbol_from_text function with class."""
        result = extract_symbol_from_text("class TestClass {}")
        self.assertEqual(result, "TestClass")
    
    def test_extract_symbol_from_text_empty(self):
        """Test legacy extract_symbol_from_text function with empty input."""
        result = extract_symbol_from_text("")
        self.assertIsNone(result)
    
    @patch('context_analyzer.ContextAnalyzer.from_view')
    def test_get_project_context_for_symbol_function(self, mock_from_view):
        """Test legacy get_project_context_for_symbol function."""
        # Mock analyzer and its method
        mock_analyzer = Mock()
        mock_analyzer.get_project_context_for_symbol.return_value = "test context"
        mock_from_view.return_value = mock_analyzer
        
        # Mock view
        mock_view = Mock()
        
        result = get_project_context_for_symbol(mock_view, "TestSymbol")
        
        self.assertEqual(result, "test context")
        mock_from_view.assert_called_once_with(mock_view)
        mock_analyzer.get_project_context_for_symbol.assert_called_once_with("TestSymbol")


class TestContextAnalyzerFileOperations(unittest.TestCase):
    """Test cases for file operations in ContextAnalyzer."""
    
    def setUp(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.analyzer = ContextAnalyzer(
            project_root=self.temp_dir,
            code_file_extensions=[".php", ".py", ".js"]
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_find_symbol_usages_multiple_occurrences(self):
        """Test finding symbol with multiple occurrences in same file."""
        # Create test file with multiple symbol occurrences
        test_file = os.path.join(self.temp_dir, "multi_usage.php")
        content = """<?php
class UserController {
    public function index() {
        $user = new UserController();
        return UserController::getUsers();
    }
}
UserController::staticMethod();
"""
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        result = self.analyzer.find_symbol_usages("UserController")
        
        # Should find multiple occurrences
        self.assertIn("UserController", result)
        self.assertIn("multi_usage.php", result)
        # Should show line numbers for different occurrences
        self.assertIn("line 2", result)  # class declaration
        self.assertIn("line 4", result)  # new instance
        self.assertIn("line 5", result)  # static call
        self.assertIn("line 8", result)  # another static call
    
    def test_find_symbol_usages_context_lines(self):
        """Test that context lines are included around matches."""
        # Create test file with symbol usage
        test_file = os.path.join(self.temp_dir, "context_test.py")
        content = """# This is a test file
# Some context before
def test_function():
    result = SomeClass.method()
    return result
# Some context after
# End of file
"""
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        result = self.analyzer.find_symbol_usages("SomeClass")
        
        # Should include context lines (2 before, 2 after)
        self.assertIn("Some context before", result)
        self.assertIn("Some context after", result)
        self.assertIn("SomeClass.method()", result)
    
    def test_find_symbol_usages_max_files_limit(self):
        """Test that file search respects max_files limit."""
        # Create more than 10 files (the max limit)
        for i in range(15):
            test_file = os.path.join(self.temp_dir, f"file_{i}.php")
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(f"<?php\nclass TestClass{i} {{\n    public $property = 'TestSymbol';\n}}\n")
        
        result = self.analyzer.find_symbol_usages("TestSymbol")
        
        # Should find the symbol but respect the 10 file limit
        self.assertIn("TestSymbol", result)
        # Count occurrences of "File:" to verify max 10 files were processed
        file_count = result.count("--- File:")
        self.assertLessEqual(file_count, 10)
    
    def test_find_symbol_usages_file_encoding_error(self):
        """Test handling of files with encoding issues."""
        # Create a file with binary content that can't be read as UTF-8
        test_file = os.path.join(self.temp_dir, "binary.php")
        with open(test_file, 'wb') as f:
            f.write(b'\x80\x81\x82\x83')  # Invalid UTF-8 bytes
        
        # Should not crash and should continue processing
        result = self.analyzer.find_symbol_usages("TestSymbol")
        self.assertEqual(result, "")  # No valid files found
    
    def test_find_symbol_usages_word_boundary(self):
        """Test that symbol matching respects word boundaries."""
        # Create test file with partial matches that shouldn't count
        test_file = os.path.join(self.temp_dir, "boundary_test.php")
        content = """<?php
class UserController {
    private $userControllerInstance;  // Should match
    private $superUserController;     // Should match
    private $userControllerData;      // Should match
    private $notUserControllerish;    // Should NOT match
}
"""
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        result = self.analyzer.find_symbol_usages("UserController")
        
        # Should find legitimate matches
        self.assertIn("userControllerInstance", result)
        self.assertIn("superUserController", result)
        self.assertIn("userControllerData", result)
        # Should NOT find partial matches
        self.assertNotIn("notUserControllerish", result)


class TestLegacyFunctionIntegration(unittest.TestCase):
    """Integration tests for legacy functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('sublime.load_settings')
    def test_get_project_context_integration(self, mock_load_settings):
        """Test full integration of get_project_context_for_symbol."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.get.return_value = [".php"]
        mock_load_settings.return_value = mock_settings
        
        # Create test file
        test_file = os.path.join(self.temp_dir, "integration_test.php")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("<?php\nclass TestClass {\n    public function method() {}\n}\n")
        
        # Mock view and window
        mock_view = Mock()
        mock_window = Mock()
        mock_window.folders.return_value = [self.temp_dir]
        mock_view.window.return_value = mock_window
        
        result = get_project_context_for_symbol(mock_view, "TestClass")
        
        self.assertIn("TestClass", result)
        self.assertIn("integration_test.php", result)


if __name__ == '__main__':
    print("🧪 Running Context Analyzer Tests...")
    print("=" * 50)
    
    # Run the tests
    unittest.main(verbosity=2, exit=False)
    
    print("\n" + "=" * 50)
    print("✅ Context Analyzer tests completed!")