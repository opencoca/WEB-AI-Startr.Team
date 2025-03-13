import inspect
import os
import pdb
import sys
import traceback
import logging
from functools import wraps
import json
import time
from typing import Any, Dict, List, Optional, Callable, Union

# Configure logging
DEBUG_LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "debug.log")
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
    handlers=[
        logging.FileHandler(DEBUG_LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

# Global debug state
DEBUG_ENABLED = os.environ.get("STARTR_DEBUG", "false").lower() == "true"
INTERACTIVE_DEBUG = os.environ.get("STARTR_INTERACTIVE", "false").lower() == "true"
BREAKPOINTS = os.environ.get("STARTR_BREAKPOINTS", "").split(",")
DEBUG_INSPECTION_POINTS = {}

def enable_debug():
    """Enable debug mode programmatically"""
    global DEBUG_ENABLED
    DEBUG_ENABLED = True
    logging.info("Debug mode enabled")

def enable_interactive():
    """Enable interactive debug mode programmatically"""
    global INTERACTIVE_DEBUG
    INTERACTIVE_DEBUG = True
    logging.info("Interactive debug mode enabled")

def add_breakpoint(name: str):
    """Add a breakpoint to trigger on"""
    global BREAKPOINTS
    if name not in BREAKPOINTS:
        BREAKPOINTS.append(name)
        logging.info(f"Added breakpoint: {name}")

def debug_log(msg: str, level: str = "debug"):
    """Log a debug message with the current stack frame information"""
    frame = inspect.currentframe().f_back
    filename = frame.f_code.co_filename
    lineno = frame.f_lineno
    function = frame.f_code.co_name
    
    log_msg = f"[{os.path.basename(filename)}:{lineno}] [{function}] {msg}"
    
    if level.lower() == "debug":
        logging.debug(log_msg)
    elif level.lower() == "info":
        logging.info(log_msg)
    elif level.lower() == "warning":
        logging.warning(log_msg)
    elif level.lower() == "error":
        logging.error(log_msg)
    elif level.lower() == "critical":
        logging.critical(log_msg)

def debug_inspect(point_name: str, data: Any = None, force_breakpoint: bool = False):
    """
    Inspect data at a specific point in the code
    
    Args:
        point_name: Name of inspection point
        data: Data to inspect
        force_breakpoint: Whether to force a breakpoint regardless of settings
    """
    # Save data for later retrieval
    DEBUG_INSPECTION_POINTS[point_name] = data
    
    # Log the inspection point was hit
    caller_info = inspect.getframeinfo(inspect.currentframe().f_back)
    debug_log(f"Inspection point hit: {point_name} at {caller_info.filename}:{caller_info.lineno}")
    
    # Print data summary
    if data is not None:
        data_type = type(data).__name__
        if hasattr(data, "__len__"):
            data_summary = f"{data_type} of length {len(data)}"
        else:
            data_summary = data_type
        debug_log(f"Data at {point_name}: {data_summary}")
        
        # If data is not too large, print it
        try:
            if isinstance(data, (dict, list)):
                data_str = json.dumps(data, default=str, indent=2)[:500]
                if len(data_str) == 500:
                    data_str += "... (truncated)"
                debug_log(f"Data preview:\n{data_str}")
            elif hasattr(data, "__str__"):
                data_str = str(data)[:500]
                if len(data_str) == 500:
                    data_str += "... (truncated)"
                debug_log(f"Data preview: {data_str}")
        except Exception as e:
            debug_log(f"Error printing data: {e}")
    
    # Check if we should breakpoint
    if force_breakpoint or point_name in BREAKPOINTS or INTERACTIVE_DEBUG:
        debug_log(f"Triggering breakpoint at {point_name}", "info")
        if INTERACTIVE_DEBUG:
            # In iPython or interactive mode
            print(f"\n*** DEBUG BREAKPOINT: {point_name} ***")
            print(f"Type 'c' to continue, or explore the 'data' variable")
            print(f"Current inspection point data accessible via debug_utils.DEBUG_INSPECTION_POINTS['{point_name}']")
            pdb.set_trace()

def debug_decorator(name: Optional[str] = None):
    """
    Decorator to add debugging to a function or method
    
    Args:
        name: Optional name for the debug point
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not DEBUG_ENABLED:
                return func(*args, **kwargs)
            
            func_name = name or func.__name__
            debug_log(f"Entering {func_name}")
            
            # Create a clean dict of args for logging
            arg_dict = {}
            # Handle 'self' in methods
            if inspect.ismethod(func) and args:
                arg_dict["self"] = f"{args[0].__class__.__name__} instance"
                named_args = dict(zip(list(inspect.signature(func).parameters)[1:], args[1:]))
            else:
                named_args = dict(zip(inspect.signature(func).parameters, args))
            
            arg_dict.update(named_args)
            arg_dict.update(kwargs)
            
            # Convert to JSON safe dict
            safe_arg_dict = {}
            for k, v in arg_dict.items():
                if isinstance(v, (str, int, float, bool, type(None))):
                    safe_arg_dict[k] = v
                else:
                    try:
                        safe_arg_dict[k] = str(v)[:100]
                    except:
                        safe_arg_dict[k] = f"{type(v).__name__} instance"
            
            debug_log(f"Arguments: {json.dumps(safe_arg_dict, default=str)}")
            
            # Check if this is a breakpoint
            if INTERACTIVE_DEBUG or func_name in BREAKPOINTS:
                debug_log(f"Breakpoint triggered for {func_name}", "info")
                print(f"\n*** DEBUG BREAKPOINT: {func_name} ***")
                print(f"Explore the local variables: {', '.join(safe_arg_dict.keys())}")
                pdb.set_trace()
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                debug_log(f"Exiting {func_name} - Duration: {end_time - start_time:.4f}s")
                
                # Log result summary
                if result is not None:
                    result_type = type(result).__name__
                    if hasattr(result, "__len__"):
                        result_summary = f"{result_type} of length {len(result)}"
                    else:
                        result_summary = result_type
                    debug_log(f"Result: {result_summary}")
                return result
            except Exception as e:
                end_time = time.time()
                error_tb = traceback.format_exc()
                debug_log(f"Error in {func_name}: {e}\n{error_tb}", "error")
                
                if INTERACTIVE_DEBUG:
                    print(f"\n*** ERROR IN {func_name}: {e} ***")
                    print("Enter debugger to inspect...")
                    pdb.post_mortem()
                raise
        
        return wrapper
    
    # Handle case where decorator is used without parentheses
    if callable(name):
        func = name
        name = func.__name__
        return decorator(func)
    
    return decorator

def debug_api_call(provider: str, model: str, messages: List[Dict], **kwargs):
    """
    Debug and record API calls to LLM providers
    
    Args:
        provider: API provider name
        model: Model name
        messages: Messages being sent
        **kwargs: Additional parameters to the API call
    """
    debug_log(f"API call to {provider} using model {model}")
    
    # Record API call details for inspection
    call_details = {
        "provider": provider,
        "model": model,
        "timestamp": time.time(),
        "messages": messages,
        "parameters": kwargs
    }
    
    # Generate a unique key for this API call
    call_key = f"api_call_{provider}_{int(time.time() * 1000)}"
    DEBUG_INSPECTION_POINTS[call_key] = call_details
    
    # Check if model exists in the list of approved models
    debug_log(f"Checking if model '{model}' is valid")
    
    # Return the inspection point key for reference
    return call_key

def get_all_debug_points():
    """Get all recorded debug inspection points"""
    return DEBUG_INSPECTION_POINTS

def clear_debug_points():
    """Clear all recorded debug inspection points"""
    global DEBUG_INSPECTION_POINTS
    DEBUG_INSPECTION_POINTS = {}
    debug_log("Cleared all debug inspection points")

def dump_debug_state(filename: str = "debug_state.json"):
    """Dump current debug state to a file"""
    state = {
        "debug_enabled": DEBUG_ENABLED,
        "interactive_debug": INTERACTIVE_DEBUG,
        "breakpoints": BREAKPOINTS,
        "inspection_points": {k: str(v) for k, v in DEBUG_INSPECTION_POINTS.items()}
    }
    
    filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), filename)
    with open(filepath, "w") as f:
        json.dump(state, f, indent=2, default=str)
    
    debug_log(f"Debug state dumped to {filepath}")
    return filepath 