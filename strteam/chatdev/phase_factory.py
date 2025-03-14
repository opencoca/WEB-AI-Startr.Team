"""
Phase Factory for WEB-AI-Startr.Team

Creates Phase instances from YAML configuration using the new Phase system.
"""

import importlib
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Callable, Type, Optional

from ..camel.typing import ModelType
from .phase_new import Phase, RecursivePhase, condition_always_false, condition_always_true, condition_task_complete
from .chat_env import ChatEnv

# Import our config reader
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.config_reader import get_phase_config

# Registry of condition functions for recursion
CONDITION_REGISTRY = {
    "always_true": condition_always_true,
    "always_false": condition_always_false,
    "task_complete": condition_task_complete
}

class PhaseFactory:
    """Factory for creating Phase instances from configuration."""
    
    @classmethod
    def create_phase_from_config(
        cls,
        phase_config: Dict[str, Any],
        role_prompts: Dict[str, str],
        model_type: ModelType,
        log_filepath: Optional[str] = None
    ) -> Phase:
        """Create a Phase instance from a configuration dictionary.
        
        Args:
            phase_config: Phase configuration dictionary
            role_prompts: Dictionary of role prompts
            model_type: The model type to use
            log_filepath: Path to log file
            
        Returns:
            Phase: A configured Phase instance
        """
        phase_type = phase_config.get("type", "SimplePhase")
        
        if phase_type == "SimplePhase":
            return cls._create_simple_phase(phase_config, role_prompts, model_type, log_filepath)
        elif phase_type == "RecursivePhase":
            return cls._create_recursive_phase(phase_config, role_prompts, model_type, log_filepath)
        else:
            raise ValueError(f"Unknown phase type: {phase_type}")
    
    @classmethod
    def _create_simple_phase(
        cls,
        config: Dict[str, Any],
        role_prompts: Dict[str, str],
        model_type: ModelType,
        log_filepath: Optional[str] = None
    ) -> Phase:
        """Create a simple Phase instance.
        
        Args:
            config: Phase configuration
            role_prompts: Dictionary of role prompts
            model_type: The model type to use
            log_filepath: Path to log file
            
        Returns:
            Phase: A configured Phase instance
        """
        # Extract necessary parameters
        name = config.get("name", "UnnamedPhase")
        assistant_role = config.get("assistant_role", "")
        user_role = config.get("user_role", "")
        phase_prompt = config.get("prompt", "")
        
        # Create an instance of the specific Phase class if it exists, otherwise use base Phase
        phase_class = cls._get_phase_class(name)
        
        # Prepare kwargs with additional config options
        kwargs = {k: v for k, v in config.items() if k not in ["name", "type", "assistant_role", 
                                                             "user_role", "prompt", "reflection", 
                                                             "max_turns", "recursion"]}
        
        # Create the phase instance
        return phase_class(
            name=name,
            assistant_role_name=assistant_role,
            user_role_name=user_role,
            phase_prompt=phase_prompt,
            role_prompts=role_prompts,
            model_type=model_type,
            log_filepath=log_filepath,
            **kwargs
        )
    
    @classmethod
    def _create_recursive_phase(
        cls,
        config: Dict[str, Any],
        role_prompts: Dict[str, str],
        model_type: ModelType,
        log_filepath: Optional[str] = None
    ) -> RecursivePhase:
        """Create a RecursivePhase instance with sub-phases.
        
        Args:
            config: Phase configuration
            role_prompts: Dictionary of role prompts
            model_type: The model type to use
            log_filepath: Path to log file
            
        Returns:
            RecursivePhase: A configured RecursivePhase instance
        """
        # Extract necessary parameters
        name = config.get("name", "UnnamedPhase")
        assistant_role = config.get("assistant_role", "")
        user_role = config.get("user_role", "")
        phase_prompt = config.get("prompt", "")
        
        # Extract recursion configuration
        recursion_config = config.get("recursion", {})
        max_depth = recursion_config.get("max_depth", 3)
        condition_name = recursion_config.get("condition", "always_false")
        
        # Get the condition function
        condition_func = CONDITION_REGISTRY.get(condition_name, condition_always_false)
        
        # Create sub-phases
        sub_phases = []
        for sub_phase_config in recursion_config.get("sub_phases", []):
            sub_phase = cls.create_phase_from_config(
                sub_phase_config,
                role_prompts,
                model_type,
                log_filepath
            )
            sub_phases.append(sub_phase)
        
        # Prepare kwargs with additional config options
        kwargs = {k: v for k, v in config.items() if k not in ["name", "type", "assistant_role", 
                                                             "user_role", "prompt", "reflection", 
                                                             "max_turns", "recursion"]}
        
        # Create the recursive phase
        return RecursivePhase(
            name=name,
            assistant_role_name=assistant_role,
            user_role_name=user_role,
            phase_prompt=phase_prompt,
            role_prompts=role_prompts,
            sub_phases=sub_phases,
            condition_func=condition_func,
            max_depth=max_depth,
            model_type=model_type,
            log_filepath=log_filepath,
            **kwargs
        )
    
    @classmethod
    def _get_phase_class(cls, phase_name: str) -> Type[Phase]:
        """Get the specific Phase class for a phase name if it exists.
        
        Args:
            phase_name: Name of the phase
            
        Returns:
            Type[Phase]: The phase class to use
        """
        # Try to import specific phase classes first
        try:
            # First check if we have a specialized implementation
            module = importlib.import_module("strteam.chatdev.phases")
            if hasattr(module, phase_name):
                return getattr(module, phase_name)
        except (ImportError, AttributeError):
            pass
            
        # Fall back to base Phase class if no specialized class exists
        return Phase
    
    @classmethod
    def create_phases_from_company_config(
        cls,
        company_name: str,
        role_prompts: Dict[str, str],
        model_type: ModelType,
        log_filepath: Optional[str] = None
    ) -> Dict[str, Phase]:
        """Create all phases defined for a company.
        
        Args:
            company_name: Name of the company configuration
            role_prompts: Dictionary of role prompts
            model_type: The model type to use
            log_filepath: Path to log file
            
        Returns:
            Dict[str, Phase]: Dictionary mapping phase names to Phase instances
        """
        # Import our config reader
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from utils.config_reader import load_company_config
        
        # Load company configuration
        config = load_company_config(company_name)
        
        # Get all phases from the configuration
        phases = {}
        
        # Process phases in the standard format
        if "process" in config and "phases" in config["process"]:
            for phase_config in config["process"]["phases"]:
                phase_name = phase_config.get("name", "")
                if not phase_name:
                    continue
                    
                phase = cls.create_phase_from_config(
                    phase_config,
                    role_prompts,
                    model_type,
                    log_filepath
                )
                phases[phase_name] = phase
                
                # Also add sub-phases from recursive phases
                if phase_config.get("type") == "RecursivePhase" and "recursion" in phase_config:
                    for sub_phase_config in phase_config["recursion"].get("sub_phases", []):
                        sub_phase_name = sub_phase_config.get("name", "")
                        if not sub_phase_name:
                            continue
                            
                        sub_phase = cls.create_phase_from_config(
                            sub_phase_config,
                            role_prompts,
                            model_type,
                            log_filepath
                        )
                        phases[sub_phase_name] = sub_phase
        
        return phases
    
    @classmethod
    def register_condition(cls, name: str, condition_func: Callable[[ChatEnv], bool]) -> None:
        """Register a new condition function for recursive phases.
        
        Args:
            name: Name to identify the condition
            condition_func: Function that evaluates if recursion should continue
        """
        CONDITION_REGISTRY[name] = condition_func