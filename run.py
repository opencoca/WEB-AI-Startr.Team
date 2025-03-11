# =========== Copyright 2025 Startr.LLC & CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the GNU Affero General Public License, Version 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.gnu.org/licenses/agpl-3.0.en.html
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Note: Portions of this codebase originating from CAMEL-AI.org are published under the Apache License, Version 2.0.
# Please use version control blame to verify the license of specific code sections.
# =========== Copyright 2025 @ Startr.LLC & CAMEL-AI.org. All Rights Reserved. ===========

import argparse
import logging
import os
import sys
from typing import NoReturn, Tuple, List

from camel.typing import ModelType
from chatdev.chat_chain import ChatChain

# Add support for debug utilities if available
try:
    from chatdev.debug_utils import debug_log, debug_inspect, debug_decorator, DEBUG_ENABLED
    from chatdev.model_utils import map_model_name
    debug_tools_available = True
except ImportError:
    debug_tools_available = False
    DEBUG_ENABLED = False
    
    # Create dummy debug functions to avoid errors
    def debug_log(msg, level="debug"):
        pass
    
    def debug_inspect(*args, **kwargs):
        pass
    
    def debug_decorator(func):
        return func

# Constants
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(ROOT_DIR, "CompanyConfig")
DEFAULT_CONFIG_DIR = os.path.join(CONFIG_DIR, "Default")

CONFIG_FILES = ["ChatChainConfig.json", "PhaseConfig.json", "RoleConfig.json"]

sys.path.append(ROOT_DIR)


def get_model_choices() -> List[str]:
    """
    Get a list of model names from the ModelType enum.

    Returns:
        List[str]: A list of model names as strings.
    """
    return [model.name for model in ModelType]


def check_api_key() -> NoReturn:
    """
    Check if the API keys are set and exit if not.

    Raises:
        SystemExit: If the required API key is not set or is empty.
    """
    if "OPENAI_API_KEY" not in os.environ or os.environ["OPENAI_API_KEY"] == "":
        print("\033[94m")
        print("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        print("You can create a key at https://platform.openai.com/account/api-keys")
        print("\033[0m")
        sys.exit(1)


def get_config(company: str) -> Tuple[str, str, str]:
    """
    Get paths to configuration files for a company.

    This function checks if custom configuration files exist for the given company.
    If custom files are found, it returns their paths. If not, it returns paths to
    default configuration files.

    Args:
        company (str): The name of the company to get configuration files for.
                    Custom configurations are stored in a folder named after the company.

    Returns:
        Tuple[str, str, str]: Paths to three configuration files:
            - Path to the main config file
            - Path to the phase config file
            - Path to the role config file
    """
    config_dir = os.path.join(CONFIG_DIR, company)
    config_paths = []

    for config_file in CONFIG_FILES:
        company_config_path = os.path.join(config_dir, config_file)
        default_config_path = os.path.join(DEFAULT_CONFIG_DIR, config_file)

        if os.path.exists(company_config_path):
            config_paths.append(company_config_path)
        else:
            config_paths.append(default_config_path)

    return tuple(config_paths)


def get_company_configs() -> List[str]:
    """
    Get a list of company names from the CompanyConfig directory.

    Returns:
        List[str]: A list of company names as strings.
    """
    return [
        name
        for name in os.listdir(CONFIG_DIR)
        if os.path.isdir(os.path.join(CONFIG_DIR, name))
    ]


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments for the Startr.Team ChatChain.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Startr.Team ChatChain")

    # Dictionary to hold argument configurations
    args_config = {
        "debug": ("store_true", False, "Enable debug mode"),
        "local": ("store_true", False, "Use local Ollama API instead of OpenAI API"),
        "config": (str, "Default", "CompanyConfig name loading settings (Choices: {})".format(", ".join(get_company_configs()))),
        "org": (str, "DefaultOrganization", "Organization name for software generation"),
        "task": (str, "Develop simple static Website using only html and css.", "Software prompt"),
        "name": (str, "Website", "Software name for generation"),
        "model": (str, "LLAMA_3", "GPT Model (choices: {})".format(", ".join(get_model_choices()))),
        "path": (str, "", "Directory for incremental mode"),
    }

    # Loop through each argument configuration
    for arg, (action_or_type, default, help_text) in args_config.items():
        flag = f"--{arg}"
        short_flag = f"-{arg[0]}"
        if action_or_type == "store_true":
            parser.add_argument(
                short_flag, flag, action=action_or_type, default=default, 
                help=f"{help_text} (default: {default})"
            )
        else:
            parser.add_argument(
                short_flag, flag, type=action_or_type, default=default, 
                help=f"{help_text} (default: {default})"
            )
    
    return parser.parse_args()


def setup_logging(log_filepath, logging_level):
    """
    Set up logging to file AND console.
    
    Args:
        log_filepath (str): Path to the log file.
        logging_level (int): Logging level (e.g., logging.DEBUG, logging.INFO).
    """
    # File log formatter - standard format
    file_log_formatter = logging.Formatter(
        fmt="[%(asctime)s %(levelname)s] %(message)s",
        datefmt="%Y-%d-%m %H:%M:%S",
    )
    
    # Console log formatter - more detailed for better visibility
    console_log_formatter = logging.Formatter(
        fmt="\033[1;36m[%(asctime)s]\033[0m \033[1;33m%(levelname)s\033[0m: %(message)s",
        datefmt="%H:%M:%S",
    )
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging_level)
    
    # Clear any existing handlers to avoid duplication
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create file handler with the given path
    file_handler = logging.FileHandler(log_filepath, encoding="utf-8")
    file_handler.setFormatter(file_log_formatter)
    root_logger.addHandler(file_handler)
    
    # Create console handler for terminal output with more verbose format
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_log_formatter)
    # Make sure console shows INFO level messages (more verbose than file might be)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    # Log to console that we've started
    print("\033[1;32m" + "="*80 + "\033[0m")
    print("\033[1;32m" + " Starting Startr.Team with enhanced logging to console " + "\033[0m")
    print("\033[1;32m" + "="*80 + "\033[0m")


