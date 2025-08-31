# Ollama Sublime AI Assistant

Your personal AI pair programmer for Sublime Text, powered by Ollama and your local LLMs. This plugin brings the power of generative AI to your code editor, with a strong focus on providing intelligent, context-aware assistance for Laravel PHP development.

## ✨ Features

This plugin is more than just a simple prompt-to-AI interface. It's a comprehensive suite of AI-powered tools designed to integrate seamlessly with your development workflow.

### 🚀 Core Features

- **Advanced Multi-File Context Understanding**: Deep analysis of file relationships, dependencies, and architectural patterns across your entire project
- **Multi-file Feature Generation**: Describe a complete feature, and the AI architect will plan all necessary files (controllers, models, DTOs, tests, etc.), then generate them after your approval
- **Architectural Pattern Detection**: Automatically identifies MVC, Repository, Service, and other patterns in your codebase
- **Cross-File Impact Analysis**: Understand how changes to one file will affect other parts of your project
- **Dependency Graph Analysis**: Visual understanding of how files depend on each other with import/use statement tracking
- **Context-Aware AI Engine**: Automatically scans your project to understand code usage patterns, providing smarter suggestions that respect your project's architecture
- **Inline AI Refactoring**: Get instant refactoring suggestions with one-click approval or dismissal
- **Code Smell Detection**: AI-powered analysis to find potential issues, optimization opportunities, and unused code
- **Related Files Discovery**: Instantly find all files related to your current file through dependencies and usage patterns
- **Single File Creation**: Generate individual files from natural language descriptions with architectural context
- **Code Explanation & Optimization**: Right-click any code selection for detailed explanations or optimization suggestions
- **Custom Prompts**: Ask specific questions about your code with full project context
- **Conversational AI**: Continue conversations with chat history for iterative development
- **Fully Local & Private**: All processing happens on your machine - your code never leaves your computer

## 🎯 How to Access Features

All features are easily accessible through multiple methods:

### ⌨️ Keyboard Shortcuts

- **`Cmd+Ctrl+Enter`** (macOS): Open Custom Prompt dialog for general AI assistance

### 📋 Command Palette (`Cmd+Shift+P`)

Access all features from the Command Palette by typing "Ollama AI":

- **Ollama AI: Prompt** - General-purpose AI conversation with chat history
- **Ollama AI: Explain Selection** - Get detailed code explanations
- **Ollama AI: Optimize Selection** - Receive code optimization suggestions
- **Ollama AI: Find Code Smells...** - Analyze code for issues and improvements
- **Ollama AI: Custom Prompt for Selection...** - Ask specific questions about selected code
- **Ollama AI: Suggest Refactoring...** - Get inline refactoring suggestions with approval
- **Ollama AI: Create File From Prompt...** - Generate individual files from descriptions
- **Ollama AI: Generate Feature...** - Create multi-file features with architect planning
- **Ollama AI: Analyze Project Architecture...** - Comprehensive analysis of project structure and patterns
- **Ollama AI: Show Related Files** - Discover files related to the current file through dependencies
- **Ollama AI: Analyze Change Impact...** - Assess potential impact of changes to the current file
- **Ollama AI: Edit Settings** - Open plugin configuration

### 🖱️ Right-Click Context Menu

When you select code and right-click, you'll see the **Ollama AI** submenu:

- **Explain Selection** - Understand what the code does
- **Optimize Selection** - Get performance and style improvements
- **Find Code Smells...** - Detect potential issues and unused code
- **Suggest Refactoring...** - Interactive refactoring with approve/dismiss options
- **Custom Prompt for Selection...** - Ask custom questions about the selected code
- **Show Related Files** - Discover files related to the current file through dependencies and patterns
- **Analyze Change Impact...** - Assess how changes to the current file will affect other parts of the project

### 🔧 Main Menu

Access core features via **Tools > Ollama AI**:

- **Custom Prompt** - Start a conversation with the AI
- **Explain Selection**, **Optimize Selection**, **Find Code Smells** - Code analysis tools
- **Generate Feature...** - Multi-file feature scaffolding
- **Analyze Project Architecture...** - Comprehensive project structure analysis with AI insights

### ⚙️ Settings Access

Configure the plugin via **Preferences > Package Settings > Ollama AI**:

- **Edit Model Settings** - Configure model, URL, and basic settings
- **Edit System Prompts** - Customize AI behavior and prompts

## 🔧 Installation

