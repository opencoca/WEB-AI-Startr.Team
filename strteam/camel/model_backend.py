from typing import Any, Dict, List, Optional
import os
import logging
import openai
import tiktoken

from .typing import ModelType
from .config_loader import config_loader


class ModelBackend:
    """Base class for model backends."""

    def run(self, *args, **kwargs) -> Dict[str, Any]:
        """Execute model query and return response in OpenAI format."""
        raise NotImplementedError("Subclasses must implement run method")


class OpenAIModel(ModelBackend):
    """Model backend for OpenAI API compatible services."""
    
    def __init__(self, model_type: ModelType, config: Dict) -> None:
        """Initialize model with configuration from model_config.yaml."""
        self.model_type = model_type
        self.config = config
        self.model_name = config["name"]
        self.base_url = config["base_url"].rstrip("/")
        self.is_groq = "groq" in self.base_url.lower()
        logging.info(f"Model initialized: {self.model_name} @ {self.base_url}")
    
    def _get_api_key(self) -> str:
        """Get API key based on provider type."""
        return os.environ.get("GROQ_API_KEY", "") if self.is_groq else os.environ.get("OPENAI_API_KEY", "")
    
    def _calculate_tokens(self, messages: List[Dict]) -> int:
        """Estimate available completion tokens."""
        try:
            # Use appropriate encoding
            encoding = tiktoken.encoding_for_model(self.model_name) if hasattr(tiktoken, "encoding_for_model") else tiktoken.get_encoding("cl100k_base")
            
            # Calculate tokens from message content
            content = "\n".join(msg.get("content", "") for msg in messages if isinstance(msg, dict))
            prompt_tokens = len(encoding.encode(content)) + (15 * len(messages))
            
            # Use config's max_tokens
            return self.config["max_tokens"] - prompt_tokens
        except Exception as e:
            logging.error(f"Token calculation error: {e}")
            # Return a small safe number without fallbacks
            return 100
    
    def run(self, *args, **kwargs) -> Dict[str, Any]:
        """Execute model query with error handling."""
        messages = kwargs.get("messages", [])
        
        # Copy config params excluding non-API parameters
        api_params = {k: v for k, v in self.config.items() if k not in ["base_url", "is_openai", "name"]}
        api_params["max_tokens"] = self._calculate_tokens(messages)
        
        try:
            # Initialize the OpenAI client using the model's API key and base URL
            client = openai.OpenAI(
                api_key=self._get_api_key(),
                base_url=self.base_url
            )
            # Create and return a chat completion using the provided messages and parameters
            return client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                **api_params
            )
        except Exception as e:
            logging.error(f"API error: {e}")
            return {
                "id": "error",
                "object": "chat.completion", 
                "model": self.model_name,
                "choices": [{
                    "message": {"role": "assistant", "content": f"Error: {e}"},
                    "finish_reason": "error",
                    "index": 0
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            }


class StubModel(ModelBackend):
    """Stub model for testing."""
    
    def run(self, *args, **kwargs) -> Dict[str, Any]:
        """Return test response."""
        return {
            "id": "stub_model_id",
            "choices": [{"finish_reason": "stop", "message": {"content": "Lorem Ipsum", "role": "assistant"}}],
            "usage": {}
        }


class ModelFactory:
    """Factory for creating model backends."""
    
    @staticmethod
    def create(model_type: ModelType = None, custom_config: Dict = None) -> ModelBackend:
        """Create model instance using configuration from model_config.yaml.
        
        Args:
            model_type: Model type from config
            custom_config: Optional override configuration
        """
        # If no model_type specified, use first model from config
        if model_type is None:
            # Get the first model from config file
            models_config = config_loader.config["models"]
            first_model_name = next(iter(models_config.keys()))
            model_type = getattr(ModelType, first_model_name)
            logging.info(f"Using first model from config: {model_type.name}")
        
        # Get configuration directly from config sources
        if custom_config:
            config = custom_config
        else:
            config = config_loader.get_model_config(model_type.name)
            if not config:
                config = config_loader.get_default_config()
        
        # Create the appropriate model backend
        if model_type == ModelType.STUB:
            return StubModel()
        return OpenAIModel(model_type, config)