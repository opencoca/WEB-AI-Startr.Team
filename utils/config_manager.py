import os
import yaml
from functools import lru_cache
from typing import Any, Dict

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")

@lru_cache(maxsize=32)
def load_config(config_name: str) -> Dict[str, Any]:
    """Load configuration from yaml file with caching."""
    config_path = os.path.join(CONFIG_DIR, f"{config_name}.yaml")
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

def get_config_value(config_name: str, *keys, default=None):
    """Get a nested configuration value using a sequence of keys."""
    config = load_config(config_name)
    current = config
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current
