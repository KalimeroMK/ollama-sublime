#!/bin/bash

# Create symlink for Laravel Workshop AI plugin
# This makes Sublime Text use files directly from your project

SOURCE_DIR="/Users/zoran/PhpstormProjects/ollama-sublime/LaravelWorkshopAI38"
TARGET_DIR="/Users/zoran/Library/Application Support/Sublime Text/Packages/LaravelWorkshopAI38"

echo "🔗 Creating symlink for Laravel Workshop AI..."
echo ""
echo "Source: $SOURCE_DIR"
echo "Target: $TARGET_DIR"
echo ""

# Check if target exists
if [ -e "$TARGET_DIR" ]; then
    echo "⚠️  Target directory already exists!"
    echo ""
    read -p "Do you want to remove it and create symlink? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Removing existing directory..."
        rm -rf "$TARGET_DIR"
    else
        echo "❌ Cancelled"
        exit 1
    fi
fi

# Create symlink
echo "🔗 Creating symlink..."
ln -s "$SOURCE_DIR" "$TARGET_DIR"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Symlink created successfully!"
    echo ""
    echo "📝 Now restart Sublime Text to reload the plugin"
    echo ""
    echo "🎉 From now on, any changes you make in your project will"
    echo "   automatically be reflected in Sublime Text!"
else
    echo ""
    echo "❌ Failed to create symlink"
    exit 1
fi
