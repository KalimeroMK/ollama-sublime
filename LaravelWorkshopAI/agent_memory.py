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
    context, Any]
    importance = 5  # 1-10 scale
    tags = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def to_dict(self):
        return asdict(self)
    
    @staticmethod
    def from_dict(data) -> 'MemoryEntry':
        return MemoryEntry(**data)


class AgentMemoryStore:
    """
    Persistent memory storage for agents
    Stores conversation history, learned patterns, and project context
    """
    
    def __init__(self, storage_path = None):
        if storage_path is None:
            # Use Sublime's package storage
            storage_path = os.path.join(
                sublime.packages_path(),
                'User',
                'LaravelWorkshopAI',
                'agent_memory.json'
            )
        
        self.storage_path = storage_path
        self.memories = []
        self.load()
    
    def load(self):
        """Load memories from disk"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r', encoding='utf-8') as f = json.load(f)
                    self.memories = [MemoryEntry.from_dict(m) for m in data]
        except Exception as e:
            print("Error loading agent memory: {0}".format(e))
            self.memories = []
    
    def save(self):
        """Save memories to disk"""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f = [m.to_dict() for m in self.memories]
                json.dump(data, f, indent=2)
        except Exception as e:
            print("Error saving agent memory: {0}".format(e))
    
    def add(
        self,
        content,
        context,
        importance = 5,
        tags = None
    ):
        """Add a new memory"""
        import hashlib
        memory_id = hashlib.md5(
            "{0}{1}".format(content, time.time()).encode()
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
        query = None,
        tags = None,
        min_importance = 0,
        limit = 10
    ):
        """Search memories"""
        results = self.memories
        
        # Filter by tags
        if tags = [
                m for m in results
                if any(tag in m.tags for tag in tags)
            ]
        
        # Filter by importance
        results = [m for m in results if m.importance >= min_importance]
        
        # Filter by query (simple substring match)
        if query = query.lower()
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
    
    def get_recent(self, limit = 10):
        """Get most recent memories"""
        sorted_memories = sorted(
            self.memories,
            key=lambda m: m.timestamp,
            reverse=True
        )
        return sorted_memories[:limit]
    
    def get_by_context(
        self,
        context_key,
        context_value,
        limit = 10
    ):
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
    
    def prune(self, max_age_days = 30, min_importance = 3):
        """Remove old, low-importance memories"""
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60
        
        self.memories = [
            m for m in self.memories
            if (current_time - m.timestamp) < max_age_seconds
            or m.importance >= min_importance
        ]
        
        self.save()
    
    def get_stats(self):
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
    
    def __init__(self, max_messages = 50):
        self.max_messages = max_messages
        self.messages, str]] = []
        self.summary = None
    
    def add_message(self, role, content):
        """Add a message to conversation history"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        
        # Trim if too long
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def get_messages(self, last_n = None):
        """Get conversation messages"""
        if last_n:
            return self.messages[-last_n:]
        return self.messages
    
    def get_context_window(self, max_tokens = 2000):
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
    
    def to_dict(self):
        """Export to dictionary"""
        return {
            "messages": self.messages,
            "summary": self.summary
        }
    
    @staticmethod
    def from_dict(data) -> 'ConversationMemory':
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
    
    def __init__(self, project_root):
        self.project_root = project_root
        self.knowledge, Any] = {
            "file_patterns": {},
            "coding_conventions": [],
            "common_imports": [],
            "project_structure": {},
            "learned_patterns": []
        }
        self.load()
    
    def get_storage_path(self):
        """Get storage path for this project"""
        import hashlib
        project_hash = hashlib.md5(self.project_root.encode()).hexdigest()
        return os.path.join(
            sublime.packages_path(),
            'User',
            'LaravelWorkshopAI',
            'projects',
            '{0}.json'.format(project_hash)
        )
    
    def load(self):
        """Load project knowledge"""
        try = self.get_storage_path()
            if os.path.exists(storage_path):
                with open(storage_path, 'r', encoding='utf-8') as f:
                    self.knowledge = json.load(f)
        except Exception as e:
            print("Error loading project memory: {0}".format(e))
    
    def save(self):
        """Save project knowledge"""
        try = self.get_storage_path()
            os.makedirs(os.path.dirname(storage_path), exist_ok=True)
            with open(storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge, f, indent=2)
        except Exception as e:
            print("Error saving project memory: {0}".format(e))
    
    def learn_pattern(self, pattern, description):
        """Learn a new pattern"""
        self.knowledge["learned_patterns"].append({
            "pattern": pattern,
            "description": description,
            "timestamp": time.time()
        })
        self.save()
    
    def learn_convention(self, convention):
        """Learn a coding convention"""
        if convention not in self.knowledge["coding_conventions"]:
            self.knowledge["coding_conventions"].append(convention)
            self.save()
    
    def get_context_summary(self):
        """Get a summary of project knowledge"""
        summary_parts = []
        
        if self.knowledge["coding_conventions"]:
            summary_parts.append(
                "Coding conventions:\n" +
                "\n".join("- {0}".format(c) for c in self.knowledge["coding_conventions"][:5])
            )
        
        if self.knowledge["learned_patterns"]:
            summary_parts.append(
                "Common patterns:\n" +
                "\n".join(
                    "- {0}".format(p['description'])
                    for p in self.knowledge["learned_patterns"][-5:]
                )
            )
        
        return "\n\n".join(summary_parts) if summary_parts else "No learned patterns yet"


# Global memory store instance
_global_memory_store = None


def get_global_memory_store():
    """Get or create global memory store"""
    global _global_memory_store
    if _global_memory_store is None = AgentMemoryStore()
    return _global_memory_store
