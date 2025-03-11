import base64
import functools
import html
import logging
import re
import time
import sys
import inspect

import markdown

#from camel.messages.system_messages import SystemMessage
#from visualizer.app import send_msg

# --------------------------------------------------------------------
# 1. Basic logging setup: console output with a simple format
# --------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# --------------------------------------------------------------------
# 2. Monkey patch the logging system to colorize messages automatically
# --------------------------------------------------------------------
ROLE_COLORS = {
    "Chief Executive Officer": "\033[1;31m",       # Red for CEO
    "Chief Product Officer": "\033[1;32m",         # Green for CPO
    "Chief Technology Officer": "\033[1;34m",      # Blue for CTO
    "Chief Human Resource Officer": "\033[1;35m",  # Magenta for CHRO
    "Chief Legal Officer": "\033[1;33m",           # Yellow for CLO 
    "Code Reviewer": "\033[1;36m",                 # Cyan for reviewers 
    "Programmer": "\033[1;36m",                    # Cyan for programmers
    "User": "\033[1;37m",                          # White for User
    "Project Manager": "\033[1;38m",               # Light blue for PM
    "Quality Assurance": "\033[1;39m",             # Light cyan for QA
    "Data Scientist": "\033[1;90m",                # Dark gray for Data Scientist
}
DEFAULT_COLOR = "\033[0;37m"  # Light gray
RESET_COLOR   = "\033[0m"

_original_log_method = logging.Logger._log

def _colorized_log_method(self, level, msg, args,
                          exc_info=None, extra=None,
                          stack_info=False, stacklevel=1):
    """
    A monkey-patched version of Logger._log to insert
    ANSI color codes based on 'extra["role"]'.
    """
    role = extra.get("role") if extra else None
    if role:
        color = ROLE_COLORS.get(role, DEFAULT_COLOR)
        msg = f"{color}{msg}{RESET_COLOR}"
    else:
        msg = f"{DEFAULT_COLOR}{msg}{RESET_COLOR}"
    _original_log_method(self, level, msg, args, exc_info, extra, stack_info, stacklevel)

# Overwrite the logging method for all loggers
logging.Logger._log = _colorized_log_method

# --------------------------------------------------------------------
# 3. Your utility methods that rely solely on logging
# --------------------------------------------------------------------
def now():
    """Return current time as YYYYmmddHHMMSS."""
    return time.strftime("%Y%m%d%H%M%S", time.localtime())


def log_visualize(role, content=None):
    """
    Log the role and content with visualization (color done via monkey patch).
    """
    if not content:
        # e.g. [SYSTEM] Something
        message = f"## [[SYSTEM]] {role}"
        logging.info(message, extra={'role': role})
    else:
        header = f"## [[{role}]]"
        logging.info(header, extra={'role': role})
        
        lines = str(content).split('\n')
        for line in lines:
            indented_line = f"  {line}"
            logging.info(indented_line, extra={'role': role})


def convert_to_markdown_table(records_kv):
    """Convert (key, value) pairs into a Markdown table string."""
    header = "| Parameter | Value |\n| --- | --- |"
    rows = [f"| **{key}** | {value} |" for (key, value) in records_kv]
    return header + "\n" + "\n".join(rows)


def escape_string(value):
    """
    Take a string, unescape HTML, convert simple markdown to HTML,
    strip HTML tags, and flatten newlines.
    """
    value = str(value)
    value = html.unescape(value)
    value = markdown.markdown(value)      # convert simple Markdown to HTML
    value = re.sub(r"<[^>]*>", "", value) # strip HTML tags
    value = value.replace("\n", " ")      # flatten newlines
    return value


def log_arguments(func):
    """
    Decorator to log a summary of the function's arguments in a Markdown table.
    """
    @functools.wraps(func)
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
            records_kv.append((name, value))

        records_table = convert_to_markdown_table(records_kv)
        records = f"**[{func.__name__}]**\n" + records_table
        log_visualize("System", records)

        return func(*args, **kwargs)
    return wrapper

# --------------------------------------------------------------------
# Example usage:
# --------------------------------------------------------------------
if __name__ == "__main__":
    # Test the log_visualize function
    log_visualize("Chief Executive Officer", "Hello from the CEO!")
    log_visualize("Chief Product Officer", "Here is a product update.\nNew line here.")
    log_visualize("System")  # no content

    # Test the @log_arguments decorator
    @log_arguments
    def sample_function(a, b, extra_info):
        return f"a={a}, b={b}, extra_info={extra_info}"

    sample_function(10, 20, "some text")
