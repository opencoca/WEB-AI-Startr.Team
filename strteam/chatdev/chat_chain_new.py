"""
New Chat Chain for WEB-AI-Startr.Team

This module replaces the old ChatChain with a version that uses the new Phase system
with unified base classes and support for recursion.
"""

import os
import sys
import yaml
import logging
import time
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from ..camel.agents import RolePlaying
from ..camel.configs import ChatGPTConfig
from ..camel.typing import ModelType, TaskType
from ..camel.web_spider import modal_trans
from .chat_env import ChatEnv, ChatEnvConfig
from .statistics import get_info
from .utils import log_visualize, now
from .phase_new import Phase, RecursivePhase
from .phase_factory import PhaseFactory

# Import our config reader
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.config_reader import load_company_config, normalize_boolean


class NewChatChain:
    """Manages the execution flow of a chat-based software development process using the new phase system."""
    
    def __init__(self, **kwargs):
        """Initialize ChatChain with configuration settings."""
        # Set instance variables from kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)
            
        # Default company name if not provided
        self.company_name = getattr(self, 'company_name', 'Default')
        
        # Load configuration files
        self._load_configs()
        
        # Initialize core components
        self.chat_turn_limit_default = 10
        
        # Initialize chat environment
        self.chat_env_config = ChatEnvConfig(
            clear_structure=self.config.get("settings", {}).get("clear_structure", False),
            gui_design=self.config.get("settings", {}).get("gui_design", False),
            git_management=self.config.get("settings", {}).get("git_management", False),
            incremental_develop=self.config.get("settings", {}).get("incremental_develop", False),
            background_prompt=self.config.get("background", ""),
            with_memory=self.config.get("settings", {}).get("with_memory", False),
        )
        self.chat_env = ChatEnv(self.chat_env_config)
        
        # Save original task prompt
        self.task_prompt_raw = self.task_prompt
        self.task_prompt = ""
        
        # Prepare role prompts from agents definition
        self.role_prompts = {
            agent["name"]: agent["prompt"]
            for agent in self.config.get("agents", [])
        }
        
        # Initialize recruits
        self.recruits = [agent["name"] for agent in self.config.get("agents", [])]
        
        # Set up logging
        self.start_time, self.log_filepath = self._setup_logging()
        
        # Initialize phases using the new factory
        self._init_phases()
        
    def _load_configs(self):
        """Load configuration using the new YAML config reader."""
        # Load company configuration
        self.config = load_company_config(self.company_name)
        
        # For backward compatibility, add web_spider and other settings
        if "settings" not in self.config:
            self.config["settings"] = {}
            
        # Use recursive flow if available and no process defined
        if "process" not in self.config:
            try:
                from utils.config_reader import get_recursive_flow_config
                recursive_flow = get_recursive_flow_config()
                
                if "workflow" in recursive_flow and "main_process" in recursive_flow["workflow"]:
                    # Use recursive flow as the configuration
                    self.config["process"] = {
                        "phases": recursive_flow["workflow"]["main_process"].get("phases", [])
                    }
                    
                    # Copy agents from recursive flow
                    if "agents" in recursive_flow and "agents" not in self.config:
                        self.config["agents"] = recursive_flow["agents"]
                        
                    # Copy settings from recursive flow
                    if "settings" in recursive_flow:
                        self.config["settings"].update(recursive_flow.get("settings", {}))
            except Exception as e:
                logging.warning(f"Failed to load recursive flow: {e}")
    
    def _setup_logging(self):
        """Set up logging and return start time and log filepath."""
        start_time = now()
        # First get the log file path without creating any directories
        log_path = self._get_log_filepath(start_time)
        # We'll let run.py setup_logging create the necessary directories
        return start_time, log_path
    
    def _get_log_filepath(self, timestamp):
        """Construct log filepath using project details and timestamp."""
        root_dir = Path(__file__).parent.parent
        log_dir = root_dir / "WareHouse" / f"{self.project_name}_{self.org_name}_{timestamp}"
        # Use a simpler filename: "chat_log.log" inside the project directory
        return str(log_dir / "chat_log.log")
    
    def _init_phases(self):
        """Initialize all phases using the PhaseFactory."""
        self.phases = PhaseFactory.create_phases_from_company_config(
            company_name=self.company_name,
            role_prompts=self.role_prompts,
            model_type=self.model_type,
            log_filepath=self.log_filepath
        )
    
    def recruit_team(self):
        """Recruit all team members specified in config."""
        for employee in self.recruits:
            self.chat_env.recruit(agent_name=employee)
    
    def execute_chain(self):
        """Execute all phases in the process sequence."""
        # Get the phases in the correct order
        phase_sequence = []
        
        if "process" in self.config and "phases" in self.config["process"]:
            for phase_config in self.config["process"]["phases"]:
                phase_name = phase_config["name"]
                if phase_name in self.phases:
                    phase_sequence.append((phase_name, phase_config))
        
        # Execute each phase
        for phase_name, phase_config in phase_sequence:
            max_turns = phase_config.get("max_turns", self.chat_turn_limit_default)
            with_reflection = phase_config.get("reflection", False)
            
            # Execute the phase
            log_visualize(f"Executing phase: {phase_name}")
            self.chat_env = self.phases[phase_name].execute(
                self.chat_env,
                max_turns,
                with_reflection
            )
            log_visualize(f"Completed phase: {phase_name}")
    
    def pre_processing(self):
        """Prepare the environment before execution."""
        # Get directories
        root_dir = Path(__file__).parent.parent
        warehouse_dir = root_dir / "WareHouse"
        software_dir = warehouse_dir / f"{self.project_name}_{self.org_name}_{self.start_time}"
        
        # Clean up existing files if needed
        if self.chat_env.config.clear_structure:
            self._cleanup_warehouse(warehouse_dir)
        
        # Set up software directory - this is where we'll put both code and logs
        os.makedirs(software_dir, exist_ok=True)
        self.chat_env.set_directory(str(software_dir))
        
        # Initialize memory if needed
        if self.chat_env.config.with_memory:
            self.chat_env.init_memory()
        
        # Save configuration YAML
        self._save_config_to_software_dir(software_dir)
        
        # Set up code base if incremental development is enabled
        if self.config.get("settings", {}).get("incremental_develop", False):
            self._setup_code_base(software_dir)
        
        # Save task prompt
        with open(software_dir / f"{self.project_name}.prompt", "w") as f:
            f.write(self.task_prompt_raw)
        
        # Log preprocessing info
        self._log_preprocessing_info()
        
        # Process task prompt
        self._process_task_prompt()
        
        # Print info about the project setup
        print(f"\033[1;32mProject directory: {software_dir}\033[0m")
        print(f"\033[1;32mLog file: {self.log_filepath}\033[0m")
    
    def _cleanup_warehouse(self, warehouse_dir):
        """Remove unnecessary files from warehouse directory."""
        for filename in os.listdir(warehouse_dir):
            file_path = warehouse_dir / filename
            if file_path.is_file() and not filename.endswith((".py", ".log")):
                os.remove(file_path)
    
    def _save_config_to_software_dir(self, software_dir):
        """Save configuration YAML to software directory."""
        # Save the full config
        with open(software_dir / "config.yaml", "w") as f:
            yaml.dump(self.config, f, default_flow_style=False)
    
    def _setup_code_base(self, software_dir):
        """Copy existing code base for incremental development."""
        base_dir = software_dir / "base"
        
        # Copy all files from code_path to base directory
        for root, _, files in os.walk(self.code_path):
            rel_path = os.path.relpath(root, self.code_path)
            target_dir = base_dir / rel_path
            os.makedirs(target_dir, exist_ok=True)
            
            for file in files:
                shutil.copy2(os.path.join(root, file), target_dir / file)
        
        # Load code base into chat environment
        self.chat_env._load_from_hardware(str(base_dir))
    
    def _log_preprocessing_info(self):
        """Log preprocessing information."""
        preprocess_msg = f"""
        **[Preprocessing]**
        **strteam Starts** ({self.start_time})
        **Timestamp**: {self.start_time}
        **Company**: {self.company_name}
        **task_prompt**: {self.task_prompt_raw}
        **project_name**: {self.project_name}
        **Log File**: {self.log_filepath}
        **strteam Config**:
        {self.chat_env.config}
        **ChatGPTConfig**:
        {ChatGPTConfig()}
        """
        # Clean whitespace
        preprocess_msg = "\n".join(line.strip() for line in preprocess_msg.split("\n"))
        log_visualize(preprocess_msg)
    
    def _process_task_prompt(self):
        """Process and enhance task prompt if needed."""
        # Determine if task prompt should be improved
        if self.config.get("settings", {}).get("self_improve", False):
            self.chat_env.env_dict["task_prompt"] = self._improve_task_prompt(self.task_prompt_raw)
        else:
            self.chat_env.env_dict["task_prompt"] = self.task_prompt_raw
        
        # Process for web spider if enabled
        if self.config.get("settings", {}).get("web_spider", False):
            self.chat_env.env_dict["task_description"] = modal_trans(self.task_prompt_raw)
    
    def _improve_task_prompt(self, original_prompt):
        """Improve task prompt using an AI agent."""
        improve_prompt = (
            "I will give you a short description of a software design requirement, "
            "please rewrite it into a detailed prompt that can make large language model know how to make this software better based this prompt, "
            "the prompt should ensure LLMs build a software that can be run correctly, which is the most import part you need to consider. "
            f"remember that the revised prompt should not contain more than 200 words, here is the short description:\"{original_prompt}\". "
            "If the revised prompt is revised_version_of_the_description, "
            "then you should return a message in a format like \"<INFO> revised_version_of_the_description\", do not return messages in other formats."
        )
        
        # Create role-playing session
        role_play = RolePlaying(
            assistant_role_name="Prompt Engineer",
            assistant_role_prompt="You are an professional prompt engineer that can improve user input prompt to make LLM better understand these prompts.",
            user_role_name="User",
            user_role_prompt="You are an user that want to use LLM to build software.",
            task_type=TaskType.STARTR_TEAM,
            task_prompt="Do prompt engineering on user query",
            with_task_specify=False,
            model_type=self.model_type,
        )
        
        # Run the conversation
        _, user_msg = role_play.init_chat(None, None, improve_prompt)
        assistant_response, _ = role_play.step(user_msg, True)
        
        # Extract improved prompt
        improved_prompt = assistant_response.msg.content.split("<INFO>")[-1].lower().strip()
        
        # Log the improvement
        log_visualize(role_play.assistant_agent.role_name, assistant_response.msg.content)
        log_visualize(
            "**[Task Prompt Self Improvement]**\n"
            f"**Original Task Prompt**: {original_prompt}\n"
            f"**Improved Task Prompt**: {improved_prompt}"
        )
        
        return improved_prompt
    
    def post_processing(self):
        """Finalize the project and clean up."""
        # Write metadata
        self.chat_env.write_meta()
        
        # Handle Git operations if enabled
        if self.chat_env_config.git_management:
            self._handle_git_operations()
        
        # Generate and log post-processing info
        self._log_post_processing_info()
        
        # Clean up cache files if needed
        self._cleanup_cache_files()
        
        # Shut down logging and move log file
        self._finalize_logging()
    
    def _handle_git_operations(self):
        """Perform Git operations for version control."""
        log_info = "**[Git Information]**\n\n"
        
        # Increment version
        self.chat_env.codes.version += 1
        version = self.chat_env.codes.version
        directory = self.chat_env.env_dict["directory"]
        
        # Add all files to Git
        os.system(f"cd {directory}; git add .")
        log_info += f"cd {directory}; git add .\n"
        
        # Commit with version number
        os.system(f'cd {directory}; git commit -m "v{version} Final Version"')
        log_info += f'cd {directory}; git commit -m "v{version} Final Version"\n'
        
        # Log Git info
        log_visualize(log_info)
        
        # Log Git history
        import subprocess
        command = f"cd {directory}; git log"
        process = subprocess.run(command, shell=True, text=True, stdout=subprocess.PIPE)
        
        git_log = "**[Git Log]**\n\n"
        git_log += process.stdout if process.returncode == 0 else f"Error executing: {command}"
        log_visualize(git_log)
    
    def _log_post_processing_info(self):
        """Log post-processing information and statistics."""
        post_info = "**[Post Info]**\n\n"
        
        # Calculate duration
        end_time = now()
        time_format = "%Y%m%d%H%M%S"
        start_datetime = datetime.strptime(self.start_time, time_format)
        end_datetime = datetime.strptime(end_time, time_format)
        duration = (end_datetime - start_datetime).total_seconds()
        
        # Get project statistics
        directory = self.chat_env.env_dict["directory"]
        stats = get_info(directory, self.log_filepath)
        post_info += f"Software Info: {stats}\n\n🕑**duration**={duration:.2f}s\n\n"
        
        # Add timestamp info
        post_info += f"strteam Starts ({self.start_time})\n\n"
        post_info += f"strteam Ends ({end_time})\n\n"
        
        log_visualize(post_info)
    
    def _cleanup_cache_files(self):
        """Remove __pycache__ directories if clear_structure is enabled."""
        if not self.chat_env.config.clear_structure:
            return
            
        directory = self.chat_env.env_dict["directory"]
        for root, dirs, _ in os.walk(directory):
            for dir_name in dirs:
                if dir_name == "__pycache__":
                    cache_path = os.path.join(root, dir_name)
                    shutil.rmtree(cache_path, ignore_errors=True)
                    log_visualize(f"{cache_path} Removed.\n\n")
    
    def _finalize_logging(self):
        """Shut down logging and move log file to final location."""
        logging.shutdown()
        time.sleep(1)
        
        # IMPORTANT: No need to move the log file or create duplicate directory
        # Just announce where the log file is
        print(f"\033[1;32mLog file finalized at: {self.log_filepath}\033[0m")