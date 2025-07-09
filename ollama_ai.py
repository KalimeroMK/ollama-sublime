import sublime
import sublime_plugin
import json
import urllib.request
import os
import re
import threading
import html

# --- Helper Functions for Code Intelligence ---

def find_symbol_usages(symbol, project_root, code_file_extensions):
    """
    Finds usages of a symbol across the project and returns a context string.
    """
    usage_context = ""
    if not symbol or not project_root:
        return ""

    max_files = 10
    files_found = 0
    contexts = []

    for root, _, files in os.walk(project_root):
        if files_found >= max_files:
            break
        for file in files:
            if files_found >= max_files:
                break
            if any(file.endswith(ext) for ext in code_file_extensions):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        matching_snippets = []
                        for i, line in enumerate(lines):
                            if re.search(r'\b' + re.escape(symbol) + r'\b', line):
                                start = max(0, i - 2)
                                end = min(len(lines), i + 3)
                                snippet = "".join(lines[start:end])
                                matching_snippets.append("... (line {})\n{}".format(i + 1, snippet))
                        
                        if matching_snippets:
                            relative_path = os.path.relpath(file_path, project_root)
                            contexts.append("--- File: {}\n{}\n".format(relative_path, "\n".join(matching_snippets)))
                            files_found += 1
                except Exception:
                    continue
    
    if not contexts:
        return ""
        
    return "\n\nFor context, here is how `{}` is used elsewhere in the project:\n".format(symbol) + "\n".join(contexts)

def extract_symbol_from_text(text):
    """
    Tries to extract a meaningful symbol (class, function) from a string.
    """
    match = re.search(r'(?:class|function|interface|trait)\s+([a-zA-Z0-9_]+)', text)
    if match:
        return match.group(1)
    match = re.search(r'\b([A-Z][a-zA-Z0-9_]+)\b', text)
    if match:
        return match.group(1)
    return None

def get_project_context_for_symbol(view, symbol):
    """
    Orchestrates getting the project context for a given symbol.
    """
    if not symbol or not view:
        return ""
    folders = view.window().folders()
    if not folders:
        return ""
    project_root = folders[0]
    settings = sublime.load_settings("Ollama.sublime-settings")
    code_file_extensions = settings.get("code_file_extensions", [".php", ".js", ".py"])
    return find_symbol_usages(symbol, project_root, code_file_extensions)

class OllamaBaseCommand:
    def get_settings(self):
        settings = sublime.load_settings("Ollama.sublime-settings")
        model = settings.get("model", "qwen2.5-coder")
        url_from_settings = settings.get("url", "http://127.0.0.1:11434")
        system_prompt = settings.get("system_prompt", "You are a Laravel PHP expert.")
        is_chat_api = "/api/chat" in url_from_settings
        base_url = url_from_settings.replace('/api/chat', '').replace('/api/generate', '').rstrip('/')
        continue_chat = settings.get("continue_chat", True)
        return model, base_url, system_prompt, is_chat_api, continue_chat

