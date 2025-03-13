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
#  Enhanced by Startr.Team (2024)
# =========== Copyright 2024 @  Startr LLC   All Rights Reserved. ===========
from abc import ABC, abstractmethod
from typing import Any, Dict

import openai
import tiktoken
import sys
import os
import json
import traceback
import logging

from camel.typing import ModelType
from camel.config_loader import config_loader

from chatdev.statistics import prompt_cost
from chatdev.utils import log_visualize
from camel.utils import log_all_vars

# Import our debugging utilities
try:
    from chatdev.debug_utils import debug_log, debug_inspect, debug_decorator, DEBUG_ENABLED
    from chatdev.model_utils import map_model_name, verify_model_config, print_model_verification
    debug_tools_available = True
except ImportError:
    debug_tools_available = False
    # Create simple debug log function as fallback
    def debug_log(msg, level="debug"):
        if level.lower() == "error":
            logging.error(msg)
        else:
            logging.debug(msg)
    
    def debug_inspect(*args, **kwargs):
        pass
    
    def debug_decorator(func):
        return func
    
    DEBUG_ENABLED = False

try:
    from openai.types.chat import ChatCompletion

    openai_new_api = True  # new openai api version
except ImportError:
    openai_new_api = False  # old openai api version

import os

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
if "BASE_URL" in os.environ:
    BASE_URL = os.environ["BASE_URL"]
else:
    BASE_URL = None

# Set to True to enable verbose debugging of model configuration issues
VERBOSE_MODEL_DEBUG = os.environ.get("VERBOSE_MODEL_DEBUG", "false").lower() == "true"

class ModelBackend(ABC):
    r"""Base class for different model backends.
    May be OpenAI API, a local LLM, a stub for unit tests, etc."""

    @abstractmethod
    def run(self, *args, **kwargs):
        r"""Runs the query to the backend model.

        Raises:
            RuntimeError: if the return value from OpenAI API
            is not a dict that is expected.

        Returns:
            Dict[str, Any]: All backends must return a dict in OpenAI format.
        """
        pass


