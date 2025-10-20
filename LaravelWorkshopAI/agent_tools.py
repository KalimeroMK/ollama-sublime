"""
Tools that AI agents can use to interact with the codebase
These enable agents to read files, write code, run tests, etc.
"""

import os
import sublime
import subprocess
from typing import Dict, Any, List, Optional
from agent_framework import Tool


class FileSystemTools:
    """Tools for file system operations"""
    
    @staticmethod
    def read_file(file_path):
        """Read contents of a file"""
        try:
            if not os.path.isabs(file_path):
                # Try to make it absolute relative to project root
                window = sublime.active_window()
                if window and window.folders():
                    file_path = os.path.join(window.folders()[0], file_path)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return "Error reading file: {0}".format(str(e))
    
    @staticmethod
    def write_file(file_path, content):
        """Write content to a file"""
        try:
            if not os.path.isabs(file_path):
                window = sublime.active_window()
                if window and window.folders():
                    file_path = os.path.join(window.folders()[0], file_path)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return "Successfully wrote to {0}".format(file_path)
        except Exception as e:
            return "Error writing file: {0}".format(str(e))
    
    @staticmethod
    def list_files(directory, pattern = "*"):
        """List files in a directory"""
        try:
            if not os.path.isabs(directory):
                window = sublime.active_window()
                if window and window.folders():
                    directory = os.path.join(window.folders()[0], directory)
            
            import glob
            files = glob.glob(os.path.join(directory, pattern))
            return "\n".join(files)
        except Exception as e:
            return "Error listing files: {0}".format(str(e))
    
    @staticmethod
    def file_exists(file_path):
        """Check if a file exists"""
        try:
            if not os.path.isabs(file_path):
                window = sublime.active_window()
                if window and window.folders():
                    file_path = os.path.join(window.folders()[0], file_path)
            
            exists = os.path.exists(file_path)
            return "File {0}: {1}".format('exists' if exists else 'does not exist', file_path)
        except Exception as e:
            return "Error checking file: {0}".format(str(e))


