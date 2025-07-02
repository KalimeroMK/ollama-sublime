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
        model = settings.get("model", "codellama")
        url = settings.get("url", "http://127.0.0.1:11434/api/generate")
        syntax = settings.get("syntax", "Packages/Markdown/Markdown.sublime-syntax")

        tab = self.window.new_file()
        tab.set_name("Ollama Prompt")
        tab.set_scratch(True)
        tab.set_syntax_file(syntax)
        tab.run_command("append", {
            "characters": "Prompt: {}\nModel: {}\n\n".format(user_input, model)
        })

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
                        parsed = json.loads(line.decode("utf-8"))
                        result += parsed.get("response", "")
                        if parsed.get("done", False):
                            break
                tab.run_command("append", {"characters": "Response:\n\n{}".format(result.strip())})
            except Exception as e:
                tab.run_command("append", {"characters": "\nERROR: {}".format(e)})

        sublime.set_timeout_async(fetch, 0)

class OllamaAiExplainCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.run_with_mode("explain_prompt", "Explain")

    def run_with_mode(self, prompt_key, mode_label):
        settings = sublime.load_settings("Ollama.sublime-settings")
        instruction = settings.get(prompt_key)
        model = settings.get("model", "codellama")
        url = settings.get("url", "http://127.0.0.1:11434/api/generate")
        syntax = settings.get("syntax", "Packages/Markdown/Markdown.sublime-syntax")
        prefix = settings.get("tab_title_prefix", "Ollama")

        sels = self.view.sel()
        if not sels or sels[0].empty():
            sublime.message_dialog("[{}] Please select some code first.".format(mode_label))
            return

        code = self.view.substr(sels[0])
        full_prompt = "You are a senior Laravel PHP developer.\n\n{}\n\nCode:\n{}".format(instruction, code)

        data = json.dumps({
            "model": model,
            "prompt": full_prompt,
            "stream": True
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

        self.output_tab = self.view.window().new_file()
        self.output_tab.set_name("{} [{}]".format(prefix, mode_label))
        self.output_tab.set_scratch(True)
        self.output_tab.set_syntax_file(syntax)
        self.output_tab.run_command("append", {
            "characters": "Running {}...\n\n".format(mode_label)
        })

        sublime.set_timeout_async(lambda: self.fetch_response(req, model), 0)

    def fetch_response(self, req, model):
        try:
            with urllib.request.urlopen(req) as response:
                result = ""
                for line in response:
                    try:
                        parsed = json.loads(line.decode("utf-8"))
                        result += parsed.get("response", "")
                        if parsed.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue

                final = "Response from {}:\n\n{}".format(model, result)
                self.output_tab.run_command("select_all")
                self.output_tab.run_command("right_delete")
                self.output_tab.run_command("append", {"characters": final})
        except Exception as e:
            self.output_tab.run_command("append", {"characters": "\n\nERROR: {}".format(str(e))})

class OllamaAiOptimizeCommand(OllamaAiExplainCommand):
    def run(self, edit):
        self.run_with_mode("optimize_prompt", "Optimize")

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
            url = settings.get("url", "http://127.0.0.1:11434/api/generate")
            
            # Collect file information
            file_info = []
            for folder in folders:
                for root, _, files in os.walk(folder):
                    for file in files:
                        if file.endswith(('.py', '.php', '.js', '.html', '.css', '.json', '.md')):
                            file_path = os.path.join(root, file)
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    # Just get a brief snippet for context
                                    snippet = content[:500] + ("..." if len(content) > 500 else "")
                                    file_info.append({
                                        "path": file_path,
                                        "snippet": snippet,
                                        "language": os.path.splitext(file)[1][1:]
                                    })
                                    
                                    # Update progress
                                    sublime.set_timeout(lambda path=file_path: 
                                        self.progress_view.run_command("append", 
                                            {"characters": f"Scanning: {path}\n"}), 0)
                                    
                            except Exception as e:
                                sublime.set_timeout(lambda e=e, path=file_path: 
                                    self.progress_view.run_command("append", 
                                        {"characters": f"Error reading {path}: {e}\n"}), 0)
            
            # Prepare a summary for the AI
            summary = json.dumps({
                "project_structure": {
                    "folders": folders,
                    "files": [f["path"] for f in file_info[:20]]  # Limit to prevent prompt size issues
                },
                "file_samples": file_info[:5],  # Only send a few samples
                "analysis_request": user_input
            }, indent=2)
            
            # Create the AI prompt
            prompt = f"""You are a code analysis assistant like Cascade.
            
Analyze this codebase and provide insights based on the following request: "{user_input}"

Project information:
{summary}

Provide an in-depth analysis with:
1. Key insights about the codebase structure
2. Recommendations based on the user's request
3. Potential improvements or issues you identify
"""
            
            # Send to Ollama
            payload = json.dumps({
                "model": model,
                "prompt": prompt,
                "stream": True
            }).encode("utf-8")
            
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            
            sublime.set_timeout(lambda: self.progress_view.run_command("append", 
                {"characters": "\n\nSending to Ollama for analysis...\n"}), 0)
                
            # Create the output view
            sublime.set_timeout(lambda: self.create_output_view(req, model), 0)
            
        except Exception as e:
            sublime.set_timeout(lambda e=e: self.progress_view.run_command("append", 
                {"characters": f"\nERROR during analysis: {e}\n"}), 0)
    
    def create_output_view(self, req, model):
        settings = sublime.load_settings("Ollama.sublime-settings")
        syntax = settings.get("syntax", "Packages/Markdown/Markdown.sublime-syntax")
        
        # Create a new view for the output
        output_view = self.window.new_file()
        output_view.set_name("Ollama Code Analysis")
        output_view.set_scratch(True)
        output_view.set_syntax_file(syntax)
        output_view.run_command("append", {"characters": "# Code Analysis\n\nModel: " + model + "\n\n"})
        
        # Start fetching the response
        threading.Thread(target=self.fetch_analysis, args=(req, output_view)).start()
        
    def fetch_analysis(self, req, output_view):
        try:
            result = ""
            with urllib.request.urlopen(req) as response:
                for line in response:
                    parsed = json.loads(line.decode("utf-8"))
                    chunk = parsed.get("response", "")
                    result += chunk
                    
                    # Update the output view
                    sublime.set_timeout(lambda chunk=chunk: 
                        output_view.run_command("append", {"characters": chunk}), 0)
                    
                    if parsed.get("done", False):
                        break
                        
            # Close the progress view
            sublime.set_timeout(lambda: self.progress_view.close(), 1000)
            
        except Exception as e:
            sublime.set_timeout(lambda e=e: 
                output_view.run_command("append", {"characters": f"\n\nERROR: {e}"}), 0)

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
                sublime.message_dialog(f"Error creating directory: {e}")
                return
                
        # Get file extension to determine language
        _, ext = os.path.splitext(full_path)
        language = ext[1:] if ext else "text"
        
        # Get Ollama settings
        settings = sublime.load_settings("Ollama.sublime-settings")
        model = settings.get("model", "codellama")
        url = settings.get("url", "http://127.0.0.1:11434/api/generate")
        
        # Create a progress view
        progress_view = self.window.new_file()
        progress_view.set_name("Creating File")
        progress_view.set_scratch(True)
        progress_view.run_command("append", {"characters": f"Creating file at {full_path}...\n"})
        
        # Generate the prompt for file creation
        prompt = f"""You are a professional developer. Create a new {language} file based on this description:
{self.description}

File should be created at: {full_path}

Generate only the file content, with no additional explanations or markdown formatting.
"""
        
        # Create the payload
        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": True
        }).encode("utf-8")
        
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        
        # Start fetching the response
        def fetch():
            try:
                file_content = ""
                with urllib.request.urlopen(req) as response:
                    for line in response:
                        parsed = json.loads(line.decode("utf-8"))
                        content = parsed.get("response", "")
                        file_content += content
                        
                        # Update progress view
                        sublime.set_timeout(lambda c=content: 
                            progress_view.run_command("append", {"characters": c}), 0)
                        
                        if parsed.get("done", False):
                            break
                            
                # Write the file
                try:
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(file_content)
                        
                    # Close the progress view and open the new file
                    sublime.set_timeout(lambda: progress_view.close(), 500)
                    sublime.set_timeout(lambda: self.window.open_file(full_path), 1000)
                    
                except Exception as e:
                    sublime.set_timeout(lambda e=e: 
                        progress_view.run_command("append", 
                            {"characters": f"\nERROR writing file: {e}"}), 0)
                    
            except Exception as e:
                sublime.set_timeout(lambda e=e: 
                    progress_view.run_command("append", 
                        {"characters": f"\nERROR: {e}"}), 0)
                    
        threading.Thread(target=fetch).start()

