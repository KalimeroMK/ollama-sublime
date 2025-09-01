# Ollama AI Sublime

AI-powered code assistance for Sublime Text 4, powered by local Ollama LLMs. **Now with Cursor-like features!** 🚀

## 🚀 Features

- **Code Generation** - Generate code from natural language prompts
- **Code Explanation** - Understand existing code with AI analysis
- **Refactoring Suggestions** - Get AI-powered code improvements
- **Multi-File Context** - AI understands your entire project structure
- **Feature Generation** - Create complete features from descriptions
- **Performance Optimization** - Get suggestions for better code performance
- **🎯 Inline AI Chat** - Cursor-like chat interface directly in your editor
- **⚡ Smart Completion** - AI-powered code completion and suggestions
- **🔍 Real-time Suggestions** - Get AI insights as you code

## 🆕 **New Cursor-like Features**

### **Inline AI Chat** (`Cmd+Shift+I`)
- Chat with AI directly in your editor
- Beautiful dark theme interface
- Real-time responses with typing indicators
- Chat history and context awareness

### **Smart Completion** (`Cmd+Shift+Space`)
- AI-powered code completion
- Context-aware suggestions
- Auto-documentation generation
- Test case generation
- Code improvement suggestions

### **Real-time AI Insights**
- Get suggestions as you type
- Performance optimization tips
- Design pattern recommendations
- Error handling suggestions

## 📦 Installation

1. **Install Ollama** and pull a model:
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ollama pull qwen2.5-coder
   ```

2. **Install the plugin**:
   - Copy `Ollama AI` folder to your Sublime Text Packages directory
   - Restart Sublime Text

3. **Configure** (optional):
   - Open `Preferences > Package Settings > Ollama AI > Settings`
   - Adjust model, URL, and other settings

## 🎯 Usage

### Quick Start
1. Open Command Palette (`Cmd+Shift+P`)
2. Type `Ollama AI: Prompt`
3. Ask for what you need: *"Create a Laravel controller for User management"*

### **New Cursor-like Commands**
- **`Cmd+Shift+I`** - Inline AI Chat (Cursor-like interface)
- **`Cmd+Shift+Space`** - Smart Completion
- **`Cmd+Shift+C`** - Cache Manager

### All Commands
- **`Ollama AI: Prompt`** - General AI assistance
- **`Ollama AI: Generate Feature...`** - Create complete functionality
- **`Ollama AI: Create File From Prompt...`** - Generate single file
- **`Ollama AI: Explain Selection`** - Explain selected code
- **`Ollama AI: Optimize Selection`** - Optimize selected code
- **`Ollama AI: Suggest Refactoring...`** - Get refactoring suggestions

### Right-Click Menu
- **Explain Selection** - Understand code
- **Optimize Selection** - Improve performance
- **Suggest Refactoring...** - Get AI suggestions
- **Inline Chat** - Quick AI conversation
- **Smart Completion** - AI-powered suggestions

## ⚙️ Configuration

Key settings in `Ollama.sublime-settings`:
```json
{
    "model": "qwen2.5-coder",
    "base_url": "http://localhost:11434",
    "enable_inline_chat": true,
    "enable_smart_completion": true,
    "enable_real_time_suggestions": true,
    "cursor_like_theme": true
}
```

## 🔧 Requirements

- Sublime Text 4 (Build 4000+)
- Ollama server running locally
- Python 3.8+

## 📝 Examples

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

