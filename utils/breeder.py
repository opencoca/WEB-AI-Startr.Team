#!/usr/bin/python
"""
This script recursively combines multiple Python files from a specified project directory
into a single output file, removing local import statements to avoid redundancy.
It is intended for use as a temporary solution for embedding dependencies until proper packaging is implemented.

Functions:
  remove_local_imports(content, local_modules):
    Removes or adjusts import statements that reference modules in the local project directory.
  combine_project(project_dir, output_file, main_filename="__main__.py"):
    Recursively combines all .py files in the specified project directory into a single output file,
    processing and removing local imports. Ensures the main file is appended last.

Usage:
  To recompile the project, run:
    python breeder.py <project_dir> [output_file]

Note:
  Update the `project_dir` variable in the `__main__` block (or via command line) to point to your project's folder.
"""

# Copyright (c) 2025 Startr.LLC
# This is a poor-man's executable builder, for embedding dependencies into
# our pagekite.py file until we have proper packaging.

import os
import re
import sys
from datetime import datetime

current_year = datetime.now().year

BREEDER_NOTE = f"""\
#
# Copyright (c) {current_year} Startr.LLC
# 
# WARNING:  This is a compilation of multiple Python files. Do not edit.
# Changes should be made to the original files in the source tree.
#
# To recompile, run:
#     python breeder.py <project_dir> [output_file]
#
"""


def remove_local_imports(content, local_modules):
    """
    Remove or adjust import statements that reference local modules.
    For 'import ...' lines, if a part of the import is local, it is removed.
    For 'from ... import ...' lines, the line is removed if the module is local.
    """
    filtered_lines = []
    import_re = re.compile(r'^\s*import\s+(.+)$')
    from_re = re.compile(r'^\s*from\s+([\w\.]+)\s+import\s+')

    for line in content.splitlines():
        imp_match = import_re.match(line)
        frm_match = from_re.match(line)
        if imp_match:
            modules_str = imp_match.group(1)
            modules = [mod.strip() for mod in modules_str.split(',')]
            # For mixed imports (local and non-local), keep only non-local modules.
            non_local_modules = []
            for mod in modules:
                # Remove any alias; e.g., "camel.agents as agents" becomes "camel.agents"
                mod_name = mod.split(' as ')[0].strip()
                if mod_name not in local_modules:
                    non_local_modules.append(mod.strip())
            if non_local_modules:
                new_line = "import " + ", ".join(non_local_modules)
                filtered_lines.append(new_line)
            # If all modules in the line are local, skip the line.
        elif frm_match:
            mod = frm_match.group(1)
            if mod not in local_modules:
                filtered_lines.append(line)
        else:
            filtered_lines.append(line)

    return "\n".join(filtered_lines)


def gather_py_files(project_dir):
    """
    Recursively gather all .py files in project_dir, excluding __pycache__ and hidden directories.
    Returns a list of tuples: (relative_path, absolute_path).
    """
    py_files = []
    for root, dirs, files in os.walk(project_dir):
        # Exclude __pycache__ and hidden directories.
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in files:
            if file.endswith('.py') and not file.startswith('.'):
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, project_dir)
                py_files.append((rel_path, abs_path))
    return sorted(py_files, key=lambda x: x[0])


def module_name_from_relpath(rel_path):
    """
    Compute the module name from a file's relative path.
    If the file is __init__.py, its module name is the directory name.
    Otherwise, replace path separators with dots and remove the .py extension.
    """
    mod = rel_path.replace(os.sep, '.')
    if mod.endswith(".__init__.py"):
        mod = mod[:-len(".__init__.py")]
    elif mod.endswith(".py"):
        mod = mod[:-3]
    return mod


def combine_project(project_dir, output_file, main_filename="__main__.py"):
    """
    Recursively combine all .py files in project_dir into a single file, processing
    and removing local imports.
    """
    py_files = gather_py_files(project_dir)

    # Build a set of local module names from all gathered files.
    local_modules = {module_name_from_relpath(rel) for rel, _ in py_files}

    # If a main file is specified and present, ensure it is appended last.
    main_files = [t for t in py_files if t[0] == main_filename]
    py_files = [t for t in py_files if t[0] != main_filename]
    py_files.extend(main_files)

    with open(output_file, 'w') as out:
        out.write(BREEDER_NOTE + "\n")
        out.write("# Combined project file\n\n")
        for rel_path, abs_path in py_files:
            with open(abs_path, 'r') as f:
                content = f.read()

            processed_content = remove_local_imports(content, local_modules)
            out.write(f"# ===== File: {rel_path} (start) =====\n")
            out.write(processed_content)
            out.write(f"\n# ===== End of {rel_path} =====\n\n")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print("""Usage:
  python breeder.py <project_dir> [output_file]

Description:
  This script recursively combines all .py files in <project_dir> into a single file, removing local imports.
  If [output_file] is not specified, it defaults to 'combined_project.py'.""")
        sys.exit(0)

    project_dir = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "combined_project.py"
    combine_project(project_dir, output_file)