class OllamaPromptCommand(OllamaBaseCommand, sublime_plugin.WindowCommand):
    def run(self):
        self.chat_history = []
        self.window.show_input_panel(
            "Enter your prompt:",
            "",
            self.on_done,
            None,
            None
        )

    def on_done(self, user_input):
        if not user_input:
            return

        model, base_url, system_prompt, is_chat_api, continue_chat = self.get_settings()

        # Maintain chat history if continue_chat is enabled
        if getattr(self, 'chat_history', None) is None:
            self.chat_history = []

        # --- CONTEXT AWARE ---
        symbol = extract_symbol_from_text(user_input)
        usage_context = ""
        view = self.window.active_view()
        if view:
            usage_context = get_project_context_for_symbol(view, symbol)
        # --- END CONTEXT AWARE ---

        full_prompt = "{}{}".format(user_input, usage_context)

        tab = self.window.new_file()
        tab.set_name("Ollama Custom Prompt")
        tab.set_scratch(True)
        tab.run_command("append", {
            "characters": "\n> " + user_input + "\n"
        })

        def fetch():
            try:
                api_endpoint = "/api/chat" if is_chat_api else "/api/generate"
                full_url = base_url + api_endpoint
                headers = {"Content-Type": "application/json"}

                if is_chat_api:
                    # Build messages array for chat
                    messages = []
                    if continue_chat and self.chat_history:
                        messages.extend(self.chat_history)
                    else:
                        self.chat_history = []
                    messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": full_prompt})
                    payload = {
                        "model": model,
                        "messages": messages,
                        "stream": False
                    }
                else:
                    payload = {
                        "model": model,
                        "prompt": "{}\n\n{}".format(system_prompt, full_prompt),
                        "stream": False
                    }
                req = urllib.request.Request(full_url, data=json.dumps(payload).encode('utf-8'), headers=headers)
                response = urllib.request.urlopen(req)
                response_data = json.loads(response.read().decode("utf-8"))
                if is_chat_api:
                    content = response_data.get('message', {}).get('content', '')
                    tab.run_command("append", {"characters": content})
                    # Save the message to chat history if continue_chat is enabled
                    if continue_chat:
                        # Only keep user/assistant roles in history for next round
                        if len(self.chat_history) > 0 and self.chat_history[0].get("role") == "system":
                            self.chat_history = self.chat_history[1:]
                        self.chat_history.append({"role": "user", "content": full_prompt})
                        self.chat_history.append({"role": "assistant", "content": content})
                else:
                    content = response_data.get('response', '')
                    tab.run_command("append", {"characters": content})
            except Exception as e:
                tab.run_command("append", {"characters": "\nERROR: {}".format(e)})

        sublime.set_timeout_async(fetch, 0)

        # If continue_chat is enabled, prompt for next input automatically
        if getattr(self, 'continue_chat_panel', None):
            try:
                self.continue_chat_panel.close()
            except Exception:
                pass
        if continue_chat:
            def ask_next():
                self.window.show_input_panel(
                    "Continue chat (leave blank to end):",
                    "",
                    self.on_done,
                    None,
                    None
                )
            self.continue_chat_panel = sublime.set_timeout_async(ask_next, 500)