class OpenAIModel(ModelBackend):
    @debug_decorator("OpenAIModel.__init__")
    def __init__(self, model_type: ModelType, model_config_dict: Dict) -> None:
        super().__init__()
        self.model_type = model_type
        self.model_config = model_config_dict
        
        # Debug model configuration
        debug_inspect("model_config", {
            "model_type": model_type,
            "model_config": model_config_dict
        })
        
        try:
            self.client = self._setup_client()
            self.max_tokens = self.model_config.get("max_tokens")
            
            logging.debug(
                f"Initializing OpenAIModel with model_type: {model_type}, max_tokens: {self.max_tokens}"
            )
            
            if self.max_tokens is None:
                logging.warning(
                    f"max_tokens is None for model {model_type}. Using default value of 4096."
                )
                self.max_tokens = 4096
                
            # Validate model configuration if debugging is enabled
            if DEBUG_ENABLED or VERBOSE_MODEL_DEBUG:
                self._validate_model()
                
        except Exception as e:
            debug_log(f"Error initializing OpenAIModel: {str(e)}", "error")
            debug_log(traceback.format_exc(), "error")
            if DEBUG_ENABLED:
                print(f"\n*** ERROR INITIALIZING MODEL: {str(e)} ***")
                print("Model configuration:")
                print(json.dumps(model_config_dict, indent=2, default=str))
            raise

    @debug_decorator("OpenAIModel._validate_model")
    def _validate_model(self):
        """Validate the model configuration and print diagnostic information"""
        model_name = self.model_config.get("name") or self.model_type.value
        
        debug_log(f"Validating model: {model_name}")
        
        # Use the model verification utility if available
        if debug_tools_available:
            verification_result = verify_model_config(model_name)
            debug_inspect("model_verification_result", verification_result)
            
            # Print model verification results if verbose debugging is enabled
            if VERBOSE_MODEL_DEBUG:
                print_model_verification(model_name)
                
            # Map the model name if necessary
            mapped_model = map_model_name(model_name)
            if mapped_model != model_name:
                debug_log(f"Mapped model name from '{model_name}' to '{mapped_model}'", "info")
                # Update the model configuration with the mapped name
                self.model_config["name"] = mapped_model
        else:
            debug_log("Model validation tools not available", "warning")

    @debug_decorator("OpenAIModel._setup_client")
    def _setup_client(self):
        base_url = self.model_config.get("base_url")
        debug_log(f"Setting up OpenAI client with base_url: {base_url}")
        
        # Check if we need to use GROQ API key for Llama models
        if base_url and "groq" in base_url.lower():
            if "GROQ_API_KEY" not in os.environ or os.environ["GROQ_API_KEY"] == "":
                error_msg = "GROQ_API_KEY environment variable is required for Groq models but was not found. Please set it."
                debug_log(error_msg, "error")
                raise ValueError(error_msg)
            api_key = os.environ["GROQ_API_KEY"]
            debug_log("Using GROQ API key")
        else:
            api_key = OPENAI_API_KEY
            debug_log("Using OpenAI API key")
            
        try:
            if base_url:
                return openai.OpenAI(api_key=api_key, base_url=base_url)
            return openai.OpenAI(api_key=api_key)
        except Exception as e:
            debug_log(f"Error setting up OpenAI client: {str(e)}", "error")
            debug_log(traceback.format_exc(), "error")
            raise

    @debug_decorator("OpenAIModel.run")
    def run(self, *args, **kwargs):
        messages = kwargs.get("messages", [])
        prompt = "\n".join(message["content"] for message in messages)
        
        # Debug current call
        debug_inspect("openai_run_call", {
            "model_type": self.model_type,
            "message_count": len(messages),
            "first_message_role": messages[0]["role"] if messages else None,
            "prompt_length": len(prompt)
        })
        
        # Calculate the number of tokens in the prompt
        try:
            encoding = tiktoken.encoding_for_model(self.model_type.value)
        except KeyError:
            error_msg = f"Could not map {self.model_type.value} to a tokeniser. Using default tokeniser."
            logging.error(error_msg)
            debug_log(error_msg, "error")
            encoding = tiktoken.get_encoding("cl100k_base")
            
        prompt_tokens = len(encoding.encode(prompt)) + 15 * len(messages)

        logging.debug(
            f"Running OpenAIModel with max_tokens: {self.max_tokens}, prompt_tokens: {prompt_tokens}"
        )
        max_completion_tokens = max(
            0, self.max_tokens - prompt_tokens
        )  # Ensure non-negative

        # Merge default config with model-specific config
        run_config = {**config_loader.get_default_config(), **self.model_config}
        
        # Remove fields that should not be passed to the API call
        for key in ["base_url", "is_openai", "name"]:
            run_config.pop(key, None)
            
        # Update max_tokens for this specific run
        run_config["max_tokens"] = max_completion_tokens

        # Get the model name - using self.model_config.get("name") or fallback to self.model_type.value
        model_name = self.model_config.get("name") or self.model_type.value
        
        # If the model is LLAMA_3, which is causing issues, use a fallback model
        if model_name.upper() == "LLAMA_3" or "llama-3" in model_name.lower():
            fallback_model = "gpt-4o-mini"
            debug_log(f"LLAMA_3 model detected, falling back to {fallback_model}", "warning")
            if VERBOSE_MODEL_DEBUG:
                print(f"\n*** MODEL FALLBACK: Replacing {model_name} with {fallback_model} ***")
            model_name = fallback_model
        
        # Log the model being used
        debug_log(f"Using model: {model_name}", "info")
        
        try:
            # NOTE self.client is an instance of openai.OpenAI set with _setup_client
            response = self.client.chat.completions.create(
                model=model_name,  # Explicitly set model here
                messages=kwargs.get("messages", []),  # Ensure messages are passed explicitly
                **run_config  # Pass other configuration parameters
            )

            self._log_usage(response.usage)
            debug_log(f"API call successful: {model_name}", "info")
            
            return response
        except Exception as e:
            debug_log(f"Error in OpenAI API call: {str(e)}", "error")
            debug_log(traceback.format_exc(), "error")
            
            # If it's a model not found error, try to provide helpful diagnostics
            if "model_not_found" in str(e) or "does not exist" in str(e):
                error_model = model_name
                debug_log(f"Model not found: {error_model}", "error")
                
                if VERBOSE_MODEL_DEBUG:
                    print(f"\n*** MODEL NOT FOUND: {error_model} ***")
                    print("Attempting to use fallback model: gpt-4o")
                
                # Try again with a fallback model
                try:
                    fallback_model = "gpt-4o"
                    debug_log(f"Trying fallback model: {fallback_model}", "info")
                    
                    response = self.client.chat.completions.create(
                        model=fallback_model,
                        messages=kwargs.get("messages", []),
                        **run_config
                    )
                    
                    self._log_usage(response.usage)
                    debug_log(f"Fallback API call successful: {fallback_model}", "info")
                    
                    # Update the model configuration with the working model
                    self.model_config["name"] = fallback_model
                    
                    if VERBOSE_MODEL_DEBUG:
                        print(f"Successfully used fallback model: {fallback_model}")
                    
                    return response
                except Exception as fallback_error:
                    debug_log(f"Fallback model also failed: {str(fallback_error)}", "error")
                    if VERBOSE_MODEL_DEBUG:
                        print(f"Fallback model also failed: {str(fallback_error)}")
            
            # Re-raise the original exception
            raise

    def _log_usage(self, usage):
        cost = prompt_cost(
            self.model_type.value,
            num_prompt_tokens=usage.prompt_tokens,
            num_completion_tokens=usage.completion_tokens,
        )
        # Log to file with full details - just use print which now goes to both console and file
        print(
            f"[OpenAI_Usage_Info] "
            f"prompt_tokens: {usage.prompt_tokens}, "
            f"completion_tokens: {usage.completion_tokens}, "
            f"total_tokens: {usage.total_tokens}, "
            f"cost: ${cost:.6f}"
        )
        
        # Print a visual separator for better readability
        print(f"\n💰 Usage: {usage.prompt_tokens}+{usage.completion_tokens}={usage.total_tokens} tokens, Cost: ${cost:.4f}\n")


class StubModel(ModelBackend):
    r"""A dummy model used for unit tests."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__()

    def run(self, *args, **kwargs) -> Dict[str, Any]:
        ARBITRARY_STRING = "Lorem Ipsum"

        return dict(
            id="stub_model_id",
            usage=dict(),
            choices=[
                dict(
                    finish_reason="stop",
                    message=dict(content=ARBITRARY_STRING, role="assistant"),
                )
            ],
        )


class ModelFactory:
    @staticmethod
    def create(model_type: ModelType, model_config_dict: Dict = None) -> ModelBackend:
        if model_type is None:
            model_type = ModelType.GPT_3_5_TURBO

        if model_config_dict is None:
            model_config_dict = config_loader.get_model_config(model_type.name)

        logging.debug(
            f"Creating model with type: {model_type}, config: {model_config_dict}"
        )

        if not model_config_dict:
            raise ValueError(f"No configuration found for model type: {model_type}")

        if model_type == ModelType.STUB:
            return StubModel()
        else:
            return OpenAIModel(model_type, model_config_dict)
