import os
import json
import requests
import logging
from typing import List, Dict, Optional, Any, Tuple

from .debug_utils import debug_log, debug_inspect, debug_decorator

# Available model types 
OPENAI_MODELS = [
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-16k",
    "gpt-4o",
    "gpt-4-32k",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo"
]

ANTHROPIC_MODELS = [
    "claude-instant-1",
    "claude-2",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307"
]

OLLAMA_MODELS = [
    "llama2",
    "llama2:13b",
    "llama2:70b",
    "gemma:2b",
    "gemma:7b",
    "mistral",
    "mixtral",
    "orca-mini"
]

@debug_decorator
def validate_api_key(api_key: Optional[str] = None, provider: str = "openai") -> Tuple[bool, str]:
    """
    Validate that the API key exists and has basic formatting correctness
    
    Args:
        api_key: API key to validate (defaults to environment variable)
        provider: API provider (openai, anthropic, etc.)
    
    Returns:
        Tuple of (is_valid, message)
    """
    if provider.lower() == "openai":
        key_var = "OPENAI_API_KEY"
        key_prefix = "sk-"
    elif provider.lower() == "anthropic":
        key_var = "ANTHROPIC_API_KEY"
        key_prefix = "sk-ant-"
    else:
        debug_log(f"Unknown provider: {provider}", "warning")
        return False, f"Unknown provider: {provider}"
    
    if api_key is None:
        api_key = os.environ.get(key_var, "")
    
    # Check if key exists
    if not api_key:
        debug_log(f"No API key found for {provider} (checked {key_var})", "error")
        return False, f"No API key found for {provider}. Set the {key_var} environment variable."
    
    # Check basic format
    if not api_key.startswith(key_prefix):
        debug_log(f"API key for {provider} does not start with expected prefix {key_prefix}", "warning")
        return False, f"API key for {provider} has incorrect format (should start with {key_prefix})"
    
    debug_log(f"API key for {provider} passes basic validation")
    return True, "API key looks valid"

@debug_decorator
def is_valid_model(model_name: str, provider: str = "openai") -> bool:
    """
    Check if a model name is in the list of known models for a provider
    
    Args:
        model_name: Name of the model to validate
        provider: Provider to check against
    
    Returns:
        True if model is known, False otherwise
    """
    provider = provider.lower()
    
    if provider == "openai":
        valid_models = OPENAI_MODELS
    elif provider == "anthropic":
        valid_models = ANTHROPIC_MODELS
    elif provider == "ollama":
        valid_models = OLLAMA_MODELS
    else:
        debug_log(f"Unknown provider: {provider}", "warning")
        return False
    
    # Check exact match
    if model_name in valid_models:
        debug_log(f"Model {model_name} is a valid {provider} model")
        return True
    
    # For development models, the name might be changing frequently
    # Log as a warning but don't fail
    debug_log(f"Model {model_name} not in known {provider} models list", "warning")
    return False

@debug_decorator
def verify_openai_model_access(model_name: str, api_key: Optional[str] = None) -> Tuple[bool, str]:
    """
    Verify that the current API key has access to the specified model
    
    Args:
        model_name: Name of the model to verify access to
        api_key: OpenAI API key (defaults to environment variable)
    
    Returns:
        Tuple of (has_access, message)
    """
    if api_key is None:
        api_key = os.environ.get("OPENAI_API_KEY", "")
    
    if not api_key:
        debug_log("No OpenAI API key provided", "error")
        return False, "No OpenAI API key provided"
    
    try:
        debug_log(f"Testing access to model: {model_name}")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # Make a minimal API call to test access
        data = {
            "model": model_name,
            "messages": [{"role": "system", "content": "Hello"}],
            "max_tokens": 5
        }
        
        # Call the OpenAI API
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        debug_inspect(f"openai_model_access_response_{model_name}", {
            "status_code": response.status_code,
            "response": response.text if response.status_code != 200 else "SUCCESS"
        })
        
        if response.status_code == 200:
            debug_log(f"Successfully verified access to model {model_name}")
            return True, "Model access verified"
        elif response.status_code == 404:
            error_data = response.json()
            debug_log(f"Model not found: {error_data.get('error', {}).get('message', 'Unknown error')}", "error")
            return False, f"Model not found: {error_data.get('error', {}).get('message', 'Unknown error')}"
        elif response.status_code == 401:
            debug_log("API key is invalid", "error")
            return False, "API key is invalid"
        else:
            debug_log(f"Error accessing model: {response.text}", "error")
            return False, f"Error accessing model: {response.text}"
    
    except Exception as e:
        debug_log(f"Exception when verifying model access: {str(e)}", "error")
        return False, f"Exception: {str(e)}"

