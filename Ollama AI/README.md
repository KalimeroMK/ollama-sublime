# Ollama AI Sublime Plugin

An intelligent AI-powered code assistance plugin for Sublime Text, designed specifically for PHP and Laravel development. Powered by local Ollama LLMs for privacy, performance, and offline capabilities.

## 🚀 Features

### Core AI Commands

#### 1. **Custom Prompt** (`Cmd+Ctrl+Enter`)
- Interactive AI chat for any coding question
- Context-aware responses based on your current file
- Supports follow-up questions and conversation flow

#### 2. **Explain Selection** 
- Get detailed explanations of selected code
- Understand complex logic and algorithms
- Learn from AI-generated code documentation

#### 3. **Optimize Selection**
- AI-powered code optimization suggestions
- Performance improvements and best practices
- Cleaner, more efficient code recommendations

#### 4. **Code Smell Detection**
- Identify potential issues in your code
- Security vulnerabilities detection
- Code quality improvements

#### 5. **Inline Refactoring** (`Cmd+Ctrl+Space`)
- Real-time code refactoring suggestions
- Preview changes before applying
- Approve or dismiss suggestions with visual indicators

### Advanced Features

#### 6. **Multi-File Feature Generation**
- Generate complete features across multiple files
- Automatic file creation and relationship management
- Laravel-specific patterns (Models, Controllers, Views, Routes)

#### 7. **File Creation from Description**
- Create new files from natural language descriptions
- Automatic boilerplate generation
- Laravel-specific file templates

#### 8. **Smart PHP/Laravel Completion** (`Cmd+Ctrl+Space`)
- AI-powered code completion for PHP and Laravel
- Context-aware suggestions based on project type
- Automatic detection of Laravel vs native PHP projects
- Intelligent fallback when LLM is unavailable

### Architecture Analysis

#### 9. **Project Architecture Analysis**
- Analyze your entire project structure
- Identify architectural patterns and dependencies
- Generate comprehensive project documentation

#### 10. **Related Files Discovery**
- Find files related to your current selection
- Understand code relationships and dependencies
- Navigate complex codebases efficiently

#### 11. **Change Impact Analysis**
- Analyze the impact of code changes
- Identify affected files and dependencies
- Prevent breaking changes

### Utility Features

#### 12. **Cache Management**
- Manage AI response caching
- Clear cache for fresh responses
- Performance optimization

#### 13. **Settings Management**
- Easy configuration of AI models
- Customize prompts and behavior
- Ollama server connection settings

## 🛠️ Installation

### Prerequisites

1. **Sublime Text 4** (recommended) or Sublime Text 3
2. **Ollama** installed and running locally
3. **PHP/Laravel model** (e.g., `qwen2.5-coder`, `llama2`, `codellama`)

### Setup Steps

1. **Install Ollama**:
   ```bash
   # macOS
   brew install ollama
   
   # Linux
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Windows
   # Download from https://ollama.ai/download
   ```

2. **Pull a coding model**:
   ```bash
   ollama pull qwen2.5-coder
   # or
   ollama pull codellama
   ```

3. **Start Ollama server**:
   ```bash
   ollama serve
   ```

4. **Install the plugin**:
   - Copy the `Ollama AI` folder to your Sublime Text Packages directory
   - Restart Sublime Text

## ⚙️ Configuration

### Settings

Access settings via: **Tools** → **Ollama AI** → **Edit Settings**

```json
{
    "model": "qwen2.5-coder",
    "base_url": "http://127.0.0.1:11434",
    "continue_chat": true,
    "max_tokens": 2000,
    "temperature": 0.3,
    "timeout": 30
}
```

### Keyboard Shortcuts

| Command | Shortcut | Description |
|---------|----------|-------------|
| Custom Prompt | `Cmd+Ctrl+Enter` | Open AI chat |
| PHP/Laravel Completion | `Cmd+Ctrl+Space` | Smart code completion |

## 🎯 Usage Examples

### PHP/Laravel Development

#### Laravel Controller Generation
1. Select a method name or description
2. Use **Generate Feature** command
3. AI will create:
   - Controller with CRUD methods
   - Model with relationships
   - Blade views
   - Route definitions
   - Migration files

