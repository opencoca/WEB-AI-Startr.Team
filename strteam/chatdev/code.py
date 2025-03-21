import difflib
import os
import re
import subprocess

from .utils import log_visualize


class Code:
    def __init__(self, generated_content=""):
        self.directory: str = None
        self.version: float = 0.0
        self.generated_content: str = generated_content
        self.codebooks = {}

        # Enhanced filename extraction from line or code block header
        def extract_filename_from_line(lines):
            file_name = ""
            # Try common filename patterns
            for candidate in re.finditer(r"[\w\-\.\/\\]+\.\w+", lines, re.DOTALL):
                potential_name = candidate.group()
                # Get just the filename part if a path is included
                file_name = os.path.basename(potential_name.strip())
                file_name = file_name.lower()
                # If we found something that looks like a valid filename, use it
                if "." in file_name and file_name not in ["e.g.", "i.e."]:
                    break
            return file_name

        # Extract filename from Python class definition if available
        def extract_filename_from_code(code):
            file_name = ""
            # Try to extract from class definition
            regex_class = r"class\s+(\w+)[\(:]"
            class_matches = re.finditer(regex_class, code, re.DOTALL)
            for match in class_matches:
                file_name = match.group(1).lower().split("(")[0] + ".py"
                return file_name

            # Try to extract from function definition for main file
            if "def main" in code:
                return "main.py"

            # Try to extract from import statements
            if file_name == "" and "import" in code:
                module_regex = r"from (\w+) import"
                module_matches = re.finditer(module_regex, code, re.DOTALL)
                for match in module_matches:
                    file_name = match.group(1).lower() + ".py"
                    return file_name

            return file_name

        # If we have content to process
        if generated_content != "":
            # First try the standard formatted code blocks
            regex = r"(.+?)\n```.*?\n(.*?)```"
            matches = re.finditer(regex, self.generated_content, re.DOTALL)

            for match in matches:
                code = match.group(2)
                if "CODE" in code:
                    continue

                group1 = match.group(1)
                filename = extract_filename_from_line(group1)

                # Check for main function/code
                if "__main__" in code:
                    filename = "main.py"
                elif "def main" in code and filename == "":
                    filename = "main.py"

                # If still no filename, try to extract from code
                if filename == "":
                    filename = extract_filename_from_code(code)

                # Default to a generic filename as last resort based on content
                if filename == "":
                    if "class" in code:
                        # Find the first class name
                        class_match = re.search(r"class (\w+)", code)
                        if class_match:
                            filename = f"{class_match.group(1).lower()}.py"
                        else:
                            filename = "class_file.py"
                    elif "<html" in code.lower() or "<!doctype html" in code.lower():
                        filename = "index.html"
                    elif "css" in code.lower() and "{" in code:
                        filename = "style.css"
                    elif "function" in code.lower() or "const" in code:
                        filename = "script.js"
                    else:
                        filename = "main.py"  # Default to main.py

                # Only add valid code
                if filename and code and len(filename) > 0 and len(code) > 0:
                    self.codebooks[filename] = self._format_code(code)

            # If no code blocks were found, try alternative code block format without description line
            if not self.codebooks:
                alt_regex = r"```.*?\n(.*?)```"
                alt_matches = re.finditer(alt_regex, self.generated_content, re.DOTALL)

                file_counter = 0
                for match in alt_matches:
                    code = match.group(1)
                    if "CODE" in code:
                        continue

                    # Try to determine filename from content
                    filename = extract_filename_from_code(code)

                    # Default filename if we couldn't extract one
                    if not filename:
                        file_counter += 1
                        if "class" in code:
                            filename = f"class_{file_counter}.py"
                        elif "def " in code:
                            filename = f"functions_{file_counter}.py"
                        elif "<html" in code.lower():
                            filename = "index.html"
                        elif "css" in code.lower():
                            filename = "style.css"
                        else:
                            filename = f"file_{file_counter}.py"

                    # Only add valid code
                    if filename and code and len(filename) > 0 and len(code) > 0:
                        self.codebooks[filename] = self._format_code(code)

    def _format_code(self, code):
        code = "\n".join([line for line in code.split("\n") if len(line.strip()) > 0])
        return code

    def _update_code(self, generated_content):
        new_code = Code(generated_content)
        difflib.Differ()
        for key in new_code.codebooks.keys():
            if (
                key not in self.codebooks.keys()
                or self.codebooks[key] != new_code.codebooks[key]
            ):
                update_code_content = "**[Update Code]**\n\n"
                update_code_content += "{} updated.\n".format(key)
                old_code_content = (
                    self.codebooks[key] if key in self.codebooks.keys() else "# None"
                )
                new_code_content = new_code.codebooks[key]

                lines_old = old_code_content.splitlines()
                lines_new = new_code_content.splitlines()

                unified_diff = difflib.unified_diff(
                    lines_old, lines_new, lineterm="", fromfile="Old", tofile="New"
                )
                unified_diff = "\n".join(unified_diff)
                update_code_content = (
                    update_code_content
                    + "\n\n"
                    + """```
'''

'''\n"""
                    + unified_diff
                    + "\n```"
                )

                log_visualize(update_code_content)
                self.codebooks[key] = new_code.codebooks[key]

    def _rewrite_code(self, git_management, phase_info=None) -> None:
        directory = self.directory
        rewrite_code_content = "**[Rewrite Code]**\n\n"
        if os.path.exists(directory) and len(os.listdir(directory)) > 0:
            self.version += 1.0
        if not os.path.exists(directory):
            os.mkdir(self.directory)
            rewrite_code_content += "{} Created\n".format(directory)

        for filename in self.codebooks.keys():
            filepath = os.path.join(directory, filename)
            with open(filepath, "w", encoding="utf-8") as writer:
                writer.write(self.codebooks[filename])
                rewrite_code_content += os.path.join(directory, filename) + " Wrote\n"

        if git_management:
            if not phase_info:
                phase_info = ""
            log_git_info = "**[Git Information]**\n\n"
            if self.version == 1.0:
                os.system("cd {}; git init".format(self.directory))
                log_git_info += "cd {}; git init\n".format(self.directory)
            os.system("cd {}; git add .".format(self.directory))
            log_git_info += "cd {}; git add .\n".format(self.directory)

            # check if there exist diff
            completed_process = subprocess.run(
                "cd {}; git status".format(self.directory),
                shell=True,
                text=True,
                stdout=subprocess.PIPE,
            )
            if "nothing to commit" in completed_process.stdout:
                self.version -= 1.0
                return

            os.system(
                'cd {}; git commit -m "v{}"'.format(
                    self.directory, str(self.version) + " " + phase_info
                )
            )
            log_git_info += 'cd {}; git commit -m "v{}"\n'.format(
                self.directory, str(self.version) + " " + phase_info
            )
            if self.version == 1.0:
                os.system(
                    "cd {}; git submodule add ./{} {}".format(
                        os.path.dirname(os.path.dirname(self.directory)),
                        "WareHouse/" + os.path.basename(self.directory),
                        "WareHouse/" + os.path.basename(self.directory),
                    )
                )
                log_git_info += "cd {}; git submodule add ./{} {}\n".format(
                    os.path.dirname(os.path.dirname(self.directory)),
                    "WareHouse/" + os.path.basename(self.directory),
                    "WareHouse/" + os.path.basename(self.directory),
                )
                log_visualize(rewrite_code_content)
            log_visualize(log_git_info)

    def _get_code(self) -> str:
        content = ""
        for filename in self.codebooks.keys():
            content += "{}\n```{}\n{}\n```\n\n".format(
                filename,
                "python" if filename.endswith(".py") else filename.split(".")[-1],
                self.codebooks[filename],
            )
        return content

    def _load_from_hardware(self, directory) -> None:
        assert (
            len(
                [
                    filename
                    for filename in os.listdir(directory)
                    if filename.endswith(".py")
                ]
            )
            > 0
        )
        for root, directories, filenames in os.walk(directory):
            for filename in filenames:
                if filename.endswith(".py"):
                    code = open(
                        os.path.join(directory, filename), "r", encoding="utf-8"
                    ).read()
                    self.codebooks[filename] = self._format_code(code)
        log_visualize(
            "{} files read from {}".format(len(self.codebooks.keys()), directory)
        )
