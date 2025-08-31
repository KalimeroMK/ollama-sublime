#!/usr/bin/env python3
"""
Simple test script to verify Ollama server connectivity and plugin functionality.
This script tests the core functionality that the Sublime Text plugin uses.
"""

import json
import urllib.request
import sys

def test_ollama_connection():
    """Test connection to Ollama server"""
    print("🔍 Testing Ollama Connection...")
    
    # Default settings from the plugin
    base_url = "http://127.0.0.1:11434"
    model = "qwen2.5-coder"
    
    try:
        # Test chat API endpoint
        api_endpoint = "/api/chat"
        full_url = base_url + api_endpoint
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful coding assistant."},
                {"role": "user", "content": "Write a simple Python function that adds two numbers."}
            ],
            "stream": False
        }
        
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(
            full_url, 
            data=json.dumps(payload).encode('utf-8'), 
            headers=headers
        )
        
        print(f"📡 Connecting to: {full_url}")
        print(f"🤖 Using model: {model}")
        
        response = urllib.request.urlopen(req, timeout=30)
        response_text = response.read().decode("utf-8")
        
        try:
            response_data = json.loads(response_text)
            content = response_data.get('message', {}).get('content', '')
            
            if content:
                print("✅ Connection successful!")
                print("🧠 AI Response:")
                print("-" * 50)
                print(content)
                print("-" * 50)
                return True
            else:
                print("❌ Empty response from AI")
                return False
                
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON response: {e}")
            print(f"Raw response: {response_text}")
            return False
            
    except urllib.error.URLError as e:
        print(f"❌ Connection failed: {e}")
        print("💡 Make sure Ollama is running:")
        print("   ollama serve")
        print(f"💡 Make sure the model '{model}' is available:")
        print(f"   ollama pull {model}")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_generate_api():
    """Test the generate API endpoint as fallback"""
    print("\n🔍 Testing Generate API (fallback)...")
    
    base_url = "http://127.0.0.1:11434"
    model = "qwen2.5-coder"
    
    try:
        api_endpoint = "/api/generate"
        full_url = base_url + api_endpoint
        
        payload = {
            "model": model,
            "prompt": "You are a helpful coding assistant.\n\nWrite a simple Python function that adds two numbers.",
            "stream": False
        }
        
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(
            full_url, 
            data=json.dumps(payload).encode('utf-8'), 
            headers=headers
        )
        
        response = urllib.request.urlopen(req, timeout=30)
        response_text = response.read().decode("utf-8")
        
        try:
            response_data = json.loads(response_text)
            content = response_data.get('response', '')
            
            if content:
                print("✅ Generate API works!")
                print("🧠 AI Response:")
                print("-" * 50)
                print(content[:200] + "..." if len(content) > 200 else content)
                print("-" * 50)
                return True
            else:
                print("❌ Empty response from Generate API")
                return False
                
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON response: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Generate API test failed: {e}")
        return False

def main():
    print("🚀 Ollama Sublime Plugin - Connection Test")
    print("=" * 50)
    
    chat_works = test_ollama_connection()
    generate_works = test_generate_api()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"Chat API: {'✅ Working' if chat_works else '❌ Failed'}")
    print(f"Generate API: {'✅ Working' if generate_works else '❌ Failed'}")
    
    if chat_works or generate_works:
        print("\n🎉 Your Ollama setup is working! The coder agent plugin should work perfectly.")
        print("\n🔧 Plugin features available:")
        print("• Custom prompts and code generation")
        print("• Context-aware code explanations")  
        print("• Code optimization suggestions")
        print("• Inline refactoring with approval")
        print("• Multi-file feature generation")
        print("• Code smell detection")
        print("• File creation from descriptions")
        return 0
    else:
        print("\n❌ Ollama connection failed. Please check your setup.")
        return 1

if __name__ == "__main__":
    sys.exit(main())