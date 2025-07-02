import sublime
import sublime_plugin
import urllib.request
import json
import os
import threading
import re

class OllamaPromptCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.show_input_panel("Enter your prompt:", "", self.on_done, None, None)

    def on_done(self, user_input):
        settings = sublime.load_settings("Ollama.sublime-settings")
        model = settings.get("model", "qwen2.5-coder")
        url = settings.get("url", "http://127.0.0.1:11434/api/chat")
        system_prompt = settings.get("system_prompt", "You are a Laravel PHP expert. When asked about code analysis or test generation, always assume PHP Laravel unless specified otherwise.")
        syntax = settings.get("syntax", "Packages/Markdown/Markdown.sublime-syntax")
        is_chat_api = "/api/chat" in url

        tab = self.window.new_file()
        tab.set_name("Ollama Prompt")
        tab.set_scratch(True)
        tab.set_syntax_file(syntax)
        tab.run_command("append", {
            "characters": "Prompt: {}\nModel: {}\n\n".format(user_input, model)
        })

        if is_chat_api:
            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                "stream": True
            }).encode("utf-8")
        else:
            payload = json.dumps({
                "model": model,
                "prompt": "{}\n\n{}".format(system_prompt, user_input),
                "stream": True
            }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

        def fetch():
            try:
                result = ""
                with urllib.request.urlopen(req) as response:
                    for line in response:
                        try:
                            parsed = json.loads(line.decode("utf-8"))
                            if is_chat_api and "message" in parsed and "content" in parsed["message"]:
                                content = parsed["message"]["content"]
                                result += content
                                tab.run_command("append", {"characters": content})
                            elif "response" in parsed:
                                result += parsed.get("response", "")
                            if parsed.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
                if not result:
                    tab.run_command("append", {"characters": "Response:\n\nNo content returned from Ollama API. Please check your configuration."})
            except Exception as e:
                tab.run_command("append", {"characters": "\nERROR: {}".format(e)})

        sublime.set_timeout_async(fetch, 0)

class OllamaAiExplainCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.run_with_mode("explain_prompt", "Explain")

    def run_with_mode(self, prompt_key, mode_label):
        settings = sublime.load_settings("Ollama.sublime-settings")
        instruction = settings.get(prompt_key)
        model = settings.get("model", "qwen2.5-coder")
        url = settings.get("url", "http://127.0.0.1:11434/api/chat")
        syntax = settings.get("syntax", "Packages/Markdown/Markdown.sublime-syntax")
        prefix = settings.get("tab_title_prefix", "Ollama")
        is_chat_api = "/api/chat" in url

        sels = self.view.sel()
        if not sels or sels[0].empty():
            sublime.message_dialog("[{}] Please select some code first.".format(mode_label))
            return

        code = self.view.substr(sels[0])
        
        # Create output tab
        self.output_tab = self.view.window().new_file()
        self.output_tab.set_name("{} [{}]".format(prefix, mode_label))
        self.output_tab.set_scratch(True)
        self.output_tab.set_syntax_file(syntax)
        self.output_tab.run_command("append", {
            "characters": "# {} Code\n\n```\n{}\n```\n\nRunning {}...\n\n".format(mode_label, code, mode_label)
        })

        # Prepare payload based on API type
        if is_chat_api:
            data = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a senior developer."},
                    {"role": "user", "content": "{}\n\nCode:\n```\n{}\n```".format(instruction, code)}
                ],
                "stream": True
            }).encode("utf-8")
        else:
            full_prompt = "You are a senior developer.\n\n{}\n\nCode:\n```\n{}\n```".format(instruction, code)
            data = json.dumps({
                "model": model,
                "prompt": full_prompt,
                "stream": True
            }).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        
        # Start fetching response
        sublime.set_timeout_async(lambda: self.fetch_response(req, model, is_chat_api), 0)

    def fetch_response(self, req, model, is_chat_api):
        try:
            result = ""
            with urllib.request.urlopen(req) as response:
                for line in response:
                    try:
                        parsed = json.loads(line.decode("utf-8"))
                        
                        # Handle different API formats
                        if is_chat_api:
                            if "message" in parsed and "content" in parsed["message"]:
                                chunk = parsed["message"]["content"]
                                result += chunk
                                self.output_tab.run_command("append", {"characters": chunk})
                        else:
                            chunk = parsed.get("response", "")
                            result += chunk
                            self.output_tab.run_command("append", {"characters": chunk})
                        
                        if parsed.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
                        
            if not result:
                self.output_tab.run_command("append", {"characters": "No response received from model."})
                
        except Exception as e:
            self.output_tab.run_command("append", {"characters": "\n\nERROR: {}".format(str(e))})

