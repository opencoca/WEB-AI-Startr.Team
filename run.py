# =========== Copyright 2023 - 2024 Startr.LLC & CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 - 2024 @ Startr.LLC & CAMEL-AI.org. All Rights Reserved. ===========


import argparse
import logging
import os
import sys
from typing import NoReturn, Tuple, List

from camel.typing import ModelType  # imports our models from model_config.yaml
from chatdev.chat_chain import ChatChain

# Add support for debug utilities if available
try:
    from chatdev.debug_utils import debug_log, debug_inspect, debug_decorator, DEBUG_ENABLED
    from chatdev.model_utils import map_model_name, verify_model_config
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

try:
    pass

    openai_new_api = True  # new openai api version
except ImportError:
    openai_new_api = False  # old openai api version
    print(
        "Warning: Your OpenAI version is outdated. \n "
        "Please update as specified in requirement.txt. \n "
        "The old API interface is no longer supported."
    )
    # TODO: This API version check should be improved. Consider using semantic versioning 
    # to check package versions instead of try/except on imports. Also, add clear 
    # instructions on how to update the package with specific commands.


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
        # Change terminal text color to blue using ANSI escape codes
        print("\033[94m")
        print("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        print("You can create a key at https://platform.openai.com/account/api-keys")
        # Reset terminal text color using ANSI escape codes
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

    Note:
        Configuration files are in JSON format.

        If a custom file is missing, the function will use the default file instead.
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


def get_CompanyConfigs() -> List[str]:
    """
    Get a list of company names from the CompanyConfig directory.

    Returns:
        List[str]: A list of company names as strings.
    """
    # return os.listdir(CONFIG_DIR) note we should only return directories
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
    # fmt: off
    args_config = {
        "debug": ("store_true", False, "Enable debug mode"),
        "local": ("store_true", False, "Use local Ollama API instead of OpenAI API"),
        "config": (str,   "Default"  ,"CompanyConfig name loading settings(Choices: {})".format(", ".join(get_CompanyConfigs())),),
        "org": ( str,"DefaultOrganization",  "Organization name for software generation",),
        "task": (str, "Develop simple static Website using only html and css.", "Software prompt"),
        "name": (str, "Website", "Software name for generation"),
        "model": ( str, "LLAMA_3", "GPT Model (choices: {})".format(", ".join(get_model_choices())),),
        "path": (str, "", "Directory for incremental mode"),
    }
    # fmt: on

    # Loop through each argument configuration
    for arg, (action_or_type, default, help_text) in args_config.items():
        flag = f"--{arg}"  # Infer long flag based on key name
        short_flag = f"-{arg[0]}"  # Infer short flag based on the first character of the key name
        if action_or_type == "store_true":
            parser.add_argument(
                short_flag, flag, action=action_or_type, default=default, 
                help=f"{help_text} (default: {default})"
            )
        else:
            # Add the argument to the parser with the given configuration
            parser.add_argument(
                short_flag, flag, type=action_or_type, default=default, 
                help=f"{help_text} (default: {default})"
            )
    
    return parser.parse_args()


def main():
    """
    Main function to run the software using command line arguments.
    """
    
    args = parse_arguments()
    # Check if the API key is set, exit if not
    try:
        check_api_key()
    except SystemExit:
        # Exit if the API key is not set
        return

    if args.debug:
        # Enable debug mode if the debug flag is set
        logging_level = logging.DEBUG
        if debug_tools_available:
            # Enable debug utilities if available
            os.environ["STARTR_DEBUG"] = "true"
            debug_log("Debug mode enabled in run.py", "info")
    else:
        logging_level = logging.INFO

    config_path, config_phase_path, config_role_path = get_config(args.config)

    # Log model type information if debug is enabled
    if debug_tools_available and args.debug:
        debug_log(f"Using model type: {args.model}", "info")
        try:
            # Attempt to validate the model configuration
            model_info = {"model_name": args.model}
            debug_inspect("run_py_model_info", model_info)
            
            # Map model name if needed
            mapped_model = map_model_name(args.model)
            if mapped_model != args.model:
                debug_log(f"Mapped model name from '{args.model}' to '{mapped_model}'", "info")
                # Check if we need to create a ModelType.MAPPED_MODEL
                if mapped_model != args.model and hasattr(ModelType, args.model):
                    debug_log(f"Model type {args.model} exists, using as-is", "info")
                else:
                    debug_log(f"Model type {args.model} not found, checking alternatives", "warning")
        except Exception as e:
            debug_log(f"Error during model validation: {e}", "error")
            print(f"Warning: Error validating model: {e}")

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

    logging.basicConfig(
        filename=chat_chain.log_filepath,
        level=logging_level,
        format="[%(asctime)s %(levelname)s] %(message)s",
        datefmt="%Y-%d-%m %H:%M:%S",
        encoding="utf-8",
    )
    
    # Write initial log information to ensure the file is created and populated
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
    logging.info(f"**task_prompt**: {args.task}")
    logging.info("")
    logging.info(f"**project_name**: {args.name}")
    logging.info("")
    logging.info(f"**Log File**: {chat_chain.log_filepath}")
    logging.info("")
    logging.info("**Startr.Team Config**:")
    logging.info(f"ChatEnvConfig.with_memory: {chat_chain.chat_env_config.with_memory}")

    try:
        # If debug tools are available, log each step
        if debug_tools_available and args.debug:
            debug_log("Starting pre-processing", "info")
        
        chat_chain.pre_processing()
        
        if debug_tools_available and args.debug:
            debug_log("Starting team recruitment", "info")
            
        chat_chain.recruit_team()
        
        if debug_tools_available and args.debug:
            debug_log("Starting chain execution", "info")
            
        chat_chain.execute_chain()
        
        if debug_tools_available and args.debug:
            debug_log("Starting post-processing", "info")
            
        chat_chain.post_processing()
        
        if debug_tools_available and args.debug:
            debug_log("Execution completed successfully", "info")
            
    except Exception as e:
        if debug_tools_available and args.debug:
            debug_log(f"Error in execution: {str(e)}", "error")
            import traceback
            debug_log(traceback.format_exc(), "error")
        logging.error(f"Error during execution: {str(e)}")
        print(f"Error: {str(e)}")
        print("For more detailed debugging, try: python debug_run.py --model-debug")
        raise


if __name__ == "__main__":
    main()
