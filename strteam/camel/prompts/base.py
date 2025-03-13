# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
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
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
#  Enhanced by the  Startr Team (2023 - 2025)
# =========== Copyright 2024 - 2025 @  Startr LLC   All Rights Reserved. ===========
import re
from typing import Dict, List, Optional, Set, Tuple, Any

from ..typing import RoleType

class TextPrompt(str):
    r"""A class for text prompts in the CAMEL chat system.
    
    This class is a subclass of :obj:`str`, so it inherits all string methods.
    """

    def __new__(cls, content: str) -> 'TextPrompt':
        r"""Create a new instance of :obj:`TextPrompt`.

        Args:
            content (str): The content of the prompt.

        Returns:
            TextPrompt: A new instance of :obj:`TextPrompt`.
        """
        return super(TextPrompt, cls).__new__(cls, content)

    def format(self, *args: Any, **kwargs: Any) -> 'TextPrompt':
        r"""Format the prompt template with the given arguments.

        Args:
            *args: Positional arguments to format the prompt template.
            **kwargs: Keyword arguments to format the prompt template.

        Returns:
            TextPrompt: A new instance of :obj:`TextPrompt` with the formatted
                content.
        """
        return TextPrompt(super().format(*args, **kwargs))

class CodePrompt(TextPrompt):
    r"""A class for code prompts in the CAMEL chat system.
    
    This class is a subclass of :obj:`TextPrompt`, so it inherits all string
    methods.

    Attributes:
        code_type (str): The type of code in the prompt.
    """

    def __new__(cls, content: str, code_type: str = "") -> 'CodePrompt':
        r"""Create a new instance of :obj:`CodePrompt`.

        Args:
            content (str): The content of the prompt.
            code_type (str, optional): The type of code in the prompt.
                (default: :obj:`""`)

        Returns:
            CodePrompt: A new instance of :obj:`CodePrompt`.
        """
        instance = super(CodePrompt, cls).__new__(cls, content)
        instance.code_type = code_type
        return instance

class TextPromptDict(Dict[Any, TextPrompt]):
    r"""A dictionary class that maps from key to :obj:`TextPrompt` object."""
    EMBODIMENT_PROMPT = TextPrompt(
        """You are the physical embodiment of the {role} who is working on solving a task: {task}.
You can do things in the physical world including browsing the Internet, reading documents, drawing images, creating videos, executing code and so on.
Your job is to perform the physical actions necessary to interact with the physical world.
You will receive thoughts from the {role} and you will need to perform the actions described in the thoughts.
You can write a series of simple commands in Python to act.
You can perform a set of actions by calling the available Python functions.
You should perform actions based on the descriptions of the functions.

Here is your action space:
{action_space}

You should only perform actions in the action space.
You can perform multiple actions.
You can perform actions in any order.
First, explain the actions you will perform and your reasons, then write Python code to implement your actions.
If you decide to perform actions, you must write Python code to implement the actions.
You may print intermediate results if necessary."""
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.update({RoleType.EMBODIMENT: self.EMBODIMENT_PROMPT})

    def get_key_words(self) -> Set[str]:
        r"""Get key words in the prompt template that need to be filled in.

        Returns:
            A set of key words in the prompt template.
        """
        from ..utils import get_prompt_template_key_words

        return get_prompt_template_key_words(str(self))
