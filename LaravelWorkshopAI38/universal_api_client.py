"""
Universal API Client - Supports multiple AI providers
- Ollama (local)
- OpenAI (ChatGPT, GPT-4)
- Google Gemini (Gemini 1.5 Pro/Flash)
- Custom servers (your Tesla L4 server)
"""

import sublime
import json
import urllib.request
import urllib.error
from typing import Callable, Optional, Dict, Any


class UniversalAPIClient:
    """Universal API client that supports multiple AI providers"""
    
    def __init__(self, provider = "ollama"):
        self.provider = provider
        self.settings = sublime.load_settings("LaravelWorkshopAI.sublime-settings")
        self._load_config()
    
    def _load_config(self):
        """Load configuration for selected provider"""
        provider_config = self.settings.get(self.provider, {})
        
        if self.provider == "ollama":
            self.base_url = provider_config.get("base_url", "http://localhost:11434")
            self.model = provider_config.get("model", "qwen2.5-coder:14b")
            self.timeout = provider_config.get("timeout", 120)
            self.stream = provider_config.get("stream", True)
            self.api_key = None
            self.headers = {"Content-Type": "application/json"}
            
        elif self.provider == "openai":
            self.base_url = provider_config.get("base_url", "https://api.openai.com/v1")
            self.model = provider_config.get("model", "gpt-4")
            self.timeout = provider_config.get("timeout", 60)
            self.stream = True
            self.api_key = provider_config.get("api_key", "")
            self.temperature = provider_config.get("temperature", 0.7)
            self.max_tokens = provider_config.get("max_tokens", 4000)
            
            if not self.api_key:
                raise ValueError("OpenAI API key is required. Set it in LaravelWorkshopAI.sublime-settings")
            
            self.headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer {0}".format(self.api_key)
            }
            
        elif self.provider == "gemini":
            self.api_key = provider_config.get("api_key", "")
            self.model = provider_config.get("model", "gemini-1.5-pro")
            self.timeout = provider_config.get("timeout", 60)
            self.stream = True
            self.temperature = provider_config.get("temperature", 0.7)
            self.max_tokens = provider_config.get("max_tokens", 8000)
            
            if not self.api_key:
                raise ValueError("Gemini API key is required. Set it in LaravelWorkshopAI.sublime-settings")
            
            # Gemini uses API key in URL, not headers
            self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/{0}".format(self.model)
            self.headers = {
                "Content-Type": "application/json"
            }
            
        elif self.provider == "custom":
            self.base_url = provider_config.get("base_url", "")
            self.model = provider_config.get("model", "")
            self.timeout = provider_config.get("timeout", 120)
            self.stream = provider_config.get("stream", True)
            self.api_key = provider_config.get("api_key", "")
            self.api_format = provider_config.get("api_format", "openai")
            
            if not self.base_url:
                raise ValueError("Custom server base_url is required")
            
            # Build headers
            self.headers = {"Content-Type": "application/json"}
            
            if self.api_key:
                self.headers["Authorization"] = "Bearer {0}".format(self.api_key)
            
            # Add custom headers
            custom_headers = provider_config.get("headers", {})
            self.headers.update(custom_headers)
        
        else:
            raise ValueError("Unknown provider: {0}".format(self.provider))
    
    def _build_request_payload(self, prompt):
        """Build request payload based on provider"""
        
        if self.provider == "ollama":
            return {
                "model": self.model,
                "prompt": prompt,
                "stream": self.stream
            }
        
        elif self.provider == "openai":
            return {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a helpful coding assistant specialized in Laravel PHP development."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": self.stream
            }
        
        elif self.provider == "gemini":
            return {
                "contents": [
                    {
                        "parts": [
                            {"text": "You are a helpful coding assistant specialized in Laravel PHP development.\n\n{0}".format(prompt)}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": self.temperature,
                    "maxOutputTokens": self.max_tokens
                }
            }
        
        elif self.provider == "custom":
            # Use format specified in config
            if self.api_format == "openai":
                return {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful coding assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    "stream": self.stream
                }
            else:  # ollama format
                return {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": self.stream
                }
    
    def _get_endpoint(self):
        """Get API endpoint based on provider"""
        
        if self.provider == "ollama":
            return "{0}/api/generate".format(self.base_url)
        
        elif self.provider == "openai":
            return "{0}/chat/completions".format(self.base_url)
        
        elif self.provider == "gemini":
            # Gemini uses streaming endpoint with API key in URL
            if self.stream:
                return "{0}:streamGenerateContent?key={1}&alt=sse".format(self.base_url, self.api_key)
            else:
                return "{0}:generateContent?key={1}".format(self.base_url, self.api_key)
        
        elif self.provider == "custom":
            if self.api_format == "openai":
                return "{0}/chat/completions".format(self.base_url)
            else:
                return "{0}/api/generate".format(self.base_url)
    
    def _parse_response_chunk(self, line):
        """Parse response chunk based on provider"""
        
        if not line.strip():
            return None
        
        try:
            if self.provider == "ollama" or (self.provider == "custom" and self.api_format == "ollama"):
                data = json.loads(line)
                return data.get("response", "")
            
            elif self.provider == "openai" or (self.provider == "custom" and self.api_format == "openai"):
                # OpenAI format: data: {...}
                if line.startswith("data: "):
                    line = line[6:]  # Remove "data: " prefix
                
                if line.strip() == "[DONE]":
                    return None
                
                data = json.loads(line)
                choices = data.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    return delta.get("content", "")
                
                return None
            
            elif self.provider == "gemini":
                # Gemini SSE format: data: {...}
                if line.startswith("data: "):
                    line = line[6:]
                
                data = json.loads(line)
                candidates = data.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
                
                return None
        
        except json.JSONDecodeError:
            return None
    
    def make_streaming_request(self, prompt, callback):
        """Make streaming request to AI provider"""
        
        endpoint = self._get_endpoint()
        payload = self._build_request_payload(prompt)
        
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode('utf-8'),
            headers=self.headers,
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                for line in response:
                    line = line.decode('utf-8').strip()
                    content = self._parse_response_chunk(line)
                    if content:
                        callback(content)
        
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception("HTTP {0}: {1}".format(e.code, error_body))
        
        except urllib.error.URLError as e:
            raise Exception("Connection error: {0}".format(str(e)))
        
        except Exception as e:
            raise Exception("Request failed: {0}".format(str(e)))
    
    def make_blocking_request(self, prompt):
        """Make blocking request to AI provider"""
        
        endpoint = self._get_endpoint()
        payload = self._build_request_payload(prompt)
        
        # Disable streaming for blocking request (except Gemini which handles it differently)
        if self.provider != "gemini":
            payload["stream"] = False
        
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode('utf-8'),
            headers=self.headers,
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                if self.provider == "ollama" or (self.provider == "custom" and self.api_format == "ollama"):
                    return data.get("response", "")
                
                elif self.provider == "openai" or (self.provider == "custom" and self.api_format == "openai"):
                    choices = data.get("choices", [])
                    if choices:
                        message = choices[0].get("message", {})
                        return message.get("content", "")
                    return ""
                
                elif self.provider == "gemini":
                    candidates = data.get("candidates", [])
                    if candidates:
                        content = candidates[0].get("content", {})
                        parts = content.get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                    return ""
        
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception("HTTP {0}: {1}".format(e.code, error_body))
        
        except urllib.error.URLError as e:
            raise Exception("Connection error: {0}".format(str(e)))
        
        except Exception as e:
            raise Exception("Request failed: {0}".format(str(e)))


def create_universal_api_client():
    """Create API client based on settings"""
    settings = sublime.load_settings("LaravelWorkshopAI.sublime-settings")
    provider = settings.get("ai_provider", "ollama")
    
    try:
        return UniversalAPIClient(provider)
    except Exception as e:
        sublime.error_message("Failed to initialize AI provider '{0}':\n\n{1}".format(provider, str(e)))
        raise


# Backward compatibility - use universal client
def create_api_client_from_settings():
    """Backward compatibility wrapper"""
    return create_universal_api_client()
