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
                                matching_snippets.append("... (line {})
{}".format(i + 1, snippet))
                        
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
        url = settings.get("url", "http://127.0.0.1:11434/api/chat")
        system_prompt = settings.get("system_prompt", "You are a Laravel PHP expert.")
        is_chat_api = "/api/chat" in url
        return model, url, system_prompt, is_chat_api

class OllamaPromptCommand(OllamaBaseCommand, sublime_plugin.WindowCommand):
    def run(self):
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

        settings = self.get_settings()
        model, url, system_prompt, is_chat_api = settings
        
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
            "characters": "Prompt: {}\nModel: {}\n\n---\n\n".format(user_input, model)
        })

        if is_chat_api:
            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                "stream": True
            }).encode("utf-8")
        else:
            payload = json.dumps({
                "model": model,
                "prompt": "{}\n\n{}".format(system_prompt, full_prompt),
                "stream": True
            }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

        def fetch():
            try:
                with urllib.request.urlopen(req) as response:
                    for line in response:
                        try:
                            parsed = json.loads(line.decode("utf-8"))
                            if is_chat_api and "message" in parsed and "content" in parsed["message"]:
                                content = parsed["message"]["content"]
                                tab.run_command("append", {"characters": content})
                            elif not is_chat_api and "response" in parsed:
                                content = parsed.get("response", "")
                                tab.run_command("append", {"characters": content})
                            if parsed.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                tab.run_command("append", {"characters": "\nERROR: {}".format(e)})

        sublime.set_timeout_async(fetch, 0)

class OllamaSelectionCommandBase(OllamaBaseCommand, sublime_plugin.TextCommand):
    def run(self, edit):
        settings = sublime.load_settings("Ollama.sublime-settings")
        model, url, system_prompt, is_chat_api = self.get_settings()

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

                if is_chat_api:
                    payload = json.dumps({
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": full_prompt}
                        ],
                        "stream": True
                    }).encode("utf-8")
                else:
                    payload = json.dumps({
                        "model": model,
                        "prompt": "{}\n\n{}".format(system_prompt, full_prompt),
                        "stream": True
                    }).encode("utf-8")

                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

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
        model, url, system_prompt, is_chat_api = self.get_settings()

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

        if is_chat_api:
            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                "stream": True
            }).encode("utf-8")
        else:
            payload = json.dumps({
                "model": model,
                "prompt": "{}\n\n{}".format(system_prompt, full_prompt),
                "stream": True
            }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

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
        url = settings.get("url", "http://127.0.0.1:11434/api/chat")

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

        # Create the payload
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful code generator."},
                {"role": "user", "content": full_prompt}
            ],
            "stream": True
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

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


