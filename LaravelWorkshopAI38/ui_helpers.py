import sublime
import os


class RefactoringOverlay:
    """Enhanced overlay for refactoring suggestions with better UX."""
    
    def __init__(self, view, original_text, suggested_text):
        self.view = view
        self.original_text = original_text
        self.suggested_text = suggested_text
        self.overlay_key = "laravel_workshop_refactor_{0}".format(id(self))
        self.is_active = False
        
    def show(self):
        """Show the refactoring overlay with enhanced UI."""
        if self.is_active:
            return
            
        # Create a phantom overlay with better styling
        phantom_set = sublime.PhantomSet(self.view, self.overlay_key)
        
        # Get the selection region
        selection = self.view.sel()[0] if self.view.sel() else None
        if not selection or selection.empty():
            return
            
        # Create enhanced HTML content
        html_content = self._create_overlay_html()
        
        # Create phantom
        phantom = sublime.Phantom(
            selection,
            html_content,
            sublime.LAYOUT_BLOCK,
            self._on_phantom_click
        )
        
        phantom_set.update([phantom])
        self.is_active = True
        
        # Store reference for cleanup
        self.phantom_set = phantom_set
        
    def _create_overlay_html(self):
        """Create enhanced HTML for the refactoring overlay."""
        return """
        <div style="background: #2d3748; border: 2px solid #4299e1; border-radius: 8px; padding: 16px; margin: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
            <div style="color: #e2e8f0; font-size: 14px; margin-bottom: 12px;">
                <strong>🤖 AI Refactoring Suggestion</strong>
            </div>
            
            <div style="background: #1a202c; border-radius: 4px; padding: 12px; margin-bottom: 12px; border-left: 4px solid #4299e1;">
                <div style="color: #a0aec0; font-size: 12px; margin-bottom: 8px;">SUGGESTED CODE:</div>
                <div style="color: #e2e8f0; font-family: 'Monaco', 'Menlo', monospace; font-size: 13px; line-height: 1.4; white-space: pre-wrap;">{self._escape_html(self.suggested_text)}</div>
            </div>
            
            <div style="display: flex; gap: 8px; justify-content: flex-end;">
                <a href="approve" style="background: #48bb78; color: white; padding: 8px 16px; border-radius: 4px; text-decoration: none; font-weight: bold; font-size: 13px;">✅ Approve</a>
                <a href="dismiss" style="background: #e53e3e; color: white; padding: 8px 16px; border-radius: 4px; text-decoration: none; font-weight: bold; font-size: 13px;">❌ Dismiss</a>
                <a href="edit" style="background: #ed8936; color: white; padding: 8px 16px; border-radius: 4px; text-decoration: none; font-weight: bold; font-size: 13px;">✏️ Edit</a>
            </div>
            
            <div style="color: #a0aec0; font-size: 11px; margin-top: 8px; text-align: center;">
                Click buttons above to apply, dismiss, or edit the suggestion
            </div>
        </div>
        """
    
    def _escape_html(self, text):
        """Escape HTML special characters."""
        return (text.replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;")
                   .replace('"', "&quot;")
                   .replace("'", "&#39;"))
    
    def _on_phantom_click(self, href):
        """Handle phantom click events."""
        if href == "approve":
            self._apply_refactoring()
        elif href == "dismiss":
            self._dismiss()
        elif href == "edit":
            self._edit_suggestion()
    
    def _apply_refactoring(self):
        """Apply the refactoring suggestion."""
        try:
            # Replace the selected text with the suggestion
            selection = self.view.sel()[0]
            self.view.run_command("replace", {
                "region": selection,
                "text": self.suggested_text
            })
            
            # Show success message
            UIHelpers.show_status_message("✅ Refactoring applied successfully!", 3000)
            
            # Clean up
            self._dismiss()
            
        except Exception as e:
            UIHelpers.show_error_message("Failed to apply refactoring: {0}".format(str(e)))
    
    def _edit_suggestion(self):
        """Open suggestion in a new tab for editing."""
        try:
            # Create a new tab with the suggestion
            window = self.view.window()
            tab = UIHelpers.create_output_tab(
                window,
                "Edit Refactoring Suggestion",
                self.suggested_text
            )
            
            # Set syntax to match current file
            current_syntax = self.view.settings().get("syntax")
            if current_syntax:
                tab.set_syntax_file(current_syntax)
            
            # Show instructions
            tab.run_command("append", {
                "characters": "\n\n--- EDIT ABOVE, THEN COPY BACK TO ORIGINAL FILE ---\n"
            })
            
            # Focus the new tab
            window.focus_view(tab)
            
            UIHelpers.show_status_message("✏️ Suggestion opened for editing", 3000)
            
        except Exception as e:
            UIHelpers.show_error_message("Failed to open suggestion for editing: {0}".format(str(e)))
    
    def _dismiss(self):
        """Dismiss the refactoring overlay."""
        if hasattr(self, 'phantom_set'):
            self.phantom_set.update([])
        self.is_active = False
    
    def cleanup(self):
        """Clean up resources."""
        self._dismiss()


