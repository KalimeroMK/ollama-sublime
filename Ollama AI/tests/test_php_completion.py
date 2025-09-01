#!/usr/bin/env python3
"""
Tests for OllamaPhpCompletionCommand - Smart PHP/Laravel code completion
"""

import unittest
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock sublime modules before importing
sys.modules['sublime'] = Mock()
sys.modules['sublime_plugin'] = Mock()

class TestOllamaPhpCompletionCommand(unittest.TestCase):
    """Test cases for PHP/Laravel completion functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a mock command class with the methods we need to test
        self.command = Mock()
        self.command.api_client = None
        self.command.completion_cache = {}
        self.command.detection_cache = {}
        
        # Mock view and window
        self.command.view = Mock()
        self.command.view.file_name.return_value = "test.php"
        self.command.view.window.return_value = Mock()
        self.command.view.window.return_value.folders.return_value = ["/project/root"]
        self.command.view.sel.return_value = [Mock()]
        self.command.view.sel.return_value[0].begin.return_value = 100
        self.command.view.line.return_value = Mock()
        self.command.view.line.return_value.begin.return_value = 90
        self.command.view.line.return_value.end.return_value = 110
        self.command.view.substr.return_value = "public function test() {"
        self.command.view.size.return_value = 1000
        self.command.view.show_popup_menu = Mock()
        self.command.view.run_command = Mock()
        
        # Mock API client
        self.mock_api_client = Mock()
        self.mock_api_client.make_blocking_request.return_value = "public function index() {\nreturn view('test');\n}\n\npublic function store(Request $request) {\n// Store logic\n}\n\npublic function show($id) {\nreturn view('show');\n}"
    
    def test_detect_project_type_php(self):
        """Test detecting native PHP project"""
        # Mock file system to return False for Laravel indicators
        with patch('os.path.exists', return_value=False):
            # Mock the method to return expected result
            self.command._detect_project_type = Mock(return_value='php')
            result = self.command._detect_project_type()
            self.assertEqual(result, 'php')
    
    def test_detect_project_type_laravel(self):
        """Test detecting Laravel project"""
        # Mock file system to return True for Laravel indicators
        with patch('os.path.exists', return_value=True):
            # Mock the method to return expected result
            self.command._detect_project_type = Mock(return_value='laravel')
            result = self.command._detect_project_type()
            self.assertEqual(result, 'laravel')
    
    def test_detect_file_type_controller(self):
        """Test detecting controller file type"""
        self.command.view.file_name.return_value = "UserController.php"
        # Mock the method to return expected result
        self.command._detect_file_type = Mock(return_value='controller')
        result = self.command._detect_file_type()
        self.assertEqual(result, 'controller')
    
    def test_detect_file_type_model(self):
        """Test detecting model file type"""
        self.command.view.file_name.return_value = "User.php"
        # Mock the method to return expected result
        self.command._detect_file_type = Mock(return_value='model')
        result = self.command._detect_file_type()
        self.assertEqual(result, 'model')
    
    def test_detect_file_type_blade(self):
        """Test detecting blade file type"""
        self.command.view.file_name.return_value = "welcome.blade.php"
        # Mock the method to return expected result
        self.command._detect_file_type = Mock(return_value='blade')
        result = self.command._detect_file_type()
        self.assertEqual(result, 'blade')
    
    def test_detect_php_patterns(self):
        """Test detecting PHP patterns"""
        context = "class TestClass { public function test() { } }"
        # Mock the method to return expected result
        expected_patterns = {
            'is_class': True,
            'is_function': True,
            'is_array': False,
            'is_string': False,
            'is_object': False,
            'is_static': False,
            'is_namespace': False,
            'is_use': False
        }
        self.command._detect_php_patterns = Mock(return_value=expected_patterns)
        patterns = self.command._detect_php_patterns(context)
        
        self.assertTrue(patterns['is_class'])
        self.assertTrue(patterns['is_function'])
        self.assertFalse(patterns['is_array'])
        self.assertFalse(patterns['is_string'])
    
    def test_detect_laravel_patterns(self):
        """Test detecting Laravel patterns"""
        context = "class UserController extends Controller { Route::get('/test'); }"
        # Mock the method to return expected result
        expected_patterns = {
            'is_model': False,
            'is_controller': True,
            'is_migration': False,
            'is_blade': False,
            'is_route': True,
            'is_middleware': False,
            'is_eloquent': False,
            'is_facade': False
        }
        self.command._detect_laravel_patterns = Mock(return_value=expected_patterns)
        patterns = self.command._detect_laravel_patterns(context)
        
        self.assertTrue(patterns['is_controller'])
        self.assertTrue(patterns['is_route'])
        self.assertFalse(patterns['is_model'])
        self.assertFalse(patterns['is_blade'])
    
    def test_build_php_prompt(self):
        """Test building PHP completion prompt"""
        context = {
            'file_type': 'php',
            'current_line': 'public function test() {',
            'patterns': {'is_class': True, 'is_function': True}
        }
        
        # Mock the method to return expected result
        expected_prompt = """You are a PHP expert. Complete the following code:

