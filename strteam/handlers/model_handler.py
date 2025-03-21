from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
import importlib
from utils.config_manager import get_config_value, load_config

@dataclass
class ModelRequest:
    prompt: str
    model_id: str = None
    max_tokens: int = None
    temperature: float = None
    params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ModelResponse:
    content: str
    model_id: str
    usage: Dict[str, Any] = field(default_factory=dict)
    raw_response: Any = None

class ModelHandler:
    def __init__(self):
        self.providers = {}
        self._load_providers()
        
    def _load_providers(self):
        """Dynamically load model providers from config."""
        providers_config = load_config("models")
        
        for provider_name, provider_data in providers_config.items():
            if not provider_data.get("enabled", False):
                continue
                
            try:
                # Dynamic import of provider modules
                module_path = provider_data.get("module_path", f"providers.{provider_name}")
                module = importlib.import_module(module_path)
                provider_class = getattr(module, provider_data.get("class_name", f"{provider_name.capitalize()}Provider"))
                
                # Create provider instance
                self.providers[provider_name] = provider_class()
            except (ImportError, AttributeError) as e:
                print(f"Failed to load provider {provider_name}: {e}")
    
    def get_completion(self, request: ModelRequest) -> ModelResponse:
        """Get completion from appropriate provider based on model_id."""
        # Determine provider from model_id if not explicitly provided
        if not request.model_id:
            request.model_id = get_config_value("models", "default_model")
            
        # Find the right provider for this model
        provider_name = self._get_provider_for_model(request.model_id)
        if not provider_name:
            raise ValueError(f"No provider found for model {request.model_id}")
            
        provider = self.providers[provider_name]
        
        # Set default parameters from config if not provided
        if request.max_tokens is None:
            request.max_tokens = get_config_value("models", provider_name, "default_max_tokens", default=1024)
        if request.temperature is None:
            request.temperature = get_config_value("models", provider_name, "default_temperature", default=0.7)
            
        # Call the provider's completion method
        return provider.get_completion(request)
    
    def _get_provider_for_model(self, model_id: str) -> Optional[str]:
        """Determine which provider handles a given model ID."""
        models_config = load_config("models")
        
        for provider_name, provider_data in models_config.items():
            if provider_data.get("enabled", False) and model_id in provider_data.get("models", []):
                return provider_name
                
        # Fallback to checking each provider's supports_model method
        for provider_name, provider in self.providers.items():
            if hasattr(provider, "supports_model") and provider.supports_model(model_id):
                return provider_name
                
        return None

# Singleton instance
model_handler = ModelHandler()
