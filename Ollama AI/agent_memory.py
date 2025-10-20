"""
Persistent memory system for AI agents
Enables long-term context retention across sessions
"""

import json
import os
import time
import sublime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class MemoryEntry:
    """Single memory entry"""
    id: str
    content: str
    timestamp: float
    context: Dict[str, Any]
    importance: int = 5  # 1-10 scale
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict) -> 'MemoryEntry':
        return MemoryEntry(**data)


class AgentMemoryStore:
    """
    Persistent memory storage for agents
    Stores conversation history, learned patterns, and project context
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        if storage_path is None:
            # Use Sublime's package storage
            storage_path = os.path.join(
                sublime.packages_path(),
                'User',
                'OllamaAI',
                'agent_memory.json'
            )
        
        self.storage_path = storage_path
        self.memories: List[MemoryEntry] = []
        self.load()
    
    def load(self):
        """Load memories from disk"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memories = [MemoryEntry.from_dict(m) for m in data]
        except Exception as e:
            print(f"Error loading agent memory: {e}")
            self.memories = []
    
    def save(self):
        """Save memories to disk"""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                data = [m.to_dict() for m in self.memories]
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving agent memory: {e}")
    
    def add(
        self,
        content: str,
        context: Dict[str, Any],
        importance: int = 5,
        tags: List[str] = None
    ) -> MemoryEntry:
        """Add a new memory"""
        import hashlib
        memory_id = hashlib.md5(
            f"{content}{time.time()}".encode()
        ).hexdigest()
        
        memory = MemoryEntry(
            id=memory_id,
            content=content,
            timestamp=time.time(),
            context=context,
            importance=importance,
            tags=tags or []
        )
        
        self.memories.append(memory)
        self.save()
        return memory
    
    def search(
        self,
        query: str = None,
        tags: List[str] = None,
        min_importance: int = 0,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """Search memories"""
        results = self.memories
        
        # Filter by tags
        if tags:
            results = [
                m for m in results
                if any(tag in m.tags for tag in tags)
            ]
        
        # Filter by importance
        results = [m for m in results if m.importance >= min_importance]
        
        # Filter by query (simple substring match)
        if query:
            query_lower = query.lower()
            results = [
                m for m in results
                if query_lower in m.content.lower()
            ]
        
        # Sort by importance and recency
        results.sort(
            key=lambda m: (m.importance, m.timestamp),
            reverse=True
        )
        
        return results[:limit]
    
    def get_recent(self, limit: int = 10) -> List[MemoryEntry]:
        """Get most recent memories"""
        sorted_memories = sorted(
            self.memories,
            key=lambda m: m.timestamp,
            reverse=True
        )
        return sorted_memories[:limit]
    
    def get_by_context(
        self,
        context_key: str,
        context_value: Any,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """Get memories by context"""
        results = [
            m for m in self.memories
            if m.context.get(context_key) == context_value
        ]
        return results[:limit]
    
    def clear(self):
        """Clear all memories"""
        self.memories = []
        self.save()
    
    def prune(self, max_age_days: int = 30, min_importance: int = 3):
        """Remove old, low-importance memories"""
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60
        
        self.memories = [
            m for m in self.memories
            if (current_time - m.timestamp) < max_age_seconds
            or m.importance >= min_importance
        ]
        
        self.save()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        if not self.memories:
            return {
                "total": 0,
                "oldest": None,
                "newest": None,
                "avg_importance": 0,
                "tags": []
            }
        
        all_tags = set()
        for m in self.memories:
            all_tags.update(m.tags)
        
        return {
            "total": len(self.memories),
            "oldest": datetime.fromtimestamp(
                min(m.timestamp for m in self.memories)
            ).isoformat(),
            "newest": datetime.fromtimestamp(
                max(m.timestamp for m in self.memories)
            ).isoformat(),
            "avg_importance": sum(m.importance for m in self.memories) / len(self.memories),
            "tags": list(all_tags)
        }


class ConversationMemory:
    """
    Manages conversation history for agents
    Provides context window management and summarization
    """
    
    def __init__(self, max_messages: int = 50):
        self.max_messages = max_messages
        self.messages: List[Dict[str, str]] = []
        self.summary: Optional[str] = None
    
    def add_message(self, role: str, content: str):
        """Add a message to conversation history"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        
        # Trim if too long
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def get_messages(self, last_n: int = None) -> List[Dict[str, str]]:
        """Get conversation messages"""
        if last_n:
            return self.messages[-last_n:]
        return self.messages
    
    def get_context_window(self, max_tokens: int = 2000) -> List[Dict[str, str]]:
        """
        Get messages that fit within token limit
        Rough estimation: 1 token ≈ 4 characters
        """
        max_chars = max_tokens * 4
        total_chars = 0
        context = []
        
        # Start from most recent
        for msg in reversed(self.messages):
            msg_chars = len(msg["content"])
            if total_chars + msg_chars > max_chars:
                break
            context.insert(0, msg)
            total_chars += msg_chars
        
        return context
    
    def clear(self):
        """Clear conversation history"""
        self.messages = []
        self.summary = None
    
    def to_dict(self) -> Dict:
        """Export to dictionary"""
        return {
            "messages": self.messages,
            "summary": self.summary
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'ConversationMemory':
        """Import from dictionary"""
        conv = ConversationMemory()
        conv.messages = data.get("messages", [])
        conv.summary = data.get("summary")
        return conv


class ProjectMemory:
    """
    Stores project-specific knowledge
    Learns patterns, conventions, and structure
    """
    
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.knowledge: Dict[str, Any] = {
            "file_patterns": {},
            "coding_conventions": [],
            "common_imports": [],
            "project_structure": {},
            "learned_patterns": []
        }
        self.load()
    
    def get_storage_path(self) -> str:
        """Get storage path for this project"""
        import hashlib
        project_hash = hashlib.md5(self.project_root.encode()).hexdigest()
        return os.path.join(
            sublime.packages_path(),
            'User',
            'OllamaAI',
            'projects',
            f'{project_hash}.json'
        )
    
    def load(self):
        """Load project knowledge"""
        try:
            storage_path = self.get_storage_path()
            if os.path.exists(storage_path):
                with open(storage_path, 'r', encoding='utf-8') as f:
                    self.knowledge = json.load(f)
        except Exception as e:
            print(f"Error loading project memory: {e}")
    
    def save(self):
        """Save project knowledge"""
        try:
            storage_path = self.get_storage_path()
            os.makedirs(os.path.dirname(storage_path), exist_ok=True)
            with open(storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge, f, indent=2)
        except Exception as e:
            print(f"Error saving project memory: {e}")
    
    def learn_pattern(self, pattern: str, description: str):
        """Learn a new pattern"""
        self.knowledge["learned_patterns"].append({
            "pattern": pattern,
            "description": description,
            "timestamp": time.time()
        })
        self.save()
    
    def learn_convention(self, convention: str):
        """Learn a coding convention"""
        if convention not in self.knowledge["coding_conventions"]:
            self.knowledge["coding_conventions"].append(convention)
            self.save()
    
    def get_context_summary(self) -> str:
        """Get a summary of project knowledge"""
        summary_parts = []
        
        if self.knowledge["coding_conventions"]:
            summary_parts.append(
                "Coding conventions:\n" +
                "\n".join(f"- {c}" for c in self.knowledge["coding_conventions"][:5])
            )
        
        if self.knowledge["learned_patterns"]:
            summary_parts.append(
                "Common patterns:\n" +
                "\n".join(
                    f"- {p['description']}"
                    for p in self.knowledge["learned_patterns"][-5:]
                )
            )
        
        return "\n\n".join(summary_parts) if summary_parts else "No learned patterns yet"


# Global memory store instance
_global_memory_store: Optional[AgentMemoryStore] = None


def get_global_memory_store() -> AgentMemoryStore:
    """Get or create global memory store"""
    global _global_memory_store
    if _global_memory_store is None:
        _global_memory_store = AgentMemoryStore()
    return _global_memory_store
