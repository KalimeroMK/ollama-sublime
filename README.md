# Laravel Workshop AI

AI-powered code assistance for Sublime Text 4, powered by local Ollama LLMs. **Now with Cursor-like file generation!** 🤖🚀

## 🎯 **NEW: Automated File Generation (Cursor-like)**

**Generate complete features automatically - just describe what you need!**

- **✨ Smart File Generation** - AI analyzes your project structure and creates all necessary files
- **📁 Multi-File Creation** - Generate models, controllers, migrations, routes, views in one go
- **🔍 Project-Aware** - Understands Laravel structure, PSR-4 namespaces, existing patterns
- **🎨 Best Practices** - Follows Laravel conventions automatically
- **💻 Inline Chat with `create:` prefix** - Chat interface that can also create files

### Usage Examples
```bash
# Generate complete CRUD for Products
Command: Laravel Workshop AI: Generate Files
Input: "Create a complete CRUD for Products with API endpoints"

# Via Chat interface
Command: Laravel Workshop AI: Inline Chat
Input: "create: Build a blog post system with comments and tags"

Result: AI analyzes project → creates 6+ files automatically!
```

## 🤖 **NEW: AI Agent Framework**

**Autonomous code generation like Cursor/Windsurf, but 100% local!**

- **🏗️ Multi-Agent Workflows** - Architect, Coder, Reviewer agents work together
- **🛠️ Tool Calling** - Agents can read files, write code, run tests autonomously
- **🧠 Persistent Memory** - Learns from your project and coding patterns
- **💬 Interactive Chat** - Multi-turn conversations with context awareness
- **🔒 100% Private** - Everything runs locally, your code never leaves your machine

### Quick Example
```
You: "Create a Laravel CRUD for Products with API and tests"

🏗️ Architect: Designs structure
💻 Coder: Writes implementation
🔍 Reviewer: Checks quality
✅ Result: Complete feature ready to use!
```


## Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Usage](#-usage)
- [AI Provider Configuration](#-ai-provider-configuration)
  - [Ollama (Local)](#ollama-local)
  - [OpenAI (ChatGPT/GPT-4)](#openai-chatgptgpt-4)
  - [Gemini Setup](#gemini-setup)
  - [Custom Server (Tesla L4)](#custom-server-tesla-l4)
- [Laravel Features](#-laravel-features)
  - [Sidebar Chat](#sidebar-chat)
  - [Model Autocomplete](#model-autocomplete)
  - [Show Model Info](#show-model-info)
- [Project Structure Detection](#-project-structure-detection)
- [Background Workers](#background-workers)
- [Scanners and Auto-Fixes](#scanners-and-auto-fixes)
  - [N+1 Detector](#n1-detector)
  - [Controller Validation → FormRequest](#controller-validation--formrequest)
- [Plugin Cleanup](#plugin-cleanup)
- [Examples](#-examples)
- [Troubleshooting](#-troubleshooting)
 - [AI Agents Guide](#-ai-agents-guide)
 - [Tesla L4 Server Setup](#-tesla-l4-server-setup)

## 🚀 Features

### AI Agent Features (NEW!)
- **🤖 Generate Feature** - Create complete features from descriptions
- **🐛 Debug Code** - AI finds and fixes bugs autonomously
- **♻️ Refactor Code** - Improve code quality with best practices
- **💬 Agent Chat** - Interactive conversations with memory
- **🎯 Custom Tasks** - Use specialized agents for any task

### Original Features
- **Code Generation** - Generate code from natural language prompts
- **Code Explanation** - Understand existing code with AI analysis
- **Refactoring Suggestions** - Get AI-powered code improvements
- **Multi-File Context** - AI understands your entire project structure
- **Performance Optimization** - Get suggestions for better code performance
- **🎯 Inline AI Chat** - Cursor-like chat interface directly in your editor
- **⚡ Smart Completion** - AI-powered code completion and suggestions
- **🔍 Real-time Suggestions** - Get AI insights as you code

## 📦 Installation

1. **Install Ollama** and pull a model:
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ollama pull qwen2.5-coder
   ```

2. **Install the plugin**:
   - Copy `LaravelWorkshopAI` folder to your Sublime Text Packages directory
   - Restart Sublime Text

3. **Configure** (optional):
   - Open `Tools → Laravel Workshop AI → Settings`
   - Adjust model, URL, and other settings

## 🎯 Usage

### Quick Start with AI Agents
1. Open Command Palette (`Cmd+Shift+P`)
2. Type `Laravel Workshop AI Agent: Generate Feature`
3. Describe what you want: *"Create a Laravel REST API for Products with validation and tests"*
4. Watch the agents work autonomously! 🤖

### **AI Agent Commands** (Primary - Use these!)
- **`Laravel Workshop AI Agent: Generate Feature`** - Multi-agent feature generation
- **`Laravel Workshop AI Agent: Debug Code`** - Autonomous debugging
- **`Laravel Workshop AI Agent: Refactor Code`** - AI-powered refactoring
- **`Laravel Workshop AI Agent: Custom Task`** - Use specialized agents
- **`Laravel Workshop AI Agent: Chat`** - Interactive chat with memory

### **Specialized Commands**
- **`Laravel Workshop AI: PHP/Laravel Completion`** - Smart PHP/Laravel autocomplete
- **`Laravel Workshop AI: Create File`** - Generate single file from description
- **`Laravel Workshop AI: Generate Files (Cursor-like)`** - ✨ **NEW!** AI analyzes project and generates multiple files
- **`Laravel Workshop AI: Inline Chat`** - Quick chat interface (use `create: ` prefix for file creation)
- **`Laravel Workshop AI: Smart Completion`** - AI-powered code completion

### **Utility Commands**
- **`Laravel Workshop AI: Cache Manager`** - Manage cache
- **`Laravel Workshop AI: Settings`** - Open settings
- **`Laravel Workshop AI: Cleanup Deprecated`** - Move legacy plugin files to `_deprecated/`
- **`Laravel Workshop AI: Auto Cleanup`** - Automatically move known legacy plugin files

### Right-Click Menu
- **🤖 AI Agents** submenu with all agent commands
- **PHP/Laravel Completion** - Smart completions
- **Create File** - Quick file generation

## ⚙️ Configuration

### AI Provider (NEW!)

Choose your AI provider:

```json
{
    // Choose: "ollama" (local), "openai" (ChatGPT), "custom" (your server)
    "ai_provider": "ollama",
    
    // Ollama (local)
    "ollama": {
        "base_url": "http://localhost:11434",
        "model": "qwen2.5-coder:14b"
    },
    
    // OpenAI (ChatGPT/GPT-4)
    "openai": {
        "api_key": "sk-proj-xxxxx",
        "model": "gpt-4"
    },
    
    // Custom (your Tesla L4 server)
    "custom": {
        "base_url": "http://your-server:8000",
        "api_key": "optional-key",
        "model": "your-model",
        "api_format": "openai"
    }
}
```

See the sections below for details.

### Ollama (Local)

Use local models with full privacy.

```json
{
  "ai_provider": "ollama",
  "ollama": { "base_url": "http://localhost:11434", "model": "qwen2.5-coder:14b" }
}
```

### OpenAI (ChatGPT/GPT-4)

```json
{
  "ai_provider": "openai",
  "openai": { "api_key": "sk-...", "model": "gpt-4" }
}
```

### Gemini Setup

To use Google Gemini, set the provider to `gemini` and add your API key from Google AI Studio.

```json
{
  "ai_provider": "gemini",
  "gemini": {
    "api_key": "AIza...",
    "model": "gemini-1.5-pro",
    "temperature": 0.7,
    "max_tokens": 8000,
    "timeout": 60
  }
}
```

Recommended models:

- `gemini-1.5-pro` – best quality, 1M-token context
- `gemini-1.5-flash` – faster and cheaper

Pricing (approx.): Pro $0.00125/1K input, Flash $0.00025/1K input. Free tier: 15 req/min.

### Custom Server (Tesla L4)

Run your own OpenAI-compatible server (e.g., vLLM) and point the client to it.

```json
{
  "ai_provider": "custom",
  "custom": {
    "base_url": "http://your-server:8000",
    "api_key": "optional-key",
    "model": "Qwen/Qwen2.5-Coder-14B-Instruct",
    "api_format": "openai",
    "stream": true
  }
}
```

## 🔧 Requirements

- Sublime Text 4 (Build 4000+)
- Ollama server running locally
- Python 3.8+

## 📝 Examples

### **✨ NEW: Generate Multiple Files (Cursor-like)**
```
Command: "Laravel Workshop AI: Generate Files"
Input: "Create a complete CRUD for Products - model, migration, controller, routes"
Result: Creates app/Models/Product.php, database/migrations/xxx_create_products_table.php, 
        app/Http/Controllers/ProductController.php, updates routes/web.php
```

### **Inline Chat with File Creation**
```
Command: "Laravel Workshop AI: Inline Chat"
Input: "create: Build a User registration system with validation"
Result: AI analyzes your project structure and creates all necessary files
```

### **Inline Chat Example**
```
You: "How can I optimize this Laravel query?"
AI: "Here are 3 ways to optimize your query: 1) Add database indexes, 2) Use eager loading, 3) Implement query caching..."
```

### **Smart Completion Example**
```
You type: "public function getUser"
AI suggests: "public function getUser(int $id): ?User { return User::find($id); }"
```

### Generate a Controller
```
Prompt: "Create a Laravel controller for Product management with CRUD operations"
Result: Complete ProductController with all methods
```

### Explain Code
```
Select: Complex Laravel query
Result: Clear explanation of what the code does
```

### Refactor Code
```
Select: Long method
Result: Suggestions to break it into smaller, cleaner methods
```

## 🐛 Troubleshooting

### Sidebar Chat

- Use `Cmd+K` to open the sidebar chat (streaming, persistent per project).
- `Cmd+Shift+K` clears history.

### Model Autocomplete

- Laravel-aware autocompletions for `$model->...` using fillable, casts, accessors, relations, IDE helper.

### Show Model Info

- Command Palette → “Show Model Info” shows properties/relations/scopes in a popup.

## 🏗️ Project Structure Detection

Agents will analyze your project for DDD, Modular, Actions, DTOs, Repository, and Services patterns and generate code in the correct paths accordingly. You can force/disable detection via settings if needed.

## 🤖 AI Agents Guide

High-level workflow similar to Cursor/Windsurf, but local:

- **Architect** designs the solution.
- **Coder** implements code.
- **Reviewer** checks quality and suggests fixes.
- **Tester/Debugger/Refactorer** optional roles for deeper flows.

How to start:

1. Command Palette → "Laravel Workshop AI Agent: Generate Feature".
2. Describe the feature (e.g., "Create Laravel REST API for Products with validation and tests").
3. Agents iterate with tool-calling to read/write files and produce results.

Tips:

- Provide clear prompts (what to build, constraints, expected paths).
- Select relevant files open in the editor for better context.
- Use Refactor/Debug agents after generation to improve quality.

## 💬 Sidebar Chat

Persistent, streaming chat in a right-side tab with per-project history.

- Open: `Cmd+K` (inside PHP files).
- Clear history: `Cmd+Shift+K`.
- Commands: "Inline Chat", "Clear Chat History", "Close Chat".
- Context-aware: selection, current file, Laravel models.

History is stored per-project under your Sublime User data directory and resumes after restart.

## 🚀 Laravel Features

Smart Laravel developer experience:

- **Model Autocomplete**: `$model->` offers fillable, casts, relationships, accessors/mutators, scopes, and IDE Helper properties.
- **Show Model Info**: command shows table, properties with types, relationships, scopes, and accessors/mutators.
- **IDE Helper Integration**: generate annotations to enrich autocomplete and type hints.

Shortcuts/config:

- Keymaps include `Cmd+K` for chat; IDE Helper and model info available via Command Palette.
- Settings allow toggling Laravel-specific features and chat behavior.

## 🏗️ Project Structure Detection (Details)

Detectors recognize patterns and route generated code accordingly:

- **DDD**: `app/Domain/<Domain>/{Entities,Repositories,Services,ValueObjects}` and `app/Application/Controllers`.
- **Modular**: `Modules/<Module>/{Entities,Http/Controllers,Repositories,Services}`.
- **Actions**: `app/Actions/*Action.php` (single-action classes).
- **DTOs**: `app/DTO/*DTO.php`.
- **Repository**: `*Repository.php` (+ optional interfaces).
- **Service**: `*Service.php` under `app/Services`.

You can disable or force a structure via settings (e.g., `force_structure: "ddd"`).

## Background Workers

The plugin uses a shared priority WorkerManager to execute background tasks without blocking the UI.

- Coalescing per task type and project (prevents duplicate scans).
- Priorities: high (apply fixes), normal (scan), low (indexing).
- Centralized scheduling for chat-triggered scans and commands.

No configuration is required, but you can tune worker counts via settings:

```json
{
  "scanner_max_workers": 8,
  "scanner_excludes": ["vendor", "node_modules", ".git", "storage", "bootstrap", "build", "dist"]
}
```

## Scanners and Auto-Fixes

### N+1 Detector

- Detects common N+1 patterns in PHP and Blade files.
- Suggests safe eager loading by injecting `->with([...])` before `get()` and `paginate(...)`.
- Uses the project index (models/relations) to boost suggestions with known relations.
- Flow:
  - Chat: type "scan n+1" / "skeniraj n+1".
  - Review results in the chat tab.
  - Choose:
    - Apply safe fixes now (writes with `.bak` backups).
    - Show diffs preview.

### Controller Validation → FormRequest

- Scans controllers for inline validation calls (`$request->validate(...)`, `Validator::make(...)`).
- Extracts best-effort validation rules and generates `app/Http/Requests/*Request.php` classes with prefilled `rules()`.
- Offers optional auto-refactor of controllers:
  - Adds `use App\Http\Requests\...` imports.
  - Changes method signatures to type-hint the generated FormRequest.
  - Replaces `$request->validate(...)` with `$request->validated()`.
- Flow:
  - Chat: type "proveri kontroleri validacija" / "request klasi".
  - Review the report, then choose:
    - Preview refactor diffs (unified diff preview in a tab).
    - Generate FormRequest classes.
    - Refactor controllers to use FormRequest (writes with `.bak` backups).

## Plugin Cleanup

Keep your plugin folder tidy without deleting files permanently:

- Command: "Laravel Workshop AI: Cleanup Deprecated" – pick files to move to `_deprecated/`.
- Command: "Laravel Workshop AI: Auto Cleanup" – automatically moves known legacy files to `_deprecated/`.

Only the plugin folder is affected; your Laravel project files are not touched.

## 🚀 Tesla L4 Server Setup

Run an OpenAI-compatible server with vLLM on a Tesla L4 GPU for high performance:

1. Install NVIDIA drivers and CUDA, then create a Python venv.
2. Install vLLM: `pip install vllm`.
3. Start server:

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-Coder-14B-Instruct \
  --host 0.0.0.0 \
  --port 8000
```

4. Configure client:

```json
{
  "ai_provider": "custom",
  "custom": {
    "base_url": "http://your-server:8000",
    "model": "Qwen/Qwen2.5-Coder-14B-Instruct",
    "api_format": "openai"
  }
}
```

Optional: add auth via reverse proxy (e.g., Nginx) and pass `api_key` in settings.

**Connection Error?**
1. Make sure Ollama is running: `ollama serve`
2. Check if model is available: `ollama list`
3. Verify URL in settings (default: `http://localhost:11434`)

**Performance Issues?**
- Reduce `max_files_to_scan` in settings
- Increase `file_size_limit` if needed
- Use cache management commands

**Cursor-like features not working?**
- Check if `enable_inline_chat`, `enable_smart_completion` are enabled
- Restart Sublime Text after enabling new features
- Verify keyboard shortcuts are not conflicting

## 📚 Support

- **Issues**: [GitHub Issues](https://github.com/KalimeroMK/ollama-sublime/issues)
- **Documentation**: [GitHub Wiki](https://github.com/KalimeroMK/ollama-sublime/wiki)

## 🤝 Contributing

Contributions welcome! Please read our contributing guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Made with ❤️ for the Sublime Text community**

**Now with Cursor-like experience! 🎉**

