# Ollama Sublime Plugin

An AI-powered code assistant for Laravel and PHP developers using [Ollama](https://ollama.com/).

## ✨ Features

- 💬 Prompt tab with custom input (via `Ctrl + Cmd + Enter`)
- ✅ Right-click contextual tools:
  - Explain selected code
  - Optimize selected code
- 🧠 Model integration with `Ollama` (local)
- 🔍 **NEW!** Codebase analysis similar to Cascade
- 📄 **NEW!** AI-powered file creation from descriptions
- ⚙️ **NEW!** Easy model configuration & prompt customization

---

## ⚙️ Configuration

Customize via the built-in settings file:

### Open settings:
- `Preferences → Package Settings → Ollama → Settings`
- **NEW!** Use the quick model switcher: `Ollama AI: Edit Model Settings`
- **NEW!** Edit system prompts: `Ollama AI: Edit System Prompts`

### Example `Ollama.sublime-settings`:
```json
{
  "model": "codellama",
  "url": "http://127.0.0.1:11434/api/generate",
  "explain_prompt": "Explain what the following Laravel code does in simple terms.",
  "optimize_prompt": "Optimize the following Laravel PHP code and return improved code snippets with explanation.",
  "analysis_prompt": "Analyze this code and provide insights on structure, patterns, and potential improvements.",
  "file_creation_prompt_template": "You are a professional developer. Create a {language} file that: {description}",
  "tab_title_prefix": "💬 Ollama",
  "syntax": "Packages/Markdown/Markdown.sublime-syntax",
  "code_file_extensions": [".py", ".php", ".js", ".html", ".css", ".json", ".md", ".rb", ".java", ".c", ".cpp", ".go", ".ts"]
}
```

---

## 🛠️ Commands

### Command Palette
- `Ollama AI: Explain Selection`
- `Ollama AI: Optimize Selection`
- `Ollama AI: Custom Prompt`
- **NEW!** `Ollama AI: Analyze Codebase`
- **NEW!** `Ollama AI: Create New File`
- **NEW!** `Ollama AI: Edit Model Settings`
- **NEW!** `Ollama AI: Edit System Prompts`

### Keyboard Shortcut
- `Ctrl + Cmd + Enter` → Open terminal-style prompt tab

### Context Menu (Right Click)
- `Ollama AI: Explain this code`
- `Ollama AI: Optimize this code`

### Tools Menu
- **NEW!** `Tools → Ollama AI` for quick access to all commands

---

## 🧪 Requirements

- [Ollama](https://ollama.com/) running locally:
  ```
  ollama serve
  ```

- Recommended models: `codellama`, `deepseek-coder`, `gemma`, etc.

## 📦 Manual Installation

Extract into:
```
~/Library/Application Support/Sublime Text/Packages/ollama-sublime/
```

Restart Sublime Text after changes.

## 🆕 New Features Guide

### Codebase Analysis

Analyze your entire codebase like Cascade:
1. Run `Ollama AI: Analyze Codebase` from the command palette
2. Enter what you'd like to analyze (e.g., "Analyze architecture patterns" or "Find security issues")
3. The plugin will scan your project files and send a summary to Ollama
4. Results appear in a new tab with insights and recommendations

### AI-Powered File Creation

Generate new files based on descriptions:
1. Run `Ollama AI: Create New File` from the command palette
2. Describe the file you want (e.g., "A Laravel controller for user authentication")
3. Enter the relative file path (e.g., "app/Http/Controllers/AuthController.php")
4. The plugin will generate and save the file, then open it in the editor

### Model Configuration

Easily switch between Ollama models:
1. Run `Ollama AI: Edit Model Settings` from the command palette
2. Select from available models or configure a custom model
3. Optionally modify the API URL if using a remote Ollama instance
4. Settings are saved automatically

### Custom System Prompts

Personalize how Ollama responds to your requests:
1. Run `Ollama AI: Edit System Prompts` from the command palette
2. Select which prompt template to modify
3. Customize the instruction text
4. Changes are applied immediately to future requests
