import sublime
import sublime_plugin
import urllib.request
import json
import os
import threading

class OllamaPromptCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.show_input_panel("Enter your prompt:", "", self.on_done, None, None)

    def on_done(self, user_input):
        settings = sublime.load_settings("Ollama.sublime-settings")
        model = settings.get("model", "qwen2.5-coder")
        url = settings.get("url", "http://127.0.0.1:11434/api/chat")
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
                    {"role": "user", "content": user_input}
                ],
                "stream": True
            }).encode("utf-8")
        else:
            payload = json.dumps({
                "model": model,
                "prompt": user_input,
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

                            # Handle chat API format
                            if is_chat_api:
                                if "message" in parsed and "content" in parsed["message"]:
                                    content = parsed["message"]["content"]
                                    result += content
                                    tab.run_command("append", {"characters": content})
                            # Handle generate API format
                            else:
                                if "response" in parsed:
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

class OllamaExplainCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        # Get selected text
        selected_text = ""
        for region in self.view.sel():
            if not region.empty():
                selected_text += self.view.substr(region)

        if not selected_text:
            sublime.status_message("Nothing selected")
            return

        # Get settings
        settings = sublime.load_settings("Ollama.sublime-settings")
        model = settings.get("model", "qwen2.5-coder")
        url = settings.get("url", "http://127.0.0.1:11434/api/chat")
        syntax = settings.get("syntax", "Packages/Markdown/Markdown.sublime-syntax")
        tab_title_prefix = settings.get("tab_title_prefix", "Ollama: ")
        explain_prompt = settings.get("explain_prompt", "Explain this code in detail:")
        is_chat_api = "/api/chat" in url

        # Create output tab
        tab = self.view.window().new_file()
        tab.set_name("{}Explain".format(tab_title_prefix))
        tab.set_syntax_file(syntax)
        tab.set_scratch(True)

        # Add header to tab
        tab.run_command("append", {"characters": "# Code Explanation\n\n```\n{}\n```\n\n".format(selected_text)})

        # Prepare payload
        if is_chat_api:
            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a helpful code explanation assistant."},
                    {"role": "user", "content": "{}\n\n```\n{}\n```".format(explain_prompt, selected_text)}
                ],
                "stream": True
            }).encode("utf-8")
        else:
            prompt = "{}\n\n```\n{}\n```".format(explain_prompt, selected_text)
            payload = json.dumps({
                "model": model,
                "prompt": prompt,
                "stream": True
            }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

        tab.run_command("append", {"characters": "## Explanation\n\n"})

        def fetch():
            try:
                with urllib.request.urlopen(req) as response:
                    for line in response:
                        try:
                            parsed = json.loads(line.decode("utf-8"))

                            # Handle both API formats
                            if is_chat_api:
                                if "message" in parsed and "content" in parsed["message"]:
                                    content = parsed["message"]["content"]
                                    tab.run_command("append", {"characters": content})
                            else:
                                if "response" in parsed:
                                    content = parsed.get("response", "")
                                    tab.run_command("append", {"characters": content})

                            if parsed.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                tab.run_command("append", {"characters": "\n\nERROR: {}".format(e)})

        sublime.set_timeout_async(fetch, 0)

class OllamaOptimizeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        # Get selected text
        selected_text = ""
        for region in self.view.sel():
            if not region.empty():
                selected_text += self.view.substr(region)

        if not selected_text:
            sublime.status_message("Nothing selected")
            return

        # Get settings
        settings = sublime.load_settings("Ollama.sublime-settings")
        model = settings.get("model", "qwen2.5-coder")
        url = settings.get("url", "http://127.0.0.1:11434/api/chat")
        syntax = settings.get("syntax", "Packages/Markdown/Markdown.sublime-syntax")
        tab_title_prefix = settings.get("tab_title_prefix", "Ollama: ")
        optimize_prompt = settings.get("optimize_prompt", "Optimize this code and explain your changes:")
        is_chat_api = "/api/chat" in url

        # Create output tab
        tab = self.view.window().new_file()
        tab.set_name("{}Optimize".format(tab_title_prefix))
        tab.set_syntax_file(syntax)
        tab.set_scratch(True)

        # Add header to tab
        tab.run_command("append", {"characters": "# Code Optimization\n\n```\n{}\n```\n\n".format(selected_text)})

        # Prepare payload
        if is_chat_api:
            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a helpful code optimization assistant."},
                    {"role": "user", "content": "{}\n\n```\n{}\n```".format(optimize_prompt, selected_text)}
                ],
                "stream": True
            }).encode("utf-8")
        else:
            prompt = "{}\n\n```\n{}\n```".format(optimize_prompt, selected_text)
            payload = json.dumps({
                "model": model,
                "prompt": prompt,
                "stream": True
            }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

        tab.run_command("append", {"characters": "## Optimized Code & Explanation\n\n"})

        def fetch():
            try:
                with urllib.request.urlopen(req) as response:
                    for line in response:
                        try:
                            parsed = json.loads(line.decode("utf-8"))

                            # Handle both API formats
                            if is_chat_api:
                                if "message" in parsed and "content" in parsed["message"]:
                                    content = parsed["message"]["content"]
                                    tab.run_command("append", {"characters": content})
                            else:
                                if "response" in parsed:
                                    content = parsed.get("response", "")
                                    tab.run_command("append", {"characters": content})

                            if parsed.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                tab.run_command("append", {"characters": "\n\nERROR: {}".format(e)})

        sublime.set_timeout_async(fetch, 0)

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
