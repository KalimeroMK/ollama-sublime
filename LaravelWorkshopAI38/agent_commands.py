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
from .project_scanner import scan_project, apply_fixes
from .controller_validation_scanner import scan_project_for_controller_validation
from .form_request_generator import generate_form_requests
from .form_request_refactor import build_refactor_plan, apply_controller_refactors, build_controller_refactor_diffs
from .worker_manager import get_worker_manager
from .project_indexer import build_project_index


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
        
        # Intent routing: allow natural-language commands to trigger scans
        intent = self.detect_intent(message)
        if intent:
            return self.handle_intent(intent)

        # Get agent response (default chat)
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

    def detect_intent(self, message: str):
        msg = (message or "").lower()
        # N+1 scan intents
        n1_phrases = ["n+1", "n + 1", "scan n+1", "skeniraj n+1", "eager load", "eagerload"]
        if any(p in msg for p in n1_phrases) and ("scan" in msg or "skenir" in msg or "proveri" in msg):
            return {"type": "nplusone"}
        # Controller validation intents
        ctrl_phrases = ["controller", "kontroler", "controllers", "kontroleri"]
        valid_phrases = ["validation", "validacija", "formrequest", "form request", "request class", "request klasi", "request klase"]
        if any(c in msg for c in ctrl_phrases) and any(v in msg for v in valid_phrases):
            return {"type": "controller_validation"}
        return None

    def handle_intent(self, intent: dict):
        if not self.output_tab:
            return
        window = self.window
        view = window.active_view()
        context_analyzer = ContextAnalyzer.from_view(view) if view else None
        project_root = context_analyzer.project_root if context_analyzer and context_analyzer.project_root else UIHelpers.ensure_project_folder(window)
        if not project_root:
            return

        settings = sublime.load_settings("LaravelWorkshopAI.sublime-settings")
        max_workers = settings.get("scanner_max_workers", 8)
        excludes = settings.get("scanner_excludes", ["vendor", "node_modules", ".git", "storage", "bootstrap", "build", "dist"]) or []

        if intent.get("type") == "nplusone":
            UIHelpers.append_to_tab(self.output_tab, "\n🔎 Scanning project for N+1...\n")

            def run_n1():
                try:
                    # Build index (routes/relations) to enrich scan
                    idx = build_project_index(project_root, max_workers=max_workers, excludes=excludes)
                    UIHelpers.append_to_tab(self.output_tab, "Index: models={0}, routes={1}\n".format(idx.get("stats", {}).get("models", 0), idx.get("stats", {}).get("routes", 0)))
                    rel_map = idx.get("relations_map", {}) or {}
                    known_rel = []
                    for arr in rel_map.values():
                        for r in arr or []:
                            if r and r not in known_rel:
                                known_rel.append(r)
                    summary = scan_project(project_root, max_workers=max_workers, excludes=excludes, known_relations=known_rel)
                    UIHelpers.append_to_tab(self.output_tab, "Total files: {0}\n".format(summary.get("total_files", 0)))
                    UIHelpers.append_to_tab(self.output_tab, "Problem files: {0}\n".format(summary.get("problem_files", 0)))
                    files = summary.get("problematic_files", [])
                    if files:
                        # Show Quick Panel of files; on select, show details/diffs
                        rels = [UIHelpers.get_project_relative_path(f, project_root) for f in files]

                        def on_pick(idx):
                            if idx == -1:
                                return
                            picked = files[idx]
                            rel = rels[idx]
                            UIHelpers.append_to_tab(self.output_tab, "\n=== {0} ===\n".format(rel))
                            # Find result entry and print diffs
                            for r in (summary.get("results") or []):
                                if r.get("file") == picked:
                                    diffs = r.get("diffs") or []
                                    if not diffs:
                                        UIHelpers.append_to_tab(self.output_tab, "No diff available.\n")
                                        return
                                    # Show first diff preview
                                    for d in diffs[:1]:
                                        changes = d.get("changes") or []
                                        UIHelpers.append_to_tab(self.output_tab, "Suggested changes: {0}\n".format(len(changes)))
                                        for (ln, old, new) in changes[:5]:
                                            UIHelpers.append_to_tab(self.output_tab, "  • L{0}: {1}→ {2}\n".format(ln + 1, old.strip()[:120], new.strip()[:120]))
                                    return

                        items = [[rels[i]] for i in range(len(rels))]
                        self.window.show_quick_panel(items, on_pick)

                        def on_choice(index):
                            if index == -1:
                                return
                            if index == 0:
                                diffs = summary.get("diffs", [])
                                res = apply_fixes(diffs)
                                UIHelpers.append_to_tab(self.output_tab, "\nApplied fixes: {0}\n".format(res.get("applied", 0)))
                            elif index == 1:
                                diffs = summary.get("diffs", [])
                                preview = []
                                for d in diffs[:50]:
                                    file_path = d.get("file")
                                    rel = UIHelpers.get_project_relative_path(file_path, project_root)
                                    changes = d.get("changes", [])
                                    preview.append("== {0} ==\n".format(rel))
                                    for idx, old, new in changes[:5]:
                                        preview.append("- {0}".format(old))
                                        preview.append("+ {0}".format(new))
                                    preview.append("\n")
                                UIHelpers.append_to_tab(self.output_tab, "\n" + "\n".join(preview))

                        items = [
                            ["Apply safe fixes now", "Writes changes to files with backup .bak"],
                            ["Show diffs preview", "View a summary of proposed changes"],
                            ["Cancel", "Do nothing"],
                        ]
                        window.show_quick_panel(items, on_choice)
                    else:
                        UIHelpers.append_to_tab(self.output_tab, "No N+1 patterns detected.\n")
                except Exception as e:
                    UIHelpers.append_to_tab(self.output_tab, "Error: {0}\n".format(str(e)))

            wm = get_worker_manager(max_workers=max_workers)
            wm.submit(run_n1, priority=1, key="scan:nplusone:" + (project_root or ""))
            return

        if intent.get("type") == "controller_validation":
            UIHelpers.append_to_tab(self.output_tab, "\n🔎 Scanning controllers for inline validation vs FormRequest...\n")

            def run_ctrl():
                try:
                    idx = build_project_index(project_root, max_workers=max_workers, excludes=excludes)
                    UIHelpers.append_to_tab(self.output_tab, "Index: models={0}, routes={1}\n".format(idx.get("stats", {}).get("models", 0), idx.get("stats", {}).get("routes", 0)))
                    summary = scan_project_for_controller_validation(project_root, max_workers=max_workers, excludes=excludes)
                    UIHelpers.append_to_tab(self.output_tab, summary.get("message", "") + "\n\n")
                    UIHelpers.append_to_tab(self.output_tab, "Total controllers: {0}\n".format(summary.get("total_controllers", 0)))
                    UIHelpers.append_to_tab(self.output_tab, "Problem files: {0}\n".format(summary.get("problem_files", 0)))
                    results = [r for r in summary.get("results", []) if r.get("issues_found")]
                    if results:
                        files = [r.get("file") for r in results]
                        rels = [UIHelpers.get_project_relative_path(p, project_root) for p in files]

                        def on_pick_ctrl(idx):
                            if idx == -1:
                                return
                            r = results[idx]
                            rel = rels[idx]
                            UIHelpers.append_to_tab(self.output_tab, "\n=== {0} ===\n".format(rel))
                            hits = r.get("inline_validation", [])
                            if not hits:
                                UIHelpers.append_to_tab(self.output_tab, "No inline validation found.\n")
                                return
                            for h in hits[:10]:
                                UIHelpers.append_to_tab(self.output_tab, "  • L{0}: {1}\n".format(h.get("line"), (h.get("snippet") or "").strip()[:200]))
                            if len(hits) > 10:
                                UIHelpers.append_to_tab(self.output_tab, "  • ...more omitted\n")

                        items = [[rels[i]] for i in range(len(rels))]
                        self.window.show_quick_panel(items, on_pick_ctrl)
                    if summary.get("problem_files", 0) == 0:
                        UIHelpers.append_to_tab(self.output_tab, "\nNo inline validation issues detected.\n")
                    else:
                        # Offer generation of FormRequest classes
                        def on_choice(index):
                            if index == -1:
                                return
                            if index == 0:
                                res = generate_form_requests(project_root, summary)
                                created = res.get("created", [])
                                skipped = res.get("skipped", [])
                                errors = res.get("errors", [])
                                UIHelpers.append_to_tab(self.output_tab, "\nGenerated FormRequest classes:\n")
                                for p in created:
                                    rel = UIHelpers.get_project_relative_path(p, project_root)
                                    UIHelpers.append_to_tab(self.output_tab, "  • {0}\n".format(rel))
                                if skipped:
                                    UIHelpers.append_to_tab(self.output_tab, "\nSkipped (already exists):\n")
                                    for p in skipped[:50]:
                                        rel = UIHelpers.get_project_relative_path(p, project_root)
                                        UIHelpers.append_to_tab(self.output_tab, "  • {0}\n".format(rel))
                                if errors:
                                    UIHelpers.append_to_tab(self.output_tab, "\nErrors:\n")
                                    for e in errors[:50]:
                                        UIHelpers.append_to_tab(self.output_tab, "  • {0}\n".format(e))
                                sublime.status_message("FormRequest generation completed")
                            elif index == 1:
                                # Preview diffs
                                UIHelpers.append_to_tab(self.output_tab, "\nBuilding refactor preview diffs...\n")
                                plan = build_refactor_plan(project_root, summary)
                                diffs = build_controller_refactor_diffs(plan)
                                if not diffs:
                                    UIHelpers.append_to_tab(self.output_tab, "No changes detected for refactor.\n")
                                    return
                                for d in diffs[:20]:
                                    rel = UIHelpers.get_project_relative_path(d.get("file"), project_root)
                                    UIHelpers.append_to_tab(self.output_tab, "\n=== {0} ===\n".format(rel))
                                    UIHelpers.append_to_tab(self.output_tab, d.get("diff", "") + "\n")
                                if len(diffs) > 20:
                                    UIHelpers.append_to_tab(self.output_tab, "\n...more diffs omitted\n")
                                sublime.status_message("Refactor preview generated")
                            elif index == 2:
                                # Build and apply controller refactor plan
                                UIHelpers.append_to_tab(self.output_tab, "\nPlanning controller refactor...\n")
                                plan = build_refactor_plan(project_root, summary)
                                items = plan.get("items", [])
                                UIHelpers.append_to_tab(self.output_tab, "Items to refactor: {0}\n".format(len(items)))
                                res = apply_controller_refactors(plan)
                                UIHelpers.append_to_tab(self.output_tab, "Applied: {0}\n".format(res.get("applied", 0)))
                                for p in res.get("changed_files", [])[:100]:
                                    rel = UIHelpers.get_project_relative_path(p, project_root)
                                    UIHelpers.append_to_tab(self.output_tab, "  • {0}\n".format(rel))
                                errs = res.get("errors", [])
                                if errs:
                                    UIHelpers.append_to_tab(self.output_tab, "\nErrors:\n")
                                    for e in errs[:50]:
                                        UIHelpers.append_to_tab(self.output_tab, "  • {0}\n".format(e))
                                sublime.status_message("Controller refactor completed")
                            else:
                                return

                        items = [
                            ["Generate FormRequest classes", "Auto-create classes in app/Http/Requests"],
                            ["Preview refactor diffs", "Show unified diffs before applying changes"],
                            ["Refactor controllers to use FormRequest", "Type-hint and replace validate() with validated()"],
                            ["Cancel", "Do nothing"],
                        ]
                        self.window.show_quick_panel(items, on_choice)
                except Exception as e:
                    UIHelpers.append_to_tab(self.output_tab, "Error: {0}\n".format(str(e)))

            wm = get_worker_manager(max_workers=max_workers)
            wm.submit(run_ctrl, priority=1, key="scan:controller_validation:" + (project_root or ""))
            return


