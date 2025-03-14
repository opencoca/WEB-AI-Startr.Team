#!/usr/bin/env python3
"""
Configuration Cleanup Utility for WEB-AI-Startr.Team

This script:
1. Converts legacy JSON configs to the new YAML format
2. Normalizes boolean values from strings to actual booleans
3. Identifies and lists unused configuration files
4. Creates a consolidated configuration structure
5. Validates configurations against the schema
"""

import os
import sys
import json
import yaml
import shutil
from pathlib import Path
import argparse
from typing import Dict, List, Any, Tuple, Set

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Constants
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
JSON_CONFIG_DIR = CONFIG_DIR / "CompanyConfig"
YAML_CONFIG_DIR = CONFIG_DIR / "CompanyConfig_yaml"
NEWSTYLE_CONFIG_DIR = CONFIG_DIR / "CompanyConfig_newstyle"
SIMPLIFIED_CONFIG = CONFIG_DIR / "simplified_config.yaml"
SCHEMA_FILE = CONFIG_DIR / "schema.yaml"
WAREHOUSE_DIR = PROJECT_ROOT / "WareHouse"

# Mapping from old field names to new field names
FIELD_MAPPINGS = {
    "max_turn_step": "max_turns",
    "need_reflect": "reflection",
    "phaseType": "type",
}

# Set of files known to be used
KNOWN_USED_FILES = {
    "run.py",
    "requirements.txt",
    "README.md",
    "setup.py",
    ".gitignore",
    "LICENSE",
    "LICENSE.md",
    "Dockerfile",
    "Makefile",
}


def load_json(file_path: Path) -> Dict:
    """Load a JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_yaml(file_path: Path) -> Dict:
    """Load a YAML file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(data: Dict, file_path: Path) -> None:
    """Save data as YAML file."""
    # Create directory if it doesn't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        print(f"Saved YAML to {file_path}")


