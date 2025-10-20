"""
Sublime Text commands that use AI agents for autonomous code generation
These commands provide Cursor/Windsurf-like experience
"""

import sublime
import sublime_plugin
import json
import os
from typing import Dict, Any

from .laravel_workshop_api import create_api_client_from_settings
from .agent_framework import create_agent_workflow, AgentRole, Agent, Task, AgentCrew
from .agent_tools import create_default_tools
from .ui_helpers import UIHelpers, TabManager
from .context_analyzer import ContextAnalyzer


class LaravelWorkshopAgentGenerateFeatureCommand(sublime_plugin.WindowCommand):
    """
    Generate a complete feature using AI agents
    This is the main "agentic" command - like Cursor's "Generate with AI"
    """
    
    def run(self):
        UIHelpers.show_input_panel(
            self.window,
            "Describe the feature you want to create:",
            "",
            self.on_description
        )
    
    def on_description(self, description):
        if not description.strip():
            return
        
        self.description = description
        
        # Get API client
        api_client = create_api_client_from_settings()
        
        # Get project context
        view = self.window.active_view()
        context_analyzer = ContextAnalyzer.from_view(view)
        
        project_context = {
            "description": description,
            "project_root": context_analyzer.project_root if context_analyzer else None,
            "current_file": view.file_name() if view else None,
            "language": view.settings().get('syntax', '').split('/')[-1].replace('.sublime-syntax', '') if view else 'unknown'
        }
        
        # Create output tab for progress
        tab_manager = TabManager(self.window)
        output_tab = tab_manager.create_output_tab(
            "agent_feature",
            "AI Agent: Feature Generation",
            "🤖 Generating feature: {0}\n\n".format(description),
            api_client.model
        )
        
        def append_log(message):
            UIHelpers.append_to_tab(output_tab, message + "\n")
        
        # Run agent workflow asynchronously
        def run_workflow():
            try:
                append_log("🚀 Starting AI agent workflow...\n")
                append_log("📋 Phase 1: Architecture Design\n")
                
                # Create workflow
                workflow = create_agent_workflow(api_client)
                tools = create_default_tools()
                
                # Execute feature creation
                result = workflow.create_feature_from_description(
                    description,
                    project_context,
                    tools
                )
                
                # Display results
                append_log("\n" + "="*50 + "\n")
                append_log("✅ Agent workflow completed!\n\n")
                
                for task_desc, task_result in result["results"].items():
                    append_log("📌 {0}\n".format(task_desc))
                    append_log("{0}\n\n".format(task_result))
                
                append_log("\n" + "="*50 + "\n")
                append_log("📝 Execution Log:\n")
                for log_entry in result["log"]:
                    append_log("  • {0}\n".format(log_entry))
                
                # Show completion message
                sublime.status_message("✅ AI Agent feature generation completed!")
                
            except Exception as e:
                append_log("\n❌ Error: {0}\n".format(str(e)))
                sublime.status_message("❌ Agent workflow failed: {0}".format(str(e)))
        
        sublime.set_timeout_async(run_workflow, 0)


class LaravelWorkshopAgentDebugCommand(sublime_plugin.TextCommand):
    """
    Debug selected code using AI agent
    Agent will analyze, find issues, and suggest fixes
    """
    
    def run(self, edit):
        # Get selected code
        selected_text = UIHelpers.get_selected_text(self.view)
        if not selected_text.strip():
            sublime.status_message("Please select code to debug")
            return
        
        # Ask for error message
        UIHelpers.show_input_panel(
            self.view.window(),
            "Describe the error or issue (optional):",
            "",
            lambda error_msg: self.start_debugging(selected_text, error_msg)
        )
    
    def start_debugging(self, code, error_message):
        # Get API client
        api_client = create_api_client_from_settings()
        
        # Get context
        context_analyzer = ContextAnalyzer.from_view(self.view)
        context = {
            "file_path": self.view.file_name() or "unknown",
            "language": self.view.settings().get('syntax', '').split('/')[-1].replace('.sublime-syntax', ''),
            "project_root": context_analyzer.project_root if context_analyzer else None
        }
        
        # Create output tab
        tab_manager = TabManager(self.view.window())
        output_tab = tab_manager.create_output_tab(
            "agent_debug",
            "AI Agent: Debug",
            "🐛 Debugging code...\n\nError: {0}\n\n".format(error_message or 'Not specified'),
            api_client.model
        )
        
        def append_log(message):
            UIHelpers.append_to_tab(output_tab, message + "\n")
        
        # Run debugging workflow
        def run_debug():
            try:
                append_log("🔍 Starting debug analysis...\n")
                
                workflow = create_agent_workflow(api_client)
                tools = create_default_tools()
                
                result = workflow.debug_code(code, error_message, context, tools)
                
                append_log("\n" + "="*50 + "\n")
                append_log("✅ Debug analysis completed!\n\n")
                
                for task_desc, task_result in result["results"].items():
                    append_log("{0}\n\n".format(task_result))
                
                sublime.status_message("✅ Debug analysis completed!")
                
            except Exception as e:
                append_log("\n❌ Error: {0}\n".format(str(e)))
                sublime.status_message("❌ Debug failed: {0}".format(str(e)))
        
        sublime.set_timeout_async(run_debug, 0)
    
    def is_visible(self):
        return UIHelpers.has_selection(self.view)