class CodeAnalysisTools:
    """Tools for analyzing code"""
    
    @staticmethod
    def find_function(file_path, function_name):
        """Find a function definition in a file"""
        try = FileSystemTools.read_file(file_path)
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if "function {0}".format(function_name) in line or "def {0}".format(function_name) in line:
                    # Get function and some context
                    start = max(0, i - 2)
                    end = min(len(lines), i + 20)
                    return "\n".join(lines[start)
            
            return "Function '{0}' not found in {1}".format(function_name, file_path)
        except Exception as e:
            return "Error finding function: {0}".format(str(e))
    
    @staticmethod
    def find_class(file_path, class_name):
        """Find a class definition in a file"""
        try = FileSystemTools.read_file(file_path)
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if "class {0}".format(class_name) in line:
                    # Get class and some context
                    start = max(0, i - 2)
                    end = min(len(lines), i + 30)
                    return "\n".join(lines[start)
            
            return "Class '{0}' not found in {1}".format(class_name, file_path)
        except Exception as e:
            return "Error finding class: {0}".format(str(e))
    
    @staticmethod
    def get_imports(file_path):
        """Get all imports from a file"""
        try = FileSystemTools.read_file(file_path)
            lines = content.split('\n')
            
            imports = []
            for line in lines = line.strip()
                if line.startswith('import ') or line.startswith('from ') or line.startswith('use '):
                    imports.append(line)
            
            return "\n".join(imports) if imports else "No imports found"
        except Exception as e:
            return "Error getting imports: {0}".format(str(e))


class ProjectTools:
    """Tools for project-level operations"""
    
    @staticmethod
    def get_project_structure():
        """Get the project directory structure"""
        try = sublime.active_window()
            if not window or not window.folders():
                return "No project folder open"
            
            project_root = window.folders()[0]
            
            structure = []
            for root, dirs, files in os.walk(project_root):
                # Skip common ignored directories
                dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', 'vendor', '__pycache__', '.venv']]
                
                level = root.replace(project_root, '').count(os.sep)
                indent = ' ' * 2 * level
                structure.append("{0}{1}/".format(indent, os.path.basename(root)))
                
                subindent = ' ' * 2 * (level + 1)
                for file in files[:10]:  # Limit files per directory
                    structure.append("{0}{1}".format(subindent, file))
                
                if len(structure) > 100:  # Limit total output
                    structure.append("... (truncated)")
                    break
            
            return "\n".join(structure)
        except Exception as e:
            return "Error getting project structure: {0}".format(str(e))
    
    @staticmethod
    def find_files_by_name(name_pattern):
        """Find files matching a pattern"""
        try = sublime.active_window()
            if not window or not window.folders():
                return "No project folder open"
            
            project_root = window.folders()[0]
            
            import glob
            pattern = os.path.join(project_root, '**', name_pattern)
            files = glob.glob(pattern, recursive=True)
            
            # Limit results
            files = files[:20]
            
            return "\n".join(files) if files else "No files found matching '{0}'".format(name_pattern)
        except Exception as e:
            return "Error finding files: {0}".format(str(e))
    
    @staticmethod
    def get_git_status():
        """Get git status of the project"""
        try = sublime.active_window()
            if not window or not window.folders():
                return "No project folder open"
            
            project_root = window.folders()[0]
            
            result = subprocess.run(
                ['git', 'status', '--short'],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return result.stdout if result.stdout else "Working tree clean"
            else:
                return "Not a git repository or git not available"
        except Exception as e:
            return "Error getting git status: {0}".format(str(e))


class LaravelTools:
    """Laravel-specific tools"""
    
    @staticmethod
    def run_artisan_command(command):
        """Run a Laravel artisan command"""
        try = sublime.active_window()
            if not window or not window.folders():
                return "No project folder open"
            
            project_root = window.folders()[0]
            
            # Check if artisan exists
            artisan_path = os.path.join(project_root, 'artisan')
            if not os.path.exists(artisan_path):
                return "Not a Laravel project (artisan not found)"
            
            result = subprocess.run(
                ['php', 'artisan', command],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return "Error running artisan command: {0}".format(str(e))
    
    @staticmethod
    def get_routes():
        """Get Laravel routes"""
        return LaravelTools.run_artisan_command('route:list')
    
    @staticmethod
    def get_models():
        """List Laravel models"""
        try = sublime.active_window()
            if not window or not window.folders():
                return "No project folder open"
            
            project_root = window.folders()[0]
            models_dir = os.path.join(project_root, 'app', 'Models')
            
            if not os.path.exists(models_dir):
                return "Models directory not found"
            
            models = [f for f in os.listdir(models_dir) if f.endswith('.php')]
            return "\n".join(models) if models else "No models found"
        except Exception as e:
            return "Error getting models: {0}".format(str(e))


class TestingTools:
    """Tools for running tests"""
    
    @staticmethod
    def run_phpunit(test_path = ""):
        """Run PHPUnit tests"""
        try = sublime.active_window()
            if not window or not window.folders():
                return "No project folder open"
            
            project_root = window.folders()[0]
            
            cmd = ['./vendor/bin/phpunit']
            if test_path:
                cmd.append(test_path)
            
            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return "Error running tests: {0}".format(str(e))
    
    @staticmethod
    def run_pest(test_path = ""):
        """Run Pest tests"""
        try = sublime.active_window()
            if not window or not window.folders():
                return "No project folder open"
            
            project_root = window.folders()[0]
            
            cmd = ['./vendor/bin/pest']
            if test_path:
                cmd.append(test_path)
            
            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return "Error running tests: {0}".format(str(e))


def create_default_tools():
    """Create a list of default tools for agents"""
    return [
        # File System Tools
        Tool(
            name="read_file",
            description="Read the contents of a file. Use this to examine existing code.",
            function=FileSystemTools.read_file,
            parameters={"file_path": "string"}
        ),
        Tool(
            name="write_file",
            description="Write content to a file. Use this to create or update files.",
            function=FileSystemTools.write_file,
            parameters={"file_path": "string", "content": "string"}
        ),
        Tool(
            name="list_files",
            description="List files in a directory with optional pattern matching.",
            function=FileSystemTools.list_files,
            parameters={"directory": "string", "pattern": "string (optional)"}
        ),
        Tool(
            name="file_exists",
            description="Check if a file exists at the given path.",
            function=FileSystemTools.file_exists,
            parameters={"file_path": "string"}
        ),
        
        # Code Analysis Tools
        Tool(
            name="find_function",
            description="Find a function definition in a file.",
            function=CodeAnalysisTools.find_function,
            parameters={"file_path": "string", "function_name": "string"}
        ),
        Tool(
            name="find_class",
            description="Find a class definition in a file.",
            function=CodeAnalysisTools.find_class,
            parameters={"file_path": "string", "class_name": "string"}
        ),
        Tool(
            name="get_imports",
            description="Get all import statements from a file.",
            function=CodeAnalysisTools.get_imports,
            parameters={"file_path": "string"}
        ),
        
        # Project Tools
        Tool(
            name="get_project_structure",
            description="Get the directory structure of the current project.",
            function=ProjectTools.get_project_structure,
            parameters={}
        ),
        Tool(
            name="find_files_by_name",
            description="Find files in the project matching a name pattern.",
            function=ProjectTools.find_files_by_name,
            parameters={"name_pattern": "string"}
        ),
        Tool(
            name="get_git_status",
            description="Get the git status of the project.",
            function=ProjectTools.get_git_status,
            parameters={}
        ),
        
        # Laravel Tools
        Tool(
            name="run_artisan",
            description="Run a Laravel artisan command.",
            function=LaravelTools.run_artisan_command,
            parameters={"command": "string"}
        ),
        Tool(
            name="get_routes",
            description="Get all Laravel routes.",
            function=LaravelTools.get_routes,
            parameters={}
        ),
        Tool(
            name="get_models",
            description="List all Laravel models.",
            function=LaravelTools.get_models,
            parameters={}
        ),
        
        # Testing Tools
        Tool(
            name="run_phpunit",
            description="Run PHPUnit tests.",
            function=TestingTools.run_phpunit,
            parameters={"test_path": "string (optional)"}
        ),
        Tool(
            name="run_pest",
            description="Run Pest tests.",
            function=TestingTools.run_pest,
            parameters={"test_path": "string (optional)"}
        ),
    ]
