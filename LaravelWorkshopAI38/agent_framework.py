"""
Minimal, compile-safe Agent Framework used by Laravel Workshop AI.

Public API (kept stable):
- AgentRole (Enum)
- Tool (dataclass)
- AgentMessage (dataclass)
- Task (dataclass)
- Agent (class)
- AgentCrew (class)
- AgentWorkflow (class)
- create_agent_workflow(api_client)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .project_structure_analyzer import analyze_project_structure


class AgentRole(Enum):
    ARCHITECT = "architect"
    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"
    DEBUGGER = "debugger"
    REFACTORER = "refactorer"


@dataclass
class Tool:
    name: str
    description: str
    function: Callable[..., Any]
    parameters: Dict[str, Any] = field(default_factory=dict)

    def execute(self, **kwargs) -> Any:
        return self.function(**kwargs)


@dataclass
class AgentMessage:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    description: str
    agent_role: AgentRole
    context: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    output: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed, failed


class Agent:
    def __init__(
        self,
        role: AgentRole,
        goal: str,
        backstory: str,
        api_client: Any,
        tools: Optional[List[Tool]] = None,
        memory: Optional[List[AgentMessage]] = None,
        project_root: Optional[str] = None,
    ) -> None:
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.api_client = api_client
        self.tools = tools or []
        self.memory = memory or []
        self.max_iterations = 3
        self.project_root = project_root
        self.project_structure = None

        if self.project_root:
            self._analyze_project_structure()

    def get_system_prompt(self) -> str:
        tools_desc = "\n".join(f"- {t.name}: {t.description}" for t in self.tools) or "No tools available"
        return (
            f"You are a {self.role.value} agent.\n\n"
            f"Role: {self.role.value.upper()}\n"
            f"Goal: {self.goal}\n"
            f"Backstory: {self.backstory}\n\n"
            f"Available Tools:\n{tools_desc}\n\n"
            "When you need to use a tool, respond with JSON: {\"tool\": \"name\", \"parameters\": {..}}\n"
            "When completed, respond with: {\"status\": \"completed\", \"result\": \"...\"}"
        )

    def execute_task(self, task: Task) -> str:
        task.status = "in_progress"
        prompt = self._build_task_prompt(task)

        if not self.memory:
            self.memory.append(AgentMessage(role="system", content=self.get_system_prompt()))
        self.memory.append(AgentMessage(role="user", content=prompt))

        response = self.api_client.make_blocking_request(prompt)
        if not response:
            task.status = "failed"
            return "Error: No response from AI"

        self.memory.append(AgentMessage(role="assistant", content=response))
        task.status = "completed"
        task.output = response
        return response

    def _build_task_prompt(self, task: Task) -> str:
        context_lines = [f"- {k}: {v}" for k, v in (task.context or {}).items()] or ["No additional context"]
        structure_context = self._get_structure_context()
        return (
            f"Task: {task.description}\n\nContext:\n" + "\n".join(context_lines) +
            (f"\n{structure_context}\n" if structure_context else "\n") +
            "Please complete this task step by step."
        )

    def _parse_tool_call(self, response: str) -> Optional[Dict[str, Any]]:
        return None

    def _execute_tool(self, tool_call: Dict[str, Any]) -> str:
        name = tool_call.get("tool") if tool_call else None
        params = tool_call.get("parameters", {}) if tool_call else {}
        for t in self.tools:
            if t.name == name:
                try:
                    return str(t.execute(**params))
                except Exception as e:
                    return f"Error executing tool {name}: {e}"
        return f"Error: Tool '{name}' not found"

    def _analyze_project_structure(self) -> None:
        try:
            self.project_structure = analyze_project_structure(self.project_root or "")
        except Exception:
            self.project_structure = None

    def _get_structure_context(self) -> str:
        ps = self.project_structure or {}
        primary = ps.get("primary_pattern")
        if not primary:
            return ""
        parts = [f"\nProject Structure: {primary.name}"]
        try:
            parts.append(f"Confidence: {primary.confidence:.0%}")
        except Exception:
            pass
        ev = getattr(primary, "evidence", []) or []
        if ev:
            parts.append("\nEvidence:")
            parts += [f"  - {e}" for e in ev[:3]]
        parts.append("\nIMPORTANT: Follow this structure when generating code!")
        return "\n".join(parts)


class AgentCrew:
    def __init__(self, agents: List[Agent], tasks: List[Task]) -> None:
        self.agents = agents
        self.tasks = tasks
        self.execution_log: List[str] = []

    def kickoff(self) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        for task in self.tasks:
            agent = self._find_agent_for_task(task)
            if not agent:
                task.status = "failed"
                results[task.description] = "Error: No agent found for task"
                continue
            self.execution_log.append(f"Starting task: {task.description} with {agent.role.value}")
            result = agent.execute_task(task)
            results[task.description] = result
            self.execution_log.append(f"Completed task: {task.description}")
        return {"results": results, "log": self.execution_log, "tasks": self.tasks}

    def _find_agent_for_task(self, task: Task) -> Optional[Agent]:
        for agent in self.agents:
            if agent.role == task.agent_role:
                return agent
        return None


class AgentWorkflow:
    def __init__(self, api_client: Any) -> None:
        self.api_client = api_client

    def create_feature_from_description(self, description: str, project_context: Dict[str, Any], tools: Optional[List[Tool]] = None) -> Dict[str, Any]:
        architect = Agent(AgentRole.ARCHITECT, "Design architecture", "Senior architect", self.api_client, tools)
        coder = Agent(AgentRole.CODER, "Implement feature", "Senior developer", self.api_client, tools)
        reviewer = Agent(AgentRole.REVIEWER, "Review quality", "Senior reviewer", self.api_client, tools)

        tasks = [
            Task(description=f"Design architecture for: {description}", agent_role=AgentRole.ARCHITECT, context=project_context),
            Task(description=f"Implement the feature: {description}", agent_role=AgentRole.CODER, context=project_context, dependencies=["architecture"]),
            Task(description=f"Review the implementation for: {description}", agent_role=AgentRole.REVIEWER, context=project_context, dependencies=["implementation"]),
        ]
        crew = AgentCrew([architect, coder, reviewer], tasks)
        return crew.kickoff()

    def debug_code(self, code: str, error_message: str, context: Dict[str, Any], tools: Optional[List[Tool]] = None) -> Dict[str, Any]:
        debugger = Agent(AgentRole.DEBUGGER, "Find and fix bug", "Expert debugger", self.api_client, tools)
        task = Task(description=f"Debug this code:\n\n{code}\n\nError: {error_message}", agent_role=AgentRole.DEBUGGER, context=context)
        crew = AgentCrew([debugger], [task])
        return crew.kickoff()

    def refactor_code(self, code: str, context: Dict[str, Any], tools: Optional[List[Tool]] = None) -> Dict[str, Any]:
        refactorer = Agent(AgentRole.REFACTORER, "Improve code quality", "Refactoring expert", self.api_client, tools)
        task = Task(description=f"Refactor this code:\n\n{code}", agent_role=AgentRole.REFACTORER, context=context)
        crew = AgentCrew([refactorer], [task])
        return crew.kickoff()


def create_agent_workflow(api_client: Any) -> AgentWorkflow:
    return AgentWorkflow(api_client)