#### Code Explanation
```php
// Select this code and use "Explain Selection"
public function calculateTotal($items) {
    return array_reduce($items, function($carry, $item) {
        return $carry + ($item['price'] * $item['quantity']);
    }, 0);
}
```

#### Smart Completion
```php
// Type this and use Cmd+Ctrl+Space
Route::get('/users', function() {
    return User::where('active', true)
    // AI will suggest: ->get(), ->paginate(), ->with('profile'), etc.
});
```

### Code Optimization

#### Before Optimization
```php
function getUserData($userId) {
    $user = DB::table('users')->where('id', $userId)->first();
    $profile = DB::table('profiles')->where('user_id', $userId)->first();
    $posts = DB::table('posts')->where('user_id', $userId)->get();
    
    return [
        'user' => $user,
        'profile' => $profile,
        'posts' => $posts
    ];
}
```

#### After AI Optimization
```php
function getUserData($userId) {
    return User::with(['profile', 'posts'])
               ->findOrFail($userId);
}
```

## 🔧 Advanced Features

### Multi-File Context Analysis

The plugin automatically analyzes your project structure to provide better suggestions:

- **File Relationships**: Understands imports, dependencies, and references
- **Architectural Patterns**: Recognizes MVC, Repository, Service patterns
- **Laravel Conventions**: Follows Laravel naming and structure conventions

### Intelligent Caching

- **Response Caching**: Similar requests are cached for faster responses
- **Context Caching**: Project analysis is cached to avoid repeated scanning
- **Smart Invalidation**: Cache is automatically updated when files change

### Error Handling

- **Graceful Degradation**: Falls back to static completions when AI is unavailable
- **Connection Recovery**: Automatically retries failed connections
- **User Feedback**: Clear error messages and suggestions

## 🧪 Testing

The plugin includes comprehensive test coverage:

```bash
# Run all tests
python3 run_all_tests.py

# Run specific test modules
python3 run_all_tests.py api          # API client tests
python3 run_all_tests.py completion   # PHP completion tests
python3 run_all_tests.py context      # Context analysis tests
```

### Test Coverage

- ✅ **API Client**: HTTP requests, streaming, error handling
- ✅ **Context Analyzer**: Symbol extraction, project scanning
- ✅ **UI Helpers**: Tab management, file operations
- ✅ **Response Processor**: Content cleaning, validation
- ✅ **PHP/Laravel Completion**: AI-powered code completion
- ✅ **Main Commands**: All 9 plugin commands
- ✅ **Ollama Server Connectivity**: Connection testing

## 🐛 Troubleshooting

### Common Issues

#### 1. **Ollama Connection Failed**
```
Error: Connection to Ollama server failed
```
**Solution**: 
- Ensure Ollama is running: `ollama serve`
- Check the base URL in settings
- Verify firewall settings

#### 2. **Model Not Found**
```
Error: Model 'qwen2.5-coder' not found
```
**Solution**:
```bash
ollama pull qwen2.5-coder
```

#### 3. **Slow Responses**
**Solutions**:
- Use a smaller model for faster responses
- Enable response caching
- Reduce max_tokens in settings

#### 4. **Completion Not Working**
**Solutions**:
- Check if you're in a PHP file
- Ensure the project is properly detected
- Try the fallback completions

### Debug Mode

Enable debug mode in settings:
```json
{
    "debug": true,
    "log_level": "debug"
}
```

## 🤝 Contributing

### Development Setup

1. Clone the repository
2. Install dependencies
3. Run tests: `python3 run_all_tests.py`
4. Make changes and test thoroughly

### Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add comprehensive tests for new features
- Update documentation for new commands

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Ollama** for providing the local LLM infrastructure
- **Sublime Text** for the excellent editor platform
- **Laravel** community for inspiration and best practices
- **Open source contributors** who made this possible

## 📞 Support

- **Issues**: Report bugs and feature requests on GitHub
- **Documentation**: Check the wiki for detailed guides
- **Community**: Join our Discord server for discussions

---

**Made with ❤️ for the PHP/Laravel community**

*Version 1.0.0 - Powered by Ollama AI*