class OllamaAiOptimizeCommand(OllamaAiExplainCommand):
    def run(self, edit):
        self.run_with_mode("optimize_prompt", "Optimize")

class OllamaSelectionPromptCommand(sublime_plugin.TextCommand):
    """
    Shows an input panel to get a custom prompt for the selected text.
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
        model = settings.get("model", "qwen2.5-coder")
        url = settings.get("url", "http://127.0.0.1:11434/api/chat")
        system_prompt = settings.get("system_prompt", "You are a Laravel PHP expert.")
        is_chat_api = "/api/chat" in url

        tab = self.view.window().new_file()
        tab.set_name("Ollama Custom Prompt")
        tab.set_scratch(True)
        tab.set_syntax_file(settings.get("syntax", "Packages/Markdown/Markdown.sublime-syntax"))
        tab.run_command("append", {
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

    def is_visible(self):
        for region in self.view.sel():
            if not region.empty():
                return True
        return False


class OllamaCodeAnalyzeCommand(sublime_plugin.WindowCommand):
    """
    Analyze codebase and provide insights similar to Cascade
    """
    def run(self):
        self.window.show_input_panel("Enter what you want to analyze in your codebase:", "", self.on_done, None, None)

    def on_done(self, user_input):
        # Collect files from the current project
        folders = self.window.folders()
        if not folders:
            sublime.message_dialog("No project folders open. Please open a project first.")
            return

        # Create a progress dialog
        self.progress_view = self.window.new_file()
        self.progress_view.set_name("Code Analysis Progress")
        self.progress_view.set_scratch(True)
        self.progress_view.run_command("append", {"characters": "Analyzing codebase...\n\n"})

        threading.Thread(target=self.analyze_codebase, args=(folders, user_input)).start()

    def analyze_codebase(self, folders, user_input):
        try:
            settings = sublime.load_settings("Ollama.sublime-settings")
            model = settings.get("model", "codellama")
            url = settings.get("url", "http://127.0.0.1:11434/api/chat")
            is_chat_api = "/api/chat" in url
            code_extensions = settings.get("code_file_extensions", [".php", ".js", ".py", ".go", ".java", ".cs", ".rb", ".ts", ".c", ".cpp", ".h", ".json", ".html", ".css", ".scss", ".less"])

            # Collect file information
            file_info = []
            for folder in folders:
                for root, dirs, files in os.walk(folder):
                    for file in files:
                        _, ext = os.path.splitext(file)
                        if ext in code_extensions:
                            file_path = os.path.join(root, file)
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    content = f.read()
                                    snippet = content[:1000] + ("..." if len(content) > 1000 else "")
                                    file_info.append({
                                        "path": os.path.relpath(file_path, folder),
                                        "snippet": snippet,
                                        "language": os.path.splitext(file)[1][1:]
                                    })

                                    # Update progress
                                    sublime.set_timeout(lambda path=file_path:
                                        self.progress_view.run_command("append", {"characters": "Scanning: {}\n".format(path)}), 0)

                            except Exception as e:
                                sublime.set_timeout(lambda e=e, path=file_path:
                                    self.progress_view.run_command("append", {"characters": "Error reading {}: {}\n".format(path, e)}), 0)

            # Prepare a summary for the AI
            summary = json.dumps({
                "project_structure": {
                    "root_folders": [os.path.basename(f) for f in folders]
                },
                "file_samples": file_info[:10],  # Send more samples
                "analysis_request": user_input
            }, indent=2)

            # Create the AI prompt
            prompt = """You are a code analysis assistant like Cascade.

Analyze this codebase and provide insights based on the following request: "{}"

Project information:
{}

