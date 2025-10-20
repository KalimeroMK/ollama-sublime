"""
AI Agent Framework for Ollama Sublime
Inspired by CrewAI and AutoGen - enables autonomous code generation with local Ollama models
Now with intelligent project structure detection!
"""

import json
import os
import time
from typing import List, Dict, Callable, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from .project_structure_analyzer import analyze_project_structure


class AgentRole(Enum):
    """Define different agent roles for specialized tasks"""
    ARCHITECT = "architect"  # Designs system architecture
    CODER = "coder"  # Writes actual code
    REVIEWER = "reviewer"  # Reviews and suggests improvements
    TESTER = "tester"  # Writes tests
    DEBUGGER = "debugger"  # Finds and fixes bugs
    REFACTORER = "refactorer"  # Improves code quality


@dataclass
class Tool:
    """Represents a tool that agents can use"""
    name: str
    description: str
    function: Callable
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters"""
        return self.function(**kwargs)


@dataclass
class AgentMessage:
    """Message in agent conversation"""
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """Represents a task for an agent to complete"""
    description: str
    agent_role: AgentRole
    context: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    output: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed, failed


class Agent:
    """
    Autonomous agent that can perform tasks using local Ollama models
    Similar to CrewAI agents but optimized for Sublime Text integration
    """
    
    def __init__(
        self,
        role: AgentRole,
        goal: str,
        backstory: str,
        api_client,
        tools: List[Tool] = None,
        memory: List[AgentMessage] = None,
        project_root: str = None
    ):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.api_client = api_client
        self.tools = tools or []
        self.memory = memory or []
        self.max_iterations = 5
        self.project_root = project_root
        self.project_structure = None
        
        # Analyze project structure if provided
        if project_root:
            self._analyze_project_structure()
        
    def get_system_prompt(self) -> str:
        """Generate system prompt based on agent role and capabilities"""
        tools_desc = "\n".join([
            f"- {tool.name}: {tool.description}" 
            for tool in self.tools
        ]) if self.tools else "No tools available"
        
        return f"""You are a {self.role.value} agent.

Role: {self.role.value.upper()}
Goal: {self.goal}
Backstory: {self.backstory}

Available Tools:
{tools_desc}

When you need to use a tool, respond with JSON in this format:
{{"tool": "tool_name", "parameters": {{"param1": "value1"}}}}

When you have completed the task, respond with:
{{"status": "completed", "result": "your final output"}}

