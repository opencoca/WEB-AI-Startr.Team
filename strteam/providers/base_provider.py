from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..handlers.model_handler import ModelRequest, ModelResponse

class BaseProvider(ABC):
    """Base interface for model providers to implement."""
    
    @abstractmethod
    def get_completion(self, request: ModelRequest) -> ModelResponse:
        """Generate completion for the given request."""
        pass
    
    def supports_model(self, model_id: str) -> bool:
        """Check if this provider supports the given model ID."""
        return False
    
    def get_available_models(self) -> List[str]:
        """Get list of model IDs available through this provider."""
        return []
