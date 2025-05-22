# Ollama Sublime Plugin

An AI-powered code assistant for Laravel and PHP developers using [Ollama](https://ollama.com/).

## ✨ Features

- 💬 Prompt tab with custom input (via `Ctrl + Cmd + Enter`)
- ✅ Right-click contextual tools:
  - Explain selected code
  - Optimize selected code
- 🧠 Model integration with `Ollama` (local)

---

## ⚙️ Configuration

Customize via the built-in settings file:

### Open settings:
- `Preferences → Package Settings → Ollama → Settings`

### Example `Ollama.sublime-settings`:
```json
{
  "model": "codellama",
  "url": "http://127.0.0.1:11434/api/generate",
  "explain_prompt": "Explain what the following Laravel code does in simple terms.",
  "optimize_prompt": "Optimize the following Laravel PHP code and return improved code snippets with explanation.",
  "tab_title_prefix": "💬 Ollama",
  "syntax": "Packages/Markdown/Markdown.sublime-syntax"
}
```

---

## 🛠️ Commands

### Command Palette
- `Ollama AI: Explain Selection`
- `Ollama AI: Optimize Selection`
- `Ollama AI: Custom Prompt`

### Keyboard Shortcut
- `Ctrl + Cmd + Enter` → Open terminal-style prompt tab

### Context Menu (Right Click)
- `Ollama AI: Explain this code`
- `Ollama AI: Optimize this code`

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