Always think step-by-step and explain your reasoning.
"""
    
    def execute_task(self, task: Task) -> str:
        """Execute a task using the agent's capabilities"""
        task.status = "in_progress"
        
        # Build context-aware prompt
        prompt = self._build_task_prompt(task)
        
        # Add system prompt to memory
        if not self.memory:
            self.memory.append(AgentMessage(
                role="system",
                content=self.get_system_prompt()
            ))
        
        # Add task to memory
        self.memory.append(AgentMessage(
            role="user",
            content=prompt
        ))
        
        # Execute with iteration loop (for tool calling)
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
            
            # Get response from LLM
            messages = [{"role": msg.role, "content": msg.content} for msg in self.memory]
            response = self.api_client.make_blocking_request(
                prompt="",  # Empty since we use messages
                messages=messages
            )
            
            if not response:
                task.status = "failed"
                return "Error: No response from LLM"
            
            # Add response to memory
            self.memory.append(AgentMessage(
                role="assistant",
                content=response
            ))
            
            # Check if agent wants to use a tool
            tool_call = self._parse_tool_call(response)
            if tool_call:
                tool_result = self._execute_tool(tool_call)
                self.memory.append(AgentMessage(
                    role="user",
                    content=f"Tool result: {tool_result}"
                ))
                continue
            
            # Check if task is completed
            if self._is_task_completed(response):
                task.status = "completed"
                task.output = self._extract_result(response)
                return task.output
        
        task.status = "failed"
        return "Error: Max iterations reached without completion"
    
    def _build_task_prompt(self, task: Task) -> str:
        """Build comprehensive prompt for task"""
        context_str = "\n".join([
            f"- {key}: {value}" 
            for key, value in task.context.items()
        ]) if task.context else "No additional context"
        
        # Add project structure context
        structure_context = self._get_structure_context()
        
        return f"""Task: {task.description}

Context:
{context_str}
{structure_context}

Please complete this task step by step. Use available tools if needed.
IMPORTANT: Respect the detected project structure and patterns!
"""
    
    def _parse_tool_call(self, response: str) -> Optional[Dict]:
        """Parse tool call from agent response"""
        try:
            # Look for JSON in response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)
                if "tool" in data:
                    return data
        except json.JSONDecodeError:
            pass
        return None
    
    def _execute_tool(self, tool_call: Dict) -> str:
        """Execute a tool based on parsed call"""
        tool_name = tool_call.get("tool")
        parameters = tool_call.get("parameters", {})
        
        for tool in self.tools:
            if tool.name == tool_name:
                try:
                    result = tool.execute(**parameters)
                    return str(result)
                except Exception as e:
                    return f"Error executing tool {tool_name}: {str(e)}"
        
        return f"Error: Tool '{tool_name}' not found"
    
    def _analyze_project_structure(self):
        """Analyze project structure and store recommendations"""
        try:
            self.project_structure = analyze_project_structure(self.project_root)
        except Exception as e:
            print(f"Error analyzing project structure: {e}")
            self.project_structure = None
    
    def _get_structure_context(self) -> str:
        """Get project structure context for prompts"""
        if not self.project_structure:
            return ""
        
        primary = self.project_structure.get('primary_pattern')
        if not primary:
            return "\nProject Structure: Standard Laravel"
        
        recommendations = self.project_structure.get('recommendations', {})
        
        context_parts = [f"\nProject Structure: {primary.name}"]
        context_parts.append(f"Confidence: {primary.confidence:.0%}")
        context_parts.append(f"\nEvidence:")
        for evidence in primary.evidence[:3]:
            context_parts.append(f"  - {evidence}")
        
        context_parts.append(f"\nIMPORTANT: Follow this structure when generating code!")
        
        if recommendations.get('use_modules'):
            modules = recommendations.get('available_modules', [])
            context_parts.append(f"\nModules: {', '.join(modules[:5])}")
            context_parts.append("Generate code in appropriate module directory")
        
        if recommendations.get('use_domains'):
            domains = recommendations.get('available_domains', [])
            context_parts.append(f"\nDomains: {', '.join(domains[:5])}")
            context_parts.append("Use Domain-Driven Design patterns")
        
        if recommendations.get('use_actions'):
            context_parts.append("\nUse Actions pattern (single-action classes)")
        
        if recommendations.get('use_dtos'):
            context_parts.append("Use DTOs for data transfer")
        
        if recommendations.get('use_repositories'):
            context_parts.append("Use Repository pattern for data access")
        
        if recommendations.get('use_services'):
            context_parts.append("Use Service layer for business logic")
        
        return "\n".join(context_parts)
    
    def _is_task_completed(self, response: str) -> bool:
        """Check if agent indicates task completion"""
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)
                return data.get("status") == "completed"
        except json.JSONDecodeError:
            pass
        
        # Also check for completion keywords
        completion_keywords = [
            "task completed",
            "finished",
            "done with",
            "successfully completed"
        ]
        return any(keyword in response.lower() for keyword in completion_keywords)
    
    def _extract_result(self, response: str) -> str:
        """Extract final result from agent response"""
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)
                if "result" in data:
                    return data["result"]
        except json.JSONDecodeError:
            pass
        
        # Return full response if no structured result
        return response


