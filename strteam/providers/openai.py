import os
from typing import List, Dict, Any
import openai
from utils.config_manager import get_config_value
from ..handlers.model_handler import ModelRequest, ModelResponse
from .base_provider import BaseProvider

class OpenaiProvider(BaseProvider):
    def __init__(self):
        # Get API key from environment variable or config
        self.api_key = os.environ.get("OPENAI_API_KEY") or get_config_value("models", "openai", "api_key")
        if not self.api_key:
            raise ValueError("OpenAI API key not found in environment or config")
            
        # Set up client
        self.client = openai.OpenAI(api_key=self.api_key)
        
        # Load supported models from config
        self.supported_models = get_config_value("models", "openai", "models", default=[])
    
    def get_completion(self, request: ModelRequest) -> ModelResponse:
        """Generate completion using OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=request.model_id,
                messages=[{"role": "user", "content": request.prompt}],
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                **request.params
            )
            
            return ModelResponse(
                content=response.choices[0].message.content,
                model_id=request.model_id,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                raw_response=response
            )
        except Exception as e:
            # Handle errors gracefully
            error_msg = f"OpenAI API error: {str(e)}"
            return ModelResponse(
                content=error_msg,
                model_id=request.model_id,
                usage={},
                raw_response=None
            )
    
    def supports_model(self, model_id: str) -> bool:
        """Check if this provider supports the given model ID."""
        return model_id in self.supported_models
    
    def get_available_models(self) -> List[str]:
        """Get list of model IDs available through OpenAI."""
        return self.supported_models