class LaravelWorkshopAgentScanProjectCommand(sublime_plugin.WindowCommand):
    def run(self):
        window = self.window
        view = window.active_view()
        project_root = None
        context_analyzer = ContextAnalyzer.from_view(view) if view else None
        if context_analyzer and context_analyzer.project_root:
            project_root = context_analyzer.project_root
        if not project_root:
            project_root = UIHelpers.ensure_project_folder(window)
        if not project_root:
            return

        settings = sublime.load_settings("LaravelWorkshopAI.sublime-settings")
        max_workers = settings.get("scanner_max_workers", 8)
        excludes = settings.get("scanner_excludes", ["vendor", "node_modules", ".git", "storage", "bootstrap", "build", "dist"]) or []

        tab_manager = TabManager(window)
        output_tab = tab_manager.create_output_tab(
            "agent_scan_project",
            "AI Agent: Project Scan",
            "Scanning project for N+1 issues...\n\n",
            ""
        )

        def append(msg):
            UIHelpers.append_to_tab(output_tab, msg + "\n")

        def run_scan():
            try:
                append("Building index...")
                idx = build_project_index(project_root, max_workers=max_workers, excludes=excludes)
                append("Index: models={0}, routes={1}".format(idx.get("stats", {}).get("models", 0), idx.get("stats", {}).get("routes", 0)))
                append("Collecting files...")
                rel_map = idx.get("relations_map", {}) or {}
                known_rel = []
                for arr in rel_map.values():
                    for r in arr or []:
                        if r and r not in known_rel:
                            known_rel.append(r)
                summary = scan_project(project_root, max_workers=max_workers, excludes=excludes, known_relations=known_rel)
                append("Total files: {0}".format(summary.get("total_files", 0)))
                append("Problem files: {0}".format(summary.get("problem_files", 0)))
                files = summary.get("problematic_files", [])
                if files:
                    rels = [UIHelpers.get_project_relative_path(f, project_root) for f in files]

                    def on_pick(idx):
                        if idx == -1:
                            return
                        picked = files[idx]
                        rel = rels[idx]
                        append("\n=== {0} ===".format(rel))
                        for r in (summary.get("results") or []):
                            if r.get("file") == picked:
                                diffs = r.get("diffs") or []
                                if not diffs:
                                    append("No diff available.")
                                    return
                                for d in diffs[:1]:
                                    changes = d.get("changes") or []
                                    append("Suggested changes: {0}".format(len(changes)))
                                    for (ln, old, new) in changes[:5]:
                                        append("  • L{0}: {1}→ {2}".format(ln + 1, (old or '').strip()[:120], (new or '').strip()[:120]))
                                return

                    items = [[rels[i]] for i in range(len(rels))]
                    self.window.show_quick_panel(items, on_pick)

                    def on_choice(index):
                        if index == -1:
                            return
                        if index == 0:
                            diffs = summary.get("diffs", [])
                            res = apply_fixes(diffs)
                            append("")
                            append("Applied fixes: {0}".format(res.get("applied", 0)))
                            errs = res.get("errors", [])
                            if errs:
                                append("Errors:")
                                for e in errs[:50]:
                                    append("  • {0}".format(e))
                            sublime.status_message("Project scan fixes applied")
                        elif index == 1:
                            diffs = summary.get("diffs", [])
                            preview = []
                            for d in diffs[:50]:
                                file_path = d.get("file")
                                rel = UIHelpers.get_project_relative_path(file_path, project_root)
                                changes = d.get("changes", [])
                                preview.append("== {0} ==\n".format(rel))
                                for idx, old, new in changes[:5]:
                                    preview.append("- {0}".format(old))
                                    preview.append("+ {0}".format(new))
                                preview.append("\n")
                            UIHelpers.append_to_tab(output_tab, "\n".join(preview))
                        else:
                            pass

                    items = [
                        ["Apply safe fixes now", "Writes changes to files with backup .bak"],
                        ["Show diffs preview", "View a summary of proposed changes"],
                        ["Cancel", "Do nothing"],
                    ]
                    window.show_quick_panel(items, on_choice)
                else:
                    append("No N+1 patterns detected.")
                    sublime.status_message("Project scan complete: no issues found")
            except Exception as e:
                append("Error: {0}".format(str(e)))
                sublime.status_message("Project scan failed")

        wm = get_worker_manager(max_workers=max_workers)
        wm.submit(run_scan, priority=1, key="scan:nplusone:" + (project_root or ""))