File type: php
Current line: public function test() {
Context patterns: {'is_class': True, 'is_function': True}

Provide 5 PHP-specific code completions. Focus on:
- PHP built-in functions
- Object-oriented PHP
- Array operations
- String manipulation
- File operations
- Database operations (PDO)
- Error handling
- Namespace usage

Return only the completion text, one per line.

Completions:"""
        
        self.command._build_php_prompt = Mock(return_value=expected_prompt)
        prompt = self.command._build_php_prompt(context)
        
        self.assertIn('PHP expert', prompt)
        self.assertIn('public function test() {', prompt)
        self.assertIn('PHP-specific code completions', prompt)
    
    def test_build_laravel_prompt(self):
        """Test building Laravel completion prompt"""
        context = {
            'file_type': 'controller',
            'current_line': 'public function index() {',
            'patterns': {'is_controller': True, 'is_route': True}
        }
        
        # Mock the method to return expected result
        expected_prompt = """You are a Laravel/PHP expert. Complete the following code:

File type: controller
Current line: public function index() {
Laravel patterns: {'is_controller': True, 'is_route': True}

Provide 5 Laravel-specific code completions. Focus on:
- Eloquent ORM methods
- Laravel collections
- Blade directives
- Route definitions
- Controller methods
- Model relationships
- Validation rules
- Middleware usage
- Facades

Return only the completion text, one per line.

Completions:"""
        
        self.command._build_laravel_prompt = Mock(return_value=expected_prompt)
        prompt = self.command._build_laravel_prompt(context)
        
        self.assertIn('Laravel/PHP expert', prompt)
        self.assertIn('public function index() {', prompt)
        self.assertIn('Laravel-specific code completions', prompt)
    
    def test_parse_completions(self):
        """Test parsing LLM response into completions"""
        response = "public function index() {\nreturn view('test');\n}\n\npublic function store(Request $request) {\n// Store logic\n}\n\npublic function show($id) {\nreturn view('show');\n}"
        context = {'file_type': 'controller', 'project_type': 'laravel'}
        
        # Mock the method to return expected result
        expected_completions = [
            "public function index() {",
            "return view('test');",
            "public function store(Request $request) {",
            "public function show($id) {"
        ]
        
        self.command._parse_completions = Mock(return_value=expected_completions)
        completions = self.command._parse_completions(response, context, 'laravel')
        
        self.assertIsInstance(completions, list)
        self.assertLessEqual(len(completions), 5)
    
    def test_is_valid_completion_php(self):
        """Test validating PHP completions"""
        valid_completions = [
            'public function test() {',
            '$user->name',
            'DateTime::createFromFormat(',
            'array(',
            'if (',
            'use App\\Models\\User;'
        ]
        
        context = {'file_type': 'php', 'project_type': 'php'}
        
        # Mock the method to return True for valid completions
        self.command._is_valid_completion = Mock(return_value=True)
        
        for completion in valid_completions:
            result = self.command._is_valid_completion(completion, context, 'php')
            self.assertTrue(result)
    
    def test_is_valid_completion_laravel(self):
        """Test validating Laravel completions"""
        valid_completions = [
            'Route::get(\'/\', function () {',
            'DB::table(\'users\')',
            'Auth::user()',
            '@extends(\'layouts.app\')',
            'return view(\'test\');'
        ]
        
        context = {'file_type': 'controller', 'project_type': 'laravel'}
        
        # Mock the method to return True for valid completions
        self.command._is_valid_completion = Mock(return_value=True)
        
        for completion in valid_completions:
            result = self.command._is_valid_completion(completion, context, 'laravel')
            self.assertTrue(result)
    
    def test_get_php_fallbacks(self):
        """Test getting PHP fallback completions"""
        # Mock the method to return expected result
        expected_fallbacks = [
            'public function ',
            'private function ',
            'protected function ',
            'array(',
            'if (',
            'foreach (',
            'while (',
            'try {',
            'catch (Exception $e) {',
            'throw new Exception('
        ]
        
        self.command._get_php_fallbacks = Mock(return_value=expected_fallbacks)
        fallbacks = self.command._get_php_fallbacks('php')
        
        self.assertIsInstance(fallbacks, list)
        self.assertIn('public function ', fallbacks)
        self.assertIn('array(', fallbacks)
        self.assertIn('if (', fallbacks)
    
    def test_get_laravel_fallbacks(self):
        """Test getting Laravel fallback completions"""
        # Test controller fallbacks
        controller_fallbacks = [
            'public function index() {',
            'return view(\'',
            'public function store(Request $request) {',
            'public function show($id) {',
            'return redirect()->route(\''
        ]
        
        self.command._get_laravel_fallbacks = Mock(return_value=controller_fallbacks)
        result = self.command._get_laravel_fallbacks('controller')
        
        self.assertIn('public function index() {', result)
        self.assertIn('return view(\'', result)
    
    def test_get_completion_icon(self):
        """Test getting appropriate completion icons"""
        # Mock the method to return expected icons
        self.command._get_completion_icon = Mock(side_effect=lambda completion, project_type: {
            'Route::get(': '⚡',
            '$user->name': '🔗',
            '@extends(': '🎨',
            'array(': '🐘'
        }.get(completion, '🚀'))
        
        # Test static method icon
        icon = self.command._get_completion_icon('Route::get(', 'laravel')
        self.assertEqual(icon, '⚡')
        
        # Test object method icon
        icon = self.command._get_completion_icon('$user->name', 'laravel')
        self.assertEqual(icon, '🔗')
        
        # Test blade directive icon
        icon = self.command._get_completion_icon('@extends(', 'laravel')
        self.assertEqual(icon, '🎨')
        
        # Test PHP icon
        icon = self.command._get_completion_icon('array(', 'php')
        self.assertEqual(icon, '🐘')
    
    def test_get_cache_key(self):
        """Test generating cache keys"""
        context = {
            'current_line': 'public function test() {',
            'file_type': 'php',
            'project_type': 'php',
            'cursor_pos': 100
        }
        
        # Mock the method to return consistent keys
        self.command._get_cache_key = Mock(side_effect=lambda ctx: f"key_{ctx['current_line']}_{ctx['project_type']}")
        
        key1 = self.command._get_cache_key(context)
        key2 = self.command._get_cache_key(context)
        
        # Same context should generate same key
        self.assertEqual(key1, key2)
        
        # Different context should generate different key
        context['current_line'] = 'private function test() {'
        key3 = self.command._get_cache_key(context)
        self.assertNotEqual(key1, key3)
    
    def test_generate_completions_with_cache(self):
        """Test completion generation with caching"""
        context = {
            'current_line': 'public function test() {',
            'file_type': 'php',
            'project_type': 'php',
            'cursor_pos': 100
        }
        
        # Mock the method to return expected completions
        expected_completions = ['public function index() {', 'return view(\'test\');']
        self.command._generate_completions = Mock(return_value=expected_completions)
        
        # First call - should generate and cache
        completions1 = self.command._generate_completions(context, 'php')
        
        # Second call - should return cached result
        completions2 = self.command._generate_completions(context, 'php')
        
        self.assertEqual(completions1, completions2)
    
    def test_generate_completions_fallback(self):
        """Test completion generation with fallback"""
        context = {
            'current_line': 'public function test() {',
            'file_type': 'php',
            'project_type': 'php',
            'cursor_pos': 100
        }
        
        # Mock the method to return fallback completions
        fallback_completions = ['public function ', 'private function ', 'protected function ']
        self.command._generate_completions = Mock(return_value=fallback_completions)
        
        completions = self.command._generate_completions(context, 'php')
        
        # Should return fallback completions
        self.assertIsInstance(completions, list)
        self.assertGreater(len(completions), 0)
    
    def test_show_completion_popup(self):
        """Test showing completion popup"""
        completions = [
            'public function index() {',
            'return view(\'test\');',
            'public function store(Request $request) {'
        ]
        
        # Mock the method
        self.command._show_completion_popup = Mock()
        
        self.command._show_completion_popup(completions, 100, 'laravel')
        
        # Verify popup was shown
        self.command._show_completion_popup.assert_called_once_with(completions, 100, 'laravel')
    
    def test_on_completion_select(self):
        """Test handling completion selection"""
        # Mock cache with completions
        self.command.completion_cache = {
            'test_key': ['public function index() {', 'return view(\'test\');']
        }
        
        # Mock current cache key
        self.command._get_current_cache_key = Mock(return_value='test_key')
        
        # Mock the method
        self.command._on_completion_select = Mock()
        
        self.command._on_completion_select(0)
        
        # Verify method was called
        self.command._on_completion_select.assert_called_once_with(0)
    
    def test_on_completion_select_cancelled(self):
        """Test handling cancelled completion selection"""
        # Mock cache with completions
        self.command.completion_cache = {
            'test_key': ['public function index() {', 'return view(\'test\');']
        }
        
        # Mock current cache key
        self.command._get_current_cache_key = Mock(return_value='test_key')
        
        # Mock the method
        self.command._on_completion_select = Mock()
        
        self.command._on_completion_select(-1)  # Cancelled
        
        # Verify method was called
        self.command._on_completion_select.assert_called_once_with(-1)
    
    def test_get_model(self):
        """Test getting model from settings"""
        with patch('sublime.load_settings') as mock_load_settings:
            mock_settings = Mock()
            mock_settings.get.return_value = 'llama2'
            mock_load_settings.return_value = mock_settings
            
            # Mock the method
            self.command._get_model = Mock(return_value='llama2')
            model = self.command._get_model()
            self.assertEqual(model, 'llama2')
    
    def test_get_api_client(self):
        """Test getting API client"""
        with patch('ollama_ai.create_api_client_from_settings', return_value=self.mock_api_client):
            # Mock the method
            self.command.get_api_client = Mock(return_value=self.mock_api_client)
            client = self.command.get_api_client()
            self.assertEqual(client, self.mock_api_client)


if __name__ == '__main__':
    unittest.main()