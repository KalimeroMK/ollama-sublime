import os
import re
import json
import hashlib
import pickle
import time
from collections import defaultdict, deque
import sublime


class ContextCache:
    """Advanced caching system for context analysis results."""
    
    def __init__(self, cache_dir=None, max_cache_size=100):
        self.cache_dir = cache_dir or os.path.expanduser("~/.sublime_ollama_cache")
        self.max_cache_size = max_cache_size
        self.cache_index = {}
        self.cache_stats = {"hits": 0, "misses": 0, "size": 0}
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Load existing cache index
        self._load_cache_index()
    
    def _get_cache_key(self, project_root, file_path, content_hash):
        """Generate a unique cache key for a file."""
        return hashlib.md5(f"{project_root}:{file_path}:{content_hash}".encode()).hexdigest()
    
    def _get_content_hash(self, content):
        """Generate hash for file content."""
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cache_file_path(self, cache_key):
        """Get the full path for a cache file."""
        return os.path.join(self.cache_dir, f"{cache_key}.cache")
    
    def _load_cache_index(self):
        """Load the cache index from disk."""
        index_file = os.path.join(self.cache_dir, "cache_index.json")
        try:
            if os.path.exists(index_file):
                with open(index_file, 'r') as f:
                    self.cache_index = json.load(f)
                    self.cache_stats["size"] = len(self.cache_index)
        except Exception:
            self.cache_index = {}
    
    def _save_cache_index(self):
        """Save the cache index to disk."""
        index_file = os.path.join(self.cache_dir, "cache_index.json")
        try:
            with open(index_file, 'w') as f:
                json.dump(self.cache_index, f)
        except Exception:
            pass
    
    def get(self, project_root, file_path, content):
        """Get cached analysis results for a file."""
        content_hash = self._get_content_hash(content)
        cache_key = self._get_cache_key(project_root, file_path, content_hash)
        
        if cache_key in self.cache_index:
            cache_info = self.cache_index[cache_key]
            cache_file = self._get_cache_file_path(cache_key)
            
            # Check if cache is still valid
            if (os.path.exists(cache_file) and 
                time.time() - cache_info["timestamp"] < cache_info["ttl"]):
                
                try:
                    with open(cache_file, 'rb') as f:
                        self.cache_stats["hits"] += 1
                        return pickle.load(f)
                except Exception:
                    # Remove invalid cache entry
                    self._remove_cache_entry(cache_key)
        
        self.cache_stats["misses"] += 1
        return None
    
    def set(self, project_root, file_path, content, analysis_result, ttl=3600):
        """Cache analysis results for a file."""
        content_hash = self._get_content_hash(content)
        cache_key = self._get_cache_key(project_root, file_path, content_hash)
        
        # Check cache size limit
        if len(self.cache_index) >= self.max_cache_size:
            self._evict_oldest_cache()
        
        try:
            cache_file = self._get_cache_file_path(cache_key)
            with open(cache_file, 'wb') as f:
                pickle.dump(analysis_result, f)
            
            # Update cache index
            self.cache_index[cache_key] = {
                "project_root": project_root,
                "file_path": file_path,
                "timestamp": time.time(),
                "ttl": ttl,
                "size": len(content)
            }
            
            self.cache_stats["size"] = len(self.cache_index)
            self._save_cache_index()
            
        except Exception:
            pass
    
    def _remove_cache_entry(self, cache_key):
        """Remove a cache entry."""
        if cache_key in self.cache_index:
            cache_file = self._get_cache_file_path(cache_key)
            try:
                if os.path.exists(cache_file):
                    os.remove(cache_file)
            except Exception:
                pass
            
            del self.cache_index[cache_key]
            self.cache_stats["size"] = len(self.cache_index)
            self._save_cache_index()
    
    def _evict_oldest_cache(self):
        """Remove the oldest cache entries to make room."""
        if not self.cache_index:
            return
        
        # Sort by timestamp and remove oldest
        sorted_entries = sorted(
            self.cache_index.items(),
            key=lambda x: x[1]["timestamp"]
        )
        
        # Remove oldest 20% of entries
        entries_to_remove = max(1, len(sorted_entries) // 5)
        for i in range(entries_to_remove):
            cache_key = sorted_entries[i][0]
            self._remove_cache_entry(cache_key)
    
    def clear(self):
        """Clear all cached data."""
        try:
            for cache_key in list(self.cache_index.keys()):
                self._remove_cache_entry(cache_key)
        except Exception:
            pass
    
    def get_stats(self):
        """Get cache statistics."""
        return self.cache_stats.copy()


class FileRelationship:
    """Represents a relationship between two files."""
    
    def __init__(self, source_file, target_file, relationship_type, line_number=None, context=None):
        self.source_file = source_file
        self.target_file = target_file
        self.relationship_type = relationship_type  # 'import', 'extends', 'implements', 'uses', 'calls'
        self.line_number = line_number
        self.context = context or ""
    
    def __repr__(self):
        return f"FileRelationship({self.source_file} -> {self.target_file} [{self.relationship_type}])"


class ArchitecturalPattern:
    """Represents detected architectural patterns in the codebase."""
    
    def __init__(self, pattern_type, files, description=""):
        self.pattern_type = pattern_type  # 'mvc', 'repository', 'service', 'facade', etc.
        self.files = files  # List of files participating in this pattern
        self.description = description
    
    def __repr__(self):
        return f"ArchitecturalPattern({self.pattern_type}: {len(self.files)} files)"


class MultiFileContextAnalyzer:
    """
    Advanced multi-file context analyzer that understands file relationships,
    dependencies, and architectural patterns across the entire project.
    """
    
    def __init__(self, project_root=None, code_file_extensions=None):
        self.project_root = project_root
        self.code_file_extensions = code_file_extensions or [".php", ".js", ".py", ".blade.php", ".vue"]
        
        # Advanced caching system
        self.cache = ContextCache()
        
        # Caches for performance
        self._file_cache = {}
        self._dependency_graph = defaultdict(list)
        self._reverse_dependency_graph = defaultdict(list)
        self._architectural_patterns = []
        self._file_roles = {}  # Maps files to their architectural roles
        
        # Performance settings
        self._max_files_to_scan = 1000
        self._file_size_limit = 1024 * 1024  # 1MB
        self._scan_timeout = 30  # seconds
        
        # Patterns for different file types
        self.php_patterns = {
            'import': [
                r'use\s+([A-Za-z\\][A-Za-z0-9\\]*);',
                r'require(?:_once)?\s+[\'"]([^\'\"]+)[\'"]',
                r'include(?:_once)?\s+[\'"]([^\'\"]+)[\'"]'
            ],
            'extends': [r'class\s+\w+\s+extends\s+([A-Za-z0-9_\\]+)'],
            'implements': [r'implements\s+([A-Za-z0-9_\\,\s]+)'],
            'namespace': [r'namespace\s+([A-Za-z0-9_\\]+);']
        }
        
        self.js_patterns = {
            'import': [
                r'import\s+.*\s+from\s+[\'"]([^\'\"]+)[\'"]',
                r'require\([\'"]([^\'\"]+)[\'"]\)',
                r'import\([\'"]([^\'\"]+)[\'"]\)'
            ],
            'export': [r'export\s+.*\s+from\s+[\'"]([^\'\"]+)[\'"]']
        }
    
    @classmethod
    def from_view(cls, view):
        """Create MultiFileContextAnalyzer instance from a Sublime Text view."""
        if not view:
            return cls()
            
        folders = view.window().folders()
        project_root = folders[0] if folders else None
        
        settings = sublime.load_settings("Ollama.sublime-settings")
        code_file_extensions = settings.get("code_file_extensions", [".php", ".js", ".py", ".blade.php", ".vue"])
        
        analyzer = cls(project_root, code_file_extensions)
        analyzer.build_project_context()
        return analyzer
    
    def build_project_context(self):
        """Build comprehensive project context by analyzing all files."""
        if not self.project_root:
            return
        
        self._scan_all_files()
        self._build_dependency_graph()
        self._detect_architectural_patterns()
        self._classify_file_roles()
    
    def _scan_all_files(self):
        """Scan all project files and cache their content and metadata with performance optimizations."""
        if not self.project_root:
            return
        
        # Check cache first
        cache_key = f"project_scan_{self.project_root}"
        cached_result = self.cache.get(self.project_root, cache_key, "")
        if cached_result:
            self._file_cache = cached_result.get("files", {})
            self._dependency_graph = defaultdict(list, cached_result.get("dependencies", {}))
            self._reverse_dependency_graph = defaultdict(list, cached_result.get("reverse_dependencies", {}))
            return
        
        # Performance settings from configuration
        settings = sublime.load_settings("Ollama.sublime-settings")
        self._max_files_to_scan = int(settings.get("max_files_to_scan", 1000))
        self._file_size_limit = int(settings.get("file_size_limit", 1024 * 1024))
        self._scan_timeout = int(settings.get("scan_timeout", 30))
        
        # Progress tracking
        total_files = 0
        scanned_files = 0
        start_time = time.time()
        
        # First pass: count files and estimate time
        for root, dirs, files in os.walk(self.project_root):
            # Skip common directories that don't contain source code
            dirs[:] = [d for d in dirs if d not in {
                '.git', '.svn', '.hg', 'node_modules', 'vendor', 
                'storage', 'cache', 'logs', 'tmp', 'temp',
                '.idea', '.vscode', 'build', 'dist', 'target'
            }]
            
            for file in files:
                if any(file.endswith(ext) for ext in self.code_file_extensions):
                    total_files += 1
                    if total_files > self._max_files_to_scan:
                        break
            if total_files > self._max_files_to_scan:
                break
        
        # Second pass: scan files with progress tracking
        for root, dirs, files in os.walk(self.project_root):
            # Skip common directories
            dirs[:] = [d for d in dirs if d not in {
                '.git', '.svn', '.hg', 'node_modules', 'vendor', 
                'storage', 'cache', 'logs', 'tmp', 'temp',
                '.idea', '.vscode', 'build', 'dist', 'target'
            }]
            
            for file in files:
                # Check timeout
                if time.time() - start_time > self._scan_timeout:
                    print(f"[Ollama AI] File scanning timeout after {self._scan_timeout}s")
                    break
                
                # Check file limit
                if scanned_files >= self._max_files_to_scan:
                    print(f"[Ollama AI] Reached maximum files limit ({self._max_files_to_scan})")
                    break
                
                # Check file extension
                if not any(file.endswith(ext) for ext in self.code_file_extensions):
                    continue
                
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, self.project_root)
                
                try:
                    # Check file size
                    file_size = os.path.getsize(file_path)
                    if file_size > self._file_size_limit:
                        print(f"[Ollama AI] Skipping large file: {relative_path} ({file_size} bytes)")
                        continue
                    
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Cache file content and metadata
                    self._file_cache[relative_path] = {
                        'content': content,
                        'size': file_size,
                        'modified': os.path.getmtime(file_path),
                        'path': file_path
                    }
                    
                    scanned_files += 1
                    
                    # Progress update every 50 files
                    if scanned_files % 50 == 0 and total_files > 0:
                        progress = (scanned_files / total_files) * 100
                        print(f"[Ollama AI] Scanning progress: {scanned_files}/{total_files} ({progress:.1f}%)")
                    
                except Exception as e:
                    print(f"[Ollama AI] Error reading file {relative_path}: {e}")
                    continue
        
        # Cache the scan results
        scan_result = {
            "files": self._file_cache,
            "dependencies": dict(self._dependency_graph),
            "reverse_dependencies": dict(self._reverse_dependency_graph),
            "scan_time": time.time() - start_time,
            "files_scanned": scanned_files
        }
        
        self.cache.set(self.project_root, cache_key, "", scan_result, ttl=1800)  # 30 minutes
        
        print(f"[Ollama AI] File scanning completed: {scanned_files} files in {scan_result['scan_time']:.2f}s")
    
    def _build_dependency_graph(self):
        """Build dependency graph with performance optimizations."""
        if not self._file_cache:
            return
        
        print("[Ollama AI] Building dependency graph...")
        start_time = time.time()
        
        # Process files in batches for better performance
        batch_size = 50
        file_paths = list(self._file_cache.keys())
        
        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i:i + batch_size]
            
            for file_path in batch:
                file_info = self._file_cache[file_path]
                content = file_info['content']
                
                # Analyze dependencies based on file type
                dependencies = self._extract_dependencies(file_path, content)
                
                for dep in dependencies:
                    if dep in self._file_cache:
                        relationship = FileRelationship(file_path, dep, "import")
                        self._dependency_graph[file_path].append(relationship)
                        self._reverse_dependency_graph[dep].append(relationship)
        
        print(f"[Ollama AI] Dependency graph built in {time.time() - start_time:.2f}s")
    
    def _extract_dependencies(self, file_path, content):
        """Extract dependencies from file content with optimized patterns."""
        dependencies = set()
        
        # Determine file type and use appropriate patterns
        if file_path.endswith('.php'):
            patterns = self.php_patterns
        elif file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
            patterns = self.js_patterns
        else:
            return dependencies
        
        # Use compiled regex patterns for better performance
        for pattern_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                try:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        if isinstance(match, tuple):
                            # Handle capture groups
                            for group in match:
                                if group:
                                    dependencies.add(self._normalize_dependency(group, file_path))
                        else:
                            dependencies.add(self._normalize_dependency(match, file_path))
                except re.error:
                    continue
        
        return dependencies
    
    def _normalize_dependency(self, dependency, source_file):
        """Normalize dependency path for consistent matching."""
        # Remove quotes and whitespace
        dependency = dependency.strip().strip('"\'')
        
        # Handle PHP namespaces
        if dependency.startswith('\\'):
            dependency = dependency[1:]
        
        # Convert namespace to file path
        if '\\' in dependency:
            parts = dependency.split('\\')
            if parts[0] in ['App', 'Tests', 'Database']:
                # Laravel namespace mapping
                if parts[0] == 'App':
                    parts[0] = 'app'
                elif parts[0] == 'Tests':
                    parts[0] = 'tests'
                elif parts[0] == 'Database':
                    parts[0] = 'database'
                
                # Convert to file path
                dependency = '/'.join(parts) + '.php'
        
        return dependency
    
    def _detect_architectural_patterns(self):
        """Detect common architectural patterns in the project."""
        # Detect MVC pattern
        controllers = [f for f in self._file_cache.keys() if 'controller' in f.lower()]
        models = [f for f in self._file_cache.keys() if 'model' in f.lower()]
        views = [f for f in self._file_cache.keys() if 'view' in f.lower() or f.endswith('.blade.php')]
        
        if controllers and models:
            self._architectural_patterns.append(
                ArchitecturalPattern('mvc', controllers + models + views, 
                                   "Model-View-Controller pattern detected")
            )
        
        # Detect Repository pattern
        repositories = [f for f in self._file_cache.keys() if 'repository' in f.lower()]
        if repositories:
            self._architectural_patterns.append(
                ArchitecturalPattern('repository', repositories, 
                                   "Repository pattern detected")
            )
        
        # Detect Service pattern
        services = [f for f in self._file_cache.keys() if 'service' in f.lower()]
        if services:
            self._architectural_patterns.append(
                ArchitecturalPattern('service', services, 
                                   "Service layer pattern detected")
            )
    
    def _classify_file_roles(self):
        """Classify files by their architectural roles."""
        for file_path in self._file_cache.keys():
            role = self._determine_file_role(file_path)
            self._file_roles[file_path] = role
    
    def _determine_file_role(self, file_path):
        """Determine the architectural role of a file."""
        path_lower = file_path.lower()
        filename = os.path.basename(file_path).lower()
        
        # Laravel-specific patterns
        if 'controller' in path_lower:
            return 'controller'
        elif 'model' in path_lower:
            return 'model'
        elif path_lower.endswith('.blade.php'):
            return 'view'
        elif 'repository' in path_lower:
            return 'repository'
        elif 'service' in path_lower:
            return 'service'
        elif 'middleware' in path_lower:
            return 'middleware'
        elif 'migration' in path_lower:
            return 'migration'
        elif 'seeder' in path_lower:
            return 'seeder'
        elif 'test' in path_lower:
            return 'test'
        elif 'config' in path_lower:
            return 'config'
        elif 'route' in path_lower:
            return 'route'
        else:
            return 'unknown'
    
    def get_file_dependencies(self, file_path):
        """Get all files that the given file depends on."""
        dependencies = []
        for relationship in self._dependency_graph.get(file_path, []):
            dependencies.append(relationship.target_file)
        return dependencies
    
    def get_file_dependents(self, file_path):
        """Get all files that depend on the given file."""
        dependents = []
        for relationship in self._reverse_dependency_graph.get(file_path, []):
            dependents.append(relationship.source_file)
        return dependents
    
    def get_related_files(self, file_path, max_depth=2):
        """Get all files related to the given file within specified depth."""
        if file_path not in self._file_cache:
            return []
        
        related = set()
        visited = set()
        queue = deque([(file_path, 0)])
        
        while queue:
            current_file, depth = queue.popleft()
            
            if current_file in visited or depth > max_depth:
                continue
            
            visited.add(current_file)
            if depth > 0:  # Don't include the source file itself
                related.add(current_file)
            
            # Add dependencies and dependents
            for relationship in self._dependency_graph.get(current_file, []):
                if relationship.target_file not in visited:
                    queue.append((relationship.target_file, depth + 1))
            
            for relationship in self._reverse_dependency_graph.get(current_file, []):
                if relationship.source_file not in visited:
                    queue.append((relationship.source_file, depth + 1))
        
        return list(related)
    
    def get_architectural_context(self, file_path):
        """Get architectural context for a file."""
        if file_path not in self._file_cache:
            return ""
        
        role = self._file_roles.get(file_path, 'unknown')
        related_files = self.get_related_files(file_path, max_depth=1)
        
        context = f"\n\nArchitectural Context for {file_path}:\n"
        context += f"- File Role: {role.title()}\n"
        
        if related_files:
            context += f"- Related Files ({len(related_files)}):\n"
            for related_file in related_files[:5]:  # Limit to top 5
                related_role = self._file_roles.get(related_file, 'unknown')
                context += f"  • {related_file} [{related_role}]\n"
        
        # Add architectural patterns this file participates in
        participating_patterns = [p for p in self._architectural_patterns if file_path in p.files]
        if participating_patterns:
            context += f"- Architectural Patterns:\n"
            for pattern in participating_patterns:
                context += f"  • {pattern.pattern_type.upper()}: {pattern.description}\n"
        
        return context
    
    def get_impact_analysis(self, file_path):
        """Analyze potential impact of changes to a file."""
        if file_path not in self._file_cache:
            return ""
        
        dependents = self.get_file_dependents(file_path)
        dependencies = self.get_file_dependencies(file_path)
        
        context = f"\n\nImpact Analysis for {file_path}:\n"
        
        if dependencies:
            context += f"- Dependencies ({len(dependencies)} files): Changes here may require updates to imported functionality\n"
            for dep in dependencies[:3]:
                context += f"  • {dep}\n"
        
        if dependents:
            context += f"- Dependents ({len(dependents)} files): Changes here will affect these files\n"
            for dep in dependents[:3]:
                context += f"  • {dep}\n"
        
        if len(dependents) > 3:
            context += f"  • ... and {len(dependents) - 3} more files\n"
        
        return context
    
    def get_comprehensive_context(self, file_path, include_content_snippets=True):
        """Get comprehensive multi-file context for a file."""
        if file_path not in self._file_cache:
            return ""
        
        context = ""
        
        # Add architectural context
        context += self.get_architectural_context(file_path)
        
        # Add impact analysis
        context += self.get_impact_analysis(file_path)
        
        # Add related file content snippets if requested
        if include_content_snippets:
            related_files = self.get_related_files(file_path, max_depth=1)
            if related_files:
                context += f"\n\nRelated File Snippets:\n"
                for related_file in related_files[:3]:  # Limit to top 3
                    snippet = self._get_file_snippet(related_file)
                    if snippet:
                        context += f"--- {related_file} ---\n{snippet}\n\n"
        
        return context
    
    def _get_file_snippet(self, file_path, max_lines=10):
        """Get a representative snippet from a file."""
        if file_path not in self._file_cache:
            return ""
        
        content = self._file_cache[file_path]['content']
        lines = content.split('\n')
        
        # For classes, try to get the class declaration and some methods
        class_pattern = r'class\s+([A-Za-z0-9_]+)'
        function_pattern = r'(?:public|private|protected)?\s*function\s+([A-Za-z0-9_]+)'
        
        important_lines = []
        
        for i, line in enumerate(lines):
            if re.search(class_pattern, line) or re.search(function_pattern, line):
                # Add context around important declarations
                start = max(0, i - 1)
                end = min(len(lines), i + 3)
                for j in range(start, end):
                    if j < len(lines):
                        important_lines.append(f"{j+1:3d}: {lines[j]}")
                
                if len(important_lines) >= max_lines:
                    break
        
        return '\n'.join(important_lines[:max_lines])
    
    def find_files_by_pattern(self, pattern_type):
        """Find files matching a specific architectural pattern."""
        matching_files = []
        
        for file_path, role in self._file_roles.items():
            if role == pattern_type:
                matching_files.append(file_path)
        
        return matching_files
    
    def get_symbol_cross_references(self, symbol):
        """Get cross-references for a symbol across all related files."""
        if not symbol or not self.project_root:
            return ""
        
        references = []
        
        # Find files that contain the symbol
        symbol_files = []
        for file_path, file_info in self._file_cache.items():
            if re.search(r'\b' + re.escape(symbol) + r'\b', file_info['content']):
                symbol_files.append(file_path)
        
        # For each file containing the symbol, get its related files and check them too
        extended_files = set(symbol_files)
        for file_path in symbol_files:
            related = self.get_related_files(file_path, max_depth=1)
            extended_files.update(related)
        
        # Collect references from all relevant files
        for file_path in list(extended_files)[:15]:  # Limit to 15 files
            if file_path in self._file_cache:
                file_info = self._file_cache[file_path]
                lines = file_info['lines']
                role = self._file_roles.get(file_path, 'unknown')
                
                matching_lines = []
                for i, line in enumerate(lines):
                    if re.search(r'\b' + re.escape(symbol) + r'\b', line):
                        context_start = max(0, i - 1)
                        context_end = min(len(lines), i + 2)
                        context_lines = lines[context_start:context_end]
                        matching_lines.append(f"Line {i+1}: {' '.join(context_lines).strip()}")
                
                if matching_lines:
                    references.append(f"--- {file_path} [{role}] ---\n" + '\n'.join(matching_lines))
        
        if not references:
            return ""
        
        return f"\n\nCross-File References for `{symbol}`:\n" + '\n\n'.join(references)
    
    def get_change_impact_summary(self, file_path):
        """Get a summary of potential change impacts."""
        if file_path not in self._file_cache:
            return ""
        
        role = self._file_roles.get(file_path, 'unknown')
        dependents = self.get_file_dependents(file_path)
        dependencies = self.get_file_dependencies(file_path)
        
        impact_summary = f"\n\nChange Impact Summary:\n"
        impact_summary += f"- Modifying this {role} file\n"
        
        if dependents:
            impact_summary += f"- Will potentially affect {len(dependents)} dependent files\n"
            high_impact_dependents = [d for d in dependents if self._file_roles.get(d) in ['controller', 'service', 'model']]
            if high_impact_dependents:
                impact_summary += f"- High-impact dependents: {', '.join(high_impact_dependents[:3])}\n"
        
        if dependencies:
            impact_summary += f"- Depends on {len(dependencies)} other files\n"
        
        # Suggest testing strategy
        test_files = [f for f in self._file_cache.keys() if 'test' in f.lower() and os.path.splitext(os.path.basename(file_path))[0].lower() in f.lower()]
        if test_files:
            impact_summary += f"- Recommended tests to run: {', '.join(test_files)}\n"
        
        return impact_summary