class OllamaSelectionCommandBase(OllamaBaseCommand, sublime_plugin.TextCommand):
    def run(self, edit):
        settings = sublime.load_settings("Ollama.sublime-settings")
        model, base_url, system_prompt, is_chat_api, continue_chat = self.get_settings()

        for region in self.view.sel():
            if not region.empty():
                selected_text = self.view.substr(region)
                
                # --- CONTEXT AWARE ---
                symbol = extract_symbol_from_text(selected_text)
                usage_context = get_project_context_for_symbol(self.view, symbol)
                # --- END CONTEXT AWARE ---

                prompt = self.get_prompt(settings).format(code=selected_text)
                full_prompt = "{}{}".format(prompt, usage_context)

                self.output_tab = self.view.window().new_file()
                self.output_tab.set_name(settings.get("tab_title", "Ollama").format(selection=selected_text[:20]))
                self.output_tab.set_scratch(True)
                self.output_tab.run_command("append", {
                    "characters": "Prompt: {}\nModel: {}\n\n---\n\n".format(prompt, model)
                })

                api_endpoint = "/api/chat" if is_chat_api else "/api/generate"
                full_url = base_url + api_endpoint

                if is_chat_api:
                    payload = {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": full_prompt}
                        ],
                        "stream": True
                    }
                else:
                    payload = {
                        "model": model,
                        "prompt": "{}\n\n{}".format(system_prompt, full_prompt),
                        "stream": True
                    }

                req = urllib.request.Request(full_url, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json"})

                def fetch():
                    try:
                        with urllib.request.urlopen(req) as response:
                            for line in response:
                                try:
                                    parsed = json.loads(line.decode("utf-8"))
                                    if is_chat_api and "message" in parsed and "content" in parsed["message"]:
                                        content = parsed["message"]["content"]
                                        self.output_tab.run_command("append", {"characters": content})
                                    elif not is_chat_api and "response" in parsed:
                                        content = parsed.get("response", "")
                                        self.output_tab.run_command("append", {"characters": content})
                                    if parsed.get("done", False):
                                        break
                                except json.JSONDecodeError:
                                    continue
                    except Exception as e:
                        self.output_tab.run_command("append", {"characters": "\nERROR: {}".format(e)})

                sublime.set_timeout_async(fetch, 0)

    def get_prompt(self, settings):
        return settings.get("prompt", "Please explain this code:\n{}\n")


class OllamaExplainSelectionCommand(OllamaSelectionCommandBase):
    def get_prompt(self, settings):
        return settings.get("explain_prompt", "Explain the following code in a concise and clear way, assuming a professional Laravel PHP developer audience. Focus on the code's purpose, its role in the system, and any non-obvious logic.\n\n---\n\n{code}")


class OllamaOptimizeSelectionCommand(OllamaSelectionCommandBase):
    def get_prompt(self, settings):
        return settings.get("optimize_prompt", "Optimize the following code, keeping in mind the conventions of modern Laravel PHP development. Return only the optimized code, without any extra explanations or markdown formatting.\n\n---\n\n{code}")


class OllamaCodeSmellFinderCommand(OllamaSelectionCommandBase):
    """
    Analyzes the selected code for code smells, suggests optimizations,
    and identifies potentially unused code.
    """
    def get_prompt(self, settings):
        return settings.get("code_smell_prompt", """
Analyze the following code for potential code smells, such as poor design choices, bugs, or non-optimal code.
Provide specific, actionable suggestions for improvement.
Based on the provided usage context, also determine if this code appears to be unused. If it is unused, explicitly state that it can likely be deleted.

Code to analyze:
{code}
""")


class OllamaSelectionPromptCommand(OllamaSelectionCommandBase):
    """
    A command that prompts the user for input and combines it with the selected text
    """
    def run(self, edit):
        self.selected_text = ""
        for region in self.view.sel():
            if not region.empty():
                self.selected_text += self.view.substr(region)

        if not self.selected_text.strip():
            sublime.status_message("Ollama: No text selected.")
            return

        self.view.window().show_input_panel(
            "Enter prompt for selected code:",
            "",
            self.on_done,
            None,
            None
        )

    def on_done(self, user_prompt):
        if not user_prompt.strip():
            return

        full_prompt = "{}\n\n---\n\n{}".format(user_prompt, self.selected_text)

        settings = sublime.load_settings("Ollama.sublime-settings")
        model, base_url, system_prompt, is_chat_api, continue_chat = self.get_settings()

        # --- CONTEXT AWARE ---
        symbol = extract_symbol_from_text(self.selected_text)
        usage_context = get_project_context_for_symbol(self.view, symbol)
        # --- END CONTEXT AWARE ---

        full_prompt = "{}{}".format(full_prompt, usage_context)

        self.output_tab = self.view.window().new_file()
        self.output_tab.set_name("Ollama Custom Prompt")
        self.output_tab.set_scratch(True)
        self.output_tab.run_command("append", {
            "characters": "Prompt: {}\nModel: {}\n\n---\n\n".format(user_prompt, model)
        })

        api_endpoint = "/api/chat" if is_chat_api else "/api/generate"
        full_url = base_url + api_endpoint

        if is_chat_api:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                "stream": True
            }
        else:
            payload = {
                "model": model,
                "prompt": "{}\n\n{}".format(system_prompt, full_prompt),
                "stream": True
            }

        req = urllib.request.Request(full_url, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json"})

        def fetch():
            try:
                with urllib.request.urlopen(req) as response:
                    for line in response:
                        try:
                            parsed = json.loads(line.decode("utf-8"))
                            if is_chat_api and "message" in parsed and "content" in parsed["message"]:
                                content = parsed["message"]["content"]
                                self.output_tab.run_command("append", {"characters": content})
                            elif not is_chat_api and "response" in parsed:
                                content = parsed.get("response", "")
                                self.output_tab.run_command("append", {"characters": content})
                            if parsed.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                self.output_tab.run_command("append", {"characters": "\nERROR: {}".format(e)})

        sublime.set_timeout_async(fetch, 0)

    def is_visible(self):
        for region in self.view.sel():
            if not region.empty():
                return True
        return False


class OllamaCreateFileCommand(sublime_plugin.WindowCommand):
    """
    Create a new file based on a prompt
    """
    def run(self):
        self.window.show_input_panel("Describe the file you want to create:", "", self.on_description, None, None)

    def on_description(self, description):
        self.description = description
        self.window.show_input_panel("Enter the file path (relative to project):", "", self.on_path, None, None)

    def on_path(self, path):
        folders = self.window.folders()
        if not folders:
            sublime.message_dialog("No project folders open. Please open a project first.")
            return

        # Determine the full file path
        full_path = os.path.join(folders[0], path)
        self.file_path = full_path

        # Make sure the directory exists
        directory = os.path.dirname(full_path)
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
            except Exception as e:
                sublime.message_dialog("Error creating directory: {}".format(e))
                return

        # Get file extension to determine language
        _, ext = os.path.splitext(full_path)
        language = ext[1:] if ext else "text"

        # Get Ollama settings
        settings = sublime.load_settings("Ollama.sublime-settings")
        model = settings.get("model", "codellama")
        base_url = settings.get("url", "http://127.0.0.1:11434").replace('/api/chat', '').replace('/api/generate', '').rstrip('/')
        is_chat_api = "/api/chat" in settings.get("url", "http://127.0.0.1:11434")

        # Create a progress view
        progress_view = self.window.new_file()
        progress_view.set_name("Creating File")
        progress_view.set_scratch(True)
        progress_view.run_command("append", {"characters": "Creating file at {}\n".format(full_path)})

        # Generate the prompt for file creation
        prompt = """You are a professional developer. Create a new {} file based on this description:
{}
File should be created at: {}

Generate only the file content, with no additional explanations or markdown formatting.
""".format(language, self.description, full_path)

        symbol = extract_symbol_from_text(self.description)
        usage_context = get_project_context_for_symbol(self.window.active_view(), symbol)
        full_prompt = "{}{}".format(prompt, usage_context)

        api_endpoint = "/api/chat" if is_chat_api else "/api/generate"
        full_url = base_url + api_endpoint

        # Create the payload
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful code generator."},
                {"role": "user", "content": full_prompt}
            ],
            "stream": True
        }

        req = urllib.request.Request(
            full_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )

        # Start fetching the response
        def fetch():
            try:
                file_content = ""
                with urllib.request.urlopen(req) as response:
                    for line in response:
                        try:
                            parsed = json.loads(line.decode("utf-8"))
                            if "message" in parsed and "content" in parsed["message"]:
                                content = parsed["message"]["content"]
                                file_content += content
                                progress_view.run_command("append", {"characters": content})
                        except json.JSONDecodeError:
                            continue

                    # Write the file
                    try:
                        with open(full_path, 'w', encoding='utf-8') as f:
                            f.write(file_content)

                        # Close the progress view and open the new file
                        sublime.set_timeout(lambda: progress_view.close(), 500)
                        sublime.set_timeout(lambda: self.window.open_file(full_path), 1000)

                    except Exception as e:
                        sublime.set_timeout(lambda e=e:
                            progress_view.run_command("append", {"characters": "\nERROR writing file: {}".format(e)}), 0)

            except Exception as e:
                sublime.set_timeout(lambda e=e:
                    progress_view.run_command("append", {"characters": "\nERROR: {}".format(e)}), 0)

        threading.Thread(target=fetch).start()


