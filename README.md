# Ollama Sublime AI Assistant

Your personal AI pair programmer for Sublime Text, powered by Ollama and your local LLMs. This plugin brings the power of generative AI to your code editor, with a strong focus on providing intelligent, context-aware assistance for Laravel PHP development.

## ✨ Features

This plugin is more than just a simple prompt-to-AI interface. It's a suite of tools designed to deeply integrate with your workflow and understand your codebase.

- **🚀 Multi-file Feature Generation**: Describe a full feature (e.g., "a product management module"), and the AI will act as an architect to plan all the necessary files (controllers, models, DTOs, tests, etc.). After you approve the plan, it generates all the files for you.
- **🧠 Context-Aware AI Engine**: The plugin automatically scans your project to find where code is used, providing the AI with crucial context. This results in smarter, more accurate suggestions that respect your project's architecture.
- **🤖 Inline AI Refactoring**: Select any code block and get an instant, inline refactoring suggestion. Approve it with a single click to apply the changes, or dismiss it to keep your original code.
- **✔️ Code Smell Finder**: Analyze your code for potential issues, get optimization suggestions, and even find out if a method is unused and can be safely deleted. The AI uses project-wide context to make its recommendations.
- **📄 AI-Powered Single File Creation**: Generate individual files (like controllers, models, or services) from a simple prompt.
- **✍️ Explain & Optimize Code**: Right-click any selection to get a clear explanation of what it does or a suggestion for how to optimize it.
- **⚙️ Highly Configurable**: Easily edit settings, models, and system prompts to tailor the AI's behavior to your needs.
- **🔒 Fully Local & Private**: All processing is done on your local machine via your Ollama instance. Your code never leaves your computer.

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

You can customize the plugin's behavior by editing the settings file at `Preferences > Package Settings > Ollama AI > Settings`.

Key settings:

-   `model`: The Ollama model to use for generating responses (e.g., `"qwen2.5-coder"`).
-   `url`: The URL of your local Ollama API endpoint.
-   `feature_architect_prompt` and `feature_coder_prompt`: Customize the two-step prompts for feature generation.
-   `explain_prompt`, `optimize_prompt`, `code_smell_prompt`: Customize the prompts used for specific commands.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Please feel free to open an issue or submit a pull request.

---

*This plugin is inspired by the powerful, context-aware capabilities of assistants like Cascade.*