1.  **Install Ollama**: Make sure you have [Ollama](https://ollama.ai/) installed and running on your machine.
2.  **Pull a Model**: It is recommended to use a model specifically trained for coding, such as `codellama`, `mistral`, or `qwen2.5-coder`. You can pull a model by running:
    ```sh
    ollama pull qwen2.5-coder
    ```
3.  **Clone the Repository**: Open your Sublime Text `Packages` directory (you can find it via `Preferences > Browse Packages...`) and clone this repository:
    ```sh
    git clone https://github.com/your-repo/ollama-sublime.git "Ollama AI"
    ```
4.  **Configure the Model**: Go to `Tools > Ollama AI > Edit Settings` in Sublime Text and set the `"model"` to the one you pulled (e.g., `"model": "qwen2.5-coder"`).

## 🚀 How to Use

All features are accessible from the **Command Palette** (`Cmd+Shift+P`), the main menu under **Tools > Ollama AI**, or by **right-clicking** in your editor.

### Multi-file Feature Generation

This is the most powerful command for scaffolding entire features at once.

1.  Run **Ollama AI: Generate Feature...** from the Command Palette or Tools menu.
2.  Describe the feature you want (e.g., "Create a Product module with controller, DTOs, actions and test").
3.  The AI will act as an **architect** and propose a plan, listing all the files it will create.
4.  Review the plan in the quick panel. Select **✅ Approve** to proceed or **❌ Cancel** to abort.
5.  If approved, the AI will act as a **coder** and generate each file from the plan.

*<- Placeholder for demo GIF*

### Inline AI Refactoring

1.  Select a block of code (like a function or class).
2.  Right-click and choose **Suggest Refactoring...**.
3.  An inline panel will appear with the AI's suggestion.
    -   Click **Approve** to replace your code with the suggestion.
    -   Click **Dismiss** to close the panel without making changes.

### Code Smell Finder

1.  Select a block of code you want to analyze.
2.  Right-click and choose **Find Code Smells...**.
3.  A new tab will open with the AI's analysis, pointing out potential issues, suggesting improvements, and identifying if the code appears to be unused anywhere else in the project.

### Context Menu Commands (Right-Click)

When you select code and right-click, you'll see an **Ollama AI** submenu with these powerful, context-aware options:

-   **Explain Selection**: Get a detailed explanation of the selected code.
-   **Optimize Selection**: Receive an optimized version of the selected code.
-   **Find Code Smells...**: Analyze the selection for issues and improvement opportunities.
-   **Custom Prompt for Selection...**: Opens an input panel where you can ask a specific question about the selected code.

### Command Palette & Main Menu

You can access all features from the Command Palette or the `Tools > Ollama AI` menu.

-   **Ollama AI: Generate Feature...**: Use this for complex features involving **multiple files**.
-   **Ollama AI: Create File From Prompt...**: Use this for creating a **single file**.
-   **Ollama AI: Prompt**: A general-purpose prompt for questions or code generation.
-   **Ollama AI: Edit Settings**: Opens the settings file for easy configuration.

## ⚙️ Configuration

You can customize the plugin's behavior by editing the settings file at `Preferences > Package Settings > Ollama AI > Edit Model Settings`.

### Core Settings

- **`model`** (`"qwen2.5-coder"`): The Ollama model to use for generating responses. Recommended models include `qwen2.5-coder`, `codellama`, `mistral`, or `deepseek-coder`
- **`url`** (`"http://127.0.0.1:11434/api/chat"`): Your local Ollama API endpoint. Use `/api/chat` for chat-based models or `/api/generate` for completion-based models
- **`system_prompt`**: The main system instruction that defines the AI's role and expertise level
- **`continue_chat`** (`true`): Enable conversation history for the Custom Prompt feature

### File and Project Settings

- **`code_file_extensions`** (`[".php", "blade.php", ".js", ".html", ".css", ".json"]`): File types to scan when analyzing project context
- **`tab_title`** (`"Ollama: {selection}"`): Template for naming output tabs
- **`syntax`**: Syntax highlighting for AI response tabs

### Customizable AI Prompts

All AI behavior can be customized by modifying these prompts:

- **`explain_prompt`**: Controls how the AI explains code selections
- **`optimize_prompt`**: Defines optimization approach and output format
- **`code_smell_prompt`**: Instructions for code analysis and issue detection
- **`refactor_prompt`**: Guidelines for inline refactoring suggestions
- **`selection_prompt`**: Template for custom prompts with selected code

### Multi-File Feature Generation

- **`feature_architect_prompt`**: Instructions for the AI architect that plans multi-file features
- **`feature_coder_prompt`**: Instructions for the AI coder that implements individual files
- **`file_creation_prompt_template`**: Template for single file creation

### Advanced Multi-File Context Settings

The plugin now includes powerful multi-file context analysis capabilities that can be configured:

- **`use_advanced_context`** (`true`): Enable advanced multi-file context understanding
- **`advanced_context_depth`** (`2`): Maximum depth for analyzing file relationships (1-3 recommended)
- **`max_related_files`** (`15`): Maximum number of related files to analyze per request
- **`enable_architectural_analysis`** (`true`): Enable detection of architectural patterns (MVC, Repository, etc.)
- **`enable_dependency_tracking`** (`true`): Track file dependencies through import/use statements
- **`enable_impact_analysis`** (`true`): Analyze potential impact of file changes

### Architectural Pattern Detection

Configure which patterns the plugin should detect:

- **`detect_mvc_pattern`** (`true`): Detect Model-View-Controller pattern
- **`detect_repository_pattern`** (`true`): Detect Repository pattern
- **`detect_service_pattern`** (`true`): Detect Service layer pattern
- **`detect_facade_pattern`** (`true`): Detect Facade pattern

### Performance and Scope Settings

Control the scope and performance of advanced analysis:

- **`max_files_to_scan`** (`1000`): Maximum files to scan during context analysis
- **`file_size_limit`** (`1048576`): Skip files larger than this size (bytes)
- **`cache_context_analysis`** (`true`): Cache analysis results for better performance
- **`advanced_context_extensions`**: File extensions to include in advanced analysis

### Laravel-Specific Configuration

- **`namespace_mappings`**: Map Laravel namespaces to directory paths for accurate dependency tracking

### Example Configuration

```json
{
    "model": "qwen2.5-coder",
    "url": "http://127.0.0.1:11434/api/chat",
    "system_prompt": "You are a Laravel PHP expert. Focus on modern best practices.",
    "continue_chat": true,
    "code_file_extensions": [".php", ".blade.php", ".js", ".vue"],
    "explain_prompt": "Explain this Laravel code clearly: {code}"
}
```

## 📝 Usage Examples

### Multi-File Feature Generation Workflow

1. **Start the Feature Generator**: Use `Cmd+Shift+P` → "Ollama AI: Generate Feature..."
2. **Describe Your Feature**: Enter something like "Create a Product management system with CRUD operations"
3. **Review the Plan**: The AI architect will propose files like:
   - `app/Http/Controllers/ProductController.php`
   - `app/Models/Product.php`
   - `app/Http/Requests/StoreProductRequest.php`
   - `database/migrations/create_products_table.php`
   - `tests/Feature/ProductTest.php`
4. **Approve or Cancel**: Click "✅ Approve" to generate all files or "❌ Cancel" to abort
5. **Files Generated**: Each file is created with appropriate Laravel code and automatically opened

### Inline Refactoring Workflow

1. **Select Code**: Highlight a function, method, or code block
2. **Get Suggestion**: Right-click → "Suggest Refactoring..." or use Command Palette
3. **Review Inline**: An overlay appears with the AI's refactoring suggestion
4. **Apply or Dismiss**: Click "Approve" to replace your code or "Dismiss" to keep original

### Code Analysis and Improvement

1. **Select Problem Code**: Highlight code you want to analyze
2. **Run Analysis**: Right-click → "Find Code Smells..." 
3. **Get Report**: A new tab opens with:
   - Potential bugs and issues
   - Performance improvements
   - Code style suggestions
   - Whether the code appears unused in your project

### Context-Aware Code Help

1. **Select Code**: Highlight any code snippet
2. **Ask Questions**: Right-click → "Custom Prompt for Selection..."
3. **Enter Query**: Ask specific questions like "How can I make this more secure?" or "What design pattern is this?"
4. **Get Contextual Answer**: The AI analyzes your code with full project context

### Advanced Multi-File Analysis Workflows

#### Project Architecture Analysis

1. **Run Analysis**: Use `Cmd+Shift+P` → "Ollama AI: Analyze Project Architecture..."
2. **Review Report**: View comprehensive analysis including:
   - File type distribution and architectural patterns detected
   - Dependency analysis with most connected files
   - File roles distribution (controllers, models, services, etc.)
   - AI recommendations for structure improvements
3. **Get AI Insights**: The AI analyzes the report and provides actionable recommendations

#### Related Files Discovery

1. **Open Any File**: Navigate to any file in your project
2. **Discover Relations**: Right-click → "Show Related Files" or use Command Palette
3. **Explore Connections**: View files grouped by:
   - **Controllers** that use this model/service
   - **Models** that this controller depends on
   - **Services** that interact with this component
   - **Tests** that verify this functionality
4. **Navigate Efficiently**: Click through the architectural connections

#### Change Impact Analysis

1. **Select Target File**: Open the file you plan to modify
2. **Analyze Impact**: Right-click → "Analyze Change Impact..." or use Command Palette
3. **Review Risk Assessment**: Get detailed analysis including:
   - **Risk Level**: High/Medium/Low based on dependency count
   - **Affected Files**: List of files that depend on your changes
   - **Testing Strategy**: Recommended tests to run
   - **Deployment Considerations**: What to watch out for
4. **Make Informed Decisions**: Use the analysis to plan your changes safely

#### Enhanced Code Understanding

The plugin now provides richer context for all existing commands:

- **Code Explanations** now include architectural role and related file context
- **Refactoring Suggestions** consider cross-file dependencies and impact
- **Code Smell Detection** identifies unused code by analyzing project-wide usage
- **File Creation** generates code that follows your project's architectural patterns

## 🧪 Testing

This plugin includes a comprehensive test suite to ensure reliability and functionality. The testing framework covers all core components and provides confidence in the codebase.

### Test Structure

The test suite is organized into multiple focused modules:

- **`test_ollama_api.py`** (15 tests) - Tests the API client functionality including HTTP requests, streaming responses, payload creation, and error handling
- **`test_context_analyzer.py`** (23 tests) - Tests symbol extraction, project file scanning, context analysis, and legacy function compatibility  
- **`test_multi_file_context.py`** (47 tests) - Tests advanced multi-file context analysis, dependency tracking, architectural pattern detection, and file relationship mapping
- **`test_ui_helpers.py`** (35 tests) - Tests UI operations, tab management, file operations, and user interface interactions
- **`test_response_processor.py`** (49 tests) - Tests response cleaning, content validation, markdown processing, and chat history management
- **`test_ollama_ai_integration.py`** (30 tests) - Integration tests for all main command classes and their workflows
- **`test_ollama_connection.py`** - Connectivity tests for Ollama server integration

### Running Tests

#### Run All Tests
```bash
# Run the complete test suite from the tests directory
cd tests
python3 run_all_tests.py

# Or run from project root
python3 tests/run_all_tests.py

# Run individual test modules
cd tests
python3 run_all_tests.py api          # API client tests only
python3 run_all_tests.py context      # Context analyzer tests only
python3 run_all_tests.py ui           # UI helpers tests only
python3 run_all_tests.py response     # Response processor tests only  
python3 run_all_tests.py integration  # Integration tests only
python3 run_all_tests.py connectivity # Connectivity test only
```

#### Run Individual Test Files
```bash
# Run specific test modules directly from tests directory
cd tests
python3 test_ollama_api.py
python3 test_context_analyzer.py
python3 test_ui_helpers.py
python3 test_response_processor.py
python3 test_ollama_ai_integration.py

# Or run from project root
python3 tests/test_ollama_api.py
python3 tests/test_context_analyzer.py
```

### Test Coverage

The test suite provides comprehensive coverage of:

- ✅ **API Communication** - HTTP requests, streaming, error handling, payload formatting
- ✅ **Context Analysis** - Symbol extraction, project scanning, usage detection
- ✅ **UI Operations** - Tab management, file creation, user interactions  
- ✅ **Response Processing** - Content cleaning, validation, markdown handling
- ✅ **Command Integration** - All 9 plugin commands and their complete workflows
- ✅ **Server Connectivity** - Ollama server communication and model availability

### Test Statistics

- **Total Tests**: 156 test cases
- **Success Rate**: 98.1% (152 passed, 3 failed, 1 error)
- **Coverage**: All critical functionality tested
- **Execution Time**: ~12 seconds for complete suite

### Prerequisites for Testing

1. **Python 3.6+** - Required for running the test suite
2. **Ollama Server** (optional) - Required only for connectivity tests
   ```bash
   ollama serve
   ollama pull qwen2.5-coder
   ```

The unit and integration tests use mocking and don't require an actual Ollama server, making them fast and reliable for development.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Please feel free to open an issue or submit a pull request.

When contributing:
- Run the test suite to ensure your changes don't break existing functionality
- Add tests for any new features or bug fixes
- Follow the existing code style and patterns