class OllamaInlineRefactorCommand(OllamaBaseCommand, sublime_plugin.TextCommand):
    """
    Shows an inline phantom with a refactoring suggestion for the selected code.
    The user can then approve or dismiss the suggestion.
    """
    def run(self, edit):
        self.selected_text = ""
        self.selection_region = None
        # Persist the phantom set on the instance to prevent garbage collection
        self.phantom_set = sublime.PhantomSet(self.view, "ollama_inline_refactor")

        for region in self.view.sel():
            if not region.empty():
                self.selected_text = self.view.substr(region)
                self.selection_region = region
                break

        if not self.selected_text.strip():
            sublime.status_message("Ollama: No text selected.")
            return

        model, base_url, system_prompt, is_chat_api, continue_chat = self.get_settings()

        # --- CONTEXT AWARE ---
        symbol = extract_symbol_from_text(self.selected_text)
        usage_context = get_project_context_for_symbol(self.view, symbol)
        # --- END CONTEXT AWARE ---

        settings = sublime.load_settings("Ollama.sublime-settings")
        prompt_template = settings.get("refactor_prompt", "Refactor this code: {code}")
        full_prompt = prompt_template.format(code=self.selected_text, context=usage_context)

        if is_chat_api:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                "stream": False
            }
        else:
            payload = {
                "model": model,
                "prompt": "{}\n\n{}".format(system_prompt, full_prompt),
                "stream": False
            }

        def do_request():
            try:
                api_endpoint = "/api/chat" if is_chat_api else "/api/generate"
                full_url = base_url + api_endpoint

                req = urllib.request.Request(
                    full_url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )

                with urllib.request.urlopen(req) as response:
                    response_data = json.loads(response.read().decode('utf-8'))
                    if is_chat_api:
                        suggestion = response_data.get('message', {}).get('content', '')
                    else:
                        suggestion = response_data.get('response', '')
                    # Strip markdown code fences like ```php and ```
                    cleaned_suggestion = suggestion.strip()
                    if cleaned_suggestion.startswith("```php"):
                        cleaned_suggestion = cleaned_suggestion[6:].lstrip()
                    if cleaned_suggestion.endswith("```"):
                        cleaned_suggestion = cleaned_suggestion[:-3].rstrip()

                    if not cleaned_suggestion:
                        sublime.status_message("Ollama: Received an empty suggestion.")
                        return

                    sublime.set_timeout(lambda: self.show_inline_suggestion(cleaned_suggestion), 0)

            except Exception as e:
                sublime.set_timeout(lambda: sublime.status_message("Ollama: Refactor error: {}".format(e)), 0)

        thread = threading.Thread(target=do_request)
        thread.start()

    def show_inline_suggestion(self, suggestion):
        self.suggestion = suggestion  # Store suggestion for the 'approve' action
        escaped_suggestion = html.escape(self.suggestion, quote=False)

        # Restore the original, styled HTML
        phantom_content = """
            <body id="ollama-inline-refactor">
                <style>
                    body {
                        font-family: sans-serif;
                        margin: 0;
                        padding: 8px;
                        border-radius: 4px;
                        background-color: var(--background);
                        color: var(--foreground);
                        border: 1px solid var(--border);
                    }
                    .header {
                        font-weight: bold;
                        margin-bottom: 8px;
                        padding-bottom: 4px;
                        border-bottom: 1px solid var(--border);
                    }
                    pre {
                        margin: 0;
                        padding: 8px;
                        border-radius: 4px;
                        background-color: var(--background_light);
                        white-space: pre-wrap;
                        word-wrap: break-word;
                    }
                    .buttons {
                        margin-top: 8px;
                        text-align: right;
                    }
                    a {
                        text-decoration: none;
                        padding: 4px 8px;
                        border-radius: 4px;
                        background-color: var(--button_background);
                        color: var(--button_foreground);
                        margin-left: 4px;
                    }
                    a.approve {
                        background-color: var(--greenish);
                    }
                </style>
                <div class="header">AI Refactoring Suggestion</div>
                <pre><code>""" + escaped_suggestion + """</code></pre>
                <div class="buttons">
                    <a href="approve" class="approve">Approve</a>
                    <a href="dismiss">Dismiss</a>
                </div>
            </body>
        """

        phantom = sublime.Phantom(
            self.selection_region,
            phantom_content,
            sublime.LAYOUT_BLOCK,
            on_navigate=self.on_phantom_navigate
        )
        self.phantom_set.update([phantom])


    def on_phantom_navigate(self, href):
        if href == "approve":
            if hasattr(self, 'suggestion') and self.suggestion:
                self.view.run_command("ollama_replace_text", {"region_start": self.selection_region.begin(), "region_end": self.selection_region.end(), "text": self.suggestion})
        
        # Erase phantoms by updating the set with an empty list
        if hasattr(self, 'phantom_set'):
            self.phantom_set.update([])

    def is_visible(self):
        for region in self.view.sel():
            if not region.empty():
                return True
        return False