class OllamaInlineRefactorCommand(sublime_plugin.TextCommand):
    """
    Shows an inline phantom with a refactoring suggestion for the selected code.
    The user can then approve or dismiss the suggestion.
    """
    def run(self, edit):
        self.selected_text = ""
        self.selection_region = None
        for region in self.view.sel():
            if not region.empty():
                self.selected_text = self.view.substr(region)
                self.selection_region = region
                break

        if not self.selected_text.strip():
            sublime.status_message("Ollama: No text selected.")
            return

        # Find context for the selected symbol
        symbol = extract_symbol_from_text(self.selected_text)
        usage_context = get_project_context_for_symbol(self.view, symbol)

        prompt = "Refactor the following code. IMPORTANT: Return ONLY the raw, updated code block. Do not include any explanation, markdown, or any text other than the code itself."
        full_prompt = "{}\n\n---\n\n{}{}".format(prompt, self.selected_text, usage_context)

        settings = sublime.load_settings("Ollama.sublime-settings")
        model, url, system_prompt, is_chat_api = OllamaBaseCommand().get_settings()

        if is_chat_api:
            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                "stream": False
            }).encode("utf-8")
        else:
            payload = json.dumps({
                "model": model,
                "prompt": "{}\n\n{}".format(system_prompt, full_prompt),
                "stream": False
            }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        sublime.set_timeout_async(lambda: self.fetch_suggestion(req, is_chat_api), 0)

    def fetch_suggestion(self, req, is_chat_api):
        try:
            with urllib.request.urlopen(req) as response:
                response_data = json.loads(response.read().decode("utf-8"))
                suggestion = response_data["message"]["content"] if is_chat_api else response_data.get("response", "")
                suggestion = re.sub(r'^```[a-zA-Z]*\n', '', suggestion)
                suggestion = re.sub(r'\n```$', '', suggestion).strip()

                if suggestion:
                    self.view.settings().set("ollama_inline_suggestion", suggestion)
                    self.show_phantom(suggestion)
                else:
                    sublime.status_message("Ollama: No suggestion received.")
        except Exception as e:
            sublime.error_message("Ollama Error: {}".format(str(e)))

    def show_phantom(self, suggestion):
        escaped_suggestion = html.escape(suggestion, quote=False)
        phantom_key = "ollama_inline_refactor"
        phantom_content = """
        <body id="ollama-inline-suggestion">
            <style>
                div.ollama-suggestion {{ background-color: var(--background); color: var(--foreground); border: 1px solid var(--accent); padding: 10px; margin-top: 5px; border-radius: 5px; }}
                div.ollama-suggestion pre {{ margin: 0; padding: 0; }}
                div.ollama-actions a {{ background-color: var(--accent); color: var(--background); padding: 2px 8px; text-decoration: none; border-radius: 3px; font-weight: bold; }}
            </style>
            <div class="ollama-suggestion">
                <div class="ollama-actions">
                    <a href="approve">Approve</a>&nbsp;&nbsp;
                    <a href="dismiss">Dismiss</a>
                </div>
                <hr>
                <pre><code>{}</code></pre>
            </div>
        </body>
        """.format(escaped_suggestion)

        phantom_set = sublime.PhantomSet(self.view, phantom_key)
        phantom = sublime.Phantom(self.selection_region, phantom_content, sublime.LAYOUT_BLOCK, on_navigate=self.on_phantom_navigate)
        phantom_set.update([phantom])

    def on_phantom_navigate(self, href):
        phantom_key = "ollama_inline_refactor"
        if href == "approve":
            suggestion = self.view.settings().get("ollama_inline_suggestion")
            if suggestion:
                self.view.run_command("ollama_replace_text", {
                    "start": self.selection_region.begin(),
                    "end": self.selection_region.end(),
                    "text": suggestion
                })
        
        phantom_set = sublime.PhantomSet(self.view, phantom_key)
        phantom_set.update([])
        self.view.settings().erase("ollama_inline_suggestion")

    def is_visible(self):
        for region in self.view.sel():
            if not region.empty():
                return True
        return False


class OllamaReplaceTextCommand(sublime_plugin.TextCommand):
    def run(self, edit, start, end, text):
        region = sublime.Region(start, end)
        self.view.replace(edit, region, text)


class OllamaGenerateFeatureCommand(OllamaBaseCommand, sublime_plugin.WindowCommand):
    """
    Generates a multi-file feature based on a high-level description using a two-step AI process.
    """
    def run(self):
        self.window.show_input_panel(
            "Describe the feature to generate (e.g., 'a product module with controller, model, and migration'):",
            "",
            self.on_description_done,
            None,
            None
        )

    def on_description_done(self, description):
        if not description.strip():
            return
        self.description = description
        sublime.status_message("Ollama: Asking AI architect for a feature plan...")
        threading.Thread(target=self.get_feature_plan).start()

    def get_feature_plan(self):
        settings = sublime.load_settings("Ollama.sublime-settings")
        prompt_template = settings.get("feature_architect_prompt")
        prompt = prompt_template.format(description=self.description)

        try:
            raw_plan = self._make_blocking_ollama_request(prompt)
            if not raw_plan:
                sublime.error_message("Ollama: AI did not return a plan.")
                return

            clean_plan = self._clean_json_response(raw_plan)
            self.plan = json.loads(clean_plan)

            if 'files' not in self.plan or not isinstance(self.plan['files'], list):
                raise ValueError("Plan must contain a 'files' list.")

            sublime.set_timeout(self.show_plan_for_approval, 0)

        except (json.JSONDecodeError, ValueError) as e:
            sublime.error_message("Ollama: AI returned an invalid plan. Error: {}\n\nResponse:\n{}".format(e, raw_plan))
        except Exception as e:
            sublime.error_message("Ollama: Failed to get feature plan. Error: {}".format(e))

    def show_plan_for_approval(self):
        self.plan_items = []
        self.plan_items.append(sublime.QuickPanelItem("✅ Approve and Create {} Files".format(len(self.plan['files'])), "Proceed with generating all files below"))
        self.plan_items.append(sublime.QuickPanelItem("❌ Cancel", "Abort the operation"))
        self.plan_items.append(sublime.QuickPanelItem("---", "", sublime.KIND_SEPARATOR))

        for file_info in self.plan['files']:
            self.plan_items.append(sublime.QuickPanelItem(file_info['path'], file_info['description']))

        self.window.show_quick_panel(self.plan_items, self.on_plan_selection)

    def on_plan_selection(self, index):
        if index == -1 or index == 1: # Canceled
            sublime.status_message("Ollama: Feature generation canceled.")
            return
        if index == 0: # Approved
            sublime.status_message("Ollama: Approved! Starting feature generation...")
            threading.Thread(target=self.create_feature_files).start()

    def create_feature_files(self):
        folders = self.window.folders()
        if not folders:
            sublime.error_message("Ollama: No project folder open.")
            return
        project_root = folders[0]

        settings = sublime.load_settings("Ollama.sublime-settings")
        coder_prompt_template = settings.get("feature_coder_prompt")

        total_files = len(self.plan['files'])
        created_files = []

        for i, file_info in enumerate(self.plan['files']):
            path = file_info['path']
            description = file_info['description']
            sublime.status_message("Ollama: Generating file {} of {}: {}".format(i + 1, total_files, path))

            try:
                prompt = coder_prompt_template.format(path=path, description=description)
                file_content = self._make_blocking_ollama_request(prompt)

                if not file_content:
                    sublime.log_message("Ollama: AI returned no content for {}. Skipping.".format(path))
                    continue

                full_path = os.path.join(project_root, path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)

                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(file_content)
                created_files.append(full_path)

            except Exception as e:
                sublime.error_message("Ollama: Failed to create file {}. Error: {}".format(path, e))

        sublime.status_message("Ollama: Feature generation complete! Created {} files.".format(len(created_files)))
        for file_path in created_files:
            self.window.open_file(file_path)

    def _make_blocking_ollama_request(self, prompt):
        model, url, system_prompt, is_chat_api = self.get_settings()

        if is_chat_api:
            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }).encode("utf-8")
        else:
            payload = json.dumps({
                "model": model,
                "prompt": "{}\n\n{}".format(system_prompt, prompt),
                "stream": False
            }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        response = urllib.request.urlopen(req)
        response_data = json.loads(response.read().decode("utf-8"))

        if is_chat_api:
            return response_data.get('message', {}).get('content', '')
        else:
            return response_data.get('response', '')

    def _clean_json_response(self, text):
        text = text.strip()
        match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text
