import sublime
import sublime_plugin
import urllib.request
import json

class OllamaAiExplainCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.run_with_mode("explain_prompt", "Explain")

    def run_with_mode(self, prompt_key, mode_label):
        settings = sublime.load_settings("Ollama.sublime-settings")
        instruction = settings.get(prompt_key)
        model = settings.get("model", "codellama")
        syntax = settings.get("syntax", "Packages/Markdown/Markdown.sublime-syntax")
        prefix = settings.get("tab_title_prefix", "💬 Ollama")

        sels = self.view.sel()
        if not sels or sels[0].empty():
            sublime.message_dialog(f"[{mode_label}] Please select some code first.")
            return

        code = self.view.substr(sels[0])
        full_prompt = f"You are a senior Laravel PHP developer.\n\n{instruction}\n\nCode:\n{code}"

        data = json.dumps({
            "model": model,
            "prompt": full_prompt,
            "stream": True
        }).encode("utf-8")

        req = urllib.request.Request(
            url="http://127.0.0.1:11434/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )

        self.output_tab = self.view.window().new_file()
        self.output_tab.set_name(f"{prefix} [{mode_label}]")
        self.output_tab.set_scratch(True)
        self.output_tab.set_syntax_file(syntax)
        self.output_tab.run_command("append", {"characters": f"## 🧠 {mode_label}:\n`{instruction}`\n\n⏳ Requesting response from model `{model}`...\n"})

        sublime.set_timeout_async(lambda: self.fetch_response(req, model, instruction), 0)

    def fetch_response(self, req, model, instruction):
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

                final = f"## ✅ Response from {model}\n\n{result}"
                self.output_tab.run_command("select_all")
                self.output_tab.run_command("right_delete")
                self.output_tab.run_command("append", {"characters": final})

        except Exception as e:
            self.output_tab.run_command("append", {"characters": f"\n\n❌ ERROR: {str(e)}"})

class OllamaAiOptimizeCommand(OllamaAiExplainCommand):
    def run(self, edit):
        self.run_with_mode("optimize_prompt", "Optimize")