class OllamaReplaceTextCommand(sublime_plugin.TextCommand):
    def run(self, edit, region_start, region_end, text):
        region = sublime.Region(region_start, region_end)
        self.view.replace(edit, region, text)


class OllamaGenerateFeatureCommand(OllamaBaseCommand, sublime_plugin.WindowCommand):
    """
    Generates multiple files for a new feature based on a high-level description.
    Uses a two-step process: Architect AI for planning and Coder AI for implementation.
    """
    def run(self):
        self.window.show_input_panel(
            "Enter a description for the new feature:",
            "",
            self.on_done,
            None,
            None
        )

    def on_done(self, description):
        if not description:
            return

        thread = threading.Thread(target=self.generate_feature, args=(description,))
        thread.start()

    def generate_feature(self, description):
        try:
            sublime.set_timeout(lambda: self.window.active_view().set_status("ollama_status", "Ollama: Asking Architect AI to create a plan..."), 0)

            # Step 1: Get the plan from the Architect AI
            architect_prompt = sublime.load_settings("Ollama.sublime-settings").get("feature_architect_prompt", "Create a JSON plan for this feature: {prompt}")
            full_architect_prompt = architect_prompt.format(prompt=description)
            plan_json_str = self._make_blocking_ollama_request(full_architect_prompt)

            if not plan_json_str:
                raise Exception("Architect AI returned an empty plan.")

            # Clean up the response to ensure it's valid JSON
            plan_json_str = plan_json_str.strip()
            if plan_json_str.startswith('```json'):
                plan_json_str = plan_json_str[7:]
            if plan_json_str.endswith('```'):
                plan_json_str = plan_json_str[:-3]

            plan = json.loads(plan_json_str)
            files_to_create = plan.get("files", [])

            if not files_to_create:
                raise Exception("Architect AI did not specify any files to create.")

            sublime.set_timeout(lambda: self.window.active_view().set_status("ollama_status", ""), 0)
            sublime.set_timeout(lambda: self.show_plan_for_approval(files_to_create), 0)

        except Exception as e:
            sublime.set_timeout(lambda: sublime.error_message("Ollama Feature Generation Error: {}\n\nCheck the console for more details.".format(e)), 0)
            print("Ollama Error: Failed to generate feature plan. Raw response from AI was:")
            print(plan_json_str)

    def show_plan_for_approval(self, files_to_create):
        self.files_to_create = files_to_create
        plan_items = ["[✅ Approve and Create Files]", "[❌ Cancel]"] + ["- " + f["path"] for f in files_to_create]

        self.window.show_quick_panel(plan_items, self.on_plan_selection)

    def on_plan_selection(self, index):
        if index == -1 or index == 1:
            sublime.status_message("Ollama: Feature generation cancelled.")
            return

        if index == 0:
            thread = threading.Thread(target=self.create_files)
            thread.start()

    def create_files(self):
        try:
            project_root = self.window.folders()[0]
            coder_prompt_template = sublime.load_settings("Ollama.sublime-settings").get("feature_coder_prompt", "Create this file: {path} - {description}")

            for i, file_info in enumerate(self.files_to_create):
                path = file_info["path"]
                description = file_info["description"]
                progress_msg = "Ollama: ({}/{}) Asking Coder AI to write {}...".format(i + 1, len(self.files_to_create), path)
                sublime.set_timeout(lambda: self.window.active_view().set_status("ollama_status", progress_msg), 0)

                # Step 2: Get the code from the Coder AI
                full_coder_prompt = coder_prompt_template.format(path=path, description=description)
                file_content = self._make_blocking_ollama_request(full_coder_prompt)

                if not file_content:
                    print("Ollama Warning: Coder AI returned empty content for {}. Skipping.".format(path))
                    continue

                # Create the file
                file_path = os.path.join(project_root, path)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(file_content)

                # Open the newly created file
                sublime.set_timeout(lambda p=file_path: self.window.open_file(p), 0)

            sublime.set_timeout(lambda: self.window.active_view().set_status("ollama_status", "Ollama: Feature generation complete!"), 0)

        except Exception as e:
            sublime.set_timeout(lambda: sublime.error_message("Ollama File Creation Error: {}".format(e)), 0)

    def _make_blocking_ollama_request(self, prompt):
        model, base_url, system_prompt, is_chat_api, continue_chat = self.get_settings()

        api_endpoint = "/api/chat" if is_chat_api else "/api/generate"
        full_url = base_url + api_endpoint

        if is_chat_api:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
        else:
            payload = {
                "model": model,
                "prompt": "{}\n\n{}".format(system_prompt, prompt),
                "stream": False
            }

        try:
            req = urllib.request.Request(full_url, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json"})
            response = urllib.request.urlopen(req)
            response_data = json.loads(response.read().decode("utf-8"))

            if is_chat_api:
                return response_data.get('message', {}).get('content', '')
            else:
                return response_data.get('response', '')
        except Exception as e:
            print("Ollama blocking request error: {}".format(e))
            return None
