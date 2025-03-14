from .base import Phase, PhaseContext
from typing import Dict, Any

class DemandAnalysis(Phase):
    """
    Analyzes the user's requirements and determines the software modality.
    This is typically the first phase in the development process.
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        # Define required inputs/outputs
        self.required_inputs = ['task_prompt']
        self.expected_outputs = ['modality']
        
    async def _process(self, context: PhaseContext) -> PhaseContext:
        """Process the demand analysis phase"""
        
        # Build analysis prompt
        analysis_prompt = """According to the new user's task:
        Task: "{task_prompt}"
        
        We need to determine the most appropriate modality (type) of software to develop.
        Consider factors like:
        - User interaction requirements
        - Data processing needs
        - Visual/UI requirements
        - Performance requirements
        
        Please analyze the requirements and specify the software modality."""
        
        # Execute chat with filled placeholders
        conclusion = await self._chat(
            context,
            analysis_prompt,
            {'task_prompt': context.inputs['task_prompt']}
        )
        
        # Parse modality from conclusion
        if '<INFO>' in conclusion:
            modality = conclusion.split('<INFO>')[-1].lower().strip()
        else:
            modality = conclusion.lower().strip()
            
        # Store result in outputs
        context.outputs['modality'] = modality
        
        # Also store in environment for other phases
        context.env['modality'] = modality
        
        return context