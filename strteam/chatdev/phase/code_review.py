from .base import RecursivePhase, Phase, PhaseContext
from typing import Dict, Any

class CodeReviewComment(Phase):
    """Phase for generating code review comments"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.required_inputs = ['code', 'language', 'task_prompt']
        self.expected_outputs = ['review_comments']
        
    async def _process(self, context: PhaseContext) -> PhaseContext:
        review_prompt = """According to the requirements and code:
        Task: "{task_prompt}"
        Language: "{language}"
        Code:
        {code}
        
        Please review the code and provide specific comments on:
        1. Code structure and organization
        2. Potential bugs or issues
        3. Performance concerns
        4. Missing features from requirements
        5. Code style and best practices
        
        Format your response with clear section headers."""
        
        comments = await self._chat(
            context,
            review_prompt,
            {
                'task_prompt': context.inputs['task_prompt'],
                'language': context.inputs['language'],
                'code': context.inputs['code']
            }
        )
        
        context.outputs['review_comments'] = comments
        context.env['review_comments'] = comments
        return context

class CodeReviewModification(Phase):
    """Phase for modifying code based on review comments"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.required_inputs = ['code', 'review_comments']
        self.expected_outputs = ['modified_code']
        
    async def _process(self, context: PhaseContext) -> PhaseContext:
        modify_prompt = """Given the code and review comments:
        Code:
        {code}
        
        Review Comments:
        {review_comments}
        
        Please modify the code to address the review comments.
        Return the complete modified code with clear explanations of changes."""
        
        modified = await self._chat(
            context,
            modify_prompt,
            {
                'code': context.inputs['code'],
                'review_comments': context.inputs['review_comments']
            }
        )
        
        context.outputs['modified_code'] = modified
        context.env['code'] = modified
        return context

class CodeReview(RecursivePhase):
    """Recursive phase that manages the code review process"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.required_inputs = ['code', 'language', 'task_prompt']
        self.expected_outputs = ['final_code']
        
        # Create and add sub-phases
        review_phase = CodeReviewComment("review", config)
        modify_phase = CodeReviewModification("modify", config)
        
        self.subphases = [review_phase, modify_phase]
        
    async def _process(self, context: PhaseContext) -> PhaseContext:
        # The parent phase can do any pre-processing here before sub-phases run
        return context
        
    def _is_complete(self, context: PhaseContext) -> bool:
        """Check if review cycles should stop"""
        if 'modified_code' not in context.outputs:
            return False
            
        # Check if review indicates no more changes needed
        review_comments = context.env.get('review_comments', '')
        return any(marker in review_comments.lower() for marker in [
            '<info> finished',
            'no further changes needed',
            'code looks good'
        ])