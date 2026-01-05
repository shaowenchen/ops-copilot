"""
OpenAI Client for Ops Copilot
"""

import os
import requests
from typing import Dict, Any, Optional, List
from ..utils.logging import get_logger

logger = get_logger(__name__)


class OpenAIClient:
    """OpenAI API Client"""
    
    def __init__(self, endpoint: str, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initialize OpenAI Client
        
        Args:
            endpoint: OpenAI API endpoint (e.g., https://api.openai.com/v1)
            api_key: OpenAI API key
            model: Model name (default: gpt-4o-mini)
        """
        self.endpoint = endpoint.rstrip('/')
        if not self.endpoint.endswith('/v1'):
            if 'api.openai.com' in self.endpoint and '/v1' not in self.endpoint:
                self.endpoint = self.endpoint + '/v1'
        
        self.api_key = api_key
        self.model = model
        self.base_url = f"{self.endpoint}/chat/completions"
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """
        Create a chat completion
        
        Args:
            messages: List of messages (each with 'role' and 'content')
            tools: Optional list of tools for function calling
            temperature: Temperature for generation
            
        Returns:
            API response
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        if tools:
            payload["tools"] = tools
        
        try:
            # Log request details (always log, not just debug)
            logger.info(f"[OpenAI API Request]")
            logger.info(f"  URL: {self.base_url}")
            logger.info(f"  Model: {self.model}")
            logger.info(f"  Messages: {len(messages)}")
            logger.info(f"  Tools: {len(tools) if tools else 0}")
            logger.info(f"  Temperature: {temperature}")
            
            response = requests.post(
                self.base_url,
                json=payload,
                headers=self.headers,
                timeout=60  # Reduce timeout from 600 to 60 seconds
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Log response details
            logger.info(f"[OpenAI API Response]")
            logger.info(f"  Status: {response.status_code}")
            if result.get('choices'):
                choice = result['choices'][0]
                content_length = len(choice.get('message', {}).get('content', ''))
                logger.info(f"  Response content length: {content_length} characters")
                finish_reason = choice.get('finish_reason', 'unknown')
                logger.info(f"  Finish reason: {finish_reason}")
                if 'usage' in result:
                    usage = result['usage']
                    logger.info(f"  Tokens - Prompt: {usage.get('prompt_tokens', 0)}, Completion: {usage.get('completion_tokens', 0)}, Total: {usage.get('total_tokens', 0)}")
            
            return result
        except requests.exceptions.Timeout as e:
            logger.error(f"OpenAI API timeout: {e}")
            raise Exception(f"Request timeout: The API request took too long to complete")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"OpenAI API connection error: {e}")
            raise Exception(f"Connection error: Unable to connect to the API. Please check your network connection and API endpoint.")
        except requests.exceptions.HTTPError as e:
            logger.error(f"OpenAI API HTTP error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise Exception(f"HTTP error {e.response.status_code if hasattr(e, 'response') and e.response else 'unknown'}: {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API error: {e}")
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            raise Exception(f"API request failed: {str(e)}")

