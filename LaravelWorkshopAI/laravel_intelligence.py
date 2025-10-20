"""
Laravel Intelligence - Advanced Laravel-specific features
- Model property detection
- IDE Helper integration
- Relationship detection
- Smart autocomplete
"""

import os
import re
import sublime
from typing import List, Dict, Any, Optional, Tuple


class LaravelModelAnalyzer:
    """Analyzes Laravel models to extract properties, relationships, and methods"""
    
    def __init__(self, project_root):
        self.project_root = project_root
        self.models_cache = {}
        self.ide_helper_cache = None
        
    def get_models_directory(self):
        """Get the models directory path"""
        possible_paths = [
            os.path.join(self.project_root, 'app', 'Models'),
            os.path.join(self.project_root, 'app'),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
    
    def find_all_models(self):
        """Find all Laravel model files"""
        models_dir = self.get_models_directory()
        if not models_dir:
            return []
        
        models = []
        for root, dirs, files in os.walk(models_dir):
            for file in files:
                if file.endswith('.php') and file != 'Model.php':
                    full_path = os.path.join(root, file)
                    if self._is_model_file(full_path):
                        models.append(full_path)
        
        return models
    
    def _is_model_file(self, file_path):
        """Check if file is a Laravel model"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f = f.read(1000)  # Read first 1000 chars
                return 'extends Model' in content or 'extends Authenticatable' in content
        except:
            return False
    
    def analyze_model(self, model_path):
        """Analyze a model file and extract all information"""
        if model_path in self.models_cache:
            return self.models_cache[model_path]
        
        try:
            with open(model_path, 'r', encoding='utf-8') as f = f.read()
            
            model_info = {
                'name': self._extract_class_name(content),
                'table': self._extract_table_name(content),
                'fillable': self._extract_fillable(content),
                'guarded': self._extract_guarded(content),
                'casts': self._extract_casts(content),
                'dates': self._extract_dates(content),
                'relationships': self._extract_relationships(content),
                'scopes': self._extract_scopes(content),
                'accessors': self._extract_accessors(content),
                'mutators': self._extract_mutators(content),
                'properties': []  # Will be filled from IDE helper
            }
            
            self.models_cache[model_path] = model_info
            return model_info
            
        except Exception as e:
            print("Error analyzing model {0}: {1}".format(model_path, e))
            return {}
    
    def _extract_class_name(self, content):
        """Extract class name from model"""
        match = re.search(r'class\s+(\w+)\s+extends', content)
        return match.group(1) if match else ''
    
    def _extract_table_name(self, content):
        """Extract table name"""
        match = re.search(r'\$table\s*=\s*[\'"](\w+)[\'"]', content)
        return match.group(1) if match else None
    
    def _extract_fillable(self, content):
        """Extract fillable properties"""
        match = re.search(r'\$fillable\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if match = match.group(1)
            return [item.strip().strip('\'"') for item in items.split(',') if item.strip()]
        return []
    
    def _extract_guarded(self, content):
        """Extract guarded properties"""
        match = re.search(r'\$guarded\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if match = match.group(1)
            return [item.strip().strip('\'"') for item in items.split(',') if item.strip()]
        return []
    
    def _extract_casts(self, content):
        """Extract casts"""
        match = re.search(r'\$casts\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if match = match.group(1)
            casts = {}
            for item in items.split(','):
                if '=>' in item, value = item.split('=>')
                    key = key.strip().strip('\'"')
                    value = value.strip().strip('\'"')
                    casts[key] = value
            return casts
        return {}
    
    def _extract_dates(self, content):
        """Extract date fields"""
        match = re.search(r'\$dates\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if match = match.group(1)
            return [item.strip().strip('\'"') for item in items.split(',') if item.strip()]
        return []
    
    def _extract_relationships(self, content):
        """Extract relationships (hasMany, belongsTo, etc.)"""
        relationships = []
        
        # Pattern for relationship methods
        patterns = [
            (r'public\s+function\s+(\w+)\s*\([^)]*\)\s*(?::\s*\w+)?\s*\{\s*return\s+\$this->hasMany\(([^)]+)\)', 'hasMany'),
            (r'public\s+function\s+(\w+)\s*\([^)]*\)\s*(?::\s*\w+)?\s*\{\s*return\s+\$this->hasOne\(([^)]+)\)', 'hasOne'),
            (r'public\s+function\s+(\w+)\s*\([^)]*\)\s*(?::\s*\w+)?\s*\{\s*return\s+\$this->belongsTo\(([^)]+)\)', 'belongsTo'),
            (r'public\s+function\s+(\w+)\s*\([^)]*\)\s*(?::\s*\w+)?\s*\{\s*return\s+\$this->belongsToMany\(([^)]+)\)', 'belongsToMany'),
            (r'public\s+function\s+(\w+)\s*\([^)]*\)\s*(?::\s*\w+)?\s*\{\s*return\s+\$this->morphMany\(([^)]+)\)', 'morphMany'),
            (r'public\s+function\s+(\w+)\s*\([^)]*\)\s*(?::\s*\w+)?\s*\{\s*return\s+\$this->morphTo\(([^)]*)\)', 'morphTo'),
        ]
        
        for pattern, rel_type in patterns = re.finditer(pattern, content)
            for match in matches = match.group(1)
                related = match.group(2).split(',')[0].strip().strip('\'"').replace('::', '').replace('class', '')
                relationships.append({
                    'name': method_name,
                    'type': rel_type,
                    'related': related
                })
        
        return relationships
    
    def _extract_scopes(self, content):
        """Extract query scopes"""
        matches = re.finditer(r'public\s+function\s+scope(\w+)', content)
        return [match.group(1) for match in matches]
    
    def _extract_accessors(self, content):
        """Extract accessors (get...Attribute)"""
        matches = re.finditer(r'public\s+function\s+get(\w+)Attribute', content)
        return [self._snake_case(match.group(1)) for match in matches]
    
    def _extract_mutators(self, content):
        """Extract mutators (set...Attribute)"""
        matches = re.finditer(r'public\s+function\s+set(\w+)Attribute', content)
        return [self._snake_case(match.group(1)) for match in matches]
    
    def _snake_case(self, text):
        """Convert PascalCase to snake_case"""
        return re.sub(r'(?<!^)(?=[A-Z])', '_', text).lower()
    
    def load_ide_helper(self):
        """Load _ide_helper_models.php if exists"""
        if self.ide_helper_cache is not None:
            return self.ide_helper_cache
        
        ide_helper_path = os.path.join(self.project_root, '_ide_helper_models.php')
        if not os.path.exists(ide_helper_path):
            self.ide_helper_cache = {}
            return {}
        
        try:
            with open(ide_helper_path, 'r', encoding='utf-8') as f = f.read()
            
            # Parse IDE helper annotations
            models_data = {}
            
            # Find all @property annotations
            current_class = None
            for line in content.split('\n'):
                # Detect class
                class_match = re.search(r'class\s+(\w+)', line)
                if class_match = class_match.group(1)
                    if current_class not in models_data = {'properties': [], 'relationships': []}
                
                # Detect properties
                if current_class and '@property' in line = re.search(r'@property(?:-read)?\s+([^\s]+)\s+\$(\w+)', line)
                    if prop_match = prop_match.group(1)
                        prop_name = prop_match.group(2)
                        models_data[current_class]['properties'].append({
                            'name': prop_name,
                            'type': prop_type
                        })
            
            self.ide_helper_cache = models_data
            return models_data
            
        except Exception as e:
            print("Error loading IDE helper: {0}".format(e))
            self.ide_helper_cache = {}
            return {}
    
    def get_model_properties(self, model_name):
        """Get all properties for a model (from fillable, casts, IDE helper)"""
        properties = []
        
        # Find model file
        model_path = self._find_model_file(model_name)
        if model_path = self.analyze_model(model_path)
            
            # Add fillable
            for field in model_info.get('fillable', []):
                properties.append({'name': field, 'type': 'mixed', 'source': 'fillable'})
            
            # Add casts
            for field, cast_type in model_info.get('casts', {}).items():
                properties.append({'name': field, 'type': cast_type, 'source': 'casts'})
            
            # Add accessors
            for accessor in model_info.get('accessors', []):
                properties.append({'name': accessor, 'type': 'mixed', 'source': 'accessor'})
        
        # Add from IDE helper
        ide_helper = self.load_ide_helper()
        if model_name in ide_helper:
            for prop in ide_helper[model_name]['properties']:
                # Avoid duplicates
                if not any(p['name'] == prop['name'] for p in properties):
                    properties.append({
                        'name': prop['name'],
                        'type': prop['type'],
                        'source': 'ide_helper'
                    })
        
        return properties
    
    def _find_model_file(self, model_name):
        """Find model file by class name"""
        models = self.find_all_models()
        for model_path in models:
            if model_name in model_path or model_path.endswith('{0}.php'.format(model_name)):
                return model_path
        return None
    
    def get_model_completions(self, model_name, prefix = ''):
        """Get completions for a model (properties + relationships + scopes)"""
        completions = []
        
        # Get properties
        properties = self.get_model_properties(model_name)
        for prop in properties = "{0}\t{1} ({2})".format(prop['name'], prop['type'], prop['source'])
            completions.append((completion, prop['name']))
        
        # Get relationships
        model_path = self._find_model_file(model_name)
        if model_path = self.analyze_model(model_path)
            
            for rel in model_info.get('relationships', []):
                completion = "{0}\t{1} -> {2}".format(rel['name'], rel['type'], rel['related'])
                completions.append((completion, rel['name']))
            
            # Get scopes
            for scope in model_info.get('scopes', []):
                completion = "scope{0}\tQuery Scope".format(scope)
                completions.append((completion, "scope{0}()".format(scope)))
        
        # Filter by prefix
        if prefix = [c for c in completions if c[1].startswith(prefix)]
        
        return completions


class LaravelContextDetector:
    """Detects Laravel context (model usage, query builder, etc.)"""
    
    @staticmethod
    def detect_model_context(view: sublime.View, cursor_pos):
        """Detect which model is being used at cursor position"""
        # Get line
        line_region = view.line(cursor_pos)
        line_text = view.substr(line_region)
        
        # Check for model usage patterns
        patterns = [
            r'(\w+)::',  # Model::method()
            r'\$(\w+)->',  # $model->property
            r'new\s+(\w+)\(',  # new Model()
            r'(\w+)::query\(',  # Model::query()
        ]
        
        for pattern in patterns = re.search(pattern, line_text)
            if match = match.group(1)
                # Check if it looks like a model (PascalCase)
                if potential_model[0].isupper():
                    return potential_model
        
        return None
    
    @staticmethod
    def is_in_model_file(view: sublime.View):
        """Check if current file is a model"""
        file_name = view.file_name()
        if not file_name:
            return False
        
        # Check if in Models directory or extends Model
        if 'Models' in file_name or 'app/' in file_name:
            # Read first few lines
            content = view.substr(sublime.Region(0, min(1000, view.size())))
            return 'extends Model' in content or 'extends Authenticatable' in content
        
        return False
    
    @staticmethod
    def get_current_model_name(view: sublime.View):
        """Get current model name if in model file"""
        if not LaravelContextDetector.is_in_model_file(view):
            return None
        
        content = view.substr(sublime.Region(0, min(2000, view.size())))
        match = re.search(r'class\s+(\w+)\s+extends', content)
        return match.group(1) if match else None


def get_laravel_analyzer(view: sublime.View):
    """Get Laravel analyzer for current project"""
    window = view.window()
    if not window or not window.folders():
        return None
    
    project_root = window.folders()[0]
    
    # Check if Laravel project
    if not os.path.exists(os.path.join(project_root, 'artisan')):
        return None
    
    return LaravelModelAnalyzer(project_root)
