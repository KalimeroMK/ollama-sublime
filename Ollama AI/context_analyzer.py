import os
import re
import sublime


class ContextAnalyzer:
    """
    Handles context-aware code analysis functionality.
    Finds symbol usages across the project to provide better context for AI requests.
    """
    
    def __init__(self, project_root=None, code_file_extensions=None):
        self.project_root = project_root
        self.code_file_extensions = code_file_extensions or [".php", ".js", ".py"]
    
    @classmethod
    def from_view(cls, view):
        """Create ContextAnalyzer instance from a Sublime Text view."""
        if not view:
            return cls()
            
        folders = view.window().folders()
        project_root = folders[0] if folders else None
        
        settings = sublime.load_settings("Ollama.sublime-settings")
        code_file_extensions = settings.get("code_file_extensions", [".php", ".js", ".py"])
        
        return cls(project_root, code_file_extensions)
    
    def extract_symbol_from_text(self, text):
        """
        Tries to extract a meaningful symbol (class, function) from a string.
        """
        if not text:
            return None
            
        # Look for class, function, interface, trait declarations
        match = re.search(r'(?:class|function|interface|trait)\s+([a-zA-Z0-9_]+)', text)
        if match:
            return match.group(1)
        
        # Look for capitalized words that might be class names
        match = re.search(r'\b([A-Z][a-zA-Z0-9_]+)\b', text)
        if match:
            return match.group(1)
            
        return None
    
    def find_symbol_usages(self, symbol):
        """
        Finds usages of a symbol across the project and returns a context string.
        """
        if not symbol or not self.project_root:
            return ""
        
        max_files = 10
        files_found = 0
        contexts = []
        
        for root, _, files in os.walk(self.project_root):
            if files_found >= max_files:
                break
                
            for file in files:
                if files_found >= max_files:
                    break
                    
                if any(file.endswith(ext) for ext in self.code_file_extensions):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            matching_snippets = []
                            
                            for i, line in enumerate(lines):
                                # Match symbol at word boundaries or as part of camelCase/compound names
                                pattern = r'(?:\b' + re.escape(symbol) + r'\b|(?<=[a-z])' + re.escape(symbol) + r'(?=[A-Z]|[a-z])|' + re.escape(symbol) + r'(?=[A-Z][a-z]))'
                                if re.search(pattern, line):
                                    start = max(0, i - 2)
                                    end = min(len(lines), i + 3)
                                    snippet = "".join(lines[start:end])
                                    matching_snippets.append(
                                        "... (line {})\n{}".format(i + 1, snippet)
                                    )
                            
                            if matching_snippets:
                                relative_path = os.path.relpath(file_path, self.project_root)
                                contexts.append(
                                    "--- File: {}\n{}\n".format(
                                        relative_path, 
                                        "\n".join(matching_snippets)
                                    )
                                )
                                files_found += 1
                                
                    except Exception:
                        # Skip files that can't be read
                        continue
        
        if not contexts:
            return ""
        
        return "\n\nFor context, here is how `{}` is used elsewhere in the project:\n{}".format(
            symbol, 
            "\n".join(contexts)
        )
    
    def get_project_context_for_symbol(self, symbol):
        """
        Orchestrates getting the project context for a given symbol.
        """
        if not symbol:
            return ""
            
        return self.find_symbol_usages(symbol)
    
    def analyze_text_for_context(self, text, current_file_path=None, use_advanced_context=None):
        """
        Analyzes text to extract symbols and provide project context.
        Returns tuple of (symbol, usage_context).
        
        Args:
            text: The text to analyze
            current_file_path: Path to current file for advanced context analysis
            use_advanced_context: Whether to use advanced multi-file context (None = auto-detect from settings)
        """
        symbol = self.extract_symbol_from_text(text)
        
        # Check if advanced context should be used
        if use_advanced_context is None:
            settings = sublime.load_settings("Ollama.sublime-settings")
            use_advanced_context = settings.get("use_advanced_context", True)
        
        if use_advanced_context and current_file_path:
            return self.analyze_text_for_advanced_context(text, current_file_path)
        else:
            # Fall back to basic context analysis
            usage_context = self.get_project_context_for_symbol(symbol)
            return symbol, usage_context
    
    def analyze_text_for_advanced_context(self, text, current_file_path):
        """
        Analyze text with advanced multi-file context understanding.
        Returns comprehensive context including architectural patterns and relationships.
        """
        try:
            from .multi_file_context import AdvancedContextAnalyzer
            
            # Create advanced analyzer instance
            advanced_analyzer = AdvancedContextAnalyzer.from_view(None)
            advanced_analyzer.project_root = self.project_root
            advanced_analyzer.code_file_extensions = self.code_file_extensions
            advanced_analyzer.build_project_context()
            
            # Get advanced analysis
            return advanced_analyzer.analyze_text_for_advanced_context(text, current_file_path)
            
        except ImportError:
            # Fallback to basic analysis if advanced module not available
            symbol = self.extract_symbol_from_text(text)
            usage_context = self.get_project_context_for_symbol(symbol)
            return symbol, usage_context
        except Exception:
            # Fallback to basic analysis on any error
            symbol = self.extract_symbol_from_text(text)
            usage_context = self.get_project_context_for_symbol(symbol)
            return symbol, usage_context
    
    def get_architectural_analysis(self, current_file_path):
        """Get architectural analysis for the current file."""
        try:
            from .multi_file_context import AdvancedContextAnalyzer
            
            advanced_analyzer = AdvancedContextAnalyzer.from_view(None)
            advanced_analyzer.project_root = self.project_root
            advanced_analyzer.code_file_extensions = self.code_file_extensions
            advanced_analyzer.build_project_context()
            
            return advanced_analyzer.get_architectural_context(current_file_path)
        except:
            return ""
    
    def get_change_impact_analysis(self, current_file_path):
        """Get change impact analysis for the current file."""
        try:
            from .multi_file_context import AdvancedContextAnalyzer
            
            advanced_analyzer = AdvancedContextAnalyzer.from_view(None)
            advanced_analyzer.project_root = self.project_root
            advanced_analyzer.code_file_extensions = self.code_file_extensions
            advanced_analyzer.build_project_context()
            
            return advanced_analyzer.get_change_impact_summary(current_file_path)
        except:
            return ""


def get_project_context_for_symbol(view, symbol):
    """
    Legacy helper function for backward compatibility.
    Orchestrates getting the project context for a given symbol.
    """
    analyzer = ContextAnalyzer.from_view(view)
    return analyzer.get_project_context_for_symbol(symbol)


def extract_symbol_from_text(text):
    """
    Legacy helper function for backward compatibility.
    Tries to extract a meaningful symbol (class, function) from a string.
    """
    analyzer = ContextAnalyzer()
    return analyzer.extract_symbol_from_text(text)