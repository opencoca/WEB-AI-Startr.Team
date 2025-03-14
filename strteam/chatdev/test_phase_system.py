import asyncio
from pathlib import Path
from typing import Dict, Any

from .chat_chain_new import ChatChain
from .phase.base import PhaseContext
from .phase.manager import PhaseManager

async def test_single_phase(phase_name: str, inputs: Dict[str, Any]):
    """Test a single phase in isolation"""
    config_path = Path(__file__).parent.parent / 'config' / 'phase_config.yaml'
    
    # Initialize phase manager
    manager = PhaseManager(str(config_path))
    manager.load_phases()
    
    # Create test context
    context = PhaseContext(inputs=inputs)
    
    # Execute phase
    phase = manager.get_phase(phase_name)
    result = await phase.execute(context)
    
    return result.outputs

async def test_full_pipeline(task_prompt: str):
    """Test the full development pipeline"""
    config_path = Path(__file__).parent.parent / 'config' / 'phase_config.yaml'
    
    # Initialize chat chain
    chain = ChatChain(
        config_path=str(config_path),
        project_name='test_project'
    )
    
    # Execute pipeline
    success = await chain.execute(task_prompt)
    
    return success

async def main():
    # Test individual phase
    demand_result = await test_single_phase(
        'DemandAnalysis',
        {'task_prompt': 'Create a simple calculator application'}
    )
    print(f"DemandAnalysis output: {demand_result}")
    
    # Test full pipeline
    pipeline_result = await test_full_pipeline(
        'Create a simple calculator application'
    )
    print(f"Pipeline execution: {'Success' if pipeline_result else 'Failed'}")

if __name__ == '__main__':
    asyncio.run(main())