class AdvancedContextAnalyzer(MultiFileContextAnalyzer):
    """
    Enhanced context analyzer that combines basic and advanced multi-file analysis.
    Extends the existing ContextAnalyzer functionality with advanced features.
    """
    
    def __init__(self, project_root=None, code_file_extensions=None):
        super().__init__(project_root, code_file_extensions)
        self.basic_analyzer = None
    
    @classmethod
    def from_view(cls, view):
        """Create AdvancedContextAnalyzer from view with automatic context building."""
        analyzer = super().from_view(view)
        
        # Also create basic analyzer for backward compatibility
        from context_analyzer import ContextAnalyzer
        analyzer.basic_analyzer = ContextAnalyzer.from_view(view)
        
        return analyzer
    
    def analyze_text_for_advanced_context(self, text, current_file_path=None):
        """
        Analyze text with advanced multi-file context understanding.
        Returns comprehensive context including architectural patterns and relationships.
        """
        # Get basic symbol analysis
        symbol = self.basic_analyzer.extract_symbol_from_text(text) if self.basic_analyzer else None
        
        context_parts = []
        
        # Add basic symbol usage context
        if symbol and self.basic_analyzer:
            basic_context = self.basic_analyzer.get_project_context_for_symbol(symbol)
            if basic_context:
                context_parts.append(basic_context)
        
        # Add advanced multi-file context
        if current_file_path:
            # Get comprehensive context for the current file
            advanced_context = self.get_comprehensive_context(current_file_path)
            if advanced_context:
                context_parts.append(advanced_context)
            
            # Get cross-references if we have a symbol
            if symbol:
                cross_refs = self.get_symbol_cross_references(symbol)
                if cross_refs:
                    context_parts.append(cross_refs)
            
            # Get change impact analysis
            impact_analysis = self.get_change_impact_summary(current_file_path)
            if impact_analysis:
                context_parts.append(impact_analysis)
        
        return symbol, '\n'.join(context_parts) if context_parts else ""