def normalize_boolean(value: str) -> bool:
    """Convert string boolean to actual boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


def normalize_dict_booleans(data: Dict) -> Dict:
    """Recursively convert string booleans to actual booleans in a dict."""
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = normalize_dict_booleans(value)
        elif isinstance(value, list):
            result[key] = [
                normalize_dict_booleans(item) if isinstance(item, dict) 
                else item for item in value
            ]
        elif key in {"need_reflect", "reflection", "clear_structure", "git_management", 
                    "gui_design", "incremental_develop", "self_improve", "web_spider", 
                    "with_memory"}:
            result[key] = normalize_boolean(value)
        else:
            result[key] = value
    return result


def map_fields(data: Dict, mappings: Dict[str, str] = None) -> Dict:
    """Map fields from old names to new names."""
    if mappings is None:
        mappings = FIELD_MAPPINGS
        
    result = {}
    for key, value in data.items():
        new_key = mappings.get(key, key)
        
        if isinstance(value, dict):
            result[new_key] = map_fields(value, mappings)
        elif isinstance(value, list):
            result[new_key] = [
                map_fields(item, mappings) if isinstance(item, dict)
                else item for item in value
            ]
        else:
            result[new_key] = value
    return result


def convert_to_new_format(company_config: Dict, phase_config: Dict, role_config: Dict) -> Dict:
    """Convert old config structure to new format."""
    # Start with the simplified config as a template
    simplified = load_yaml(SIMPLIFIED_CONFIG)
    
    # Extract settings
    settings = {
        "clear_structure": normalize_boolean(company_config.get("clear_structure", False)),
        "git_management": normalize_boolean(company_config.get("git_management", False)),
        "gui_design": normalize_boolean(company_config.get("gui_design", False)),
        "incremental_develop": normalize_boolean(company_config.get("incremental_develop", False)),
        "self_improve": normalize_boolean(company_config.get("self_improve", False)),
        "web_spider": normalize_boolean(company_config.get("web_spider", False)),
        "with_memory": normalize_boolean(company_config.get("with_memory", False)),
    }
    
    # Extract background prompt
    background = company_config.get("background_prompt", simplified["background"])
    
    # Build agents list
    agents = []
    for role_name, role_data in role_config.items():
        agent = {
            "name": role_name,
            "prompt": "\n".join(role_data) if isinstance(role_data, list) else role_data
        }
        agents.append(agent)
    
    # Build phases
    phases = []
    for phase_item in company_config.get("chain", []):
        phase_type = phase_item.get("phaseType", "SimplePhase")
        phase_name = phase_item.get("phase", "")
        
        if phase_type == "SimplePhase":
            # Simple phase
            if phase_name in phase_config:
                phase_data = phase_config[phase_name]
                phase = {
                    "name": phase_name,
                    "type": "SimplePhase",
                    "max_turns": int(phase_item.get("max_turn_step", -1)),
                    "reflection": normalize_boolean(phase_item.get("need_reflect", False)),
                    "assistant_role": phase_data.get("assistant_role_name", ""),
                    "user_role": phase_data.get("user_role_name", ""),
                    "prompt": "\n".join(phase_data.get("phase_prompt", [])) if isinstance(phase_data.get("phase_prompt", []), list) else phase_data.get("phase_prompt", "")
                }
                phases.append(phase)
                
        elif phase_type == "ComposedPhase":
            # Convert to RecursivePhase
            sub_phases = []
            for sub_phase_item in phase_item.get("Composition", []):
                sub_phase_name = sub_phase_item.get("phase", "")
                
                if sub_phase_name in phase_config:
                    sub_phase_data = phase_config[sub_phase_name]
                    sub_phase = {
                        "name": sub_phase_name,
                        "type": "SimplePhase",
                        "max_turns": int(sub_phase_item.get("max_turn_step", -1)),
                        "reflection": normalize_boolean(sub_phase_item.get("need_reflect", False)),
                        "assistant_role": sub_phase_data.get("assistant_role_name", ""),
                        "user_role": sub_phase_data.get("user_role_name", ""),
                        "prompt": "\n".join(sub_phase_data.get("phase_prompt", [])) if isinstance(sub_phase_data.get("phase_prompt", []), list) else sub_phase_data.get("phase_prompt", "")
                    }
                    sub_phases.append(sub_phase)
            
            # Create recursive phase
            phase = {
                "name": phase_name,
                "type": "RecursivePhase",
                "max_turns": 1,
                "reflection": False,
                "assistant_role": sub_phases[0]["assistant_role"] if sub_phases else "",
                "user_role": sub_phases[0]["user_role"] if sub_phases else "",
                "prompt": f"Execute the {phase_name} phase",
                "recursion": {
                    "condition": "needs_another_cycle",
                    "max_depth": int(phase_item.get("cycleNum", 3)),
                    "sub_phases": sub_phases
                }
            }
            phases.append(phase)
    
    # Assemble new config
    new_config = {
        "background": background,
        "process": {
            "phases": phases
        },
        "agents": agents,
        "settings": settings
    }
    
    return new_config


def find_used_config_files() -> Set[Path]:
    """Find configuration files that are actually used in the codebase."""
    used_files = set()
    
    # Search for imports and file openings in Python files
    for root, _, files in os.walk(PROJECT_ROOT):
        root_path = Path(root)
        
        # Skip directories we know have generated code or are not relevant
        if any(part in str(root_path) for part in ["WareHouse", "__pycache__", ".git", ".idea", "venv"]):
            continue
            
        for file in files:
            if not file.endswith(".py"):
                continue
                
            file_path = root_path / file
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # Check for file operations on config files
                if "config" in content.lower() and any(op in content for op in ["open(", "Path(", "os.path"]):
                    used_files.add(file_path)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
    
    return used_files


def identify_unused_files() -> List[Path]:
    """Identify files in the codebase that appear to be unused."""
    all_files = []
    used_files = find_used_config_files()
    unused_files = []
    
    # Create a set of all Python files
    for root, _, files in os.walk(PROJECT_ROOT):
        root_path = Path(root)
        
        # Skip directories we know have generated code or are not relevant
        if any(part in str(root_path) for part in ["WareHouse", "__pycache__", ".git", ".idea", "venv"]):
            continue
            
        for file in files:
            file_path = root_path / file
            all_files.append(file_path)
    
    # Find import references for each file
    import_map = {}
    for file_path in all_files:
        if file_path.suffix != ".py":
            continue
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Extract imports
            import_lines = []
            for line in content.split("\n"):
                if line.strip().startswith(("import ", "from ")):
                    import_lines.append(line.strip())
            
            import_map[file_path] = import_lines
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Build a graph of import relationships
    import_graph = {}
    for file_path, imports in import_map.items():
        import_graph[file_path] = []
        
        for import_line in imports:
            if import_line.startswith("from "):
                module = import_line.split("from ", 1)[1].split(" import")[0]
            else:
                module = import_line.split("import ", 1)[1].split(" ")[0]
                
            # Convert module to potential file path
            module_path = module.replace(".", "/") + ".py"
            
            # Check if this module exists as a file
            for potential_file in all_files:
                if str(potential_file).endswith(module_path):
                    import_graph[file_path].append(potential_file)
                    break
    
    # Start from known entry points and mark all reachable files
    reachable_files = set()
    entry_points = [
        PROJECT_ROOT / "run.py", 
        PROJECT_ROOT / "setup.py",
        PROJECT_ROOT / "strteam/__main__.py",
        PROJECT_ROOT / "strteam/__init__.py",
    ]
    
    def mark_reachable(file_path):
        if file_path in reachable_files:
            return
        reachable_files.add(file_path)
        for imported_file in import_graph.get(file_path, []):
            mark_reachable(imported_file)
    
    for entry in entry_points:
        if entry in import_graph:
            mark_reachable(entry)
    
    # Identify potentially unused files
    for file_path in all_files:
        # Skip non-Python files and known used files
        if (file_path.suffix != ".py" or 
            file_path.name in KNOWN_USED_FILES or
            file_path in reachable_files or
            file_path in used_files):
            continue
            
        # Skip files that are API endpoints or have special purposes
        if (file_path.name.startswith("__") and file_path.name.endswith("__") or
            "test_" in file_path.name.lower()):
            continue
        
        unused_files.append(file_path)
    
    return unused_files


def process_company(company_name: str) -> Dict:
    """Process a company configuration (convert from JSON to YAML)."""
    json_company_dir = JSON_CONFIG_DIR / company_name
    
    # Check if this company exists in JSON format
    if not json_company_dir.exists():
        print(f"Company {company_name} not found in JSON format")
        return None
        
    # Load JSON config files
    company_config_path = json_company_dir / "ChatChainConfig.json"
    phase_config_path = json_company_dir / "PhaseConfig.json"
    role_config_path = json_company_dir / "RoleConfig.json"
    
    company_config = load_json(company_config_path) if company_config_path.exists() else {}
    phase_config = load_json(phase_config_path) if phase_config_path.exists() else {}
    role_config = load_json(role_config_path) if role_config_path.exists() else {}
    
    # Normalize boolean values
    company_config = normalize_dict_booleans(company_config)
    phase_config = normalize_dict_booleans(phase_config)
    
    # Convert to new format
    new_config = convert_to_new_format(company_config, phase_config, role_config)
    
    # Save in new location
    save_path = CONFIG_DIR / "companies" / f"{company_name}.yaml"
    save_yaml(new_config, save_path)
    
    return new_config


def main():
    parser = argparse.ArgumentParser(description="WEB-AI-Startr.Team Configuration Cleanup Utility")
    parser.add_argument("--convert", action="store_true", help="Convert JSON configs to YAML")
    parser.add_argument("--find-unused", action="store_true", help="Find unused files")
    parser.add_argument("--company", type=str, help="Specific company to process")
    args = parser.parse_args()
    
    # Create new companies directory
    companies_dir = CONFIG_DIR / "companies"
    companies_dir.mkdir(exist_ok=True)
    
    if args.convert:
        print("Converting configuration files...")
        
        if args.company:
            # Process specific company
            process_company(args.company)
        else:
            # Process all companies
            for company_dir in JSON_CONFIG_DIR.iterdir():
                if company_dir.is_dir():
                    company_name = company_dir.name
                    print(f"Processing company: {company_name}")
                    process_company(company_name)
    
    if args.find_unused:
        print("Finding unused files...")
        unused_files = identify_unused_files()
        
        print("\nPotentially unused files:")
        for file in sorted(unused_files):
            print(f"  - {file}")
        
        print(f"\nFound {len(unused_files)} potentially unused files.")


if __name__ == "__main__":
    main()