class LaravelWorkshopAgentCleanupDeprecatedCommand(sublime_plugin.WindowCommand):
    def run(self):
        window = self.window
        project_root = UIHelpers.ensure_project_folder(window)
        if not project_root:
            return

        base = os.path.dirname(__file__)
        # Candidates for deprecation (safeguarded by existence check)
        candidates = [
            os.path.join(base, "laravel_autocomplete.py"),
            os.path.join(base, "laravel_intelligence.py"),
            os.path.join(base, "agent_memory.py"),
        ]
        existing = [p for p in candidates if os.path.exists(p)]
        if not existing:
            sublime.status_message("No candidate files found for cleanup")
            return

        items = [[os.path.basename(p), p] for p in existing] + [["Cancel", "Do nothing"]]

        def on_done(index):
            if index == -1 or index >= len(existing):
                return
            # Move selected file to _deprecated
            src = existing[index]
            dst_dir = os.path.join(base, "_deprecated")
            try:
                os.makedirs(dst_dir, exist_ok=True)
                dst = os.path.join(dst_dir, os.path.basename(src))
                os.rename(src, dst)
                sublime.status_message("Moved to _deprecated: " + os.path.basename(src))
            except Exception as e:
                sublime.error_message("Cleanup failed: {0}".format(e))

        window.show_quick_panel(items, on_done)


class LaravelWorkshopAgentAutoCleanupCommand(sublime_plugin.WindowCommand):
    def run(self):
        base = os.path.dirname(__file__)
        dst_dir = os.path.join(base, "_deprecated")
        os.makedirs(dst_dir, exist_ok=True)

        candidates = [
            os.path.join(base, "laravel_autocomplete.py"),
            os.path.join(base, "laravel_intelligence.py"),
            os.path.join(base, "agent_memory.py"),
        ]

        moved = []
        skipped = []
        for src in candidates:
            if not os.path.exists(src):
                skipped.append((src, "missing"))
                continue
            try:
                dst = os.path.join(dst_dir, os.path.basename(src))
                os.rename(src, dst)
                moved.append(dst)
            except Exception as e:
                skipped.append((src, str(e)))

        msg = "Cleanup: moved {} file(s), skipped {}".format(len(moved), len(skipped))
        sublime.status_message(msg)
        # Optional: brief log dialog for transparency
        if skipped:
            UIHelpers.show_info_message(msg + "\n\nSkipped:\n" + "\n".join([f"- {os.path.basename(p)}: {why}" for p, why in skipped]))