class LaravelWorkshopAgentRefactorCommand(sublime_plugin.TextCommand):
    """
    Refactor selected code using AI agent
    Agent will improve code quality and suggest best practices
    """
    
    def run(self, edit):
        # Get selected code
        selected_text = UIHelpers.get_selected_text(self.view)
        if not selected_text.strip():
            sublime.status_message("Please select code to refactor")
            return
        
        # Get API client
        api_client = create_api_client_from_settings()
        
        # Get context
        context_analyzer = ContextAnalyzer.from_view(self.view)
        context = {
            "file_path": self.view.file_name() or "unknown",
            "language": self.view.settings().get('syntax', '').split('/')[-1].replace('.sublime-syntax', ''),
            "project_root": context_analyzer.project_root if context_analyzer else None
        }
        
        # Create output tab
        tab_manager = TabManager(self.view.window())
        output_tab = tab_manager.create_output_tab(
            "agent_refactor",
            "AI Agent: Refactor",
            "♻️ Refactoring code...\n\n",
            api_client.model
        )
        
        def append_log(message):
            UIHelpers.append_to_tab(output_tab, message + "\n")
        
        # Run refactoring workflow
        def run_refactor():
            try:
                append_log("🔧 Starting refactoring analysis...\n")
                
                workflow = create_agent_workflow(api_client)
                tools = create_default_tools()
                
                result = workflow.refactor_code(selected_text, context, tools)
                
                append_log("\n" + "="*50 + "\n")
                append_log("✅ Refactoring completed!\n\n")
                
                for task_desc, task_result in result["results"].items():
                    append_log("{0}\n\n".format(task_result))
                
                sublime.status_message("✅ Refactoring completed!")
                
            except Exception as e:
                append_log("\n❌ Error: {0}\n".format(str(e)))
                sublime.status_message("❌ Refactoring failed: {0}".format(str(e)))
        
        sublime.set_timeout_async(run_refactor, 0)
    
    def is_visible(self):
        return UIHelpers.has_selection(self.view)


class LaravelWorkshopAgentCustomTaskCommand(sublime_plugin.WindowCommand):
    """
    Execute a custom task using AI agents
    User can describe any task and agents will try to complete it
    """
    
    def run(self):
        UIHelpers.show_input_panel(
            self.window,
            "Describe the task for AI agents:",
            "",
            self.on_task_description
        )
    
    def on_task_description(self, task_description):
        if not task_description.strip():
            return
        
        # Ask which agent role to use
        roles = [
            ["🏗️ Architect", "Design system architecture"],
            ["💻 Coder", "Write code implementation"],
            ["🔍 Reviewer", "Review code quality"],
            ["🧪 Tester", "Write tests"],
            ["🐛 Debugger", "Find and fix bugs"],
            ["♻️ Refactorer", "Improve code quality"]
        ]
        
        def on_role_select(index):
            if index == -1:
                return
            
            role_map = {
                0: AgentRole.ARCHITECT,
                1: AgentRole.CODER,
                2: AgentRole.REVIEWER,
                3: AgentRole.TESTER,
                4: AgentRole.DEBUGGER,
                5: AgentRole.REFACTORER
            }
            
            selected_role = role_map[index]
            self.execute_custom_task(task_description, selected_role)
        
        self.window.show_quick_panel(roles, on_role_select)
    
    def execute_custom_task(self, task_description, agent_role):
        # Get API client
        api_client = create_api_client_from_settings()
        
        # Get context
        view = self.window.active_view()
        context_analyzer = ContextAnalyzer.from_view(view)
        
        context = {
            "task": task_description,
            "project_root": context_analyzer.project_root if context_analyzer else None,
            "current_file": view.file_name() if view else None
        }
        
        # Create output tab
        tab_manager = TabManager(self.window)
        output_tab = tab_manager.create_output_tab(
            "agent_custom",
            "AI Agent: {0}".format(agent_role.value.title()),
            "🤖 Executing task: {0}\n\n".format(task_description),
            api_client.model
        )
        
        def append_log(message):
            UIHelpers.append_to_tab(output_tab, message + "\n")
        
        # Run custom task
        def run_task():
            try:
                append_log("🚀 Starting {0} agent...\n".format(agent_role.value))
                
                # Create agent
                tools = create_default_tools()
                agent = Agent(
                    role=agent_role,
                    goal="Complete the task: {0}".format(task_description),
                    backstory="You are an expert {0} who excels at this type of work".format(agent_role.value),
                    api_client=api_client,
                    tools=tools
                )
                
                # Create task
                task = Task(
                    description=task_description,
                    agent_role=agent_role,
                    context=context
                )
                
                # Execute
                crew = AgentCrew(agents=[agent], tasks=[task])
                result = crew.kickoff()
                
                append_log("\n" + "="*50 + "\n")
                append_log("✅ Task completed!\n\n")
                
                for task_desc, task_result in result["results"].items():
                    append_log("{0}\n\n".format(task_result))
                
                sublime.status_message("✅ Agent task completed!")
                
            except Exception as e:
                append_log("\n❌ Error: {0}\n".format(str(e)))
                sublime.status_message("❌ Task failed: {0}".format(str(e)))
        
        sublime.set_timeout_async(run_task, 0)