class OllamaEditSettingsCommand(sublime_plugin.WindowCommand):
    """
    Edit Ollama.sublime-settings with model configuration
    """
    def run(self):
        settings = sublime.load_settings("Ollama.sublime-settings")
        
        # Get available models from Ollama API
        url = settings.get("url", "http://127.0.0.1:11434/api/generate").replace("/api/generate", "/api")
        models_url = f"{url}/tags"
        
        def fetch_models():
            try:
                with urllib.request.urlopen(models_url) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    # Extract model names
                    models = [model['name'] for model in data.get('models', [])]
                    if not models:
                        models = ["codellama", "llama2", "mistral", "phi"]  # Fallback options
                    
                    sublime.set_timeout(lambda models=models: self.show_models_panel(models), 0)
            except Exception as e:
                print(f"Error fetching models: {e}")
                # Fallback to default models
                models = ["codellama", "llama2", "mistral", "phi"]
                sublime.set_timeout(lambda models=models: self.show_models_panel(models), 0)
        
        threading.Thread(target=fetch_models).start()
    
    def show_models_panel(self, models):
        self.models = models
        self.window.show_quick_panel(models, self.on_model_selected)
    
    def on_model_selected(self, index):
        if index == -1:
            return
            
        model = self.models[index]
        settings = sublime.load_settings("Ollama.sublime-settings")
        
        # Update model in settings
        settings.set("model", model)
        sublime.save_settings("Ollama.sublime-settings")
        
        # Show confirmation
        sublime.status_message(f"Ollama model updated to: {model}")
        
        # Now ask for URL configuration
        self.window.show_input_panel(
            "Ollama API URL (leave empty for default):",
            settings.get("url", "http://127.0.0.1:11434/api/generate"),
            self.on_url_entered, None, None
        )
    
    def on_url_entered(self, url):
        if url:
            settings = sublime.load_settings("Ollama.sublime-settings")
            settings.set("url", url)
            sublime.save_settings("Ollama.sublime-settings")
            sublime.status_message(f"Ollama API URL updated to: {url}")
            
        # Open the settings file for additional editing
        self.window.run_command("open_file", {"file": "${packages}/User/Ollama.sublime-settings"})

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
            f"Edit {self.prompt_descriptions[index]}:",
            current_value,
            self.on_prompt_edited, None, None
        )
    
    def on_prompt_edited(self, new_value):
        settings = sublime.load_settings("Ollama.sublime-settings")
        settings.set(self.selected_prompt, new_value)
        sublime.save_settings("Ollama.sublime-settings")
        sublime.status_message(f"Updated {self.selected_prompt}")