def log_initial_info(chat_chain, config_path, config_phase_path, config_role_path, task):
    """
    Log initial information about the ChatChain run.
    
    Args:
        chat_chain (ChatChain): The ChatChain instance.
        config_path (str): Path to the main config file.
        config_phase_path (str): Path to the phase config file.
        config_role_path (str): Path to the role config file.
        task (str): The task prompt.
    """
    logging.info("")
    logging.info("**[Preprocessing]**")
    logging.info("")
    logging.info(f"**Startr.Team Starts** ({chat_chain.start_time})")
    logging.info("")
    logging.info(f"**Timestamp**: {chat_chain.start_time}")
    logging.info("")
    logging.info(f"**config_path**: {config_path}")
    logging.info("")
    logging.info(f"**config_phase_path**: {config_phase_path}")
    logging.info("")
    logging.info(f"**config_role_path**: {config_role_path}")
    logging.info("")
    logging.info(f"**task_prompt**: {task}")
    logging.info("")
    logging.info(f"**project_name**: {chat_chain.project_name}")
    logging.info("")
    logging.info(f"**Log File**: {chat_chain.log_filepath}")
    logging.info("")
    logging.info("**Startr.Team Config**:")
    logging.info(f"ChatEnvConfig.with_memory: {chat_chain.chat_env_config.with_memory}")


def flush_log_handlers():
    """Flush all log handlers to ensure logs are written to disk."""
    for handler in logging.getLogger().handlers:
        handler.flush()


def execute_chat_chain(chat_chain):
    """
    Execute all steps of the ChatChain.
    
    Args:
        chat_chain (ChatChain): The ChatChain instance.
    """
    try:
        # Pre-processing step
        if debug_tools_available and DEBUG_ENABLED:
            debug_log("Starting pre-processing", "info")
        
        chat_chain.pre_processing()
        flush_log_handlers()
        
        # Team recruitment step
        if debug_tools_available and DEBUG_ENABLED:
            debug_log("Starting team recruitment", "info")
            
        chat_chain.recruit_team()
        flush_log_handlers()
        
        # Chain execution step
        if debug_tools_available and DEBUG_ENABLED:
            debug_log("Starting chain execution", "info")
            
        chat_chain.execute_chain()
        flush_log_handlers()
        
        # Post-processing step
        if debug_tools_available and DEBUG_ENABLED:
            debug_log("Starting post-processing", "info")
            
        chat_chain.post_processing()
        flush_log_handlers()
        
        if debug_tools_available and DEBUG_ENABLED:
            debug_log("Execution completed successfully", "info")
            
    except Exception as e:
        if debug_tools_available and DEBUG_ENABLED:
            debug_log(f"Error in execution: {str(e)}", "error")
            import traceback
            debug_log(traceback.format_exc(), "error")
        logging.error(f"Error during execution: {str(e)}")
        print(f"Error: {str(e)}")
        print("For more detailed debugging, try: python debug_run.py --model-debug")
        raise


def main():
    """
    Main function to run the software using command line arguments.
    """
    args = parse_arguments()
    
    # Check if the API key is set
    try:
        check_api_key()
    except SystemExit:
        return

    # Set up logging level based on debug flag
    logging_level = logging.DEBUG if args.debug else logging.INFO
    
    # Enable debug mode if requested
    if args.debug and debug_tools_available:
        os.environ["STARTR_DEBUG"] = "true"
        debug_log("Debug mode enabled in run.py", "info")
        
        # Log model type information
        debug_log(f"Using model type: {args.model}", "info")
        try:
            model_info = {"model_name": args.model}
            debug_inspect("run_py_model_info", model_info)
            
            # Map model name if needed
            mapped_model = map_model_name(args.model)
            if mapped_model != args.model:
                debug_log(f"Mapped model name from '{args.model}' to '{mapped_model}'", "info")
        except Exception as e:
            debug_log(f"Error during model validation: {e}", "error")
            print(f"Warning: Error validating model: {e}")

    # Get configuration paths
    config_path, config_phase_path, config_role_path = get_config(args.config)

    # Initialize the ChatChain
    chat_chain = ChatChain(
        use_ollama=args.local,
        config_path=config_path,
        config_phase_path=config_phase_path,
        config_role_path=config_role_path,
        task_prompt=args.task,
        project_name=args.name,
        org_name=args.org,
        model_type=ModelType[args.model],
        code_path=args.path,
    )

    # Set up logging
    setup_logging(chat_chain.log_filepath, logging_level)
    
    # Log initial information
    log_initial_info(chat_chain, config_path, config_phase_path, config_role_path, args.task)

    # Execute the ChatChain
    execute_chat_chain(chat_chain)


if __name__ == "__main__":
    main()