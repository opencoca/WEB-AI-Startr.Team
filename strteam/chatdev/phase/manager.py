import importlib
from typing import Dict, Any, List, Type
import yaml
from pathlib import Path

from .base import Phase, PhaseContext, RecursivePhase
from .validator import ConfigurationValidator

class PhaseManager:
    """Manages loading, validation and execution of phases"""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.phases: Dict[str, Phase] = {}
        self.config = self._load_and_validate_config()
        
    def _load_and_validate_config(self) -> Dict[str, Any]:
        """Load and validate configuration"""
        # Validate config file
        errors = ConfigurationValidator.validate_file(self.config_path)
        if errors:
            raise ValueError(
                "Configuration validation failed:\n" + 
                "\n".join(f"- {e}" for e in errors)
            )
            
        # Load validated config
        with open(self.config_path) as f:
            return yaml.safe_load(f)
        
    def _import_phase_class(self, phase_name: str) -> Type[Phase]:
        """Import a phase class by name"""
        # Convert name to module path (e.g. CodeReview -> code_review)
        module_name = ''.join(['_' + c.lower() if c.isupper() else c 
                             for c in phase_name]).lstrip('_')
                             
        try:
            module = importlib.import_module(f'.{module_name}', package='strteam.chatdev.phase')
            return getattr(module, phase_name)
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Could not load phase class {phase_name}: {e}")
            
    def load_phases(self):
        """Load all phases from configuration"""
        for phase_config in self.config['phases']:
            name = phase_config['name']
            phase_type = phase_config['phaseType']
            
            # Import the phase class
            phase_class = self._import_phase_class(name)
            
            # Create phase instance
            phase = phase_class(name, phase_config)
            
            # For composed phases, recursively load sub-phases
            if isinstance(phase, RecursivePhase):
                for subphase_config in phase_config.get('Composition', []):
                    subphase_name = subphase_config['name']
                    subphase_class = self._import_phase_class(subphase_name)
                    subphase = subphase_class(subphase_name, subphase_config)
                    phase.subphases.append(subphase)
                    
            self.phases[name] = phase
            
    async def execute_pipeline(self, initial_context: PhaseContext) -> PhaseContext:
        """Execute all phases in sequence"""
        context = initial_context
        
        for phase_name in self.config['phase_sequence']:
            if phase_name not in self.phases:
                raise ValueError(f"Phase {phase_name} not found")
                
            phase = self.phases[phase_name]
            context = await phase.execute(context)
            
        return context
        
    def get_phase(self, name: str) -> Phase:
        """Get a loaded phase by name"""
        if name not in self.phases:
            raise ValueError(f"Phase {name} not found")
        return self.phases[name]