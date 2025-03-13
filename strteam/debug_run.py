#!/usr/bin/env python3
"""
Debug runner for WEB-AI-strteam

This script enables debugging capabilities for the WEB-AI-strteam system.
It allows you to run the system with extensive logging, breakpoints, and
interactive debugging.

Usage:
    python -m strteam.debug_run --task "build a simple website" --name "TestSite" --debug --interactive
    
    Additional flags:
    --model-debug: Enable verbose model debugging
    --breakpoints: Comma-separated list of breakpoint names
    --log-level: Set logging level (debug, info, warning, error)
"""

import os
import sys
import argparse
import logging
import time
from typing import List, Optional

# Add the debug flag to environment variables
os.environ["STARTR_DEBUG"] = "true"

# Import the debug utilities
from chatdev.debug_utils import (
    enable_debug, 
    enable_interactive, 
    add_breakpoint, 
    dump_debug_state,
    debug_log
)

# Import __main__ functionality
from strteam.__main__ import (
    get_model_choices,
    check_api_key,
    get_config,
    get_company_configs as get_config/CompanyConfigs,
    execute_chat_chain,
    parse_arguments,
    setup_logging,
    log_initial_info
)
from camel.typing import ModelType
from chatdev.chat_chain import ChatChain


def setup_debug_logging(log_level: str = "debug") -> None:
    """
    Set up logging for debugging.
    
    Args:
        log_level: The logging level to use.
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    debug_log(f"Debug logging initialized at {log_level} level")


def parse_debug_arguments() -> argparse.Namespace:
    """
    Parse command line arguments for debug mode.
    
    Returns:
        Parsed arguments
    """
    # First get the standard arguments
    standard_parser = parse_arguments()
    
    # Create a new parser with debug-specific arguments
    parser = argparse.ArgumentParser(description="strteam Debug Runner")
    
    # Standard arguments from run.py
    args_config = {
        "debug": ("store_true", False, "Enable debug mode"),
        "local": ("store_true", False, "Use local Ollama API instead of OpenAI API"),
        "config": (str, "Default", "config/CompanyConfig name loading settings (Choices: {})".format(", ".join(get_config/CompanyConfigs()))),
        "org": (str, "DefaultOrganization", "Organization name for software generation"),
        "task": (str, "Develop simple static Website using only html and css.", "Software prompt"),
        "name": (str, "Website", "Software name for generation"),
        "model": (str, "LLAMA_3", "GPT Model (choices: {})".format(", ".join(get_model_choices()))),
        "path": (str, "", "Directory for incremental mode"),
    }
    
    # Debug-specific arguments
    debug_args_config = {
        "interactive": ("store_true", False, "Enable interactive debugging"),
        "breakpoints": (str, "", "Comma-separated list of breakpoint names"),
        "model-debug": ("store_true", False, "Enable verbose model debug logging"),
        "check-model": ("store_true", False, "Test model connectivity and validation"),
        "log-level": (str, "debug", "Logging level (debug, info, warning, error)"),
    }
    
    # Combine the configurations
    args_config.update(debug_args_config)
    
    # Add all arguments to the parser
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


def main() -> None:
    """Main entry point for debug mode."""
    args = parse_debug_arguments()
    
    # Set up debug logging
    setup_debug_logging(args.log_level)
    
    # Enable interactive debugging if requested
    if args.interactive:
        enable_interactive()
        debug_log("Interactive debugging enabled", "info")
    
    # Enable model debugging if requested
    if args.model_debug:
        os.environ["VERBOSE_MODEL_DEBUG"] = "true"
        debug_log("Verbose model debugging enabled", "info")
    
    # Add breakpoints if specified
    if args.breakpoints:
        breakpoint_names = args.breakpoints.split(',')
        for bp in breakpoint_names:
            add_breakpoint(bp.strip())
            debug_log(f"Added breakpoint: {bp.strip()}", "info")
    
    # Check model connectivity if requested
    if args.check_model:
        from chatdev.model_utils import verify_model_access
        verify_model_access(ModelType[args.model])
        debug_log("Model verification completed", "info")
        return  # Exit after model verification
    
    # Perform API key check
    try:
        check_api_key()
    except SystemExit:
        debug_log("API key check failed", "error")
        return
    
    # Get config paths
    config_path, config_phase_path, config_role_path = get_config(args.config)
    
    # Initialize the chat chain
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
    
    # Set up logging (from run.py)
    stdout, file_handler = setup_logging(chat_chain.log_filepath, logging.DEBUG)
    
    try:
        # Log initial information
        log_initial_info(chat_chain, config_path, config_phase_path, config_role_path, args.task)
        
        # Execute the chat chain
        execute_chat_chain(chat_chain)
        
        debug_log("Task completed successfully!", "info")
    except Exception as e:
        debug_log(f"Error during execution: {str(e)}", "error")
        import traceback
        error_trace = traceback.format_exc()
        logging.error(error_trace)
        print(error_trace)
    finally:
        # Close the log file
        if file_handler:
            file_handler.close()
            logging.getLogger().removeHandler(file_handler)
        
        debug_log("Debug session completed", "info")


if __name__ == "__main__":
    main() 