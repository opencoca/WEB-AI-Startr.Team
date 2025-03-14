from typing import Dict, Any, List
import jsonschema
import yaml
from pathlib import Path

class ConfigurationValidator:
    """Validates phase configurations against the schema"""
    
    @staticmethod
    def validate_config(config: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """
        Validate configuration against schema
        Returns list of validation errors, empty if valid
        """
        validator = jsonschema.Draft7Validator(schema)
        errors = []
        
        for error in validator.iter_errors(config):
            # Format error path
            path = ' -> '.join(str(p) for p in error.path)
            errors.append(f"{path}: {error.message}")
            
        return errors

    @staticmethod
    def validate_phase_inputs_outputs(config: Dict[str, Any]) -> List[str]:
        """Validate phase input/output connections"""
        errors = []
        phase_sequence = config.get('phase_sequence', [])
        phases = {p['name']: p for p in config.get('phases', [])}
        
        # Track available outputs
        available_outputs = set()
        
        # Check each phase in sequence
        for phase_name in phase_sequence:
            phase = phases.get(phase_name)
            if not phase:
                errors.append(f"Phase {phase_name} not found in phase definitions")
                continue
                
            # Check inputs are available
            required_inputs = phase.get('inputs', [])
            missing_inputs = [inp for inp in required_inputs 
                            if inp not in available_outputs]
            
            if missing_inputs:
                errors.append(
                    f"Phase {phase_name} requires inputs {missing_inputs} but they "
                    "are not produced by any previous phase"
                )
                
            # Add this phase's outputs to available set
            available_outputs.update(phase.get('outputs', []))
            
            # For composed phases, check subphases
            if phase['phaseType'] == 'ComposedPhase':
                for subphase in phase.get('Composition', []):
                    subphase_name = subphase['name']
                    subphase_inputs = subphase.get('inputs', [])
                    missing_subphase_inputs = [
                        inp for inp in subphase_inputs 
                        if inp not in available_outputs
                    ]
                    
                    if missing_subphase_inputs:
                        errors.append(
                            f"Subphase {subphase_name} in {phase_name} requires inputs "
                            f"{missing_subphase_inputs} but they are not available"
                        )
                    
                    available_outputs.update(subphase.get('outputs', []))
                    
        return errors

    @staticmethod
    def validate_file(config_path: Path) -> List[str]:
        """Validate a configuration file"""
        # Load config
        with open(config_path) as f:
            config = yaml.safe_load(f)
            
        # Load schema
        schema_path = config_path.parent / 'schema.yaml'
        with open(schema_path) as f:
            schema = yaml.safe_load(f)
            
        # Run validations
        errors = []
        errors.extend(ConfigurationValidator.validate_config(config, schema))
        errors.extend(ConfigurationValidator.validate_phase_inputs_outputs(config))
        
        return errors