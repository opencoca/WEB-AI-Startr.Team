#!/usr/bin/env python3
"""
Configuration Reader for WEB-AI-Startr.Team

This utility standardizes how configurations are loaded from YAML files,
validates them against the schema, and handles defaults appropriately.
"""

import os
import sys
import yaml
import json
import logging
import jsonschema
from pathlib import Path
from typing import Dict, Any, Optional, Union

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Constants
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
SCHEMA_FILE = CONFIG_DIR / "schema.yaml"
COMPANIES_DIR = CONFIG_DIR / "companies"
DEFAULT_CONFIG = COMPANIES_DIR / "Default.yaml"
RECURSIVE_FLOW = CONFIG_DIR / "recursive_flow.yaml"

# Legacy constants for backward compatibility
LEGACY_CONFIG_DIR = CONFIG_DIR / "CompanyConfig"
LEGACY_YAML_CONFIG_DIR = CONFIG_DIR / "CompanyConfig_yaml"


def load_yaml(file_path: Path) -> Dict:
    """Load a YAML file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Error loading YAML from {file_path}: {e}")
        return {}


def load_json(file_path: Path) -> Dict:
    """Load a JSON file (for backward compatibility)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading JSON from {file_path}: {e}")
        return {}


def save_yaml(data: Dict, file_path: Path) -> bool:
    """Save data as YAML file."""
    try:
        # Create directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        return True
    except Exception as e:
        logging.error(f"Error saving YAML to {file_path}: {e}")
        return False


def load_schema() -> Dict:
    """Load the configuration schema."""
    return load_yaml(SCHEMA_FILE)


def validate_config(config: Dict, schema: Dict) -> bool:
    """Validate configuration against schema."""
    try:
        jsonschema.validate(instance=config, schema=schema)
        return True
    except jsonschema.exceptions.ValidationError as e:
        logging.error(f"Configuration validation error: {e}")
        return False


def normalize_boolean(value: Union[str, bool]) -> bool:
    """Convert various boolean representations to actual booleans."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


def normalize_booleans_in_dict(data: Dict) -> Dict:
    """Recursively normalize boolean values in a dictionary."""
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = normalize_booleans_in_dict(value)
        elif isinstance(value, list):
            result[key] = [
                normalize_booleans_in_dict(item) if isinstance(item, dict) 
                else item for item in value
            ]
        elif key in {"reflection", "need_reflect", "clear_structure", "git_management", 
                     "gui_design", "incremental_develop", "self_improve", "web_spider", 
                     "with_memory"}:
            result[key] = normalize_boolean(value)
        else:
            result[key] = value
    return result


def load_company_config(company_name: str = "Default") -> Dict:
    """Load a company configuration, trying the new format first, then falling back to legacy formats."""
    # Try the new YAML format first
    yaml_path = COMPANIES_DIR / f"{company_name}.yaml"
    if yaml_path.exists():
        config = load_yaml(yaml_path)
        return normalize_booleans_in_dict(config)
    
    # If new format doesn't exist, try legacy YAML format
    legacy_yaml_path = LEGACY_YAML_CONFIG_DIR / company_name / "ChatChainConfig.yaml"
    if legacy_yaml_path.exists():
        config = load_yaml(legacy_yaml_path)
        return normalize_booleans_in_dict(config)
    
    # Fallback to legacy JSON format
    legacy_json_path = LEGACY_CONFIG_DIR / company_name / "ChatChainConfig.json"
    if legacy_json_path.exists():
        config = load_json(legacy_json_path)
        return normalize_booleans_in_dict(config)
    
    # If all else fails, use Default
    logging.warning(f"Company '{company_name}' not found, using Default")
    return load_company_config("Default")


def get_recursive_flow_config() -> Dict:
    """Load the recursive flow configuration."""
    return load_yaml(RECURSIVE_FLOW)


def get_all_available_companies() -> list:
    """Get a list of all available company configurations."""
    companies = []
    
    # Check new format
    if COMPANIES_DIR.exists():
        companies.extend([path.stem for path in COMPANIES_DIR.glob("*.yaml")])
    
    # Check legacy YAML format
    if LEGACY_YAML_CONFIG_DIR.exists():
        companies.extend([path.name for path in LEGACY_YAML_CONFIG_DIR.iterdir() if path.is_dir()])
    
    # Check legacy JSON format
    if LEGACY_CONFIG_DIR.exists():
        companies.extend([path.name for path in LEGACY_CONFIG_DIR.iterdir() if path.is_dir()])
    
    # Remove duplicates and sort
    return sorted(list(set(companies)))


def get_phase_config(company_name: str, phase_name: str) -> Dict:
    """Get configuration for a specific phase from a company."""
    config = load_company_config(company_name)
    
    # Handle new format
    if "process" in config and "phases" in config["process"]:
        for phase in config["process"]["phases"]:
            if phase.get("name") == phase_name:
                return phase
    
    # Handle recursive flow format
    recursive_flow = get_recursive_flow_config()
    if "workflow" in recursive_flow and "main_process" in recursive_flow["workflow"]:
        for phase in recursive_flow["workflow"]["main_process"].get("phases", []):
            if phase.get("name") == phase_name:
                return phase
            # Check sub-phases in recursive phases
            if "recursion" in phase and "sub_phases" in phase["recursion"]:
                for sub_phase in phase["recursion"]["sub_phases"]:
                    if sub_phase.get("name") == phase_name:
                        return sub_phase
    
    # Fallback - return empty dict
    logging.warning(f"Phase '{phase_name}' not found in company '{company_name}'")
    return {}


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Config Reader Utility")
    parser.add_argument("--company", type=str, default="Default", 
                       help="Company configuration to load")
    parser.add_argument("--list", action="store_true", 
                       help="List all available companies")
    parser.add_argument("--validate", action="store_true",
                       help="Validate configuration against schema")
    
    args = parser.parse_args()
    
    if args.list:
        companies = get_all_available_companies()
        print(f"Available companies: {', '.join(companies)}")
        sys.exit(0)
    
    config = load_company_config(args.company)
    print(f"Loaded config for: {args.company}")
    
    if args.validate:
        schema = load_schema()
        is_valid = validate_config(config, schema)
        print(f"Config is valid: {is_valid}")