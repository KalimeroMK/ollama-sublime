import json
import urllib.request
import sublime
import socket
import urllib.error

# Import universal API client
from .universal_api_client import create_universal_api_client


class LaravelWorkshopApiClient:
    """
    Handles all API communication with Ollama server.
    Centralizes request/response logic to avoid code duplication.
    """
    
    def __init__(self, base_url, model, system_prompt, is_chat_api=True):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.system_prompt = system_prompt
        self.is_chat_api = is_chat_api
    
    def _get_api_endpoint(self):
        """Get the appropriate API endpoint based on configuration."""
        return "/api/chat" if self.is_chat_api else "/api/generate"
    
    def _create_payload(self, prompt, stream=False, messages=None):
        """Create request payload based on API type."""
        if self.is_chat_api:
            if messages is None:
                messages = [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ]
            return {
                "model": self.model,
                "messages": messages,
                "stream": stream
            }
        else:
            full_prompt = "{}\n\n{}".format(self.system_prompt, prompt)
            return {
                "model": self.model,
                "prompt": full_prompt,
                "stream": stream
            }
    
    def _make_request(self, payload):
        """Make HTTP request to Ollama API with improved error handling."""
        full_url = self.base_url + self._get_api_endpoint()
        headers = {"Content-Type": "application/json"}
        
        try:
            req = urllib.request.Request(
                full_url,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers
            )
            
            # Add timeout to prevent hanging
            return urllib.request.urlopen(req, timeout=30)
            
        except urllib.error.URLError as e:
            if isinstance(e.reason, socket.timeout):
                raise ConnectionError("Connection timeout to Ollama server at {0}".format(full_url))
            elif "Connection refused" in str(e.reason):
                raise ConnectionError("Ollama server is not running at {0}. Please start Ollama with 'ollama serve'".format(full_url))
            elif "Name or service not known" in str(e.reason):
                raise ConnectionError("Cannot resolve Ollama server address: {0}".format(full_url))
            else:
                raise ConnectionError("Failed to connect to Ollama server: {0}".format(e.reason))
        except socket.timeout:
            raise ConnectionError("Connection timeout to Ollama server at {0}".format(full_url))
        except Exception as e:
            raise ConnectionError("Unexpected error connecting to Ollama: {0}".format(str(e)))
    
    def make_blocking_request(self, prompt, messages=None):
        """Make a blocking request and return the response content with improved error handling."""
        try:
            payload = self._create_payload(prompt, stream=False, messages=messages)
            response = self._make_request(payload)
            response_text = response.read().decode("utf-8")
            
            try:
                response_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                print("[DEBUG] Invalid JSON from API: {0}\n{1}".format(e, response_text))
                return None
            
            if self.is_chat_api:
                return response_data.get('message', {}).get('content', '')
            else:
                return response_data.get('response', '')
                
        except ConnectionError as e:
            error_msg = "🔴 **Ollama Connection Error:** {0}\n\n".format(str(e))
            error_msg += "**Troubleshooting steps:**\n"
            error_msg += "1. Make sure Ollama is installed: `ollama --version`\n"
            error_msg += "2. Start Ollama server: `ollama serve`\n"
            error_msg += "3. Check if the model is available: `ollama list`\n"
            error_msg += "4. Verify the URL in settings: {}\n".format(self.base_url)
            error_msg += "5. Check firewall/network settings\n\n"
            error_msg += "**Current settings:**\n"
            error_msg += "- Model: {0}\n".format(self.model)
            error_msg += "- URL: {0}\n".format(self.base_url)
            error_msg += "- API Type: {0}".format('Chat' if self.is_chat_api else 'Generate')
            
            print("[Laravel Workshop AI] {0}".format(error_msg))
            return error_msg
            
        except Exception as e:
            error_msg = "🔴 **Unexpected Error:** {0}\n\n".format(str(e))
            error_msg += "Please check the console for more details or report this issue."
            print("[Laravel Workshop AI] Unexpected error: {0}".format(e))
            return error_msg
    
    def make_streaming_request(self, prompt, callback, messages=None):
        """Make a streaming request and call callback for each chunk with improved error handling."""
        try:
            payload = self._create_payload(prompt, stream=True, messages=messages)
            response = self._make_request(payload)
            
            with response:
                for line in response:
                    try:
                        parsed = json.loads(line.decode("utf-8"))
                        
                        content = None
                        if self.is_chat_api and "message" in parsed and "content" in parsed["message"]:
                            content = parsed["message"]["content"]
                        elif not self.is_chat_api and "response" in parsed:
                            content = parsed.get("response", "")
                        
                        if content is not None:
                            callback(content)
                        
                        if parsed.get("done", False):
                            break
                            
                    except json.JSONDecodeError:
                        continue
                        
        except ConnectionError as e:
            error_msg = "🔴 **Ollama Connection Error:** {0}\n\n".format(str(e))
            error_msg += "**Troubleshooting steps:**\n"
            error_msg += "1. Make sure Ollama is installed: `ollama --version`\n"
            error_msg += "2. Start Ollama server: `ollama serve`\n"
            error_msg += "3. Check if the model is available: `ollama list`\n"
            error_msg += "4. Verify the URL in settings: {}\n".format(self.base_url)
            error_msg += "5. Check firewall/network settings"
            
            callback("\n{0}".format(error_msg))
        except Exception as e:
            callback("\n🔴 **Unexpected Error:** {0}".format(str(e)))


def create_api_client_from_settings():
    """Factory function to create API client from Sublime settings."""
    settings = sublime.load_settings("LaravelWorkshopAI.sublime-settings")
    
    # Check if using new universal API client
    provider = settings.get("ai_provider", None)
    
    if provider:
        # Use new universal API client
        return create_universal_api_client()
    else:
        # Backward compatibility - use old Ollama client
        model = settings.get("model", "qwen2.5-coder")
        url_from_settings = settings.get("url", "http://127.0.0.1:11434")
        system_prompt = settings.get("system_prompt", "You are a Laravel PHP expert.")
        is_chat_api = "/api/chat" in url_from_settings
        base_url = url_from_settings.replace('/api/chat', '').replace('/api/generate', '')
        
        return OllamaApiClient(base_url, model, system_prompt, is_chat_api)