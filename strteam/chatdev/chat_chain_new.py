from pathlib import Path
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from .phase.manager import PhaseManager
from .phase.base import PhaseContext
from .chat_env import ChatEnv, ChatEnvConfig
from .utils import log_visualize
from .typing import TaskType, ModelType

class ChatChain:
    """New implementation of ChatChain using the refactored phase system"""
    
    def __init__(self, **kwargs):
        """Initialize ChatChain with configuration"""
        # Store constructor arguments
        for key, value in kwargs.items():
            setattr(self, key, value)
            
        # Load phase manager with config
        self.phase_manager = PhaseManager(self.config_path)
        self.phase_manager.load_phases()
        
        # Initialize chat environment
        self.chat_env_config = ChatEnvConfig(
            clear_structure=self.config.get('settings', {}).get('clear_structure', True),
            gui_design=self.config.get('settings', {}).get('gui_design', False),
            git_management=self.config.get('settings', {}).get('git_management', False),
            incremental_develop=self.config.get('settings', {}).get('incremental_develop', False),
            background_prompt=self.config.get('background_prompt', ''),
            with_memory=self.config.get('settings', {}).get('with_memory', False)
        )
        self.chat_env = ChatEnv(self.chat_env_config)
        
        # Initialize other attributes
        self.start_time = datetime.now().strftime("%Y%m%d%H%M%S")
        self.project_name = kwargs.get('project_name', 'unnamed_project')
        self.model_type = kwargs.get('model_type', ModelType.GPT_3_5_TURBO)
        
    async def execute(self, task_prompt: str):
        """Execute the full development pipeline"""
        try:
            # Pre-processing
            await self._pre_process(task_prompt)
            
            # Create initial context
            context = PhaseContext(
                inputs={
                    'task_prompt': task_prompt,
                    'model_type': self.model_type
                },
                config=self.config,
                env=self.chat_env.env_dict,
                memory=self.chat_env.memory if self.chat_env_config.with_memory else None
            )
            
            # Execute all phases
            context = await self.phase_manager.execute_pipeline(context)
            
            # Post-processing
            await self._post_process()
            
            return True
            
        except Exception as e:
            logging.error(f"Error in ChatChain execution: {e}")
            return False
            
    async def _pre_process(self, task_prompt: str):
        """Prepare the environment before execution"""
        # Set up project directory
        root_dir = Path(__file__).parent.parent
        warehouse_dir = root_dir / "WareHouse"
        software_dir = warehouse_dir / f"{self.project_name}_{self.start_time}"
        
        # Clean up if needed
        if self.chat_env_config.clear_structure:
            self._cleanup_warehouse(warehouse_dir)
            
        # Create directories
        software_dir.mkdir(parents=True, exist_ok=True)
        self.chat_env.set_directory(str(software_dir))
        
        # Initialize memory if needed
        if self.chat_env_config.with_memory:
            self.chat_env.init_memory()
            
        # Copy configs and set up code base
        self._copy_configs(software_dir)
        if self.chat_env_config.incremental_develop:
            self._setup_codebase(software_dir)
            
        # Save task prompt
        task_file = software_dir / f"{self.project_name}.prompt"
        task_file.write_text(task_prompt)
        
        # Log preprocessing info
        self._log_preprocessing_info()
        
    async def _post_process(self):
        """Finalize the project"""
        # Write metadata
        self.chat_env.write_meta()
        
        # Handle git if enabled
        if self.chat_env_config.git_management:
            self._handle_git()
            
        # Log final info
        self._log_postprocessing_info()
        
        # Cleanup
        if self.chat_env_config.clear_structure:
            self._cleanup_cache()
            
    def _cleanup_warehouse(self, warehouse_dir: Path):
        """Clean up warehouse directory"""
        # Implementation of warehouse cleanup
        pass
        
    def _copy_configs(self, software_dir: Path):
        """Copy configuration files"""
        # Implementation of config copying
        pass
        
    def _setup_codebase(self, software_dir: Path):
        """Set up initial code base for incremental development"""
        # Implementation of code base setup
        pass
        
    def _handle_git(self):
        """Handle git operations"""
        # Implementation of git operations
        pass
        
    def _cleanup_cache(self):
        """Clean up cache files"""
        # Implementation of cache cleanup
        pass
        
    def _log_preprocessing_info(self):
        """Log preprocessing information"""
        info = f"""
        **[Preprocessing]**
        Start Time: {self.start_time}
        Project: {self.project_name}
        Model: {self.model_type}
        Config: {self.config_path}
        """
        log_visualize(info)
        
    def _log_postprocessing_info(self):
        """Log postprocessing information"""
        end_time = datetime.now().strftime("%Y%m%d%H%M%S")
        info = f"""
        **[Postprocessing]**
        End Time: {end_time}
        Project: {self.project_name}
        """
        log_visualize(info)