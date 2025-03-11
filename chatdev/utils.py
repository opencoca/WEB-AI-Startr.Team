import base64
import functools
import html
import logging
import re
import time
import sys

import markdown
import inspect
from camel.messages.system_messages import SystemMessage
from visualizer.app import send_msg


def now():
    return time.strftime("%Y%m%d%H%M%S", time.localtime())


def log_visualize(role, content=None):
    """
    Log the role and content with visualization.
    This function uses the logging module to ensure output goes to both console and log file.
    
    Args:
        role (str): The role.
        content (str, optional): The content. Defaults to None.
    """
    # Color mapping for terminal output (doesn't affect log files)
    color_map = {
        "Chief Executive Officer": "\033[1;31m",     # Red for CEO
        "Chief Product Officer": "\033[1;32m",       # Green for CPO
        "Chief Technology Officer": "\033[1;34m",    # Blue for CTO
        "Chief Human Resource Officer": "\033[1;35m",# Magenta for CHRO
        "Chief Legal Officer": "\033[1;33m",         # Yellow for CLO 
        "Code Reviewer": "\033[1;36m",               # Cyan for reviewers 
        "Programmer": "\033[1;36m",                  # Cyan for programmers
        "User": "\033[1;37m",                        # White for User
        "default": "\033[0;37m"                      # Light gray for others
    }
    reset_color = "\033[0m"
    
    # Get color for terminal output
    role_color = color_map.get(str(role), color_map["default"])
    
    if not content:
        # System message - log as INFO
        message = f"[SYSTEM] {role}"
        logging.info(message)
        # Also print to console with color (for terminal)
        print(f"{role_color}[SYSTEM] {role}{reset_color}")
    else:
        # Agent message with a header and indented content - log as INFO
        header = f"\n[{role}]"
        logging.info(header)
        
        # Log content with line indentation
        lines = str(content).split('\n')
        for line in lines:
            indented_line = f"  {line}"
            logging.info(indented_line)
        
        # Also print to console with color (for terminal)
        print(f"{role_color}{header}{reset_color}")
        for line in lines:
            print(f"{role_color}  {line}{reset_color}")


def convert_to_markdown_table(records_kv):
    # Create the Markdown table header
    header = "| Parameter | Value |\n| --- | --- |"

    # Create the Markdown table rows
    rows = [f"| **{key}** | {value} |" for (key, value) in records_kv]

    # Combine the header and rows to form the final Markdown table
    markdown_table = header + "\n" + "\n".join(rows)

    return markdown_table


def log_arguments(func):
    def wrapper(*args, **kwargs):
        sig = inspect.signature(func)
        params = sig.parameters

        all_args = {}
        all_args.update({name: value for name, value in zip(params.keys(), args)})
        all_args.update(kwargs)

        records_kv = []
        for name, value in all_args.items():
            if name in ["self", "chat_env", "task_type"]:
                continue
            value = escape_string(value)
            records_kv.append([name, value])
        records = f"**[{func.__name__}]**\n\n" + convert_to_markdown_table(records_kv)
        log_visualize("System", records)

        return func(*args, **kwargs)

    return wrapper


def escape_string(value):
    value = str(value)
    value = html.unescape(value)
    value = markdown.markdown(value)
    value = re.sub(r"<[^>]*>", "", value)
    value = value.replace("\n", " ")
    return value
