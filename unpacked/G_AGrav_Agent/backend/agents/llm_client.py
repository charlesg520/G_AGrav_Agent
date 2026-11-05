import requests
import json
from typing import Dict, Any, List
from config import config

class FlexibleLLMClient:
    """Universal OpenAI-compatible LLM Client supporting OpenAI, DeepSeek, OpenRouter, Ollama, etc."""

    def __init__(self):
        pass

    def chat_completion(self, messages: List[Dict[str, str]], system_prompt: str = "") -> str:
        """Calls the configured LLM API provider using standard OpenAI REST format."""
        
        api_key = config.LLM_API_KEY
        base_url = config.LLM_BASE_URL.rstrip('/')
        model = config.LLM_MODEL

        if not api_key and "localhost" not in base_url and "127.0.0.1" not in base_url:
            # Fallback response if no API key supplied yet
            return (
                f"[AETHER AI Engine | {config.LLM_PROVIDER.upper()}]\n"
                f"I am actively monitoring live market feeds and executing risk-controlled trades. "
                f"To enable real-time conversational responses with {model}, please add your LLM_API_KEY in .env!"
            )

        endpoint = f"{base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        formatted_messages.extend(messages)

        payload = {
            "model": model,
            "messages": formatted_messages,
            "temperature": 0.3
        }

        try:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=12)
            if response.status_code == 200:
                res_data = response.json()
                return res_data["choices"][0]["message"]["content"]
            else:
                return f"LLM API Error ({response.status_code}): {response.text}"
        except Exception as e:
            return f"LLM Connection Error: {str(e)}. Please check LLM_BASE_URL and LLM_API_KEY in .env."

llm_client = FlexibleLLMClient()
