#!/usr/bin/env python3
"""
Debug runner for WEB-AI-Startr.Team

This script enables debugging capabilities for the WEB-AI-Startr.Team system.
It allows you to run the system with extensive logging, breakpoints, and
interactive debugging.

Usage:
    python debug_run.py --task "build a simple website" --name "TestSite" --debug --interactive
    
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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chatdev.debug_utils import (
    enable_debug, 
    enable_interactive, 
    add_breakpoint, 
    dump_debug_state,
    debug_log
)

# Import run.py functionality
from run import get_model_choices, check_api_key, get_config, get_CompanyConfigs, parse_arguments
from camel.typing import ModelType
from chatdev.chat_chain import ChatChain

# Import model utilities for verification
from chatdev.model_utils import print_model_verification


def setup_logging(log_level: str = "debug") -> None:
    """Set up logging with the specified level"""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    
    logging.basicConfig(
        filename=f"debug_{int(time.time())}.log",
        level=numeric_level,
        format="[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Also output to console
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(numeric_level)
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s")
    console.setFormatter(formatter)
    logging.getLogger("").addHandler(console)


def parse_debug_arguments() -> argparse.Namespace:
    """Parse command-line arguments with additional debugging options"""
    parser = argparse.ArgumentParser(description="WEB-AI-Startr.Team Debug Runner")
    
    # Standard arguments from run.py
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("-l", "--local", action="store_true", help="Use local Ollama API instead of OpenAI API")
    parser.add_argument("-c", "--config", type=str, default="Default", 
                        help=f"CompanyConfig name loading settings (Choices: {', '.join(get_CompanyConfigs())})")
    parser.add_argument("-o", "--org", type=str, default="DefaultOrganization", 
                        help="Organization name for software generation")
    parser.add_argument("-t", "--task", type=str, 
                        default="Develop simple static Website using only html and css.", 
                        help="Software prompt")
    parser.add_argument("-n", "--name", type=str, default="Website", help="Software name for generation")
    parser.add_argument("-m", "--model", type=str, default="GPT_4", 
                        help=f"GPT Model (choices: {', '.join(get_model_choices())})")
    parser.add_argument("-p", "--path", type=str, default="", help="Directory for incremental mode")
    
    # Additional debugging arguments
    parser.add_argument("--interactive", action="store_true", help="Enable interactive debugging with pdb")
    parser.add_argument("--model-debug", action="store_true", help="Enable verbose model debugging")
    parser.add_argument("--breakpoints", type=str, default="", 
                        help="Comma-separated list of breakpoint names")
    parser.add_argument("--log-level", type=str, default="debug", 
                        choices=["debug", "info", "warning", "error", "critical"],
                        help="Set logging level")
    parser.add_argument("--check-model", action="store_true", 
                        help="Only check model configuration and exit")
    parser.add_argument("--pause-before-start", action="store_true",
                        help="Pause for debugging before starting the process")
    
    return parser.parse_args()


def main() -> None:
    """Main entry point for debug runner"""
    # Parse arguments
    args = parse_debug_arguments()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Enable debugging modes
    enable_debug()
    if args.interactive:
        enable_interactive()
        os.environ["STARTR_INTERACTIVE"] = "true"
    
    # Set verbose model debugging if requested
    if args.model_debug:
        os.environ["VERBOSE_MODEL_DEBUG"] = "true"
    
    # Set breakpoints
    if args.breakpoints:
        for bp in args.breakpoints.split(","):
            add_breakpoint(bp.strip())
    
    # Log startup information
    debug_log(f"Starting WEB-AI-Startr.Team in debug mode", "info")
    debug_log(f"Arguments: {vars(args)}", "info")
    
    # Check API key (non-fatal in debug mode)
    try:
        check_api_key()
    except SystemExit:
        debug_log("API key check failed, but continuing in debug mode", "warning")
    
    # If only checking model, do that and exit
    if args.check_model:
        print("\nChecking model configuration...")
        print_model_verification(args.model)
        return
    
    # Get configuration paths
    config_path, config_phase_path, config_role_path = get_config(args.config)
    
    # Allow manual inspection before starting if requested
    if args.pause_before_start:
        print("\n*** DEBUG: Pausing before starting process ***")
        print("Examine the arguments and configuration, then continue")
        import pdb; pdb.set_trace()
    
    # Initialize ChatChain
    debug_log("Initializing ChatChain", "info")
    try:
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
        
        # Save debug state before starting
        dump_debug_state("debug_state_init.json")
        
        # Run the ChatChain process
        debug_log("Starting ChatChain execution", "info")
        chat_chain.pre_processing()
        
        debug_log("Recruiting team", "info")
        chat_chain.recruit_team()
        
        # Save debug state after team recruitment
        dump_debug_state("debug_state_post_recruit.json")
        
        debug_log("Executing chain", "info")
        chat_chain.execute_chain()
        
        debug_log("Post-processing", "info")
        chat_chain.post_processing()
        
        # Final debug state
        dump_debug_state("debug_state_final.json")
        
        debug_log("ChatChain execution completed successfully", "info")
        
    except Exception as e:
        debug_log(f"Error in ChatChain execution: {str(e)}", "error")
        import traceback
        traceback.print_exc()
        
        # Save debug state on error
        dump_debug_state("debug_state_error.json")
        
        # Enter debugger on error if interactive mode is enabled
        if args.interactive:
            print("\n*** ERROR IN EXECUTION ***")
            print("Entering debugger for post-mortem analysis...")
            import pdb; pdb.post_mortem()


if __name__ == "__main__":
    main() 