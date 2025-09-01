#!/usr/bin/env python3
"""
Unit tests for ollama_api.py module.
Tests the OllamaApiClient class and its methods.
"""

import unittest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock sublime module before importing
sys.modules['sublime'] = Mock()

from ollama_api import OllamaApiClient, create_api_client_from_settings


class TestOllamaApiClient(unittest.TestCase):
    """Test cases for OllamaApiClient class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.base_url = "http://127.0.0.1:11434"
        self.model = "test-model"
        self.system_prompt = "You are a test assistant."
        self.client_chat = OllamaApiClient(self.base_url, self.model, self.system_prompt, is_chat_api=True)
        self.client_generate = OllamaApiClient(self.base_url, self.model, self.system_prompt, is_chat_api=False)
    
    def test_init_chat_api(self):
        """Test initialization for chat API client."""
        self.assertEqual(self.client_chat.base_url, "http://127.0.0.1:11434")
        self.assertEqual(self.client_chat.model, "test-model")
        self.assertEqual(self.client_chat.system_prompt, "You are a test assistant.")
        self.assertTrue(self.client_chat.is_chat_api)
    
    def test_init_generate_api(self):
        """Test initialization for generate API client."""
        self.assertEqual(self.client_generate.base_url, "http://127.0.0.1:11434")
        self.assertEqual(self.client_generate.model, "test-model")
        self.assertEqual(self.client_generate.system_prompt, "You are a test assistant.")
        self.assertFalse(self.client_generate.is_chat_api)
    
    def test_base_url_stripping(self):
        """Test that trailing slashes are properly stripped from base URL."""
        client = OllamaApiClient("http://127.0.0.1:11434/", self.model, self.system_prompt)
        self.assertEqual(client.base_url, "http://127.0.0.1:11434")
    
    def test_get_api_endpoint_chat(self):
        """Test API endpoint for chat API."""
        self.assertEqual(self.client_chat._get_api_endpoint(), "/api/chat")
    
    def test_get_api_endpoint_generate(self):
        """Test API endpoint for generate API."""
        self.assertEqual(self.client_generate._get_api_endpoint(), "/api/generate")
    
    def test_create_payload_chat_without_messages(self):
        """Test payload creation for chat API without existing messages."""
        prompt = "Test prompt"
        payload = self.client_chat._create_payload(prompt, stream=False)
        
        expected_payload = {
            "model": "test-model",
            "messages": [
                {"role": "system", "content": "You are a test assistant."},
                {"role": "user", "content": "Test prompt"}
            ],
            "stream": False
        }
        
        self.assertEqual(payload, expected_payload)
    
    def test_create_payload_chat_with_messages(self):
        """Test payload creation for chat API with existing messages."""
        prompt = "Test prompt"
        existing_messages = [
            {"role": "system", "content": "Custom system"},
            {"role": "user", "content": "Previous user message"},
            {"role": "assistant", "content": "Previous assistant response"}
        ]
        
        payload = self.client_chat._create_payload(prompt, stream=True, messages=existing_messages)
        
        expected_payload = {
            "model": "test-model",
            "messages": existing_messages,
            "stream": True
        }
        
        self.assertEqual(payload, expected_payload)
    
    def test_create_payload_generate(self):
        """Test payload creation for generate API."""
        prompt = "Test prompt"
        payload = self.client_generate._create_payload(prompt, stream=False)
        
        expected_payload = {
            "model": "test-model",
            "prompt": "You are a test assistant.\n\nTest prompt",
            "stream": False
        }
        
        self.assertEqual(payload, expected_payload)
    
    @patch('urllib.request.urlopen')
    def test_make_blocking_request_chat_success(self, mock_urlopen):
        """Test successful blocking request for chat API."""
        # Mock response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "message": {"content": "Test response content"}
        }).encode('utf-8')
        mock_urlopen.return_value = mock_response
        
        result = self.client_chat.make_blocking_request("Test prompt")
        self.assertEqual(result, "Test response content")
    
    @patch('urllib.request.urlopen')
    def test_make_blocking_request_generate_success(self, mock_urlopen):
        """Test successful blocking request for generate API."""
        # Mock response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "response": "Test response content"
        }).encode('utf-8')
        mock_urlopen.return_value = mock_response
        
        result = self.client_generate.make_blocking_request("Test prompt")
        self.assertEqual(result, "Test response content")
    
    @patch('urllib.request.urlopen')
    def test_make_blocking_request_invalid_json(self, mock_urlopen):
        """Test blocking request with invalid JSON response."""
        # Mock response with invalid JSON
        mock_response = Mock()
        mock_response.read.return_value = b"Invalid JSON response"
        mock_urlopen.return_value = mock_response
        
        result = self.client_chat.make_blocking_request("Test prompt")
        self.assertIsNone(result)
    
    @patch('urllib.request.urlopen')
    def test_make_blocking_request_network_error(self, mock_urlopen):
        """Test blocking request with network error."""
        # Mock network error
        mock_urlopen.side_effect = Exception("Network error")
        
        result = self.client_chat.make_blocking_request("test prompt")
        
        # Should return error message instead of None
        self.assertIsNotNone(result)
        self.assertIn("Ollama Connection Error", result)
        self.assertIn("Network error", result)
    
    @patch('urllib.request.urlopen')
    def test_make_streaming_request_chat(self, mock_urlopen):
        """Test streaming request for chat API."""
        # Mock streaming response
        mock_response = Mock()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_response.__iter__ = Mock(return_value=iter([
            json.dumps({"message": {"content": "chunk1"}}).encode('utf-8'),
            json.dumps({"message": {"content": "chunk2"}}).encode('utf-8'),
            json.dumps({"done": True}).encode('utf-8')
        ]))
        mock_urlopen.return_value = mock_response
        
        # Collect callback results
        callback_results = []
        def test_callback(content):
            callback_results.append(content)
        
        self.client_chat.make_streaming_request("Test prompt", test_callback)
        self.assertEqual(callback_results, ["chunk1", "chunk2"])
    
    @patch('urllib.request.urlopen')
    def test_make_streaming_request_generate(self, mock_urlopen):
        """Test streaming request for generate API."""
        # Mock streaming response
        mock_response = Mock()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_response.__iter__ = Mock(return_value=iter([
            json.dumps({"response": "chunk1"}).encode('utf-8'),
            json.dumps({"response": "chunk2"}).encode('utf-8'),
            json.dumps({"done": True}).encode('utf-8')
        ]))
        mock_urlopen.return_value = mock_response
        
        # Collect callback results
        callback_results = []
        def test_callback(content):
            callback_results.append(content)
        
        self.client_generate.make_streaming_request("Test prompt", test_callback)
        self.assertEqual(callback_results, ["chunk1", "chunk2"])
    
    @patch('urllib.request.urlopen')
    def test_make_streaming_request_error(self, mock_urlopen):
        """Test streaming request with error."""
        # Mock network error
        mock_urlopen.side_effect = Exception("Network error")
        
        callback_results = []
        def mock_callback(chunk):
            callback_results.append(chunk)
        
        self.client_chat.make_streaming_request("test prompt", mock_callback)
        
        # Should return error message instead of "ERROR"
        self.assertTrue(len(callback_results) > 0)
        self.assertIn("Ollama Connection Error", callback_results[0])
        self.assertIn("Network error", callback_results[0])


class TestCreateApiClientFromSettings(unittest.TestCase):
    """Test cases for the factory function."""
    
    @patch('sublime.load_settings')
    def test_create_api_client_chat_defaults(self, mock_load_settings):
        """Test creating API client with default settings for chat API."""
        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default: {
            "model": "qwen2.5-coder",
            "url": "http://127.0.0.1:11434",
            "system_prompt": "You are a Laravel PHP expert."
        }.get(key, default)
        mock_load_settings.return_value = mock_settings
        
        client = create_api_client_from_settings()
        
        self.assertEqual(client.base_url, "http://127.0.0.1:11434")
        self.assertEqual(client.model, "qwen2.5-coder")
        self.assertEqual(client.system_prompt, "You are a Laravel PHP expert.")
        self.assertFalse(client.is_chat_api)  # Default URL doesn't contain /api/chat
    
    @patch('sublime.load_settings')
    def test_create_api_client_chat_api(self, mock_load_settings):
        """Test creating API client with chat API URL."""
        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default: {
            "model": "custom-model",
            "url": "http://127.0.0.1:11434/api/chat",
            "system_prompt": "Custom system prompt."
        }.get(key, default)
        mock_load_settings.return_value = mock_settings
        
        client = create_api_client_from_settings()
        
        self.assertEqual(client.base_url, "http://127.0.0.1:11434")
        self.assertEqual(client.model, "custom-model")
        self.assertEqual(client.system_prompt, "Custom system prompt.")
        self.assertTrue(client.is_chat_api)
    
    @patch('sublime.load_settings')
    def test_create_api_client_generate_api(self, mock_load_settings):
        """Test creating API client with generate API URL."""
        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default: {
            "model": "generate-model",
            "url": "http://127.0.0.1:11434/api/generate",
            "system_prompt": "Generate system prompt."
        }.get(key, default)
        mock_load_settings.return_value = mock_settings
        
        client = create_api_client_from_settings()
        
        self.assertEqual(client.base_url, "http://127.0.0.1:11434")
        self.assertEqual(client.model, "generate-model")
        self.assertEqual(client.system_prompt, "Generate system prompt.")
        self.assertFalse(client.is_chat_api)


if __name__ == '__main__':
    print("🧪 Running Ollama API Tests...")
    print("=" * 50)
    
    # Run the tests
    unittest.main(verbosity=2, exit=False)
    
    print("\n" + "=" * 50)
    print("✅ Ollama API tests completed!")