Provide:
1. A high-level overview of the codebase structure
2. Recommendations based on the user's request
3. Potential improvements or issues you identify
""".format(user_input, summary)

            # Send to Ollama
            if is_chat_api:
                payload = json.dumps({
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful code analysis assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    "stream": True
                }).encode("utf-8")
            else:
                payload = json.dumps({
                    "model": model,
                    "prompt": prompt,
                    "stream": True
                }).encode("utf-8")

            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

            sublime.set_timeout(lambda: self.progress_view.run_command("append", {"characters": "\n\nSending to Ollama for analysis...\n"}), 0)

            # Create the output view
            sublime.set_timeout(lambda: self.create_output_view(req, model), 0)

        except Exception as e:
            sublime.set_timeout(lambda e=e: self.progress_view.run_command("append", {"characters": "\nERROR during analysis: {}\n".format(e)}), 0)

    def create_output_view(self, req, model):
        settings = sublime.load_settings("Ollama.sublime-settings")
        syntax = settings.get("syntax", "Packages/Markdown/Markdown.sublime-syntax")
        is_chat_api = "/api/chat" in settings.get("url", "")

        # Create a new view for the output
        output_view = self.window.new_file()
        output_view.set_name("Ollama Code Analysis")
        output_view.set_scratch(True)
        output_view.set_syntax_file(syntax)
        output_view.run_command("append", {"characters": "# Code Analysis\n\nModel: {}\n\n".format(model)})

        # Start fetching the response
        threading.Thread(target=self.fetch_analysis, args=(req, output_view, is_chat_api)).start()

    def fetch_analysis(self, req, output_view, is_chat_api):
        try:
            result = ""
            with urllib.request.urlopen(req) as response:
                for line in response:
                    try:
                        parsed = json.loads(line.decode("utf-8"))
                        
                        # Handle different API formats
                        if is_chat_api:
                            if "message" in parsed and "content" in parsed["message"]:
                                chunk = parsed["message"]["content"]
                                result += chunk
                                sublime.set_timeout(lambda chunk=chunk:
                                    output_view.run_command("append", {"characters": chunk}), 0)
                        else:
                            chunk = parsed.get("response", "")
                            result += chunk
                            sublime.set_timeout(lambda chunk=chunk:
                                output_view.run_command("append", {"characters": chunk}), 0)
                        
                        if parsed.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue

            # Close the progress view
            sublime.set_timeout(lambda: self.progress_view.close(), 1000)

        except Exception as e:
            sublime.set_timeout(lambda e=e:
                output_view.run_command("append", {"characters": "\n\nERROR: {}".format(e)}), 0)

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

        # Create the payload
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful code generator."},
                {"role": "user", "content": prompt}
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

class OllamaEditSettingsCommand(sublime_plugin.WindowCommand):
    """
    Edit Ollama.sublime-settings with model configuration
    """
    def run(self):
        settings = sublime.load_settings("Ollama.sublime-settings")

        # Get available models from Ollama API
        url = settings.get("url", "http://127.0.0.1:11434/api/chat")
        base_url = url.split('/api/')[0] + '/api'

        # Try different model listing endpoints
        def fetch_models():
            try:
                # First try the newer Ollama API endpoint
                models_url = "{}/models".format(base_url)
                with urllib.request.urlopen(models_url) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    models = [model['name'] for model in data.get('models', [])]
                    if not models and 'models' not in data:
                        # If no models in response, try alternate structure
                        models = [model for model in data]

                    if not models:
                        # Try older API endpoint
                        models_url_alt = "{}/tags".format(base_url)
                        with urllib.request.urlopen(models_url_alt) as response:
                            data = json.loads(response.read().decode('utf-8'))
                            models = [model['name'] for model in data.get('models', [])]

                    if not models:
                        # Fallback options
                        models = ["codellama", "llama2", "mistral", "phi", "qwen2.5-coder"]

                    sublime.set_timeout(lambda models=models: self.show_models_panel(models), 0)
            except Exception as e:
                print("Error fetching models: {}".format(e))
                # Fallback to default models
                models = ["codellama", "llama2", "mistral", "phi", "qwen2.5-coder"]
                sublime.set_timeout(lambda models=models: self.show_models_panel(models), 0)

        import threading
        threading.Thread(target=fetch_models).start()

    def show_models_panel(self, models):
        self.models = models
        try:
            self.window.show_quick_panel(models, self.on_model_selected)
        except Exception as e:
            print("Error showing quick panel: {}".format(e))
            # Fallback to input panel if quick panel fails
            self.window.show_input_panel("Enter model name:",
                                         models[0] if models else "qwen2.5-coder",
                                         self.on_model_input, None, None)

    def on_model_input(self, model):
        if not model:
            return
        self.update_model_settings(model)

    def on_model_selected(self, index):
        if index == -1:
            return
        model = self.models[index]
        self.update_model_settings(model)

    def update_model_settings(self, model):
        settings = sublime.load_settings("Ollama.sublime-settings")

        # Update model in settings
        settings.set("model", model)
        sublime.save_settings("Ollama.sublime-settings")

        # Show confirmation
        sublime.status_message("Ollama model updated to: {}".format(model))

        # Now ask for URL configuration
        self.window.show_input_panel(
            "Ollama API URL (leave empty for default):",
            settings.get("url", "http://127.0.0.1:11434/api/chat"),
            self.on_url_entered, None, None
        )

    def on_url_entered(self, url):
        if url:
            settings = sublime.load_settings("Ollama.sublime-settings")
            settings.set("url", url)
            sublime.save_settings("Ollama.sublime-settings")
            sublime.status_message("Ollama API URL updated to: {}".format(url))

        # Open the settings file for additional editing
        # First try package-specific path
        package_path = sublime.packages_path()
        settings_path = os.path.join(package_path, "ollama-sublime", "Ollama.sublime-settings")

        # Check if file exists or try User folder
        if not os.path.exists(settings_path):
            settings_path = "${packages}/User/Ollama.sublime-settings"

        self.window.run_command("open_file", {"file": settings_path})

class OllamaEditSystemPromptsCommand(sublime_plugin.WindowCommand):
    """
    Edit system prompts in the settings
    """
    def run(self):
        self.prompts = [
            "explain_prompt",
            "optimize_prompt",
            "analysis_prompt"
        ]
        self.prompt_descriptions = [
            "Explanation Prompt",
            "Optimization Prompt",
            "Analysis Prompt"
        ]
        self.window.show_quick_panel(self.prompt_descriptions, self.on_prompt_selected)

    def on_prompt_selected(self, index):
        if index == -1:
            return

        settings = sublime.load_settings("Ollama.sublime-settings")
        prompt_key = self.prompts[index]
        current_value = settings.get(prompt_key, "")

        self.selected_prompt = prompt_key
        self.window.show_input_panel(
            "{}".format(self.prompt_descriptions[index]),
            current_value,
            self.on_prompt_edited, None, None
        )

    def on_prompt_edited(self, new_value):
        settings = sublime.load_settings("Ollama.sublime-settings")
        settings.set(self.selected_prompt, new_value)
        sublime.save_settings("Ollama.sublime-settings")
        sublime.status_message("Updated {}".format(self.selected_prompt))

class OllamaGenerateLaravelFeatureCommand(sublime_plugin.WindowCommand):
    """
    Generate multiple Laravel files (Controller, DTO, Action, etc.) from a natural language prompt.
    """
    def run(self):
        self.window.show_input_panel(
            "Describe the Laravel feature to generate:",
            "",
            self.on_feature_description_provided,
            None, None
        )

    def on_feature_description_provided(self, description):
        if not description:
            return

        self.window.show_input_panel(
            "Enter destination directory (relative to project root):",
            "app",
            lambda dir_path: self.generate_feature(description, dir_path),
            None, None
        )

    def generate_feature(self, description, base_directory):
        # Get settings
        settings = sublime.load_settings("Ollama.sublime-settings")
        model = settings.get("model", "qwen2.5-coder")
        url = settings.get("url", "http://127.0.0.1:11434/api/chat")

        # Prepare progress view
        progress_view = self.window.new_file()
        progress_view.set_name("Ollama - Generating Laravel Feature")
        progress_view.set_scratch(True)
        progress_view.run_command("append", {
            "characters": "Generating Laravel feature based on description:\n\n{}\n\n".format(description)
        })

        # Get project root path
        folders = self.window.folders()
        if not folders:
            progress_view.run_command("append", {"characters": "ERROR: No project folder open"})
            return

        project_root = folders[0]

        # Define the system prompt
        system_prompt = """You are an expert Laravel developer. Given the following feature request, 
