import sublime
import sublime_plugin
import urllib.request
import json

class OllamaPromptCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.show_input_panel("💬 Enter your prompt:", "", self.on_done, None, None)

    def on_done(self, user_input):
        settings = sublime.load_settings("Ollama.sublime-settings")
        model = settings.get("model", "codellama")
        url = settings.get("url", "http://127.0.0.1:11434/api/generate")
        syntax = settings.get("syntax", "Packages/Markdown/Markdown.sublime-syntax")

        tab = self.window.new_file()
        tab.set_name("💬 Ollama Prompt")
        tab.set_scratch(True)
        tab.set_syntax_file(syntax)
        tab.run_command("append", {"characters": "🧠 Prompt: {}\n⏳ Model: {}\n\n".format(user_input, model)})
⏳ Model: {}

".format(user_input, model)})

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
                tab.run_command("append", {"characters": "✅ Response:

{}".format(result.strip())})
            except Exception as e:
                tab.run_command("append", {"characters": "\n❌ ERROR: {}".format(e)})

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
        prefix = settings.get("tab_title_prefix", "💬 Ollama")

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
            "characters": "## 🧠 {}:\n`{}`\n\n⏳ Requesting response from model `{}`...\n".format(mode_label, instruction, model)
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

                final = "## ✅ Response from {}\n\n{}".format(model, result)
                self.output_tab.run_command("select_all")
                self.output_tab.run_command("right_delete")
                self.output_tab.run_command("append", {"characters": final})
        except Exception as e:
            self.output_tab.run_command("append", {"characters": "\n\n❌ ERROR: {}".format(str(e))})

class OllamaAiOptimizeCommand(OllamaAiExplainCommand):
    def run(self, edit):
        self.run_with_mode("optimize_prompt", "Optimize")
