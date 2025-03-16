# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
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
    def __init__(self, model_type: ModelType, model_config_dict: Dict) -> None:
        """Initialize OpenAI API model backend.
        
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
        
        # Initialize the client immediately with base_url from config
        self.client = self._setup_client()
        
    def _setup_client(self):
        """Set up and return the OpenAI client with proper base URL."""
        # Get base URL from config
        base_url = self.model_config.get("base_url")
        
        # Default to OpenAI API key
        api_key = os.environ.get("OPENAI_API_KEY", "")
        
        # Handle provider-specific API keys
        if base_url:
            # Case-insensitive check for known API providers
            base_url_lower = str(base_url).lower()
            
            # Handle Groq API
            if "groq" in base_url_lower:
                provider_api_key = os.environ.get("GROQ_API_KEY", "")
                if provider_api_key:
                    api_key = provider_api_key
                    logging.info(f"Model {self.model_name}: Using GROQ_API_KEY")
                else:
                    logging.warning(f"Model {self.model_name}: GROQ_API_KEY not found, using OPENAI_API_KEY as fallback")
        
        # Create client with base_url when provided
        client_kwargs = {"api_key": api_key}
        if base_url:
            # Remove trailing slash if present to avoid URL normalization issues
            if base_url.endswith("/"):
                base_url = base_url[:-1]
            client_kwargs["base_url"] = base_url
            
        # Log creation details without exposing API key
        logging.info(f"Creating API client with base_url: {base_url}")
        client = openai.OpenAI(**client_kwargs)
        
        # Log actual base_url to verify it was set correctly
        logging.info(f"Client configured with base_url: {getattr(client, 'base_url', 'default')}")
        
        return client
        
    def _validate_model(self):
        """Validate that the configured model is available at the API endpoint."""
        # Skip validation for stub or test models
        if self.model_type == ModelType.STUB or not self.model_name:
            return
            
        try:
            # Make a minimal API call to test model availability
            self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
                n=1
            )
            logging.info(f"Successfully validated model: {self.model_name}")
        except Exception as e:
            # Log the error but don't fail - we'll handle this during actual usage
            logging.warning(f"Model validation failed for {self.model_name}: {str(e)}")
            
            # Provide helpful message for common error cases
            if "not_found" in str(e).lower() or "model_not_found" in str(e).lower():
                base_url = self.model_config.get("base_url", "default API")
                logging.error(f"The model '{self.model_name}' was not found at {base_url}.")
                
                # Suggest checking provider documentation for valid model names
                if "groq" in str(base_url).lower():
                    logging.error("For Groq API, ensure you're using a valid model name like 'llama3-70b-8192'.")
            
    def run(self, *args, **kwargs):
        """Run the model with the provided arguments."""
        messages = kwargs.get("messages", [])
        
        # Ensure model_name is not None
        if self.model_name is None:
            self.model_name = "gpt-3.5-turbo"
            logging.warning(f"Model name is None, using default model: {self.model_name}")
            
        # Verify base_url is being used
        base_url = self.model_config.get("base_url")
        client_base_url = getattr(self.client, "base_url", "default")
        logging.info(f"Using client with base_url: {client_base_url}")
        
        # If there's a mismatch, recreate the client
        if base_url and client_base_url != base_url and "default" not in client_base_url:
            logging.warning(f"Base URL mismatch. Expected: {base_url}, Got: {client_base_url}. Recreating client...")
            self.client = self._setup_client()
        
        # Calculate tokens for max_tokens limit
        try:
            encoding = tiktoken.encoding_for_model(self.model_name)
        except KeyError:
            logging.warning(f"No tokenizer for {self.model_name}, using default")
            encoding = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            # Handle any other exceptions with tiktoken
            logging.warning(f"Error getting tokenizer: {str(e)}, using default")
            encoding = tiktoken.get_encoding("cl100k_base")
        
        # Safely calculate prompt tokens
        try:
            prompt = "\n".join(message["content"] for message in messages if message.get("content"))
            prompt_tokens = len(encoding.encode(prompt)) + 15 * len(messages)
        except Exception as e:
            logging.warning(f"Error calculating prompt tokens: {str(e)}")
            prompt_tokens = 0  # Safe fallback
        
        # Set safe max_tokens value
        if self.max_tokens is None:
            self.max_tokens = 4096
            logging.warning(f"max_tokens is None, setting to default {self.max_tokens}")
        
        max_completion_tokens = max(0, self.max_tokens - prompt_tokens)
        
        # Prepare parameters for the API call
        run_config = {}
        
        # Get default config but filter out non-API parameters
        default_config = config_loader.get_default_config()
        for key, value in default_config.items():
            if key not in ["base_url", "is_openai", "name"]:
                run_config[key] = value
        
        # Add config parameters, but skip non-API params
        for key, value in self.model_config.items():
            if key not in ["base_url", "is_openai", "name"]:
                run_config[key] = value
                
        run_config["max_tokens"] = max_completion_tokens
        
        try:
            # Log request info for debugging
            logging.info(f"Making API call to model: {self.model_name}")
            logging.info(f"Using client base_url: {getattr(self.client, 'base_url', 'default')}")
            
            # Make the API call with explicit model name from config
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                **run_config
            )
            return response
            
        except openai.NotFoundError as e:
            # Handle model not found errors with helpful message
            base_url = self.model_config.get("base_url", "default API")
            logging.error(f"Model '{self.model_name}' not found at {base_url}")
            
            # Provide helpful guidance based on the API provider
            if "groq" in str(base_url).lower():
                logging.error("For Groq API, check https://console.groq.com/docs/models for valid model names")
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