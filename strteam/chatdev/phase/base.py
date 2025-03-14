from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from ..camel.typing import TaskType, ModelType
from ..camel.agents import RolePlaying

@dataclass
class PhaseContext:
    """Context object passed between phases containing inputs/outputs and configuration"""
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict) 
    config: Dict[str, Any] = field(default_factory=dict)
    env: Dict[str, Any] = field(default_factory=dict)
    memory: Optional[Any] = None

class Phase(ABC):
    """Base class for all phases in the system"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.required_inputs = config.get('inputs', [])
        self.expected_outputs = config.get('outputs', [])
        self.assistant_role = config.get('roles', {}).get('assistant')
        self.user_role = config.get('roles', {}).get('user')
        self.model_type = config.get('model_type', ModelType.GPT_3_5_TURBO)
        self.max_retries = config.get('max_retries', 3)
        self.reflection_enabled = config.get('need_reflect', False)
        
    def validate_inputs(self, context: PhaseContext) -> bool:
        """Verify all required inputs are present"""
        return all(inp in context.inputs for inp in self.required_inputs)
        
    def validate_outputs(self, context: PhaseContext) -> bool:
        """Verify all expected outputs were produced"""
        return all(out in context.outputs for out in self.expected_outputs)

    @abstractmethod
    async def _process(self, context: PhaseContext) -> PhaseContext:
        """Main phase processing logic - must be implemented by subclasses"""
        pass
        
    async def execute(self, context: PhaseContext) -> PhaseContext:
        """Execute the phase with validation and error handling"""
        if not self.validate_inputs(context):
            missing = [inp for inp in self.required_inputs if inp not in context.inputs]
            raise ValueError(f"Missing required inputs for {self.name}: {missing}")
            
        context = await self._process(context)
        
        if not self.validate_outputs(context):
            missing = [out for out in self.expected_outputs if out not in context.outputs]
            raise ValueError(f"Missing required outputs for {self.name}: {missing}")
            
        return context

    async def _chat(self, context: PhaseContext, prompt: str, placeholders: Dict[str, Any] = None) -> str:
        """Execute a chat interaction with roles"""
        session = RolePlaying(
            assistant_role_name=self.assistant_role,
            user_role_name=self.user_role,
            task_prompt=context.inputs.get('task_prompt', ''),
            model_type=self.model_type,
            memory=context.memory
        )
        
        # Initialize chat with phase prompt
        _, user_msg = session.init_chat(None, placeholders, prompt)
        
        # Get response
        assistant_response, _ = session.step(user_msg)
        
        # Handle reflection if enabled
        conclusion = assistant_response.msg.content
        if self.reflection_enabled:
            conclusion = await self._reflect(context, session, conclusion)
            
        return conclusion

    async def _reflect(self, context: PhaseContext, session: RolePlaying, conclusion: str) -> str:
        """Run reflection with CEO and Counselor if enabled"""
        # Skip reflection for empty conclusions or if they already contain INFO markers
        if not conclusion or '<INFO>' in conclusion:
            return conclusion
            
        reflection_prompt = f"""Here is a conversation between two roles: {{conversations}}
        Please analyze the conversation and provide a clear conclusion about: {self.name}"""
        
        reflected = await self._chat(
            context,
            reflection_prompt,
            {'conversations': session.chat_history}
        )
        
        return f"<INFO> {reflected}"


class RecursivePhase(Phase):
    """A phase that can contain and execute sub-phases"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.max_depth = config.get('max_depth', 3)
        self.subphases: List[Phase] = []
        
    async def add_subphase(self, phase: Phase):
        """Add a sub-phase to this recursive phase"""
        self.subphases.append(phase)
        
    async def _process(self, context: PhaseContext) -> PhaseContext:
        """Process this phase and all sub-phases recursively"""
        # Process parent phase
        context = await super()._process(context)
        
        # Process all sub-phases
        depth = 0
        while depth < self.max_depth and not self._is_complete(context):
            for subphase in self.subphases:
                context = await subphase.execute(context)
            depth += 1
            
        return context
        
    def _is_complete(self, context: PhaseContext) -> bool:
        """Check if recursive processing should stop"""
        # Default implementation - subclasses should override
        return False