class UIHelpers:
    """
    Utility functions for handling Sublime Text UI operations.
    Centralizes common UI patterns used across multiple commands.
    """
    
    @staticmethod
    def create_output_tab(window, title, initial_content=""):
        """Create a new output tab with the specified title and content."""
        tab = window.new_file()
        tab.set_name(title)
        tab.set_scratch(True)
        
        if initial_content:
            tab.run_command("append", {"characters": initial_content})
        
        return tab
    
    @staticmethod
    def create_progress_tab(window, title, description=""):
        """Create a progress tracking tab for long-running operations."""
        tab = UIHelpers.create_output_tab(window, title)
        
        if description:
            tab.run_command("append", {"characters": description + "\n"})
        
        return tab
    
    @staticmethod
    def append_to_tab(tab, content):
        """Safely append content to a tab."""
        if tab and tab.is_valid():
            tab.run_command("append", {"characters": content})
    
    @staticmethod
    def get_selected_text(view):
        """Get all selected text from a view, concatenated."""
        selected_text = ""
        for region in view.sel():
            if not region.empty():
                selected_text += view.substr(region)
        return selected_text
    
    @staticmethod
    def has_selection(view):
        """Check if the view has any non-empty selections."""
        for region in view.sel():
            if not region.empty():
                return True
        return False
    
    @staticmethod
    def show_status_message(message, timeout=5000):
        """Show a status message with optional timeout."""
        sublime.status_message(message)
        if timeout > 0:
            sublime.set_timeout(lambda: sublime.status_message(""), timeout)
    
    @staticmethod
    def show_error_message(message):
        """Show an error message dialog."""
        sublime.error_message(message)
    
    @staticmethod
    def show_info_message(message):
        """Show an info message dialog."""
        sublime.message_dialog(message)
    
    @staticmethod
    def show_refactoring_overlay(view, original_text, suggested_text):
        """Show an enhanced refactoring overlay."""
        overlay = RefactoringOverlay(view, original_text, suggested_text)
        overlay.show()
        return overlay
    
    @staticmethod
    def show_enhanced_input_panel(window, caption, initial_text, on_done, on_change=None, on_cancel=None):
        """Show an enhanced input panel with better styling."""
        # Create a custom input panel with enhanced UI
        panel = window.show_input_panel(
            caption,
            initial_text,
            on_done,
            on_change,
            on_cancel
        )
        
        # Focus the panel
        if panel:
            panel.focus()
        
        return panel
    
    @staticmethod
    def show_quick_panel_with_preview(window, items, on_done, flags=0, selected_index=-1, on_highlighted=None):
        """Show a quick panel with preview capabilities."""
        return window.show_quick_panel(
            items,
            on_done,
            flags,
            selected_index,
            on_highlighted
        )
    
    @staticmethod
    def format_tab_title(template, selection="", max_length=50):
        """Format a tab title with selection preview, respecting max length."""
        # First format the template to see the full result
        formatted = template.format(selection=selection)
        
        # If it's too long, truncate the selection part
        if len(formatted) > max_length:
            # Calculate how much selection text we can keep
            template_base = template.format(selection="")
            available_for_selection = max_length - len(template_base) - 3  # Reserve 3 for "..."
            
            if available_for_selection > 0:
                truncated_selection = selection[:available_for_selection] + "..."
                return template.format(selection=truncated_selection)
            else:
                # If template itself is too long, just truncate the whole thing
                return formatted[:max_length-3] + "..."
        
        return formatted
    
    @staticmethod
    def ensure_project_folder(window):
        """Ensure a project folder is open, return the first folder or None."""
        folders = window.folders()
        if not folders:
            UIHelpers.show_error_message("No project folders open. Please open a project first.")
            return None
        return folders[0]
    
    @staticmethod
    def create_file_safely(file_path, content):
        """Create a file with proper error handling and directory creation."""
        try:
            # Make sure the directory exists
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # Write the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
            
        except Exception as e:
            UIHelpers.show_error_message("Error creating file: {}".format(e))
            return False
    
    @staticmethod
    def open_file_in_window(window, file_path, delay=0):
        """Open a file in the specified window with optional delay."""
        if delay > 0:
            sublime.set_timeout(lambda: window.open_file(file_path), delay)
        else:
            window.open_file(file_path)
    
    @staticmethod
    def close_tab_delayed(tab, delay=500):
        """Close a tab after a specified delay."""
        if tab and tab.is_valid():
            sublime.set_timeout(lambda: tab.close() if tab.is_valid() else None, delay)
    
    @staticmethod
    def show_input_panel(window, caption, initial_text, on_done, on_change=None, on_cancel=None):
        """Show an input panel with proper defaults."""
        return window.show_input_panel(
            caption,
            initial_text,
            on_done,
            on_change,
            on_cancel
        )
    
    @staticmethod
    def get_project_relative_path(file_path, project_root):
        """Get the relative path of a file within the project."""
        try:
            rel_path = os.path.relpath(file_path, project_root)
            # If the relative path goes up directories (starts with ..), 
            # the file is outside the project root
            if rel_path.startswith('..'):
                return file_path
            return rel_path
        except ValueError:
            # File is not within project root
            return file_path


