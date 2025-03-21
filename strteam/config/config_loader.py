"""Configuration loader for the Startr.Team framework.

This module provides centralized access to configuration files with caching
and hierarchical key access.
"""

import os
import yaml
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union, Tuple

class ConfigLoader:
    """Centralized configuration loader that provides access to YAML config files."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """Initialize with optional custom config directory path.
        
        Args:
            config_dir: Path to configuration directory. If None, uses default.
        """
        if config_dir is None:
            # Default to config directory in the project structure
            self.config_dir = os.path.dirname(os.path.abspath(__file__))
        else:
            self.config_dir = config_dir
    
    @lru_cache(maxsize=32)
    def _load_yaml(self, filepath: str) -> Dict[str, Any]:
        """Load and parse a YAML file with caching.
        
        Args:
            filepath: Full path to the YAML file
            
        Returns:
            Parsed YAML content as dictionary
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file) or {}
        except FileNotFoundError:
            print(f"Warning: Config file {filepath} not found")
            return {}
        except yaml.YAMLError as e:
            print(f"Error parsing YAML in {filepath}: {e}")
            return {}
    
    def load_config(self, config_name: str) -> Dict[str, Any]:
        """Load a configuration file by name.
        
        Args:
            config_name: Name of the configuration file (with or without .yaml extension)
            
        Returns:
            Configuration as a dictionary
        """
        if not config_name.endswith('.yaml'):
            config_name = f"{config_name}.yaml"
            
        config_path = os.path.join(self.config_dir, config_name)
        return self._load_yaml(config_path)
    
    def get_value(self, config_name: str, *keys: Union[str, int, List, Tuple], default: Any = None) -> Any:
        """Get a nested value from configuration using key path.
        
        Args:
            config_name: Name of the configuration file
            *keys: Sequence of keys/indices to navigate the config hierarchy
            default: Value to return if path not found
            
        Returns:
            The value at the specified path or the default
        """
        config = self.load_config(config_name)
        current = config
        
        for key in keys:
            # Handle different container types
            if isinstance(current, dict):
                if isinstance(key, (str, int)) and key in current:
                    current = current[key]
                else:
                    return default
            elif isinstance(current, list):
                if isinstance(key, int) and 0 <= key < len(current):
                    current = current[key]
                else:
                    # If key is a string, try to find a dict with that key in the list
                    if isinstance(key, str):
                        found = False
                        for item in current:
                            if isinstance(item, dict) and key in item:
                                current = item[key]
                                found = True
                                break
                        if not found:
                            return default
                    else:
                        return default
            else:
                # Current is not a container we can navigate
                return default
                
        return current

# Create a singleton instance
config_loader = ConfigLoader()
