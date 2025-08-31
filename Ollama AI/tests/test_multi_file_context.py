#!/usr/bin/env python3
"""
Unit tests for multi_file_context.py module.
Tests the MultiFileContextAnalyzer and AdvancedContextAnalyzer classes.
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

from multi_file_context import (
    FileRelationship, 
    ArchitecturalPattern, 
    MultiFileContextAnalyzer, 
    AdvancedContextAnalyzer
)


class TestFileRelationship(unittest.TestCase):
    """Test cases for FileRelationship class."""
    
    def test_init(self):
        """Test FileRelationship initialization."""
        rel = FileRelationship(
            "src/file1.php", 
            "src/file2.php", 
            "import", 
            line_number=10, 
            context="use App\\Models\\User;"
        )
        
        self.assertEqual(rel.source_file, "src/file1.php")
        self.assertEqual(rel.target_file, "src/file2.php")
        self.assertEqual(rel.relationship_type, "import")
        self.assertEqual(rel.line_number, 10)
        self.assertEqual(rel.context, "use App\\Models\\User;")
    
    def test_init_minimal(self):
        """Test FileRelationship with minimal parameters."""
        rel = FileRelationship("file1.php", "file2.php", "extends")
        
        self.assertEqual(rel.source_file, "file1.php")
        self.assertEqual(rel.target_file, "file2.php")
        self.assertEqual(rel.relationship_type, "extends")
        self.assertIsNone(rel.line_number)
        self.assertEqual(rel.context, "")
    
    def test_repr(self):
        """Test FileRelationship string representation."""
        rel = FileRelationship("file1.php", "file2.php", "import")
        expected = "FileRelationship(file1.php -> file2.php [import])"
        self.assertEqual(repr(rel), expected)


class TestArchitecturalPattern(unittest.TestCase):
    """Test cases for ArchitecturalPattern class."""
    
    def test_init(self):
        """Test ArchitecturalPattern initialization."""
        files = ["Controller.php", "Model.php", "View.blade.php"]
        pattern = ArchitecturalPattern("mvc", files, "MVC pattern detected")
        
        self.assertEqual(pattern.pattern_type, "mvc")
        self.assertEqual(pattern.files, files)
        self.assertEqual(pattern.description, "MVC pattern detected")
    
    def test_init_minimal(self):
        """Test ArchitecturalPattern with minimal parameters."""
        files = ["Repository.php"]
        pattern = ArchitecturalPattern("repository", files)
        
        self.assertEqual(pattern.pattern_type, "repository")
        self.assertEqual(pattern.files, files)
        self.assertEqual(pattern.description, "")
    
    def test_repr(self):
        """Test ArchitecturalPattern string representation."""
        pattern = ArchitecturalPattern("service", ["Service1.php", "Service2.php"])
        expected = "ArchitecturalPattern(service: 2 files)"
        self.assertEqual(repr(pattern), expected)


class TestMultiFileContextAnalyzer(unittest.TestCase):
    """Test cases for MultiFileContextAnalyzer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.analyzer = MultiFileContextAnalyzer(
            project_root=self.temp_dir,
            code_file_extensions=[".php", ".js", ".py"]
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """Test MultiFileContextAnalyzer initialization."""
        self.assertEqual(self.analyzer.project_root, self.temp_dir)
        self.assertEqual(self.analyzer.code_file_extensions, [".php", ".js", ".py"])
        self.assertEqual(self.analyzer._file_cache, {})
        self.assertEqual(len(self.analyzer._dependency_graph), 0)
        self.assertEqual(len(self.analyzer._architectural_patterns), 0)
    
    @patch('sublime.load_settings')
    def test_from_view(self, mock_load_settings):
        """Test creating analyzer from view."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.get.return_value = [".php", ".blade.php", ".js"]
        mock_load_settings.return_value = mock_settings
        
        # Mock view and window
        mock_view = Mock()
        mock_window = Mock()
        mock_window.folders.return_value = ["/project/root"]
        mock_view.window.return_value = mock_window
        
        analyzer = MultiFileContextAnalyzer.from_view(mock_view)
        
        self.assertEqual(analyzer.project_root, "/project/root")
        self.assertEqual(analyzer.code_file_extensions, [".php", ".blade.php", ".js"])
    
    def test_scan_all_files(self):
        """Test scanning and caching all project files."""
        # Create test files
        test_files = {
            "Controller.php": "<?php\nclass TestController {}",
            "Model.php": "<?php\nclass TestModel {}",
            "test.js": "const test = 'test';",
            "ignored.txt": "This should be ignored"
        }
        
        for filename, content in test_files.items():
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        self.analyzer._scan_all_files()
        
        # Check that PHP and JS files were cached, but not txt
        self.assertIn("Controller.php", self.analyzer._file_cache)
        self.assertIn("Model.php", self.analyzer._file_cache)
        self.assertIn("test.js", self.analyzer._file_cache)
        self.assertNotIn("ignored.txt", self.analyzer._file_cache)
        
        # Check file info structure
        file_info = self.analyzer._file_cache["Controller.php"]
        self.assertIn('content', file_info)
        self.assertIn('lines', file_info)
        self.assertIn('extension', file_info)
        self.assertEqual(file_info['extension'], '.php')
    
    def test_namespace_to_file_path(self):
        """Test converting PHP namespace to file path."""
        # Mock file cache
        self.analyzer._file_cache = {
            "app/Models/User.php": {},
            "app/Http/Controllers/UserController.php": {},
            "tests/Feature/UserTest.php": {}
        }
        
        # Test Laravel namespace mappings
        self.assertEqual(
            self.analyzer._namespace_to_file_path("App\\Models\\User", ".php"),
            "app/Models/User.php"
        )
        
        self.assertEqual(
            self.analyzer._namespace_to_file_path("Tests\\Feature\\UserTest", ".php"),
            "tests/Feature/UserTest.php"
        )
        
        # Test non-existent namespace
        self.assertIsNone(
            self.analyzer._namespace_to_file_path("NonExistent\\Class", ".php")
        )
    
    def test_determine_file_role(self):
        """Test file role determination."""
        test_cases = [
            ("app/Http/Controllers/UserController.php", "controller"),
            ("app/Models/User.php", "model"),
            ("resources/views/user.blade.php", "view"),
            ("app/Repositories/UserRepository.php", "repository"),
            ("app/Services/UserService.php", "service"),
            ("app/Http/Middleware/Auth.php", "middleware"),
            ("database/migrations/create_users_table.php", "migration"),
            ("database/seeders/UserSeeder.php", "seeder"),
            ("tests/Feature/UserTest.php", "test"),
            ("config/app.php", "config"),
            ("routes/web.php", "route"),
            ("app/Utils/Helper.php", "unknown")
        ]
        
        for file_path, expected_role in test_cases:
            with self.subTest(file_path=file_path):
                role = self.analyzer._determine_file_role(file_path)
                self.assertEqual(role, expected_role)
    
    def test_analyze_php_dependencies(self):
        """Test PHP dependency analysis."""
        # Create test file with various PHP dependency patterns
        content = """<?php
namespace App\\Http\\Controllers;

use App\\Models\\User;
use Illuminate\\Http\\Request;
require_once 'helper.php';

class UserController extends BaseController implements UserInterface {
    // Class content
}
"""
        
        # Mock file cache to include potential targets
        self.analyzer._file_cache = {
            "test.php": {"content": content, "extension": ".php"},
            "app/Models/User.php": {"content": "<?php class User {}", "extension": ".php"},
            "helper.php": {"content": "<?php // helper", "extension": ".php"}
        }
        
        self.analyzer._analyze_php_dependencies("test.php", content)
        
        # Check that dependencies were detected
        dependencies = self.analyzer._dependency_graph["test.php"]
        
        # Should find the User model dependency
        user_deps = [d for d in dependencies if d.target_file == "app/Models/User.php"]
        self.assertTrue(len(user_deps) > 0)
        self.assertEqual(user_deps[0].relationship_type, "import")
    
    def test_get_related_files(self):
        """Test getting related files within specified depth."""
        # Mock dependency graph
        self.analyzer._file_cache = {
            "A.php": {},
            "B.php": {},
            "C.php": {},
            "D.php": {}
        }
        
        # Create dependency chain: A -> B -> C -> D
        self.analyzer._dependency_graph = {
            "A.php": [FileRelationship("A.php", "B.php", "import")],
            "B.php": [FileRelationship("B.php", "C.php", "import")],
            "C.php": [FileRelationship("C.php", "D.php", "import")]
        }
        
        self.analyzer._reverse_dependency_graph = {
            "B.php": [FileRelationship("A.php", "B.php", "import")],
            "C.php": [FileRelationship("B.php", "C.php", "import")],
            "D.php": [FileRelationship("C.php", "D.php", "import")]
        }
        
        # Test with depth 1 - should only get direct dependencies
        related_depth_1 = self.analyzer.get_related_files("A.php", max_depth=1)
        self.assertIn("B.php", related_depth_1)
        self.assertNotIn("C.php", related_depth_1)
        
        # Test with depth 2 - should get dependencies and their dependencies
        related_depth_2 = self.analyzer.get_related_files("A.php", max_depth=2)
        self.assertIn("B.php", related_depth_2)
        self.assertIn("C.php", related_depth_2)
    
    def test_detect_architectural_patterns(self):
        """Test architectural pattern detection."""
        # Mock file cache with MVC pattern files
        self.analyzer._file_cache = {
            "app/Http/Controllers/UserController.php": {},
            "app/Http/Controllers/PostController.php": {},
            "app/Models/User.php": {},
            "app/Models/Post.php": {},
            "resources/views/user.blade.php": {},
            "app/Repositories/UserRepository.php": {},
            "app/Services/UserService.php": {}
        }
        
        self.analyzer._detect_architectural_patterns()
        
        # Should detect MVC pattern
        mvc_patterns = [p for p in self.analyzer._architectural_patterns if p.pattern_type == 'mvc']
        self.assertTrue(len(mvc_patterns) > 0)
        
        # Should detect Repository pattern
        repo_patterns = [p for p in self.analyzer._architectural_patterns if p.pattern_type == 'repository']
        self.assertTrue(len(repo_patterns) > 0)
        
        # Should detect Service pattern
        service_patterns = [p for p in self.analyzer._architectural_patterns if p.pattern_type == 'service']
        self.assertTrue(len(service_patterns) > 0)
    
    def test_get_architectural_context(self):
        """Test getting architectural context for a file."""
        # Setup file cache and roles
        self.analyzer._file_cache = {"app/Models/User.php": {}}
        self.analyzer._file_roles = {"app/Models/User.php": "model"}
        self.analyzer._architectural_patterns = [
            ArchitecturalPattern("mvc", ["app/Models/User.php"], "MVC pattern")
        ]
        
        # Mock get_related_files to return some related files
        with patch.object(self.analyzer, 'get_related_files', return_value=["app/Http/Controllers/UserController.php"]):
            self.analyzer._file_roles["app/Http/Controllers/UserController.php"] = "controller"
            
            context = self.analyzer.get_architectural_context("app/Models/User.php")
            
            self.assertIn("Model", context)
            self.assertIn("Related Files", context)
            self.assertIn("UserController.php", context)
            self.assertIn("MVC", context)
    
    def test_get_symbol_cross_references(self):
        """Test getting cross-references for a symbol."""
        # Create test files with symbol references
        self.analyzer._file_cache = {
            "Controller.php": {
                "content": "class UserController { public function index() { return User::all(); } }",
                "lines": ["class UserController {", "    public function index() {", "        return User::all();", "    }", "}"]
            },
            "Model.php": {
                "content": "class User extends Model { }",
                "lines": ["class User extends Model {", "}"]
            }
        }
        
        self.analyzer._file_roles = {
            "Controller.php": "controller",
            "Model.php": "model"
        }
        
        # Mock get_related_files
        with patch.object(self.analyzer, 'get_related_files', return_value=["Controller.php"]):
            cross_refs = self.analyzer.get_symbol_cross_references("User")
            
            self.assertIn("User", cross_refs)
            self.assertIn("Controller.php [controller]", cross_refs)
            self.assertIn("Model.php [model]", cross_refs)


class TestAdvancedContextAnalyzer(unittest.TestCase):
    """Test cases for AdvancedContextAnalyzer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('sublime.load_settings')
    @patch('context_analyzer.ContextAnalyzer')
    def test_from_view_integration(self, mock_context_analyzer, mock_load_settings):
        """Test creating AdvancedContextAnalyzer from view with basic analyzer integration."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.get.return_value = [".php", ".js"]
        mock_load_settings.return_value = mock_settings
        
        # Mock view and window
        mock_view = Mock()
        mock_window = Mock()
        mock_window.folders.return_value = [self.temp_dir]
        mock_view.window.return_value = mock_window
        
        # Mock basic analyzer
        mock_basic_analyzer = Mock()
        mock_context_analyzer.from_view.return_value = mock_basic_analyzer
        
        analyzer = AdvancedContextAnalyzer.from_view(mock_view)
        
        self.assertEqual(analyzer.project_root, self.temp_dir)
        self.assertEqual(analyzer.basic_analyzer, mock_basic_analyzer)
    
    def test_analyze_text_for_advanced_context_with_file(self):
        """Test advanced context analysis with current file path."""
        analyzer = AdvancedContextAnalyzer(self.temp_dir)
        
        # Mock basic analyzer
        mock_basic_analyzer = Mock()
        mock_basic_analyzer.extract_symbol_from_text.return_value = "TestClass"
        mock_basic_analyzer.get_project_context_for_symbol.return_value = "Basic context"
        analyzer.basic_analyzer = mock_basic_analyzer
        
        # Mock advanced methods
        with patch.object(analyzer, 'get_comprehensive_context', return_value="Advanced context"):
            with patch.object(analyzer, 'get_symbol_cross_references', return_value="Cross refs"):
                with patch.object(analyzer, 'get_change_impact_summary', return_value="Impact analysis"):
                    
                    symbol, context = analyzer.analyze_text_for_advanced_context("class TestClass {}", "app/Models/Test.php")
                    
                    self.assertEqual(symbol, "TestClass")
                    self.assertIn("Basic context", context)
                    self.assertIn("Advanced context", context)
                    self.assertIn("Cross refs", context)
                    self.assertIn("Impact analysis", context)
    
    def test_analyze_text_for_advanced_context_no_file(self):
        """Test advanced context analysis without current file path."""
        analyzer = AdvancedContextAnalyzer(self.temp_dir)
        
        # Mock basic analyzer
        mock_basic_analyzer = Mock()
        mock_basic_analyzer.extract_symbol_from_text.return_value = "TestClass"
        mock_basic_analyzer.get_project_context_for_symbol.return_value = "Basic context"
        analyzer.basic_analyzer = mock_basic_analyzer
        
        symbol, context = analyzer.analyze_text_for_advanced_context("class TestClass {}", None)
        
        self.assertEqual(symbol, "TestClass")
        self.assertEqual(context, "Basic context")  # Should only get basic context


class TestDependencyAnalysis(unittest.TestCase):
    """Test cases for dependency analysis functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.analyzer = MultiFileContextAnalyzer(
            project_root=self.temp_dir,
            code_file_extensions=[".php"]
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_php_use_statement_detection(self):
        """Test detection of PHP use statements."""
        content = """<?php
namespace App\\Http\\Controllers;

use App\\Models\\User;
use Illuminate\\Http\\Request;
use App\\Services\\UserService;

class UserController {
}
"""
        
        # Create target files
        target_files = [
            "app/Models/User.php",
            "app/Services/UserService.php"
        ]
        
        for target in target_files:
            target_path = os.path.join(self.temp_dir, target)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, 'w') as f:
                f.write("<?php // Target file")
        
        # Add files to cache
        self.analyzer._file_cache = {
            "Controller.php": {"content": content, "extension": ".php"},
            "app/Models/User.php": {"content": "<?php class User {}", "extension": ".php"},
            "app/Services/UserService.php": {"content": "<?php class UserService {}", "extension": ".php"}
        }
        
        self.analyzer._analyze_php_dependencies("Controller.php", content)
        
        dependencies = self.analyzer._dependency_graph["Controller.php"]
        target_files_found = [d.target_file for d in dependencies]
        
        self.assertIn("app/Models/User.php", target_files_found)
        self.assertIn("app/Services/UserService.php", target_files_found)
    
    def test_get_file_dependencies_and_dependents(self):
        """Test getting file dependencies and dependents."""
        # Setup mock dependency graph
        self.analyzer._file_cache = {"A.php": {}, "B.php": {}, "C.php": {}}
        
        rel1 = FileRelationship("A.php", "B.php", "import")
        rel2 = FileRelationship("A.php", "C.php", "import")
        
        self.analyzer._dependency_graph = {"A.php": [rel1, rel2]}
        self.analyzer._reverse_dependency_graph = {
            "B.php": [rel1],
            "C.php": [rel2]
        }
        
        # Test dependencies
        deps = self.analyzer.get_file_dependencies("A.php")
        self.assertEqual(set(deps), {"B.php", "C.php"})
        
        # Test dependents
        dependents = self.analyzer.get_file_dependents("B.php")
        self.assertEqual(dependents, ["A.php"])


class TestIntegrationScenarios(unittest.TestCase):
    """Integration test scenarios for complex multi-file analysis."""
    
    def setUp(self):
        """Set up test fixtures with realistic Laravel project structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.analyzer = MultiFileContextAnalyzer(
            project_root=self.temp_dir,
            code_file_extensions=[".php", ".blade.php", ".js"]
        )
        
        # Create realistic Laravel file structure
        self.test_files = {
            "app/Models/User.php": """<?php
namespace App\\Models;
use Illuminate\\Foundation\\Auth\\User as Authenticatable;

class User extends Authenticatable {
    protected $fillable = ['name', 'email'];
}""",
            "app/Http/Controllers/UserController.php": """<?php
namespace App\\Http\\Controllers;
use App\\Models\\User;
use App\\Services\\UserService;

class UserController extends Controller {
    public function index() {
        return User::all();
    }
}""",
            "app/Services/UserService.php": """<?php
namespace App\\Services;
use App\\Models\\User;

class UserService {
    public function createUser($data) {
        return User::create($data);
    }
}""",
            "resources/views/users/index.blade.php": """@extends('layouts.app')
@section('content')
<div>Users list</div>
@endsection""",
            "tests/Feature/UserTest.php": """<?php
namespace Tests\\Feature;
use App\\Models\\User;

class UserTest extends TestCase {
    public function test_user_creation() {
        $user = User::factory()->create();
    }
}"""
        }
        
        # Create files
        for file_path, content in self.test_files.items():
            full_path = os.path.join(self.temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_full_project_analysis(self):
        """Test complete project analysis workflow."""
        self.analyzer.build_project_context()
        
        # Check that files were scanned
        self.assertTrue(len(self.analyzer._file_cache) > 0)
        
        # Check architectural pattern detection
        mvc_patterns = [p for p in self.analyzer._architectural_patterns if p.pattern_type == 'mvc']
        self.assertTrue(len(mvc_patterns) > 0)
        
        # Check file role classification
        user_model_role = self.analyzer._file_roles.get("app/Models/User.php")
        self.assertEqual(user_model_role, "model")
        
        user_controller_role = self.analyzer._file_roles.get("app/Http/Controllers/UserController.php")
        self.assertEqual(user_controller_role, "controller")
    
    def test_user_model_dependencies(self):
        """Test dependency analysis for User model."""
        self.analyzer.build_project_context()
        
        # Get files that depend on User model
        dependents = self.analyzer.get_file_dependents("app/Models/User.php")
        
        # Should include controller, service, and test files
        self.assertIn("app/Http/Controllers/UserController.php", dependents)
        self.assertIn("app/Services/UserService.php", dependents)
        self.assertIn("tests/Feature/UserTest.php", dependents)
    
    def test_comprehensive_context_generation(self):
        """Test generating comprehensive context for a file."""
        self.analyzer.build_project_context()
        
        context = self.analyzer.get_comprehensive_context("app/Models/User.php")
        
        # Should include architectural context
        self.assertIn("Architectural Context", context)
        self.assertIn("Model", context)
        
        # Should include impact analysis
        self.assertIn("Impact Analysis", context)
        
        # Should include related file snippets
        self.assertIn("Related File Snippets", context)


if __name__ == '__main__':
    print("🧪 Running Multi-File Context Tests...")
    print("=" * 50)
    
    # Run the tests
    unittest.main(verbosity=2, exit=False)
    
    print("\n" + "=" * 50)
    print("✅ Multi-File Context tests completed!")