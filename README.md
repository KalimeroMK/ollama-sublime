# Ollama Sublime Plugin

![Ollama AI](https://img.shields.io/badge/Ollama-AI-blue)

Leverage AI coding assistance right within Sublime Text using local LLM models via Ollama.

- 💬 Prompt tab with custom input (via `Ctrl + Cmd + Enter`)
- ✅ Right-click contextual tools:
    - Explain selected code
    - Optimize selected code
- 🧠 Model integration with `Ollama` (local)
- 🔍 **NEW!** Codebase analysis similar to Cascade
- 📄 **NEW!** AI-powered file creation from descriptions
- 🧪 **NEW!** Auto-generate unit tests for controllers
- 🏗️ **NEW!** Multi-file feature generation with preview and save options
- 💻 **NEW!** Full Laravel support for controllers, DTOs, actions, and more

## ⚙️ Configuration

Customize via the built-in settings file:

### Open settings:

- `Preferences → Package Settings → Ollama → Settings`
- **NEW!** Use the quick model switcher: `Ollama AI: Edit Model Settings`
- **NEW!** Edit system prompts: `Ollama AI: Edit System Prompts`
 
### Example `Ollama.sublime-settings`:

```json
{
  "model": "qwen2.5-coder",
  "url": "http://127.0.0.1:11434/api/chat",
  "explain_prompt": "Explain what the following Laravel PHP code does in simple terms.",
  "optimize_prompt": "Act as a Laravel and PHP expert and optimize the following code. Return improved code snippets with explanation.",
  "analysis_prompt": "Analyze this Laravel PHP code and provide insights on structure, patterns, and potential improvements.",
  "file_creation_prompt_template": "You are a professional Laravel PHP developer. Create a {language} file that: {description}",
  "tab_title_prefix": "💬 Ollama",
  "syntax": "Packages/Markdown/Markdown.sublime-syntax",
  "system_prompt": "You are a Laravel PHP expert. When asked about code analysis or test generation, always assume PHP Laravel unless specified otherwise.",
  "code_file_extensions": [
    ".php",
    "blade.php",
    ".js",
    ".html",
    ".css",
    ".json",
    ".md"
  ]
}
```

## 🛠️ Commands

### Command Palette

- `Ollama AI: Explain Selection`
- `Ollama AI: Optimize Selection`
- `Ollama AI: Custom Prompt`
- **NEW!** `Ollama AI: Analyze Codebase`
- **NEW!** `Ollama AI: Create New File`
- **NEW!** `Ollama AI: Edit Model Settings`
- **NEW!** `Ollama AI: Edit System Prompts`
- **NEW!** `Ollama AI: Generate Unit Test`
- **NEW!** `Ollama AI: Generate Feature`
- **NEW!** `Ollama AI: Generate Laravel Feature`

### Keyboard Shortcut

- `Ctrl + Cmd + Enter` → Open terminal-style prompt tab

### Context Menu (Right Click)

- `Ollama AI: Explain this code`
- `Ollama AI: Optimize this code`

### Main Menu

- **NEW!** `Tools → Ollama AI` for quick access to all commands

---

## ⚡ Requirements

- macOS, Linux or Windows
- [Ollama](https://ollama.ai/) installed and running locally
- Ollama model (e.g., `qwen2.5-coder` or any compatible model)
- Sublime Text 3 (Python 3.3+)

## 📦 Installation

### From Package Control (Recommended)

Coming soon! This plugin will be available via Package Control.

### From GitHub Repository

1. Open Sublime Text and go to `Preferences > Browse Packages...` to open the Packages directory
2. Open a terminal and navigate to the Packages directory
3. Clone the repository:
   ```
   git clone https://github.com/KalimeroMK/ollama-sublime.git
   ```
4. Restart Sublime Text

### Manual Installation

Download or clone the repository and extract into:

```
~/Library/Application Support/Sublime Text/Packages/ollama-sublime/
```

## 📚 Usage Guide

### Codebase Analysis

Analyze your entire codebase like Cascade:

1. Run `Ollama AI: Analyze Codebase` from the command palette
2. Enter what you'd like to analyze (e.g., "Analyze architecture patterns" or "Find security issues")
3. The plugin will scan your project files and send a summary to Ollama
4. View the AI analysis in a new tab

### AI-Powered File Creation

Generate new files based on descriptions:

1. Run `Ollama AI: Create New File` from the command palette
2. Describe the file you want (e.g., "A Laravel controller for user authentication")
3. Enter the relative file path (e.g., "app/Http/Controllers/AuthController.php")
4. Ollama will generate the file content and save it

### Generate Unit Tests

Automatically create tests for your controllers:

1. Run `Ollama AI: Generate Unit Test` from the command palette
2. The plugin will scan your project for controllers
3. Select a controller from the list to generate tests for
4. Tests will be generated in the appropriate test directory and opened for review

### Generate Complete Features

Create multiple files for a feature with one command:

1. Run `Ollama AI: Generate Feature` from the command palette
2. Describe what you want to create (e.g., "Create a product controller with DTOs and action classes")
3. Preview all files that will be created
4. Click "Save All Files" to create everything or "Discard" to cancel

### Model Configuration

Easily switch between Ollama models:

1. Run `Ollama AI: Edit Model Settings` from the command palette
2. Select from available models or configure a custom model
3. Optionally modify the API URL if using a remote Ollama instance

### Custom System Prompts

Personalize how Ollama responds to your requests:

1. Run `Ollama AI: Edit System Prompts` from the command palette
2. Select which prompt template to modify
3. Customize the instruction text

## 🔄 API Compatibility

The plugin supports both of Ollama's API endpoints:
- `/api/chat` endpoint (newer, messages-based format)
- `/api/generate` endpoint (older, prompt-based format)

It will automatically detect and use the appropriate format based on your configuration.

## 💡 Tips

- For best results with code generation, be specific in your requests
- Use the system prompt setting to customize the AI's expertise (e.g., Laravel, React)
- When analyzing large codebases, be patient as processing may take time
- The model setting affects both quality and speed - larger models are more capable but slower

## 📝 License

MIT
