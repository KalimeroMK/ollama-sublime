import json
import urllib.request
import sublime
import socket
import urllib.error


class OllamaApiClient:
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
                raise ConnectionError(f"Connection timeout to Ollama server at {full_url}")
            elif "Connection refused" in str(e.reason):
                raise ConnectionError(f"Ollama server is not running at {full_url}. Please start Ollama with 'ollama serve'")
            elif "Name or service not known" in str(e.reason):
                raise ConnectionError(f"Cannot resolve Ollama server address: {full_url}")
            else:
                raise ConnectionError(f"Failed to connect to Ollama server: {e.reason}")
        except socket.timeout:
            raise ConnectionError(f"Connection timeout to Ollama server at {full_url}")
        except Exception as e:
            raise ConnectionError(f"Unexpected error connecting to Ollama: {str(e)}")
    
    def make_blocking_request(self, prompt, messages=None):
        """Make a blocking request and return the response content with improved error handling."""
        try:
            payload = self._create_payload(prompt, stream=False, messages=messages)
            response = self._make_request(payload)
            response_text = response.read().decode("utf-8")
            
            try:
                response_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                print(f"[DEBUG] Invalid JSON from API: {e}\n{response_text}")
                return None
            
            if self.is_chat_api:
                return response_data.get('message', {}).get('content', '')
            else:
                return response_data.get('response', '')
                
        except ConnectionError as e:
            error_msg = f"🔴 **Ollama Connection Error:** {str(e)}\n\n"
            error_msg += "**Troubleshooting steps:**\n"
            error_msg += "1. Make sure Ollama is installed: `ollama --version`\n"
            error_msg += "2. Start Ollama server: `ollama serve`\n"
            error_msg += "3. Check if the model is available: `ollama list`\n"
            error_msg += "4. Verify the URL in settings: {}\n".format(self.base_url)
            error_msg += "5. Check firewall/network settings\n\n"
            error_msg += "**Current settings:**\n"
            error_msg += f"- Model: {self.model}\n"
            error_msg += f"- URL: {self.base_url}\n"
            error_msg += f"- API Type: {'Chat' if self.is_chat_api else 'Generate'}"
            
            print(f"[Ollama AI] {error_msg}")
            return error_msg
            
        except Exception as e:
            error_msg = f"🔴 **Unexpected Error:** {str(e)}\n\n"
            error_msg += "Please check the console for more details or report this issue."
            print(f"[Ollama AI] Unexpected error: {e}")
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
            error_msg = f"🔴 **Ollama Connection Error:** {str(e)}\n\n"
            error_msg += "**Troubleshooting steps:**\n"
            error_msg += "1. Make sure Ollama is installed: `ollama --version`\n"
            error_msg += "2. Start Ollama server: `ollama serve`\n"
            error_msg += "3. Check if the model is available: `ollama list`\n"
            error_msg += "4. Verify the URL in settings: {}\n".format(self.base_url)
            error_msg += "5. Check firewall/network settings"
            
            callback(f"\n{error_msg}")
        except Exception as e:
            callback(f"\n🔴 **Unexpected Error:** {str(e)}")


def create_api_client_from_settings():
    """Factory function to create API client from Sublime settings."""
    settings = sublime.load_settings("Ollama.sublime-settings")
    model = settings.get("model", "qwen2.5-coder")
    url_from_settings = settings.get("url", "http://127.0.0.1:11434")
    system_prompt = settings.get("system_prompt", "You are a Laravel PHP expert.")
    is_chat_api = "/api/chat" in url_from_settings
    base_url = url_from_settings.replace('/api/chat', '').replace('/api/generate', '')
    
    return OllamaApiClient(base_url, model, system_prompt, is_chat_api)