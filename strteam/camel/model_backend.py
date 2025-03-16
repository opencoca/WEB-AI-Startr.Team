# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from typing import Any, Dict, List, Optional, Union
import json
import warnings
import os
import logging
import openai
import tiktoken

from .typing import ModelType
from .config_loader import config_loader

class ModelBackend:
    """Base class for different model backends (OpenAI API, local LLM, test stubs, etc.)"""

    def run(self, *args, **kwargs):
        """Runs the query to the backend model.
        
        Returns:
            Dict[str, Any]: All backends must return a dict in OpenAI format.
        """
        pass


class OpenAIModel(ModelBackend):
    """Model backend that uses the OpenAI API format, supporting multiple providers including OpenAI and Groq."""
    
    def __init__(self, model_type: ModelType, model_config_dict: Dict) -> None:
        """Initialize API model backend.
        
        Args:
            model_type: The type of model to use
            model_config_dict: Configuration parameters for the model
        """
        super().__init__()
        self.model_type = model_type
        self.model_config = model_config_dict
        
        # Set max tokens with fallback to default
        self.max_tokens = self.model_config.get("max_tokens", 4096)
        
        # Get the model name directly from config with a fallback
        self.model_name = self.model_config.get("name")
        if self.model_name is None:
            # Fallback to the model_type value if name is not in config
            self.model_name = self.model_type.value if self.model_type else "gpt-3.5-turbo"
            logging.warning(f"Model name not found in config, using fallback: {self.model_name}")
        
        # Determine the API provider based on configuration
        self.base_url = self.model_config.get("base_url", "https://api.openai.com/v1")
        self.is_groq = "groq" in str(self.base_url).lower()
        
        # Validate the configuration
        self._validate_config()
        
    def _validate_config(self):
        """Validate and log the configuration to help with debugging."""
        # Log the key configuration details
        logging.info(f"Initialized model: {self.model_type.name}")
        logging.info(f"  Model name: {self.model_name}")
        logging.info(f"  Base URL: {self.base_url}")
        logging.info(f"  Using {'Groq' if self.is_groq else 'OpenAI'} API")
        
        # Validate provider-specific configuration
        if self.is_groq and "groq" in str(self.base_url).lower():
            if not os.environ.get("GROQ_API_KEY"):
                logging.warning("GROQ_API_KEY environment variable is not set, will use OPENAI_API_KEY as fallback")
        
    def _get_client_for_request(self):
        """Create a fresh client for this request with the correct API configuration."""
        # Get base URL from config - prefer model-specific config over default
        base_url = self.model_config.get("base_url")
        
        # Handle special cases for Llama/Groq models
        if self.is_groq or (self.model_type == ModelType.LLAMA_3) or ("llama" in str(self.model_name).lower()):
            # Ensure we're using the Groq URL from config, with a fallback
            if not base_url or "groq" not in str(base_url).lower():
                base_url = self.model_config.get("base_url") or "https://api.groq.com/openai/v1"
                logging.info(f"Using base_url from config: {base_url}")
            
            # Use Groq API key if available
            api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
            logging.info(f"Using {'GROQ_API_KEY' if os.environ.get('GROQ_API_KEY') else 'OPENAI_API_KEY as fallback'}")
        else:
            # Standard OpenAI handling
            base_url = base_url or "https://api.openai.com/v1"
            api_key = os.environ.get("OPENAI_API_KEY", "")
        
        # Create client with explicit kwargs
        client_kwargs = {"api_key": api_key}
        
        # Always set the base_url explicitly
        if isinstance(base_url, str) and base_url.endswith("/"):
            base_url = base_url[:-1]  # Remove trailing slash
        client_kwargs["base_url"] = base_url
        
        # Create a fresh client for this request
        logging.info(f"Creating client with explicit base_url: {base_url}")
        client = openai.OpenAI(**client_kwargs)
        
        # Force verification that base_url was correctly set
        actual_base_url = str(getattr(client, "base_url", "unknown"))
        logging.info(f"VERIFICATION - Client created with base_url: {actual_base_url}")
        
        if base_url not in actual_base_url:
            logging.error(f"BASE URL ERROR: Expected {base_url}, got {actual_base_url}")
            
        return client
    
    def run(self, *args, **kwargs):
        """Run the model with the provided arguments, creating a fresh client for each request."""
        messages = kwargs.get("messages", [])
        
        # Always create a fresh client for each request to ensure correct configuration
        client = self._get_client_for_request()
        
        # Calculate tokens for max_tokens limit using appropriate encoding
        try:
            encoding = tiktoken.encoding_for_model(self.model_name)
        except KeyError:
            logging.warning(f"No tokenizer for {self.model_name}, using default")
            encoding = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logging.warning(f"Error getting tokenizer: {str(e)}, using default")
            encoding = tiktoken.get_encoding("cl100k_base")
        
        # Safely calculate prompt tokens
        try:
            prompt = "\n".join(message["content"] for message in messages if message.get("content"))
            prompt_tokens = len(encoding.encode(prompt)) + 15 * len(messages)
        except Exception as e:
            logging.warning(f"Error calculating prompt tokens: {str(e)}")
            prompt_tokens = 0  # Safe fallback
        
        # Calculate max_completion_tokens
        max_completion_tokens = max(0, self.max_tokens - prompt_tokens)
        
        # Prepare parameters for the API call - first from default config
        run_config = {}
        default_config = config_loader.get_default_config()
        for key, value in default_config.items():
            if key not in ["base_url", "is_openai", "name"]:
                run_config[key] = value
        
        # Override with model-specific config
        for key, value in self.model_config.items():
            if key not in ["base_url", "is_openai", "name"]:
                run_config[key] = value
                
        run_config["max_tokens"] = max_completion_tokens
        
        # Log the API call details
        base_url = getattr(client, "base_url", self.base_url)
        logging.info(f"Making API call to {base_url} for model: {self.model_name}")
        
        try:
            # Make the API call
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                **run_config
            )
            
            # Log the response content for visibility
            if hasattr(response, "choices") and response.choices:
                first_choice = response.choices[0]
                if hasattr(first_choice, "message") and hasattr(first_choice.message, "content"):
                    content = first_choice.message.content
                    # Log the first 100 chars of the response with ellipsis if longer
                    preview = content[:100] + ("..." if len(content) > 100 else "")
                    logging.info(f"Response received - preview: {preview}")
                    
            return response
            
        except openai.NotFoundError as e:
            # Handle model not found errors with helpful message
            logging.error(f"Model '{self.model_name}' not found at {base_url}")
            
            # Provide helpful guidance based on the API provider
            if self.is_groq or "groq" in str(base_url).lower():
                logging.error("For Groq API, check https://console.groq.com/docs/models for valid model names")
                logging.error("Valid Groq models include: llama-3.3-70b-versatile, mixtral-8x7b-32768, etc.")
            raise
            
        except Exception as e:
            logging.error(f"API call failed with model {self.model_name}: {str(e)}")
            # More detailed error logging for troubleshooting
            if hasattr(e, "response"):
                logging.error(f"Response status: {getattr(e.response, 'status_code', 'unknown')}")
                logging.error(f"Response headers: {getattr(e.response, 'headers', {})}")
                logging.error(f"Response body: {getattr(e.response, 'text', '')}")
            raise

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

        # Log the current model_type to help with debugging
        logging.info(f"Creating model backend for model_type: {model_type}")
        
        # If no config provided, fetch it from the config loader
        if model_config_dict is None:
            logging.info(f"Loading model config for {model_type.name}")
            model_config_dict = config_loader.get_model_config(model_type.name)
            logging.info(f"Loaded config: {model_config_dict}")

        if not model_config_dict:
            raise ValueError(f"No configuration found for model type: {model_type}")
        
        # Ensure critical config values are preserved and not overridden
        # This is crucial for base_url which is often getting lost
        base_url = model_config_dict.get("base_url")
        is_openai = model_config_dict.get("is_openai", True)
        
        # Log important config values for debugging
        logging.info(f"Model config - is_openai: {is_openai}, base_url: {base_url}")
        
        # Add explicit logging for Groq models
        if base_url and "groq" in str(base_url).lower():
            logging.info(f"GROQ model detected with base_url: {base_url}")
            # Ensure GROQ_API_KEY is available
            if os.environ.get("GROQ_API_KEY"):
                logging.info("GROQ_API_KEY environment variable is set")
            else:
                logging.warning("GROQ_API_KEY environment variable is not set, will use OPENAI_API_KEY as fallback")
        
        # Return StubModel only for the STUB model type
        # For all other models, including Groq models with custom base_url, use OpenAIModel
        if model_type == ModelType.STUB:
            return StubModel()
        else:
            # Create OpenAIModel with the model_config_dict that must contain base_url if specified
            model = OpenAIModel(model_type, model_config_dict)
            
            # Verify critical settings after initialization
            if base_url:
                client_base_url = getattr(model.client, "base_url", None)
                logging.info(f"Verifying base_url after client creation: {client_base_url}")
                
                # If base_url is not correctly set, log a warning
                if not client_base_url or base_url not in str(client_base_url):
                    logging.error(f"base_url mismatch! Config: {base_url}, Client: {client_base_url}")
                    
            return model