generate all necessary Laravel files (controllers, DTOs, action classes, routes, etc.) 
and return a JSON manifest array. Each item should have: 'path' (relative to project root), 
'content' (the file content), and optionally 'append_to' (for routes/web.php, etc.). 
Do not include explanations. Example:
[
  {
    'path': 'app/Http/Controllers/ProductController.php', 
    'content': '<?php\\n\\nnamespace ...\\n\\nclass ...\\n{\\n    ...\\n}\\n'
  },
  {
    'path': 'app/DataTransferObjects/ProductDTO.php', 
    'content': '<?php\\n\\nnamespace ...\\n\\nclass ...\\n{\\n    ...\\n}\\n'
  },
  {
    'append_to': 'routes/web.php', 
    'content': \"Route::get('/products', [ProductController::class, 'index'])->name('products.index');\"
  }
]
The JSON must be valid, properly escaped, and contain nothing but the JSON. No explanation or other text."""

        # Prepare the prompt
        user_prompt = """Generate a Laravel feature with the following description:

{}
Make sure to include all necessary files (Controllers, Models, Migrations, Views, etc.) 
and follow Laravel best practices.""".format(description)

        is_chat_api = "/api/chat" in url

        # Create the payload based on API type
        if is_chat_api:
            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False  # Set to false for structured output
            }).encode("utf-8")
        else:
            # Legacy generate API format
            full_prompt = system_prompt + "\n\n" + user_prompt
            payload = json.dumps({
                "model": model,
                "prompt": full_prompt,
                "stream": False
            }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

        # Start fetching the response
        def fetch():
            try:
                progress_view.run_command("append", {"characters": "Sending request to Ollama API...\n\n"})

                with urllib.request.urlopen(req) as response:
                    result = response.read().decode('utf-8')
                    parsed = json.loads(result)

                    # Extract JSON from response
                    json_response = ""
                    if is_chat_api:
                        if "message" in parsed and "content" in parsed["message"]:
                            json_response = parsed["message"]["content"]
                    else:
                        json_response = parsed.get("response", "")

                    # Clean up the response to ensure it's valid JSON
                    json_response = json_response.strip()

                    # Remove any markdown code block markers
                    if json_response.startswith("```json"):
                        json_response = json_response[7:]
                    if json_response.startswith("```"):
                        json_response = json_response[3:]
                    if json_response.endswith("```"):
                        json_response = json_response[:-3]

                    json_response = json_response.strip()

                    try:
                        feature_data = json.loads(json_response)

                        # Process and create files
                        progress_view.run_command("append", {"characters": "Creating files...\n\n"})

                        for file_data in feature_data.get("files", []):
                            path = file_data.get("path", "")
                            content = file_data.get("content", "")

                            if not path or not content:
                                continue

                            # Create full path
                            full_path = os.path.join(project_root, path)

                            # Ensure directory exists
                            os.makedirs(os.path.dirname(full_path), exist_ok=True)

                            # Write file
                            with open(full_path, "w", encoding="utf-8") as f:
                                f.write(content)

                            progress_view.run_command("append", {"characters": "✓ Created {}\n".format(path)})

                        # Process routes
                        if "routes" in feature_data:
                            routes = feature_data["routes"]

                            # Web routes
                            if "web" in routes and routes["web"]:
                                web_routes_path = os.path.join(project_root, "routes/web.php")
                                if os.path.exists(web_routes_path):
                                    with open(web_routes_path, "a", encoding="utf-8") as f:
                                        f.write("\n\n// Added routes\n")
                                        for route in routes["web"]:
                                            f.write(route + "\n")
                                    progress_view.run_command("append", {"characters": "✓ Added web routes\n"})

                            # API routes
                            if "api" in routes and routes["api"]:
                                api_routes_path = os.path.join(project_root, "routes/api.php")
                                if os.path.exists(api_routes_path):
                                    with open(api_routes_path, "a", encoding="utf-8") as f:
                                        f.write("\n\n// Added routes\n")
                                        for route in routes["api"]:
                                            f.write(route + "\n")
                                    progress_view.run_command("append", {"characters": "✓ Added API routes\n"})

                        progress_view.run_command("append", {"characters": "\n✓ Feature generation complete!\n"})

                    except json.JSONDecodeError as e:
                        progress_view.run_command("append", {
                            "characters": "\nERROR: Failed to parse model response as JSON. Error: {}\n\nRaw response:\n{}".format(str(e), json_response)
                        })

            except Exception as e:
                progress_view.run_command("append", {"characters": "\nERROR: {}".format(e)})

        sublime.set_timeout_async(fetch, 0)

class OllamaGenerateTestCommand(sublime_plugin.WindowCommand):
    """
    Command to generate unit tests for a controller by analyzing the existing controller file
    and creating a proper test file in the tests directory.
    """
    
    def run(self):
        # Get active folders in project
        folders = self.window.folders()
        if not folders:
            sublime.error_message("No project folders found. Please open a project first.")
            return
            
        # Create a progress indicator
        self.progress_view = self.window.create_output_panel("ollama_test_progress")
        self.window.run_command("show_panel", {"panel": "output.ollama_test_progress"})
        self.progress_view.run_command("append", {"characters": "Searching for controllers...\n"})
        
        # Start search in a background thread
        sublime.set_timeout_async(lambda: self.find_controllers(folders[0]), 0)
    
    def find_controllers(self, project_root):
        controllers = []
        controllers_dir = os.path.join(project_root, "app", "Http", "Controllers")
        
        # Check if the Controllers directory exists
        if not os.path.exists(controllers_dir):
            # Try app/Controllers as fallback
            controllers_dir = os.path.join(project_root, "app", "Controllers")
            if not os.path.exists(controllers_dir):
                self.progress_view.run_command("append", {"characters": "❌ No controllers directory found. Looking for PHP files...\n"})
                # Fallback: Search for all PHP files that might be controllers
                for root, dirs, files in os.walk(os.path.join(project_root, "app")):
                    for file in files:
                        if file.endswith(".php") and "Controller" in file:
                            rel_path = os.path.relpath(os.path.join(root, file), project_root)
                            controllers.append(rel_path)
                
                if not controllers:
                    self.progress_view.run_command("append", {"characters": "❌ No controllers found in the project.\n"})
                    return
        else:
            # Find all PHP files in the Controllers directory and subdirectories
            for root, dirs, files in os.walk(controllers_dir):
                for file in files:
                    if file.endswith(".php"):
                        rel_path = os.path.relpath(os.path.join(root, file), project_root)
                        controllers.append(rel_path)
        
        # Sort controllers alphabetically
        controllers.sort()
        
        if controllers:
            self.progress_view.run_command("append", {"characters": "✅ Found {} controllers\n".format(len(controllers))})
            self.project_root = project_root
            
            # Show quick panel to select controller
            sublime.set_timeout(lambda: self.window.show_quick_panel(controllers, lambda idx: self.on_controller_selected(idx, controllers, project_root)), 0)
        else:
            self.progress_view.run_command("append", {"characters": "❌ No controllers found in the project.\n"})
    
    def on_controller_selected(self, idx, controllers, project_root):
        if idx == -1:
            return  # User cancelled
            
        controller_path = controllers[idx]
        controller_file = os.path.join(project_root, controller_path)
        
        self.progress_view.run_command("append", {"characters": "Selected: {}\n".format(controller_path)})
        
        # Read the controller file
        try:
            with open(controller_file, 'r') as f:
                controller_code = f.read()
        except Exception as e:
            self.progress_view.run_command("append", {"characters": "❌ Error reading controller file: {}\n".format(str(e))})
            return
        
        # Extract the controller name from file path
        controller_name = os.path.basename(controller_path)
        controller_name = os.path.splitext(controller_name)[0]
        
        # Generate test file path (following Laravel convention)
        test_dir = os.path.join(project_root, "tests", "Feature")
        if not os.path.exists(test_dir):
            # Try Unit directory if Feature doesn't exist
            test_dir = os.path.join(project_root, "tests", "Unit")
            if not os.path.exists(test_dir):
                # Create Feature directory if neither exists
                os.makedirs(os.path.join(project_root, "tests", "Feature"), exist_ok=True)
                test_dir = os.path.join(project_root, "tests", "Feature")
        
        test_file = os.path.join(test_dir, controller_name + "Test.php")
        
        self.progress_view.run_command("append", {"characters": "Analyzing controller: {}\nGenerating test...\n".format(controller_name)})
        
        # Get settings
        settings = sublime.load_settings("Ollama.sublime-settings")
        model = settings.get("model", "qwen2.5-coder")
        url = settings.get("url", "http://127.0.0.1:11434/api/chat")
        system_prompt = settings.get("system_prompt", "You are a Laravel PHP expert.")
        is_chat_api = "/api/chat" in url
        
        # Prepare the prompt
        user_prompt = "Create a PHPUnit test for this Laravel controller. Return ONLY the complete PHP code for a test file that would go in {}. Include proper namespaces and imports. The test should cover all methods and functionality of this controller:\n\n```php\n{}\n```".format(test_file, controller_code)
        
        # Prepare API payload
        if is_chat_api:
            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False  # We want complete response, not streamed
            }).encode("utf-8")
        else:
            payload = json.dumps({
                "model": model,
                "prompt": "{}\n\n{}".format(system_prompt, user_prompt),
                "stream": False
            }).encode("utf-8")
        
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        
        # Call API in a separate thread
        sublime.set_timeout_async(lambda: self.fetch_test(req, test_file, is_chat_api, controller_name), 0)
    
    def fetch_test(self, req, test_file, is_chat_api, controller_name):
        try:
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    # Parse response
                    response_data = json.loads(response.read().decode("utf-8"))
                    
                    # Extract code from response
                    if is_chat_api and "message" in response_data:
                        test_code = response_data["message"]["content"]
                    else:
                        test_code = response_data.get("response", "")
                    
                    # Extract code block if wrapped in markdown
                    if "```php" in test_code:
                        code_blocks = re.findall(r"```php\n(.*?)\n```", test_code, re.DOTALL)
                        if code_blocks:
                            test_code = code_blocks[0]
                    elif "```" in test_code:
                        code_blocks = re.findall(r"```\n(.*?)\n```", test_code, re.DOTALL)
                        if code_blocks:
                            test_code = code_blocks[0]
                    
                    # Write test to file
                    os.makedirs(os.path.dirname(test_file), exist_ok=True)
                    with open(test_file, 'w') as f:
                        f.write(test_code)
                    
                    # Show success message
                    self.progress_view.run_command("append", {"characters": "✅ Test file created: {}\n".format(test_file)})
                    
                    # Open the test file
                    self.window.open_file(test_file)
                else:
                    self.progress_view.run_command("append", {"characters": "Error: API returned status {}\n".format(response.status)})
        
        except Exception as e:
            self.progress_view.run_command("append", {"characters": "Error generating test: {}\n".format(str(e))})

class OllamaSmartGenerateCommand(sublime_plugin.WindowCommand):
    """
    Advanced command to generate multiple files from a single prompt.
    Similar to how Cascade works, this can create controllers, models, DTOs,
    and other related files from a natural language description.
    """
    
    def run(self):
        # Get user prompt for what to generate
        self.window.show_input_panel(
            "Describe what to generate (e.g., 'Create a Product controller with DTOs and action classes'):",
            "",
            self.on_prompt_done,
            None,
            None
        )
    
    def on_prompt_done(self, user_prompt):
        if not user_prompt.strip():
            return
            
        # Get project folders
        folders = self.window.folders()
        if not folders:
            sublime.error_message("No project folders found. Please open a project first.")
            return
            
        project_root = folders[0]
        
        # Create progress view
        self.progress_view = self.window.create_output_panel("ollama_generate_progress")
        self.window.run_command("show_panel", {"panel": "output.ollama_generate_progress"})
        self.progress_view.run_command("append", {"characters": "Analyzing request: '{}'\n".format(user_prompt)})
        
        # Get settings
        settings = sublime.load_settings("Ollama.sublime-settings")
        model = settings.get("model", "qwen2.5-coder")
        url = settings.get("url", "http://127.0.0.1:11434/api/chat")
        system_prompt = settings.get("system_prompt", "You are a Laravel PHP expert.")
        is_chat_api = "/api/chat" in url
        
        # Prepare the prompt
        feature_prompt = """
        Analyze the user's request and generate multiple Laravel files as needed. 
        Output must be a valid JSON object with this structure:
        
        {
          "files": [
            {
              "path": "relative/path/to/file.php",
              "content": "<?php\\n\\nnamespace...the full file content"
            },
            ...more files...
          ]
        }
        
        You must return valid JSON only. Create all necessary files for the request including controllers, 
        models, DTOs, repositories, services, routes, migrations, etc. Follow Laravel best practices 
        with proper namespaces. The path should be relative to the Laravel project root.
        
        User request: {}
        """.format(user_prompt)
        
        # Prepare API payload
        if is_chat_api:
            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": feature_prompt}
                ],
                "stream": False  # We need the complete response at once
            }).encode("utf-8")
        else:
            payload = json.dumps({
                "model": model,
                "prompt": "{}\n\n{}".format(system_prompt, feature_prompt),
                "stream": False
            }).encode("utf-8")
        
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        
        # Call API in a separate thread
        sublime.set_timeout_async(lambda: self.fetch_and_process_files(req, is_chat_api, project_root), 0)
    
    def fetch_and_process_files(self, req, is_chat_api, project_root):
        try:
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    # Parse response
                    response_data = json.loads(response.read().decode("utf-8"))
                    
                    # Extract content from response
                    if is_chat_api and "message" in response_data:
                        content = response_data["message"]["content"]
                    else:
                        content = response_data.get("response", "")
                    
                    # Try to extract JSON from the content
                    try:
                        # Find JSON content within markdown or text
                        json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
                        if json_match:
                            content = json_match.group(1)
                        else:
                            # Try to find any JSON block
                            json_match = re.search(r'```\n(.*?)\n```', content, re.DOTALL)
                            if json_match:
                                content = json_match.group(1)
                        
                        # Parse the JSON
                        files_data = json.loads(content)
                        
                        # If there's no "files" key but the response is a valid array
                        if isinstance(files_data, list):
                            files = files_data
                        else:
                            files = files_data.get("files", [])
                        
                        # Create a new tab to preview the files
                        preview_view = self.window.new_file()
                        preview_view.set_name("Ollama Generate Preview")
                        preview_view.set_scratch(True)
                        
                        # Add header and files content to preview
                        preview_content = "# Generated Files Preview\n\n"
                        preview_content += "The following files will be created:\n\n"
                        
                        file_paths = []
                        file_contents = []
                        
                        for file_info in files:
                            file_path = file_info.get("path")
                            file_content = file_info.get("content")
                            
                            if file_path and file_content:
                                file_paths.append(file_path)
                                file_contents.append(file_content)
                                
                                preview_content += "# {}\n\n```php\n{}\n```\n\n".format(file_path, file_content)
                        
                        preview_view.run_command("append", {"characters": preview_content})
                        
                        # Store files data for later use
                        preview_view.settings().set("ollama_files", {
                            "paths": file_paths,
                            "contents": file_contents,
                            "project_root": project_root
                        })
                        
                        # Add buttons for save/discard
                        self.add_phantom_buttons(preview_view)
                        
                        # Log success to progress view
                        self.progress_view.run_command("append", {
                            "characters": "Generated {} files. Review them in the preview and choose to save or discard.\n".format(len(file_paths))
                        })
                        
                    except json.JSONDecodeError as e:
                        # If we couldn't parse JSON, show the raw output in a tab
                        self.progress_view.run_command("append", {"characters": "Failed to parse JSON response: {}\n".format(str(e))})
                        
                        # Show raw response in a new tab
                        raw_view = self.window.new_file()
                        raw_view.set_name("Ollama Raw Response")
                        raw_view.set_scratch(True)
                        raw_view.run_command("append", {"characters": "Failed to parse JSON. Raw response:\n\n" + content})
                else:
                    self.progress_view.run_command("append", {"characters": "API returned error status: {}\n".format(response.status)})
        except Exception as e:
            self.progress_view.run_command("append", {"characters": "Error: {}\n".format(str(e))})
    
    def add_phantom_buttons(self, view):
        """Add Save/Discard buttons to the preview view"""
        phantom_content = """
        <div style="padding: 10px;">
            <a href="save">Save All Files</a>&nbsp;&nbsp;|&nbsp;&nbsp;<a href="discard">Discard</a>
        </div>
        """
        
        phantom_set = sublime.PhantomSet(view, "ollama_buttons")
        phantom = sublime.Phantom(
            sublime.Region(0, 0),
            phantom_content,
            sublime.LAYOUT_BLOCK,
            on_navigate=lambda href: self.on_button_click(href, view)
        )
        phantom_set.update([phantom])
    
    def on_button_click(self, href, view):
        """Handle button clicks in the preview"""
        if href == "save":
            # Get stored file data
            file_data = view.settings().get("ollama_files")
            if not file_data:
                sublime.error_message("File data not found")
                return
                
            paths = file_data.get("paths", [])
            contents = file_data.get("contents", [])
            project_root = file_data.get("project_root", "")
            
            # Create files
            created_files = []
            for i, (rel_path, content) in enumerate(zip(paths, contents)):
                try:
                    full_path = os.path.join(project_root, rel_path)
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    
                    with open(full_path, "w") as f:
                        f.write(content)
                    
                    created_files.append(rel_path)
                except Exception as e:
                    sublime.error_message("Error creating file {}: {}".format(rel_path, str(e)))
            
            # Close preview tab
            self.window.focus_view(view)
            self.window.run_command("close")
            
            # Show success message
            if created_files:
                message = "Created {} files:\n".format(len(created_files)) + "\n".join(created_files)
                sublime.message_dialog(message)
                
                # Open the first file
                if created_files:
                    self.window.open_file(os.path.join(project_root, created_files[0]))
                    
        elif href == "discard":
            # Close preview tab without saving
            self.window.focus_view(view)
            self.window.run_command("close")
            sublime.status_message("Generation discarded")