class OllamaGenerateLaravelFeatureCommand(sublime_plugin.WindowCommand):
    """
    Generate multiple Laravel files (Controller, DTO, Action, etc.) from a natural language prompt.
    """
    def run(self):
        self.window.show_input_panel(
            "Describe the Laravel feature to generate:",
            "Create Product controller with DTO and action class",
            self.on_done, None, None
        )

    def on_done(self, user_prompt):
        folders = self.window.folders()
        if not folders:
            sublime.message_dialog("No project folders open. Please open a project first.")
            return
        self.project_root = folders[0]
        self.progress_view = self.window.new_file()
        self.progress_view.set_name("Laravel Feature Generation Progress")
        self.progress_view.set_scratch(True)
        self.progress_view.run_command("append", {"characters": f"Generating files for: {user_prompt}\n"})

        # Meta-instruction for the model
        meta_instruction = (
            "You are an expert Laravel developer. Given the following feature request, "
            "generate all necessary Laravel files (controllers, DTOs, action classes, routes, etc.) "
            "and return a JSON manifest array. Each item should have: 'path' (relative to project root), "
            "'content' (the file content), and optionally 'append_to' (for routes/web.php, etc.). "
            "Do not include explanations. Example:\n"
            "[\n"
            "  {\n    'path': 'app/Http/Controllers/ProductController.php', 'content': '...php code...'\n  },\n"
            "  {\n    'path': 'app/DataTransferObjects/ProductDTO.php', 'content': '...php code...'\n  },\n"
            "  {\n    'append_to': 'routes/web.php', 'content': "Route::resource('products', ProductController::class);"\n  }\n"
            "]\n"
            "Now, here is the feature request: " + user_prompt
        )

        # Get settings
        settings = sublime.load_settings("Ollama.sublime-settings")
        model = settings.get("model", "codellama")
        url = settings.get("url", "http://127.0.0.1:11434/api/generate")

        # Prepare payload (use /api/chat if needed)
        if "/chat" in url:
            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a helpful Laravel code generator."},
                    {"role": "user", "content": meta_instruction}
                ],
                "stream": True
            }).encode("utf-8")
        else:
            payload = json.dumps({
                "model": model,
                "prompt": meta_instruction,
                "stream": True
            }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

        # Start async fetch
        import threading
        threading.Thread(target=self.fetch_and_generate, args=(req,)).start()

    def fetch_and_generate(self, req):
        import re
        import time
        try:
            buffer = ""
            with urllib.request.urlopen(req) as response:
                for line in response:
                    try:
                        parsed = json.loads(line.decode("utf-8"))
                        chunk = parsed.get("response", "") or parsed.get("content", "")
                        buffer += chunk
                        sublime.set_timeout(lambda c=chunk: self.progress_view.run_command("append", {"characters": c}), 0)
                        if parsed.get("done", False):
                            break
                    except Exception:
                        continue
            # Try to extract JSON manifest from buffer
            manifest_match = re.search(r'(\[.*\])', buffer, re.DOTALL)
            if not manifest_match:
                sublime.set_timeout(lambda: self.progress_view.run_command("append", {"characters": "\nERROR: Could not parse manifest from model output."}), 0)
                return
            manifest_str = manifest_match.group(1)
            try:
                manifest = json.loads(manifest_str.replace("'", '"'))
            except Exception as e:
                sublime.set_timeout(lambda: self.progress_view.run_command("append", {"characters": f"\nERROR parsing manifest: {e}"}), 0)
                return
            # Create files and append to routes
            for item in manifest:
                if 'path' in item:
                    abs_path = os.path.join(self.project_root, item['path'])
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    with open(abs_path, 'w', encoding='utf-8') as f:
                        f.write(item['content'])
                    sublime.set_timeout(lambda p=abs_path: self.progress_view.run_command("append", {"characters": f"\nCreated: {p}"}), 0)
                    sublime.set_timeout(lambda p=abs_path: self.window.open_file(p), 0)
                elif 'append_to' in item:
                    abs_path = os.path.join(self.project_root, item['append_to'])
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    with open(abs_path, 'a', encoding='utf-8') as f:
                        f.write('\n' + item['content'])
                    sublime.set_timeout(lambda p=abs_path: self.progress_view.run_command("append", {"characters": f"\nAppended to: {p}"}), 0)
            sublime.set_timeout(lambda: self.progress_view.run_command("append", {"characters": "\nAll files generated."}), 0)
        except Exception as e:
            sublime.set_timeout(lambda: self.progress_view.run_command("append", {"characters": f"\nERROR: {e}"}), 0)
