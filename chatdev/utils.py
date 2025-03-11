import html
import logging
import re
import time

import markdown
import inspect
from camel.messages.system_messages import SystemMessage
from visualizer.app import send_msg


def now():
    return time.strftime("%Y%m%d%H%M%S", time.localtime())


def log_visualize(role, content=None):
    """
    send the role and content to visualizer server to show log on webpage in real-time
    You can leave the role undefined and just pass the content, i.e. log_visualize("messages"), where the role is "System".
    Args:
        role: the agent that sends message
        content: the content of message

    Returns: None

    """
    # Color codes for different roles
    color_map = {
        "System": "\033[1;37m",  # White
        "Chief Executive Officer": "\033[1;34m",  # Blue
        "Chief Product Officer": "\033[1;32m",  # Green
        "Chief Technology Officer": "\033[1;35m",  # Purple
        "Prompt Engineer": "\033[1;33m",  # Yellow
        "Software Test Engineer": "\033[1;36m",  # Cyan
        "Software Developer": "\033[1;31m",  # Red
        "default": "\033[0;37m"  # Light gray for others
    }
    
    # Reset color code
    reset_color = "\033[0m"
    
    # Get color for role
    role_color = color_map.get(str(role), color_map["default"])
    
    if not content:
        # Log without content - just a message
        message = role + "\n"
        logging.info(message)
        # Flush logs to ensure they're written to disk
        for handler in logging.getLogger().handlers:
            handler.flush()
        send_msg("System", role)
        
        # Print to console with color
        formatted_message = f"{role_color}{message}{reset_color}"
        print(formatted_message)
    else:
        # Log with role and content
        message = str(role) + ": " + str(content) + "\n"
        logging.info(message)
        # Flush logs to ensure they're written to disk
        for handler in logging.getLogger().handlers:
            handler.flush()
        
        # Print to console with color
        formatted_message = f"{role_color}{role}{reset_color}: {str(content)}"
        print(formatted_message)
        
        if isinstance(content, SystemMessage):
            records_kv = []
            content.meta_dict["content"] = content.content
            for key in content.meta_dict:
                value = content.meta_dict[key]
                value = escape_string(value)
                records_kv.append([key, value])
            content = "**[SystemMessage**]\n\n" + convert_to_markdown_table(records_kv)
        else:
            role = str(role)
            content = str(content)
        send_msg(role, content)


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
