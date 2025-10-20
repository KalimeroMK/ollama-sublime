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
    parameters, Any] = field(default_factory=dict)
    
    def execute(self, **kwargs):
        """Execute the tool with given parameters"""
        return self.function(**kwargs)


@dataclass
class AgentMessage:
    """Message in agent conversation"""
    role: str
    content: str
    timestamp = field(default_factory=time.time)
    metadata, Any] = field(default_factory=dict)


@dataclass
class Task:
    """Represents a task for an agent to complete"""
    description: str
    agent_role: AgentRole
    context, Any] = field(default_factory=dict)
    dependencies = field(default_factory=list)
    output = None
    status = "pending"  # pending, in_progress, completed, failed


class Agent:
    """
    Autonomous agent that can perform tasks using local Ollama models
    Similar to CrewAI agents but optimized for Sublime Text integration
    """
    
    def __init__(
        self,
        role,
        goal,
        backstory,
        api_client,
        tools = None,
        memory = None,
        project_root = None
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
        
    def get_system_prompt(self):
        """Generate system prompt based on agent role and capabilities"""
        tools_desc = "\n".join([
            "- {0}: {1}".format(tool.name, tool.description) 
            for tool in self.tools
        ]) if self.tools else "No tools available"
        
        return """You are a {self.role.value} agent.

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
    
    def execute_task(self, task):
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
            if tool_call = self._execute_tool(tool_call)
                self.memory.append(AgentMessage(
                    role="user",
                    content="Tool result: {0}".format(tool_result)
                ))
                continue
            
            # Check if task is completed
            if self._is_task_completed(response):
                task.status = "completed"
                task.output = self._extract_result(response)
                return task.output
        
        task.status = "failed"
        return "Error: Max iterations reached without completion"
    
    def _build_task_prompt(self, task):
        """Build comprehensive prompt for task"""
        context_str = "\n".join([
            "- {0}: {1}".format(key, value) 
            for key, value in task.context.items()
        ]) if task.context else "No additional context"
        
        # Add project structure context
        structure_context = self._get_structure_context()
        
        return """Task: {task.description}

Context:
{context_str}
{structure_context}

Please complete this task step by step. Use available tools if needed.
IMPORTANT: Respect the detected project structure and patterns!
"""
    
    def _parse_tool_call(self, response):
        """Parse tool call from agent response"""
        try:
            # Look for JSON in response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start = response[start:end]
                data = json.loads(json_str)
                if "tool" in data:
                    return data
        except json.JSONDecodeError:
            pass
        return None
    
    def _execute_tool(self, tool_call):
        """Execute a tool based on parsed call"""
        tool_name = tool_call.get("tool")
        parameters = tool_call.get("parameters", {})
        
        for tool in self.tools:
            if tool.name == tool_name:
                try = tool.execute(**parameters)
                    return str(result)
                except Exception as e:
                    return "Error executing tool {0}: {1}".format(tool_name, str(e))
        
        return "Error: Tool '{0}' not found".format(tool_name)
    
    def _analyze_project_structure(self):
        """Analyze project structure and store recommendations"""
        try:
            self.project_structure = analyze_project_structure(self.project_root)
        except Exception as e:
            print("Error analyzing project structure: {0}".format(e))
            self.project_structure = None
    
    def _get_structure_context(self):
        """Get project structure context for prompts"""
        if not self.project_structure:
            return ""
        
        primary = self.project_structure.get('primary_pattern')
        if not primary:
            return "\nProject Structure: Standard Laravel"
        
        recommendations = self.project_structure.get('recommendations', {})
        
        context_parts = ["\nProject Structure: {0}".format(primary.name)]
        context_parts.append("Confidence: {0}".format(primary.confidence:.0%))
        context_parts.append("\nEvidence:")
        for evidence in primary.evidence[:3]:
            context_parts.append("  - {0}".format(evidence))
        
        context_parts.append("\nIMPORTANT: Follow this structure when generating code!")
        
        if recommendations.get('use_modules'):
            modules = recommendations.get('available_modules', [])
            context_parts.append("\nModules: {0}".format(', '.join(modules[:5])))
            context_parts.append("Generate code in appropriate module directory")
        
        if recommendations.get('use_domains'):
            domains = recommendations.get('available_domains', [])
            context_parts.append("\nDomains: {0}".format(', '.join(domains[:5])))
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
    
    def _is_task_completed(self, response):
        """Check if agent indicates task completion"""
        try = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start = response[start:end]
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
    
    def _extract_result(self, response):
        """Extract final result from agent response"""
        try = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start = response[start:end]
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
    
    def __init__(self, agents, tasks):
        self.agents = agents
        self.tasks = tasks
        self.execution_log = []
        
    def kickoff(self):
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
            self.execution_log.append("Starting task: {0} with {1}".format(task.description, agent.role.value))
            result = agent.execute_task(task)
            results[task.description] = result
            self.execution_log.append("Completed task: {0}".format(task.description))
        
        return {
            "results": results,
            "log": self.execution_log,
            "tasks": self.tasks
        }
    
    def _find_agent_for_task(self, task):
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
        description,
        project_context,
        tools = None
    ):
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
                description="Design architecture for: {0}".format(description),
                agent_role=AgentRole.ARCHITECT,
                context=project_context
            ),
            Task(
                description="Implement the feature: {0}".format(description),
                agent_role=AgentRole.CODER,
                context=project_context,
                dependencies=["architecture"]
            ),
            Task(
                description="Review the implementation for: {0}".format(description),
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
        code,
        error_message,
        context,
        tools = None
    ):
        """Debug code using specialized debugger agent"""
        
        debugger = Agent(
            role=AgentRole.DEBUGGER,
            goal="Find and fix the bug in the code",
            backstory="You are an expert debugger who can quickly identify and fix issues",
            api_client=self.api_client,
            tools=tools
        )
        
        task = Task(
            description="Debug this code:\n\n{0}\n\nError: {1}".format(code, error_message),
            agent_role=AgentRole.DEBUGGER,
            context=context
        )
        
        crew = AgentCrew(agents=[debugger], tasks=[task])
        return crew.kickoff()
    
    def refactor_code(
        self,
        code,
        context,
        tools = None
    ):
        """Refactor code using specialized refactorer agent"""
        
        refactorer = Agent(
            role=AgentRole.REFACTORER,
            goal="Improve code quality, readability, and maintainability",
            backstory="You are an expert at refactoring code to follow best practices",
            api_client=self.api_client,
            tools=tools
        )
        
        task = Task(
            description="Refactor this code:\n\n{0}".format(code),
            agent_role=AgentRole.REFACTORER,
            context=context
        )
        
        crew = AgentCrew(agents=[refactorer], tasks=[task])
        return crew.kickoff()


# Factory function for easy integration
def create_agent_workflow(api_client):
    """Create an agent workflow instance"""
    return AgentWorkflow(api_client)
