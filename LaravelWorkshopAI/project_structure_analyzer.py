"""
Project Structure Analyzer - Detects and respects existing project patterns
- DDD (Domain-Driven Design)
- Modular architecture
- Actions pattern
- DTOs (Data Transfer Objects)
- Repository pattern
- Service layer
"""

import os
import re
from typing import Dict, List, Optional, Set
from dataclasses import dataclass


@dataclass
class ProjectPattern:
    """Detected project pattern"""
    name: str
    confidence: float  # 0.0 - 1.0
    evidence: List[str]
    structure: Dict[str, str]


class ProjectStructureAnalyzer:
    """Analyzes project structure and detects architectural patterns"""
    
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.patterns = []
        self.directory_structure = {}
        
    def analyze(self) -> Dict[str, any]:
        """Analyze project and return detected patterns"""
        
        # Scan directory structure
        self._scan_directories()
        
        # Detect patterns
        self._detect_ddd_pattern()
        self._detect_modular_pattern()
        self._detect_actions_pattern()
        self._detect_dto_pattern()
        self._detect_repository_pattern()
        self._detect_service_pattern()
        
        # Determine primary pattern
        primary_pattern = self._get_primary_pattern()
        
        return {
            'primary_pattern': primary_pattern,
            'all_patterns': self.patterns,
            'structure': self.directory_structure,
            'recommendations': self._get_recommendations()
        }
    
    def _scan_directories(self):
        """Scan project directories"""
        app_path = os.path.join(self.project_root, 'app')
        if not os.path.exists(app_path):
            return
        
        for root, dirs, files in os.walk(app_path):
            rel_path = os.path.relpath(root, app_path)
            self.directory_structure[rel_path] = {
                'dirs': dirs,
                'files': [f for f in files if f.endswith('.php')]
            }
    
    def _detect_ddd_pattern(self):
        """Detect Domain-Driven Design pattern"""
        evidence = []
        confidence = 0.0
        structure = {}
        
        # Check for DDD directories
        ddd_indicators = [
            'Domain', 'Domains',
            'Application',
            'Infrastructure',
            'ValueObjects',
            'Entities',
            'Aggregates'
        ]
        
        for indicator in ddd_indicators:
            if self._directory_exists(indicator):
                evidence.append(f"Found {indicator} directory")
                confidence += 0.15
        
        # Check for domain subdirectories
        domain_path = self._find_directory(['Domain', 'Domains'])
        if domain_path:
            subdirs = self._get_subdirectories(domain_path)
            if len(subdirs) > 0:
                evidence.append(f"Found {len(subdirs)} domain modules")
                confidence += 0.2
                structure['domains'] = subdirs
        
        # Check for typical DDD files
        if self._file_pattern_exists('*Repository.php'):
            evidence.append("Found Repository pattern")
            confidence += 0.1
        
        if self._file_pattern_exists('*Entity.php'):
            evidence.append("Found Entity pattern")
            confidence += 0.1
        
        if confidence > 0.3:
            self.patterns.append(ProjectPattern(
                name='DDD',
                confidence=min(confidence, 1.0),
                evidence=evidence,
                structure=structure
            ))
    
    def _detect_modular_pattern(self):
        """Detect modular architecture (Laravel Modules, nWidart)"""
        evidence = []
        confidence = 0.0
        structure = {}
        
        # Check for Modules directory
        modules_path = os.path.join(self.project_root, 'Modules')
        if os.path.exists(modules_path):
            evidence.append("Found Modules directory")
            confidence += 0.5
            
            # Get module names
            modules = [d for d in os.listdir(modules_path) 
                      if os.path.isdir(os.path.join(modules_path, d))]
            
            if modules:
                evidence.append(f"Found {len(modules)} modules: {', '.join(modules[:3])}")
                confidence += 0.3
                structure['modules'] = modules
                
                # Check module structure
                sample_module = os.path.join(modules_path, modules[0])
                if os.path.exists(os.path.join(sample_module, 'Entities')):
                    evidence.append("Modules use Entities")
                    structure['uses_entities'] = True
                
                if os.path.exists(os.path.join(sample_module, 'Http', 'Controllers')):
                    evidence.append("Modules have Controllers")
                    structure['uses_controllers'] = True
        
        if confidence > 0.3:
            self.patterns.append(ProjectPattern(
                name='Modular',
                confidence=min(confidence, 1.0),
                evidence=evidence,
                structure=structure
            ))
    
    def _detect_actions_pattern(self):
        """Detect Actions pattern (single-action controllers)"""
        evidence = []
        confidence = 0.0
        structure = {}
        
        # Check for Actions directory
        actions_paths = [
            'app/Actions',
            'app/Domain/*/Actions',
            'Modules/*/Actions'
        ]
        
        actions_found = []
        for pattern in actions_paths:
            matches = self._find_directories_by_pattern(pattern)
            actions_found.extend(matches)
        
        if actions_found:
            evidence.append(f"Found {len(actions_found)} Actions directories")
            confidence += 0.4
            structure['actions_paths'] = actions_found
            
            # Check for action files
            action_files = self._find_files_by_pattern('*Action.php')
            if action_files:
                evidence.append(f"Found {len(action_files)} Action classes")
                confidence += 0.3
                structure['action_count'] = len(action_files)
        
        if confidence > 0.3:
            self.patterns.append(ProjectPattern(
                name='Actions',
                confidence=min(confidence, 1.0),
                evidence=evidence,
                structure=structure
            ))
    
    def _detect_dto_pattern(self):
        """Detect DTO (Data Transfer Objects) pattern"""
        evidence = []
        confidence = 0.0
        structure = {}
        
        # Check for DTO directories
        dto_paths = [
            'app/DTO',
            'app/DTOs',
            'app/DataTransferObjects',
            'app/Domain/*/DTO',
            'Modules/*/DTO'
        ]
        
        dto_found = []
        for pattern in dto_paths:
            matches = self._find_directories_by_pattern(pattern)
            dto_found.extend(matches)
        
        if dto_found:
            evidence.append(f"Found {len(dto_found)} DTO directories")
            confidence += 0.4
            structure['dto_paths'] = dto_found
            
            # Check for DTO files
            dto_files = self._find_files_by_pattern('*DTO.php')
            if dto_files:
                evidence.append(f"Found {len(dto_files)} DTO classes")
                confidence += 0.3
                structure['dto_count'] = len(dto_files)
        
        if confidence > 0.3:
            self.patterns.append(ProjectPattern(
                name='DTO',
                confidence=min(confidence, 1.0),
                evidence=evidence,
                structure=structure
            ))
    
    def _detect_repository_pattern(self):
        """Detect Repository pattern"""
        evidence = []
        confidence = 0.0
        structure = {}
        
        # Check for Repository files
        repo_files = self._find_files_by_pattern('*Repository.php')
        if repo_files:
            evidence.append(f"Found {len(repo_files)} Repository classes")
            confidence += 0.4
            structure['repository_count'] = len(repo_files)
            
            # Check for Repository interface
            interface_files = self._find_files_by_pattern('*RepositoryInterface.php')
            if interface_files:
                evidence.append("Found Repository interfaces")
                confidence += 0.2
                structure['uses_interfaces'] = True
        
        if confidence > 0.3:
            self.patterns.append(ProjectPattern(
                name='Repository',
                confidence=min(confidence, 1.0),
                evidence=evidence,
                structure=structure
            ))
    
    def _detect_service_pattern(self):
        """Detect Service layer pattern"""
        evidence = []
        confidence = 0.0
        structure = {}
        
        # Check for Services directory
        if self._directory_exists('Services'):
            evidence.append("Found Services directory")
            confidence += 0.4
            
            # Check for Service files
            service_files = self._find_files_by_pattern('*Service.php')
            if service_files:
                evidence.append(f"Found {len(service_files)} Service classes")
                confidence += 0.3
                structure['service_count'] = len(service_files)
        
        if confidence > 0.3:
            self.patterns.append(ProjectPattern(
                name='Service',
                confidence=min(confidence, 1.0),
                evidence=evidence,
                structure=structure
            ))
    
    def _get_primary_pattern(self) -> Optional[ProjectPattern]:
        """Get primary pattern based on confidence"""
        if not self.patterns:
            return None
        
        return max(self.patterns, key=lambda p: p.confidence)
    
    def _get_recommendations(self) -> Dict[str, str]:
        """Get recommendations for code generation"""
        recommendations = {}
        
        primary = self._get_primary_pattern()
        if not primary:
            recommendations['structure'] = 'standard_laravel'
            recommendations['controller_path'] = 'app/Http/Controllers'
            recommendations['model_path'] = 'app/Models'
            return recommendations
        
        if primary.name == 'DDD':
            recommendations['structure'] = 'ddd'
            recommendations['use_domains'] = True
            recommendations['use_value_objects'] = True
            recommendations['use_repositories'] = True
            
            if 'domains' in primary.structure:
                recommendations['available_domains'] = primary.structure['domains']
        
        elif primary.name == 'Modular':
            recommendations['structure'] = 'modular'
            recommendations['use_modules'] = True
            
            if 'modules' in primary.structure:
                recommendations['available_modules'] = primary.structure['modules']
        
        elif primary.name == 'Actions':
            recommendations['structure'] = 'actions'
            recommendations['use_actions'] = True
            recommendations['single_action_controllers'] = True
        
        # Check for additional patterns
        pattern_names = [p.name for p in self.patterns]
        
        if 'DTO' in pattern_names:
            recommendations['use_dtos'] = True
        
        if 'Repository' in pattern_names:
            recommendations['use_repositories'] = True
        
        if 'Service' in pattern_names:
            recommendations['use_services'] = True
        
        return recommendations
    
    def get_file_path_for_type(self, file_type: str, context: Dict = None) -> str:
        """Get appropriate file path based on detected patterns"""
        primary = self._get_primary_pattern()
        context = context or {}
        
        if primary and primary.name == 'Modular':
            module = context.get('module') or primary.structure.get('modules', [''])[0]
            
            paths = {
                'controller': f'Modules/{module}/Http/Controllers',
                'model': f'Modules/{module}/Entities',
                'action': f'Modules/{module}/Actions',
                'dto': f'Modules/{module}/DTO',
                'repository': f'Modules/{module}/Repositories',
                'service': f'Modules/{module}/Services'
            }
            
            return paths.get(file_type, f'Modules/{module}')
        
        elif primary and primary.name == 'DDD':
            domain = context.get('domain', 'Core')
            
            paths = {
                'controller': f'app/Application/Controllers',
                'model': f'app/Domain/{domain}/Models',
                'entity': f'app/Domain/{domain}/Entities',
                'action': f'app/Domain/{domain}/Actions',
                'dto': f'app/Domain/{domain}/DTO',
                'repository': f'app/Domain/{domain}/Repositories',
                'service': f'app/Domain/{domain}/Services',
                'value_object': f'app/Domain/{domain}/ValueObjects'
            }
            
            return paths.get(file_type, f'app/Domain/{domain}')
        
        else:
            # Standard Laravel
            paths = {
                'controller': 'app/Http/Controllers',
                'model': 'app/Models',
                'action': 'app/Actions',
                'dto': 'app/DTO',
                'repository': 'app/Repositories',
                'service': 'app/Services'
            }
            
            return paths.get(file_type, 'app')
    
    # Helper methods
    
    def _directory_exists(self, name: str) -> bool:
        """Check if directory exists in app/"""
        return name in str(self.directory_structure)
    
    def _find_directory(self, names: List[str]) -> Optional[str]:
        """Find first matching directory"""
        for name in names:
            if self._directory_exists(name):
                return name
        return None
    
    def _get_subdirectories(self, path: str) -> List[str]:
        """Get subdirectories of a path"""
        full_path = os.path.join(self.project_root, 'app', path)
        if not os.path.exists(full_path):
            return []
        
        return [d for d in os.listdir(full_path) 
                if os.path.isdir(os.path.join(full_path, d))]
    
    def _find_directories_by_pattern(self, pattern: str) -> List[str]:
        """Find directories matching pattern"""
        import glob
        full_pattern = os.path.join(self.project_root, pattern)
        return glob.glob(full_pattern)
    
    def _find_files_by_pattern(self, pattern: str) -> List[str]:
        """Find files matching pattern"""
        import glob
        full_pattern = os.path.join(self.project_root, 'app', '**', pattern)
        return glob.glob(full_pattern, recursive=True)
    
    def _file_pattern_exists(self, pattern: str) -> bool:
        """Check if files matching pattern exist"""
        return len(self._find_files_by_pattern(pattern)) > 0


def analyze_project_structure(project_root: str) -> Dict[str, any]:
    """Analyze project structure and return recommendations"""
    analyzer = ProjectStructureAnalyzer(project_root)
    return analyzer.analyze()
