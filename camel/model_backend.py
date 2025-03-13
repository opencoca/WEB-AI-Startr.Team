import openai
import tiktoken
import os
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from camel.typing import ModelType
from camel.config_loader import config_loader

class ModelBackend(ABC):
    """Base class for different model backends (OpenAI API, local LLM, test stubs, etc.)"""

    @abstractmethod
    def run(self, *args, **kwargs):
        """Runs the query to the backend model.
        
        Returns:
            Dict[str, Any]: All backends must return a dict in OpenAI format.
        """
        pass


class OpenAIModel(ModelBackend):
    def __init__(self, model_type: ModelType, model_config_dict: Dict) -> None:
        """Initialize OpenAI API model backend.
        
        Args:
            model_type: The type of model to use
            model_config_dict: Configuration parameters for the model
        """
        super().__init__()
        self.model_type = model_type
        self.model_config = model_config_dict
        self.client = self._setup_client()
        
        # Set max tokens with fallback to default
        self.max_tokens = self.model_config.get("max_tokens", 4096)
        logging.debug(f"Initialized OpenAIModel: {model_type}, max_tokens: {self.max_tokens}")

    def _setup_client(self):
        """Set up and return the OpenAI client."""
        api_key = os.environ["OPENAI_API_KEY"]
        base_url = self.model_config.get("base_url")
        
        # Check if we need to use a different API key for specific providers
        if base_url and "groq" in base_url.lower():
            if "GROQ_API_KEY" not in os.environ or not os.environ["GROQ_API_KEY"]:
                raise ValueError("GROQ_API_KEY environment variable is required for Groq models")
            api_key = os.environ["GROQ_API_KEY"]
        
        # Create and return the client
        return openai.OpenAI(api_key=api_key, base_url=base_url) if base_url else openai.OpenAI(api_key=api_key)

    def run(self, *args, **kwargs):
        """Run the model with the provided arguments."""
        messages = kwargs.get("messages", [])
        prompt = "\n".join(message["content"] for message in messages)
        
        # Calculate tokens in the prompt
        try:
            encoding = tiktoken.encoding_for_model(self.model_type.value)
        except KeyError:
            logging.warning(f"No tokenizer for {self.model_type.value}, using default")
            encoding = tiktoken.get_encoding("cl100k_base")
            
        prompt_tokens = len(encoding.encode(prompt)) + 15 * len(messages)
        max_completion_tokens = max(0, self.max_tokens - prompt_tokens)
        
        # Prepare run configuration
        run_config = {**config_loader.get_default_config(), **self.model_config}
        # Remove fields that should not be passed to the API
        for key in ["base_url", "is_openai", "name"]:
            run_config.pop(key, None)
        run_config["max_tokens"] = max_completion_tokens
        
        # Get model name with fallback
        model_name = self.model_config.get("name") or self.model_type.value
        
        try:
            # Make the API call
            logging.debug(f"Prompt sent to {model_name}: {prompt}")
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                **run_config
            )
            logging.debug(f"Model response: {response}")
            self._log_usage(response.usage)
            return response
        except Exception as e:
            logging.error(f"API call failed with model {model_name}: {str(e)}")
            
            # Try fallback model if model not found
            if "model_not_found" in str(e) or "does not exist" in str(e):
                try:
                    fallback_model = "gpt-4o-mini"
                    logging.info(f"Trying fallback model: {fallback_model}")
                    
                    response = self.client.chat.completions.create(
                        model=fallback_model,
                        messages=messages,
                        **run_config
                    )
                    logging.debug(f"Model response: {response}")
                    self._log_usage(response.usage)
                    self.model_config["name"] = fallback_model
                    return response
                except Exception as fallback_error:
                    logging.error(f"Fallback model also failed: {str(fallback_error)}")
            
            # Re-raise the original exception
            raise

    def _log_usage(self, usage):
        """Log token usage and cost information."""
        from chatdev.statistics import prompt_cost
        
        cost = prompt_cost(
            self.model_type.value,
            num_prompt_tokens=usage.prompt_tokens,
            num_completion_tokens=usage.completion_tokens,
        )
        
        print(
            f"[OpenAI_Usage_Info] "
            f"prompt_tokens: {usage.prompt_tokens}, "
            f"completion_tokens: {usage.completion_tokens}, "
            f"total_tokens: {usage.total_tokens}, "
            f"cost: ${cost:.6f}"
        )
        print(f"\n💰 Usage: {usage.prompt_tokens}+{usage.completion_tokens}={usage.total_tokens} tokens, Cost: ${cost:.4f}\n")


class StubModel(ModelBackend):
    """A dummy model used for unit tests."""

    def run(self, *args, **kwargs) -> Dict[str, Any]:
        return {
            "id": "stub_model_id",
            "usage": {},
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": "Lorem Ipsum", "role": "assistant"},
                }
            ],
        }


class ModelFactory:
    @staticmethod
    def create(model_type: ModelType, model_config_dict: Dict = None) -> ModelBackend:
        """Create and return a model backend instance of the specified type."""
        if model_type is None:
            model_type = ModelType.GPT_3_5_TURBO

        if model_config_dict is None:
            model_config_dict = config_loader.get_model_config(model_type.name)

        if not model_config_dict:
            raise ValueError(f"No configuration found for model type: {model_type}")

        if model_type == ModelType.STUB:
            return StubModel()
        else:
            return OpenAIModel(model_type, model_config_dict)