@debug_decorator
def map_model_name(model_name: str) -> str:
    """
    Map a model name to a standard one if needed
    
    Some model names might be custom or aliases - this function 
    maps them to standard names that the API recognizes
    
    Args:
        model_name: Original model name
    
    Returns:
        Mapped model name for API calls
    """
    # Special case mapping for LLAMA_3 model which appears to be causing issues
    if model_name.upper() == "LLAMA_3":
        debug_log("Mapping LLAMA_3 to gpt-4o", "info")
        return "gpt-4o"
    
    model_mapping = {
        # Add known mappings here
        "GPT_3_5_TURBO": "gpt-3.5-turbo",
        "GPT_4": "gpt-4o",
        "GPT_4_TURBO": "gpt-4-turbo",
        "GPT_4O": "gpt-4o",
        "GPT_4O_MINI": "gpt-4o-mini",
        "CLAUDE_INSTANT": "claude-instant-1",
        "CLAUDE_2": "claude-2",
        "CLAUDE_3_OPUS": "claude-3-opus-20240229",
        "CLAUDE_3_SONNET": "claude-3-sonnet-20240229",
        "CLAUDE_3_HAIKU": "claude-3-haiku-20240307"
    }
    
    # Convert model name to lowercase for case-insensitive mapping
    if model_name.upper() in model_mapping:
        mapped_name = model_mapping[model_name.upper()]
        debug_log(f"Mapped model name '{model_name}' to '{mapped_name}'")
        return mapped_name
    
    # Return original if no mapping exists
    return model_name

@debug_decorator
def verify_model_config(model_name: str) -> Dict[str, Any]:
    """
    Verify the model configuration and provide troubleshooting information
    
    Args:
        model_name: Name of the model to verify
    
    Returns:
        Dict containing verification results and troubleshooting info
    """
    result = {
        "original_model": model_name,
        "issues": [],
        "recommendations": []
    }
    
    # Check if we need to map the model name
    mapped_model = map_model_name(model_name)
    result["mapped_model"] = mapped_model
    
    if mapped_model != model_name:
        result["issues"].append(f"Using mapped model name: {mapped_model}")
    
    # Validate the API key
    api_key_valid, api_key_msg = validate_api_key()
    result["api_key_valid"] = api_key_valid
    
    if not api_key_valid:
        result["issues"].append(api_key_msg)
        result["recommendations"].append("Set a valid OPENAI_API_KEY environment variable")
    
    # Check if the model is in our known list
    is_known_model = is_valid_model(mapped_model)
    result["is_known_model"] = is_known_model
    
    if not is_known_model:
        result["issues"].append(f"Model '{mapped_model}' is not in the list of known models")
        result["recommendations"].append(f"Use one of these known models: {', '.join(OPENAI_MODELS)}")
    
    # Verify OpenAI model access if API key is valid
    if api_key_valid:
        has_access, access_msg = verify_openai_model_access(mapped_model)
        result["has_model_access"] = has_access
        
        if not has_access:
            result["issues"].append(access_msg)
            result["recommendations"].append("Ensure your account has access to this model")
            result["recommendations"].append("Try using a different model like gpt-4 or gpt-3.5-turbo")
    
    return result

def print_model_verification(model_name: str):
    """
    Print model verification results in a user-friendly format
    
    Args:
        model_name: Name of the model to verify
    """
    results = verify_model_config(model_name)
    
    print("\n=" * 40)
    print(f"MODEL VERIFICATION: {model_name}")
    print("=" * 40)
    
    print(f"\nOriginal model name: {results['original_model']}")
    if results.get("mapped_model") != results['original_model']:
        print(f"Mapped to: {results['mapped_model']}")
    
    print(f"\nAPI key valid: {'✅' if results.get('api_key_valid', False) else '❌'}")
    print(f"Known model: {'✅' if results.get('is_known_model', False) else '❌'}")
    print(f"Model access: {'✅' if results.get('has_model_access', False) else '❌'}")
    
    if results.get("issues"):
        print("\nISSUES FOUND:")
        for i, issue in enumerate(results["issues"], 1):
            print(f"{i}. {issue}")
    
    if results.get("recommendations"):
        print("\nRECOMMENDATIONS:")
        for i, rec in enumerate(results["recommendations"], 1):
            print(f"{i}. {rec}")
    
    print("\n" + "=" * 40)

if __name__ == "__main__":
    # If run directly, test the model verification with the current environment
    import sys
    model_to_test = sys.argv[1] if len(sys.argv) > 1 else "gpt-3.5-turbo"
    print_model_verification(model_to_test) 