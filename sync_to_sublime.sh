#!/bin/bash

# Sync script for Laravel Workshop AI plugin
# Copies files from local project to Sublime Text Packages directory

SOURCE_DIR="/Users/zoran/PhpstormProjects/ollama-sublime/LaravelWorkshopAI38"
TARGET_DIR="/Users/zoran/Library/Application Support/Sublime Text/Packages/LaravelWorkshopAI38"

echo "🔄 Syncing Laravel Workshop AI to Sublime Text..."
echo "Source: $SOURCE_DIR"
echo "Target: $TARGET_DIR"
echo ""

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Copy all Python files
rsync -av --delete \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='.DS_Store' \
    "$SOURCE_DIR/" "$TARGET_DIR/"

echo ""
echo "✅ Sync complete!"
echo ""
echo "📝 To reload the plugin in Sublime Text:"
echo "   1. Open Sublime Text Console (View → Show Console)"
echo "   2. Run: sublime.run_command('reload_plugin', {'name': 'LaravelWorkshopAI'})"
echo "   OR just restart Sublime Text"
