import os
import re
import shutil
import signal
import subprocess
import time
from typing import Dict

import openai
import requests

from .code import Code
from .documents import Documents
from .roster import Roster
from .utils import log_visualize
from ..ecl.memory import Memory

try:
    pass

    openai_new_api = True  # new openai api version
except ImportError:
    openai_new_api = False  # old openai api version


class ChatEnvConfig:
    def __init__(
        self,
        clear_structure,
        gui_design,
        git_management,
        incremental_develop,
        background_prompt,
        with_memory,
    ):
        self.clear_structure = clear_structure  # Whether to clear non-software files in the WareHouse and cache files in generated software path
        self.gui_design = gui_design  # Encourage strteam generate software with GUI
        self.git_management = git_management  # Whether to use git to manage the creation and changes of generated software
        self.incremental_develop = incremental_develop  # Whether to use incremental develop on an existing project
        self.background_prompt = background_prompt  # background prompt that will be added to every inquiry to LLM
        self.with_memory = (
            with_memory  # Wheter to use memroy in the interaction between agents
        )

    def __str__(self):
        string = ""
        string += "ChatEnvConfig.with_memory: {}\n".format(self.with_memory)
        string += "ChatEnvConfig.clear_structure: {}\n".format(self.clear_structure)
        string += "ChatEnvConfig.git_management: {}\n".format(self.git_management)
        string += "ChatEnvConfig.gui_design: {}\n".format(self.gui_design)
        string += "ChatEnvConfig.incremental_develop: {}\n".format(
            self.incremental_develop
        )
        string += "ChatEnvConfig.background_prompt: {}\n".format(self.background_prompt)
        return string


