import yaml
import os
from enum import Enum
import logging
from pathlib import Path

class ConfigLoader:
    def __init__(self, config_path="config/model_config.yaml"):
        """Initialize the configuration loader.
        
        Args:
            config_path: Path to the model configuration YAML file
        """
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.config = self.load_config()
        self.ModelType = self.create_model_type_enum()

    def load_config(self):
        """Load model configuration from YAML file with error handling."""
        self.logger.debug(f"Loading config from {self.config_path}")
        
        try:
            with open(self.config_path, "r") as file:
                config = yaml.safe_load(file)
            
            # Basic validation of config structure
            if not isinstance(config, dict):
                self.logger.error(f"Invalid config format: {self.config_path} must contain a dictionary")
                raise ValueError("Invalid config format: root must be a dictionary")
                
            if "models" not in config:
                self.logger.error(f"Invalid config: {self.config_path} must contain a 'models' section")
                raise ValueError("Invalid config: missing 'models' section")
                
            if "default_config" not in config:
                self.logger.error(f"Invalid config: {self.config_path} must contain a 'default_config' section")
                raise ValueError("Invalid config: missing 'default_config' section")
                
            self.logger.debug(f"Successfully loaded config with {len(config['models'])} models")
            
            # Apply environment variable overrides
            self._apply_env_overrides(config)
                
            return config
            
        except FileNotFoundError:
            self.logger.error(f"Config file not found: {self.config_path}")
            # Instead of hardcoded fallbacks, exit with a clear error message
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML config: {str(e)}")
            raise ValueError(f"Invalid YAML in config file: {str(e)}")

    def _apply_env_overrides(self, config):
        """Apply any environment variable overrides to the config."""
        # Override base URLs from environment variables if set
        groq_base_url = os.environ.get("GROQ_BASE_URL")
        if groq_base_url:
            self.logger.info(f"Using GROQ_BASE_URL from environment: {groq_base_url}")
            # Apply to any Groq models that use Llama
            for model_key, model_config in config["models"].items():
                model_name = model_config.get("name", "").lower()
                if "llama" in model_name or model_config.get("base_url", "").lower().startswith("https://api.groq.com"):
                    model_config["base_url"] = groq_base_url
                    self.logger.info(f"Applied GROQ_BASE_URL to model {model_key}")
        
        # Add OpenAI base URL override if present
        openai_base_url = os.environ.get("OPENAI_BASE_URL")
        if openai_base_url:
            self.logger.info(f"Using OPENAI_BASE_URL from environment: {openai_base_url}")
            # Apply to OpenAI models
            for model_key, model_config in config["models"].items():
                if model_config.get("is_openai", False):
                    model_config["base_url"] = openai_base_url
                    self.logger.info(f"Applied OPENAI_BASE_URL to model {model_key}")

    def get_model_config(self, model_name):
        """Get configuration for a specific model with error handling."""
        self.logger.debug(f"Retrieving config for model: {model_name}")
        
        # Handle case where model_name is None by delegating to default selection
        if model_name is None:
            self.logger.warning("Model name is None, using default model")
            return self.get_default_model_config()
        
        # Get model configuration
        model_config = self.config["models"].get(model_name)
        
        if model_config is None:
            self.logger.error(f"No configuration found for model: {model_name}")
            self.logger.debug(f"Available models: {list(self.config['models'].keys())}")
            
            # Try case-insensitive match
            for key in self.config["models"].keys():
                if key.lower() == model_name.lower():
                    model_config = self.config["models"][key]
                    self.logger.warning(f"Found case-insensitive match for {model_name}: {key}")
                    break
                    
            # If still not found, raise error instead of using hardcoded fallback
            if model_config is None:
                raise ValueError(f"No configuration found for model: {model_name}")
        
        # Merge with default config to ensure all required fields exist
        merged_config = self.get_default_config().copy()
        merged_config.update(model_config)
        
        return merged_config
        
    def get_default_model_config(self):
        """Get configuration for the default model."""
        # Look for a designated default model in the config
        default_model_name = self.config.get("default_model")
        if default_model_name:
            try:
                return self.get_model_config(default_model_name)
            except ValueError:
                self.logger.warning(f"Default model {default_model_name} not found")
                
        # Use first model in config instead of hardcoded GPT_3_5_TURBO
        model_keys = list(self.config["models"].keys())
        if not model_keys:
            raise ValueError("No models defined in configuration")
            
        first_model = model_keys[0]
        self.logger.warning(f"No default model specified, using first available: {first_model}")
        return self.get_model_config(first_model)

    def get_all_model_configs(self):
        """Get all model configurations."""
        return self.config["models"]

    def get_default_config(self):
        """Get default configuration parameters."""
        return self.config["default_config"]

    def create_model_type_enum(self):
        """Create an enum from model names."""
        # Create a dictionary of enum values
        enum_dict = {}
        
        # Get models from config
        models = self.config.get("models", {})
        if not models:
            self.logger.error("No models defined for ModelType enum")
            raise ValueError("Configuration must define at least one model")
            
        # Create enum entries from model configs
        for key, value in models.items():
            # Use 'name' field if available, otherwise use key
            enum_dict[key] = value.get("name", key)
                
        return Enum("ModelType", enum_dict)

# Create a single instance of ConfigLoader
config_loader = ConfigLoader()

# Use the dynamically created ModelType enum
ModelType = config_loader.ModelType