class LaravelWorkshopAgentChatCommand(sublime_plugin.WindowCommand):
    """
    Interactive chat with AI agent
    Maintains conversation history and context
    """
    
    def __init__(self, window):
        super().__init__(window)
        self.conversation_history = []
        self.agent = None
        self.output_tab = None
    
    def run(self):
        if not self.agent:
            self.start_new_conversation()
        else:
            self.continue_conversation()
    
    def start_new_conversation(self):
        # Ask for agent role
        roles = [
            ["💻 General Coding Assistant", "Help with any coding task"],
            ["🏗️ Architect", "Design system architecture"],
            ["🐛 Debugger", "Find and fix bugs"],
            ["♻️ Refactorer", "Improve code quality"]
        ]
        
        def on_role_select(index):
            if index == -1:
                return
            
            role_map = {
                0: AgentRole.CODER,
                1: AgentRole.ARCHITECT,
                2: AgentRole.DEBUGGER,
                3: AgentRole.REFACTORER
            }
            
            selected_role = role_map[index]
            self.initialize_agent(selected_role)
            self.continue_conversation()
        
        self.window.show_quick_panel(roles, on_role_select)
    
    def initialize_agent(self, role):
        api_client = create_api_client_from_settings()
        tools = create_default_tools()
        
        self.agent = Agent(
            role=role,
            goal="Assist the user with their coding tasks",
            backstory="You are a helpful {0} assistant".format(role.value),
            api_client=api_client,
            tools=tools
        )
        
        # Create output tab
        tab_manager = TabManager(self.window)
        self.output_tab = tab_manager.create_output_tab(
            "agent_chat",
            "AI Agent Chat: {0}".format(role.value.title()),
            "🤖 Chat with {0} agent\n\n".format(role.value),
            api_client.model
        )
    
    def continue_conversation(self):
        UIHelpers.show_input_panel(
            self.window,
            "You:",
            "",
            self.on_user_message
        )
    
    def on_user_message(self, message):
        if not message.strip():
            return
        
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": message})
        
        # Display user message
        UIHelpers.append_to_tab(self.output_tab, "\n👤 You: {0}\n\n".format(message))
        
        # Get agent response
        def get_response():
            try:
                UIHelpers.append_to_tab(self.output_tab, "🤖 Agent: ")
                
                # Create task
                task = Task(
                    description=message,
                    agent_role=self.agent.role,
                    context={"conversation_history": self.conversation_history}
                )
                
                # Execute
                response = self.agent.execute_task(task)
                
                # Add to conversation history
                self.conversation_history.append({"role": "assistant", "content": response})
                
                # Display response
                UIHelpers.append_to_tab(self.output_tab, "{0}\n\n".format(response))
                UIHelpers.append_to_tab(self.output_tab, "-" * 50 + "\n")
                
                # Continue conversation
                sublime.set_timeout(self.continue_conversation, 100)
                
            except Exception as e:
                UIHelpers.append_to_tab(self.output_tab, "\n❌ Error: {0}\n".format(str(e)))
        
        sublime.set_timeout_async(get_response, 0)