class ChatEnv:
    def __init__(self, chat_env_config: ChatEnvConfig):
        self.config = chat_env_config
        self.roster: Roster = Roster()
        self.code: Code = Code()
        self.memory: Memory = Memory()
        self.proposed_images: Dict[str, str] = {}
        self.incorporated_images: Dict[str, str] = {}
        self.requirements: Documents = Documents()
        self.manuals: Documents = Documents()
        self.env_dict = {
            "directory": "",
            "task_prompt": "",
            "task_description": "",
            "modality": "",
            "ideas": "",
            "language": "",
            "review_comments": "",
            "error_summary": "",
            "test_reports": "",
        }

    @staticmethod
    def fix_module_not_found_error(test_reports):
        if "ModuleNotFoundError" in test_reports:
            for match in re.finditer(
                r"No module named '(\S+)'", test_reports, re.DOTALL
            ):
                module = match.group(1)
                subprocess.Popen("pip install {}".format(module), shell=True).wait()
                log_visualize(
                    "**[CMD Execute]**\n\n[CMD] pip install {}".format(module)
                )

    def set_directory(self, directory):
        assert len(self.env_dict["directory"]) == 0
        self.env_dict["directory"] = directory
        self.code.directory = directory
        self.requirements.directory = directory
        self.manuals.directory = directory

        # Create or clean the directory without creating a backup copy
        if os.path.exists(self.env_dict["directory"]):
            # Directory exists - but we don't want to back it up with a timestamp suffix anymore
            if len(os.listdir(directory)) > 0:
                # Just clean the existing directory
                shutil.rmtree(self.env_dict["directory"])
                os.mkdir(self.env_dict["directory"])
                print(f"{directory} cleaned and recreated")
        else:
            # Directory doesn't exist, create it
            os.mkdir(self.env_dict["directory"])
            print(f"{directory} created")

    def init_memory(self):
        self.memory.id_enabled = True
        self.memory.directory = os.path.join(os.getcwd(), "ecl", "memory")
        if not os.path.exists(self.memory.directory):
            os.mkdir(self.memory.directory)
        self.memory.upload()

    def exist_bugs(self) -> tuple[bool, str]:
        directory = self.env_dict["directory"]

        success_info = "The software run successfully without errors."
        try:

            # check if we are on windows or linux
            if os.name == "nt":
                command = "cd {} && dir && python main.py".format(directory)
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                command = "cd {}; ls -l; python3 main.py;".format(directory)
                process = subprocess.Popen(
                    command,
                    shell=True,
                    preexec_fn=os.setsid,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            time.sleep(3)
            return_code = process.returncode
            # Check if the software is still running
            if process.poll() is None:
                if "killpg" in dir(os):
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    os.kill(process.pid, signal.SIGTERM)
                    if process.poll() is None:
                        os.kill(process.pid, signal.CTRL_BREAK_EVENT)

            if return_code == 0:
                return False, success_info
            else:
                error_output = process.stderr.read().decode("utf-8")
                if error_output:
                    if "Traceback".lower() in error_output.lower():
                        errs = error_output.replace(directory + "/", "")
                        return True, errs
                else:
                    return False, success_info
        except subprocess.CalledProcessError as e:
            return True, f"Error: {e}"
        except Exception as ex:
            return True, f"An error occurred: {ex}"

        return False, success_info

    def recruit(self, agent_name: str):
        self.roster._recruit(agent_name)

    def exist_employee(self, agent_name: str) -> bool:
        return self.roster._exist_employee(agent_name)

    def print_employees(self):
        self.roster._print_employees()

    def update_code(self, generated_content):
        self.code._update_code(generated_content)

    def rewrite_code(self, phase_info=None) -> None:
        self.code._rewrite_code(self.config.git_management, phase_info)

    def get_code(self) -> str:
        return self.code._get_code()

    def _load_from_hardware(self, directory) -> None:
        self.code._load_from_hardware(directory)

    def _update_requirements(self, generated_content):
        self.requirements._update_docs(generated_content)

    def rewrite_requirements(self):
        self.requirements._rewrite_docs()

    def get_requirements(self) -> str:
        return self.requirements._get_docs()

    def _update_manuals(self, generated_content):
        self.manuals._update_docs(
            generated_content, parse=False, predifined_filename="manual.md"
        )

    def rewrite_manuals(self):
        self.manuals._rewrite_docs()

    def write_meta(self) -> None:
        directory = self.env_dict["directory"]

        if not os.path.exists(directory):
            os.mkdir(directory)
            print("{} Created.".format(directory))

        meta_filename = "meta.txt"
        with open(
            os.path.join(directory, meta_filename), "w", encoding="utf-8"
        ) as writer:
            writer.write("{}:\n{}\n\n".format("Task", self.env_dict["task_prompt"]))
            writer.write("{}:\n{}\n\n".format("Config", self.config.__str__()))
            writer.write("{}:\n{}\n\n".format("Roster", ", ".join(self.roster.agents)))
            writer.write("{}:\n{}\n\n".format("Modality", self.env_dict["modality"]))
            writer.write("{}:\n{}\n\n".format("Ideas", self.env_dict["ideas"]))
            writer.write("{}:\n{}\n\n".format("Language", self.env_dict["language"]))
            writer.write("{}:\n{}\n\n".format("Code_Version", self.code.version))
            writer.write(
                "{}:\n{}\n\n".format(
                    "Proposed_images", len(self.proposed_images.keys())
                )
            )
            writer.write(
                "{}:\n{}\n\n".format(
                    "Incorporated_images", len(self.incorporated_images.keys())
                )
            )
        print(os.path.join(directory, meta_filename), "Wrote")

    def generate_images_from_code(self):
        def download(img_url, file_name):
            r = requests.get(img_url)
            filepath = os.path.join(self.env_dict["directory"], file_name)
            if os.path.exists(filepath):
                os.remove(filepath)
            with open(filepath, "wb") as f:
                f.write(r.content)
                print("{} Downloaded".format(filepath))

        regex = r"(\w+.png)"
        joined_code = self.get_code()
        matches = re.finditer(regex, joined_code, re.DOTALL)
        # matched_images = {}
        for match in matches:
            filename = match.group(1).strip()
            if filename in self.proposed_images.keys():
                self.incorporated_images[filename] = self.proposed_images[filename]
            else:
                self.incorporated_images[filename] = filename.replace("_", " ")

        for filename in self.incorporated_images.keys():
            if not os.path.exists(os.path.join(self.env_dict["directory"], filename)):
                desc = self.incorporated_images[filename]
                if desc.endswith(".png"):
                    desc = desc.replace(".png", "")
                print("{}: {}".format(filename, desc))
                if openai_new_api:
                    response = openai.images.generate(prompt=desc, n=1, size="256x256")
                    image_url = response.data[0].url
                else:
                    response = openai.Image.create(prompt=desc, n=1, size="256x256")
                    image_url = response["data"][0]["url"]
                download(image_url, filename)

    def get_proposed_images_from_message(self, messages):
        def download(img_url, file_name):
            r = requests.get(img_url)
            filepath = os.path.join(self.env_dict["directory"], file_name)
            if os.path.exists(filepath):
                os.remove(filepath)
            with open(filepath, "wb") as f:
                f.write(r.content)
                print("{} Downloaded".format(filepath))

        regex = r"(\w+.png):(.*?)\n"
        matches = re.finditer(regex, messages, re.DOTALL)
        images = {}
        for match in matches:
            filename = match.group(1).strip()
            desc = match.group(2).strip()
            images[filename] = desc

        if len(images.keys()) == 0:
            regex = r"(\w+.png)"
            matches = re.finditer(regex, messages, re.DOTALL)
            images = {}
            for match in matches:
                filename = match.group(1).strip()
                desc = " ".join(filename.replace(".png", "").split("_"))
                images[filename] = desc
                print("{}: {}".format(filename, images[filename]))

        for filename in images.keys():
            if not os.path.exists(os.path.join(self.env_dict["directory"], filename)):
                desc = images[filename]
                if desc.endswith(".png"):
                    desc = desc.replace(".png", "")
                print("{}: {}".format(filename, desc))

                if openai_new_api:
                    response = openai.images.generate(prompt=desc, n=1, size="256x256")
                    image_url = response.data[0].url
                else:
                    response = openai.Image.create(prompt=desc, n=1, size="256x256")
                    image_url = response["data"][0]["url"]

                download(image_url, filename)

        return images