class AgentCrew:
    """
    Orchestrates multiple agents to work together on complex tasks
    Similar to CrewAI's Crew concept
    """
    
    def __init__(self, agents: List[Agent], tasks: List[Task]):
        self.agents = agents
        self.tasks = tasks
        self.execution_log = []
        
    def kickoff(self) -> Dict[str, Any]:
        """Start the crew execution"""
        results = {}
        
        for task in self.tasks:
            # Find agent with matching role
            agent = self._find_agent_for_task(task)
            if not agent:
                task.status = "failed"
                results[task.description] = "Error: No agent found for task"
                continue
            
            # Execute task
            self.execution_log.append(f"Starting task: {task.description} with {agent.role.value}")
            result = agent.execute_task(task)
            results[task.description] = result
            self.execution_log.append(f"Completed task: {task.description}")
        
        return {
            "results": results,
            "log": self.execution_log,
            "tasks": self.tasks
        }
    
    def _find_agent_for_task(self, task: Task) -> Optional[Agent]:
        """Find appropriate agent for a task"""
        for agent in self.agents:
            if agent.role == task.agent_role:
                return agent
        return None


class AgentWorkflow:
    """
    High-level workflow orchestrator for common coding tasks
    This is what makes it feel like Cursor/Windsurf
    """
    
    def __init__(self, api_client):
        self.api_client = api_client
        
    def create_feature_from_description(
        self,
        description: str,
        project_context: Dict[str, Any],
        tools: List[Tool] = None
    ) -> Dict[str, Any]:
        """
        Create a complete feature from description using multiple agents
        This is the main "agentic" workflow
        """
        
        # Create specialized agents
        architect = Agent(
            role=AgentRole.ARCHITECT,
            goal="Design the architecture and file structure for the feature",
            backstory="You are an expert software architect who designs clean, maintainable systems",
            api_client=self.api_client,
            tools=tools
        )
        
        coder = Agent(
            role=AgentRole.CODER,
            goal="Implement the feature based on architectural design",
            backstory="You are an expert programmer who writes clean, efficient code",
            api_client=self.api_client,
            tools=tools
        )
        
        reviewer = Agent(
            role=AgentRole.REVIEWER,
            goal="Review code for quality, security, and best practices",
            backstory="You are a senior code reviewer who ensures high quality standards",
            api_client=self.api_client,
            tools=tools
        )
        
        # Create tasks
        tasks = [
            Task(
                description=f"Design architecture for: {description}",
                agent_role=AgentRole.ARCHITECT,
                context=project_context
            ),
            Task(
                description=f"Implement the feature: {description}",
                agent_role=AgentRole.CODER,
                context=project_context,
                dependencies=["architecture"]
            ),
            Task(
                description=f"Review the implementation for: {description}",
                agent_role=AgentRole.REVIEWER,
                context=project_context,
                dependencies=["implementation"]
            )
        ]
        
        # Create and run crew
        crew = AgentCrew(
            agents=[architect, coder, reviewer],
            tasks=tasks
        )
        
        return crew.kickoff()
    
    def debug_code(
        self,
        code: str,
        error_message: str,
        context: Dict[str, Any],
        tools: List[Tool] = None
    ) -> Dict[str, Any]:
        """Debug code using specialized debugger agent"""
        
        debugger = Agent(
            role=AgentRole.DEBUGGER,
            goal="Find and fix the bug in the code",
            backstory="You are an expert debugger who can quickly identify and fix issues",
            api_client=self.api_client,
            tools=tools
        )
        
        task = Task(
            description=f"Debug this code:\n\n{code}\n\nError: {error_message}",
            agent_role=AgentRole.DEBUGGER,
            context=context
        )
        
        crew = AgentCrew(agents=[debugger], tasks=[task])
        return crew.kickoff()
    
    def refactor_code(
        self,
        code: str,
        context: Dict[str, Any],
        tools: List[Tool] = None
    ) -> Dict[str, Any]:
        """Refactor code using specialized refactorer agent"""
        
        refactorer = Agent(
            role=AgentRole.REFACTORER,
            goal="Improve code quality, readability, and maintainability",
            backstory="You are an expert at refactoring code to follow best practices",
            api_client=self.api_client,
            tools=tools
        )
        
        task = Task(
            description=f"Refactor this code:\n\n{code}",
            agent_role=AgentRole.REFACTORER,
            context=context
        )
        
        crew = AgentCrew(agents=[refactorer], tasks=[task])
        return crew.kickoff()


# Factory function for easy integration
def create_agent_workflow(api_client) -> AgentWorkflow:
    """Create an agent workflow instance"""
    return AgentWorkflow(api_client)
