#!/usr/bin/env python3
"""
Model Configuration Debugging Tool for WEB-AI-Startr.Team

This script helps diagnose and debug model configuration issues by:
1. Validating the OpenAI API key
2. Testing access to different models
3. Verifying model configuration from model_config.yaml
4. Attempting to fix common issues

Usage:
    python debug_model.py                # Test default GPT-4 model
    python debug_model.py LLAMA_3        # Test specific model
    python debug_model.py --list         # List all configured models
    python debug_model.py --fix          # Fix common configuration issues
"""

import os
import sys
import yaml
import argparse
import openai
import traceback
from typing import Dict, Any, List, Optional, Tuple

# Configure fallback models for problematic ones
MODEL_FALLBACKS = {
    "llama-3.3-70b-versatile": "GPT-4o",
    "llama-3-70b-versatile": "GPT-4o, 
    "llama-3.1-70b-versatile": "GPT-4o"
}

def print_header(text: str) -> None:
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)

def load_model_config() -> Dict[str, Any]:
    """Load model configuration from YAML file"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_config.yaml")
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"Error loading model configuration: {e}")
        return {"models": {}}

def validate_api_key() -> bool:
    """Validate that OpenAI API key is set and basic format is correct"""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("❌ OpenAI API key not found in environment variables")
        print("   Please set the OPENAI_API_KEY environment variable")
        return False
    
    if not api_key.startswith("sk-"):
        print("⚠️ Warning: OpenAI API key does not start with 'sk-'")
        print("   Your API key may be invalid or in an incorrect format")
    else:
        print("✅ OpenAI API key found and format looks valid")
    
    return True

def test_model_access(model_name: str) -> Tuple[bool, str]:
    """Test if API key has access to the specified model"""
    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    
    try:
        print(f"Testing access to model: {model_name}")
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Hello, are you working?"}],
            max_tokens=10
        )
        return True, "Model access verified"
    except openai.NotFoundError as e:
        return False, f"Model not found: {str(e)}"
    except openai.AuthenticationError as e:
        return False, f"Authentication error: {str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def print_model_info(model_name: str, model_config: Dict[str, Any]) -> None:
    """Print information about a specific model configuration"""
    print(f"\nModel: {model_name}")
    print(f"  Name: {model_config.get('name', 'Not specified')}")
    print(f"  Max tokens: {model_config.get('max_tokens', 'Not specified')}")
    print(f"  Is OpenAI: {model_config.get('is_openai', True)}")
    
    # Check for base_url override
    base_url = model_config.get('base_url', '')
    if base_url and base_url != "https://api.openai.com/v1/":
        print(f"  Base URL: {base_url}")
        
        # Check if base URL is for Groq but no Groq API key
        if "groq" in base_url.lower() and not os.environ.get("GROQ_API_KEY"):
            print("  ❌ Groq API detected but GROQ_API_KEY not set in environment")
    
    # Check for fallback models
    if model_config.get('name') in MODEL_FALLBACKS:
        print(f"  ⚠️ Warning: This model has a known fallback: {MODEL_FALLBACKS[model_config.get('name')]}")

def test_specific_model(model_type: str) -> None:
    """Test a specific model configuration"""
    config = load_model_config()
    models = config.get("models", {})
    
    if model_type not in models:
        print(f"❌ Model type {model_type} not found in model_config.yaml")
        print(f"Available models: {', '.join(models.keys())}")
        return
    
    model_config = models[model_type]
    model_name = model_config.get("name", "")
    
    print_header(f"Testing model: {model_type} ({model_name})")
    print_model_info(model_type, model_config)
    
    if not validate_api_key():
        return
    
    # Test access to model
    success, message = test_model_access(model_name)
    
    if success:
        print(f"✅ Successfully accessed model: {model_name}")
    else:
        print(f"❌ Failed to access model: {model_name}")
        print(f"   Error: {message}")
        
        # Check if there's a fallback model
        if model_name in MODEL_FALLBACKS:
            fallback_model = MODEL_FALLBACKS[model_name]
            print(f"\nTrying fallback model: {fallback_model}")
            fallback_success, fallback_message = test_model_access(fallback_model)
            
            if fallback_success:
                print(f"✅ Successfully accessed fallback model: {fallback_model}")
                print(f"   Recommendation: Update model_config.yaml to use {fallback_model} instead of {model_name}")
            else:
                print(f"❌ Fallback model also failed: {fallback_message}")

def list_all_models() -> None:
    """List all models in configuration"""
    config = load_model_config()
    models = config.get("models", {})
    
    print_header("Available Model Configurations")
    
    for model_type, model_config in models.items():
        print_model_info(model_type, model_config)

def fix_common_issues() -> None:
    """Fix common configuration issues"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_config.yaml")
    config = load_model_config()
    models = config.get("models", {})
    
    print_header("Fixing Common Configuration Issues")
    
    changes_made = False
    
    # Check for LLAMA_3 configuration issues
    if "LLAMA_3" in models:
        llama_config = models["LLAMA_3"]
        llama_name = llama_config.get("name", "")
        
        if llama_name in MODEL_FALLBACKS:
            print(f"⚠️ Fixing LLAMA_3 model configuration (changing {llama_name} to {MODEL_FALLBACKS[llama_name]})")
            
            # Update to use fallback
            llama_config["name"] = MODEL_FALLBACKS[llama_name]
            
            # If using Groq base URL, switch to default OpenAI
            if llama_config.get("base_url", "").startswith("https://api.groq.com"):
                print("⚠️ Removing Groq base URL from LLAMA_3 configuration")
                # Remove base_url to use default OpenAI URL
                llama_config.pop("base_url", None)
            
            changes_made = True
    
    # Write changes if any were made
    if changes_made:
        try:
            with open(config_path, "w") as f:
                yaml.dump(config, f)
            print("✅ Successfully updated model_config.yaml")
        except Exception as e:
            print(f"❌ Failed to update model_config.yaml: {e}")
    else:
        print("✓ No configuration issues detected")

def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Debug model configuration issues")
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("model", nargs="?", help="Model type to test (e.g., LLAMA_3, GPT_4)")
    group.add_argument("--list", action="store_true", help="List all configured models")
    group.add_argument("--fix", action="store_true", help="Fix common configuration issues")
    
    return parser.parse_args()

def main() -> None:
    """Main function"""
    args = parse_args()
    
    try:
        if args.list:
            list_all_models()
        elif args.fix:
            fix_common_issues()
        else:
            # Test specific model or default to GPT_4
            test_specific_model(args.model or "GPT_4")
    except Exception as e:
        print("\n❌ Error occurred during execution:")
        print(str(e))
        print("\nStacktrace:")
        print(traceback.format_exc())

if __name__ == "__main__":
    main() 