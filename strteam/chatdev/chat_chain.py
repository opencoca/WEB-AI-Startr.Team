import importlib
import json
import logging
import os
import shutil
import time
import yaml  # Added import for YAML parsing
from datetime import datetime
from pathlib import Path

from ..camel.agents import RolePlaying
from ..camel.configs import ChatGPTConfig
from ..camel.typing import TaskType
from ..camel.web_spider import modal_trans
from .chat_env import ChatEnv, ChatEnvConfig
from .statistics import get_info
from .utils import log_visualize, now


def is_true(s):
    """Check if string value represents 'true', case-insensitive."""
    if not isinstance(s, str):
        raise TypeError(f"Expected a string, but got {type(s).__name__}.")
    return s.casefold() == "true"


class ChatChain:
    """Manages the execution flow of a chat-based software development process."""
    
    def __init__(self, **kwargs):
        """Initialize ChatChain with configuration settings."""
        # Set instance variables from kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)
            
        # Load configuration files
        self._load_configs()
        
        # Initialize core components
        self.chain = self.config["chain"]
        self.recruits = self.config["recruits"]
        self.web_spider = self.config["web_spider"]
        self.chat_turn_limit_default = 10
        
        # Initialize chat environment
        self.chat_env_config = ChatEnvConfig(
            clear_structure=is_true(self.config["clear_structure"]),
            gui_design=is_true(self.config["gui_design"]),
            git_management=is_true(self.config["git_management"]),
            incremental_develop=is_true(self.config["incremental_develop"]),
            background_prompt=self.config["background_prompt"],
            with_memory=is_true(self.config["with_memory"]),
        )
        self.chat_env = ChatEnv(self.chat_env_config)
        
        # Save original task prompt
        self.task_prompt_raw = self.task_prompt
        self.task_prompt = ""
        
        # Prepare role prompts
        self.role_prompts = {role: "\n".join(lines) for role, lines in self.config_role.items()}
        
        # Set up logging
        self.start_time, self.log_filepath = self._setup_logging()
        
        # Import phase modules
        self._import_phase_modules()
        
        # Initialize phases
        self._init_phases()
        
    def _load_configs(self):
        """Load configuration files (both YAML and JSON supported)."""
        for attr in dir(self):
            if attr.startswith("config_") and attr.endswith("_path"):
                config_attr = attr.replace("_path", "")
                file_path = getattr(self, attr)
                with open(file_path, "r", encoding="utf8") as file:
                    # Check if the file is YAML or JSON based on extension
                    if file_path.lower().endswith(('.yaml', '.yml')):
                        setattr(self, config_attr, yaml.safe_load(file))
                    else:
                        setattr(self, config_attr, json.load(file))
    
    def _setup_logging(self):
        """Set up logging and return start time and log filepath."""
        start_time = now()
        # First get the log file path without creating any directories
        log_path = self._get_log_filepath(start_time)
        # We'll let run.py setup_logging create the necessary directories
        return start_time, log_path
    
    def _get_log_filepath(self, timestamp):
        """Construct log filepath using project details and timestamp.
        
        IMPORTANT: This method should NOT create directories, only return the path.
        Directories will be created in pre_processing to avoid duplicates.
        """
        root_dir = Path(__file__).parent.parent
        log_dir = root_dir / "WareHouse" / f"{self.project_name}_{self.org_name}_{timestamp}"
        # Use a simpler filename: "chat_log.log" inside the project directory
        return str(log_dir / "chat_log.log")
    
    def _import_phase_modules(self):
        """Import required phase modules."""
        self.phase_module = importlib.import_module("strteam.chatdev.phase")
        self.compose_phase_module = importlib.import_module("strteam.chatdev.composed_phase")
    
    def _init_phases(self):
        """Initialize all phases from configuration."""
        self.phases = {}
        for phase_name, phase_config in self.config_phase.items():
            # Get phase parameters
            assistant_role = phase_config["assistant_role_name"]
            user_role = phase_config["user_role_name"]
            phase_prompt = "\n\n".join(phase_config["phase_prompt"])
            
            # Create phase instance
            phase_class = getattr(self.phase_module, phase_name)
            self.phases[phase_name] = phase_class(
                assistant_role_name=assistant_role,
                user_role_name=user_role,
                phase_prompt=phase_prompt,
                role_prompts=self.role_prompts,
                phase_name=phase_name,
                model_type=self.model_type,
                log_filepath=self.log_filepath,
            )
    
    def recruit_team(self):
        """Recruit all team members specified in config."""
        for employee in self.recruits:
            self.chat_env.recruit(agent_name=employee)
    
    def execute_chain(self):
        """Execute all phases in the chain sequence."""
        for phase_item in self.chain:
            self.execute_step(phase_item)
    
    def execute_step(self, phase_item):
        """Execute a single phase in the chain."""
        phase = phase_item["phase"]
        phase_type = phase_item["phaseType"]
        
        if phase_type == "SimplePhase":
            self._run_simple_phase(phase, phase_item)
        elif phase_type == "ComposedPhase":
            self._run_composed_phase(phase, phase_item)
        else:
            raise ValueError(f"Unknown phase type: {phase_type}")
    
    def _run_simple_phase(self, phase, config):
        """Execute a simple phase."""
        if phase not in self.phases:
            raise ValueError(f"Phase '{phase}' not found")
            
        max_turns = config["max_turn_step"]
        need_reflect = is_true(config["need_reflect"])
        
        # Use default turn limit if not specified
        if max_turns <= 0:
            max_turns = self.chat_turn_limit_default
            
        self.chat_env = self.phases[phase].execute(
            self.chat_env,
            max_turns,
            need_reflect
        )
    
    def _run_composed_phase(self, phase, config):
        """Execute a composed phase."""
        # Get the composed phase class
        phase_class = getattr(self.compose_phase_module, phase, None)
        if not phase_class:
            raise ValueError(f"Composed phase '{phase}' not found")
        
        # Create and execute the composed phase
        phase_instance = phase_class(
            phase_name=phase,
            cycle_num=config["cycleNum"],
            composition=config["Composition"],
            config_phase=self.config_phase,
            config_role=self.config_role,
            model_type=self.model_type,
            log_filepath=self.log_filepath,
        )
        self.chat_env = phase_instance.execute(self.chat_env)
    
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
        
        # Copy config files
        self._copy_configs_to_software_dir(software_dir)
        
        # Set up code base if incremental development is enabled
        if is_true(self.config["incremental_develop"]):
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
    
    def _copy_configs_to_software_dir(self, software_dir):
        """Copy configuration files to software directory."""
        for config_file in [self.config_path, self.config_phase_path, self.config_role_path]:
            shutil.copy(config_file, software_dir)
    
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

        **config_path**: {self.config_path}

        **config_phase_path**: {self.config_phase_path}

        **config_role_path**: {self.config_role_path}

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
        if is_true(self.config["self_improve"]):
            self.chat_env.env_dict["task_prompt"] = self._improve_task_prompt(self.task_prompt_raw)
        else:
            self.chat_env.env_dict["task_prompt"] = self.task_prompt_raw
        
        # Process for web spider if enabled
        if is_true(self.web_spider):
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
        self.chat_env.code.version += 1
        version = self.chat_env.code.version
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