from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class PhaseContext:
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    config: Dict[str, Any]

class Phase:
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.inputs: List[str] = config.get('inputs', [])
        self.outputs: List[str] = config.get('outputs', [])
        self.subphases: List[Phase] = []
    
    async def execute(self, context: PhaseContext) -> PhaseContext:
        raise NotImplementedError("Must implement execute method")
    
    def validate_inputs(self, context: PhaseContext) -> bool:
        return all(inp in context.inputs for inp in self.inputs)

class RecursivePhase(Phase):
    async def execute(self, context: PhaseContext) -> PhaseContext:
        if not self.validate_inputs(context):
            raise ValueError(f"Missing required inputs for phase {self.name}")
        
        result = await self._process(context)
        
        for subphase in self.subphases:
            result = await subphase.execute(result)
        
        return result
    
    async def _process(self, context: PhaseContext) -> PhaseContext:
        """Override this method to implement phase-specific logic"""
        return context