class TabManager:
    """
    Manages output tabs and their lifecycle.
    Provides a higher-level interface for tab operations.
    """
    
    def __init__(self, window):
        self.window = window
        self.tabs = {}
    
    def create_output_tab(self, key, title, prompt="", model=""):
        """Create and register an output tab."""
        tab = UIHelpers.create_output_tab(self.window, title)
        
        if prompt or model:
            header_content = ""
            if prompt:
                header_content += "Prompt: {}\n".format(prompt)
            if model:
                header_content += "Model: {}\n".format(model)
            if header_content:
                header_content += "\n---\n\n"
                UIHelpers.append_to_tab(tab, header_content)
        
        self.tabs[key] = tab
        return tab
    
    def get_tab(self, key):
        """Get a registered tab by key."""
        return self.tabs.get(key)
    
    def append_to_tab(self, key, content):
        """Append content to a registered tab."""
        tab = self.get_tab(key)
        if tab:
            UIHelpers.append_to_tab(tab, content)
    
    def close_tab(self, key, delay=0):
        """Close and unregister a tab."""
        tab = self.tabs.pop(key, None)
        if tab:
            if delay > 0:
                UIHelpers.close_tab_delayed(tab, delay)
            elif tab.is_valid():
                tab.close()
    
    def cleanup(self):
        """Clean up all registered tabs."""
        for key in list(self.tabs.keys()):
            self.close_tab(key)