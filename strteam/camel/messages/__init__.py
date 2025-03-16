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
#  Development continued by the  Startr Team (2023 - 2025)
# =========== Copyright 2024 - 2025 @  Startr LLC   All Rights Reserved. ===========
from typing import Dict, Union, ForwardRef

# Define OpenAI message types
OpenAISystemMessage = Dict[str, str]
OpenAIAssistantMessage = Dict[str, str]
OpenAIUserMessage = Dict[str, str]
OpenAIChatMessage = Union[OpenAIUserMessage, OpenAIAssistantMessage]
OpenAIMessage = Union[OpenAISystemMessage, OpenAIChatMessage]

# Import message classes
from .base import BaseMessage
from .system_messages import (
    SystemMessage,
    AssistantSystemMessage,
    UserSystemMessage,
)
from .chat_messages import (
    ChatMessage,
    AssistantChatMessage,
    UserChatMessage,
)

# Define message types using the imported classes
MessageType = Union[
    BaseMessage,
    SystemMessage,
    AssistantSystemMessage,
    UserSystemMessage,
    ChatMessage,
    AssistantChatMessage,
    UserChatMessage,
]
SystemMessageType = Union[SystemMessage, AssistantSystemMessage, UserSystemMessage]
ChatMessageType = Union[ChatMessage, AssistantChatMessage, UserChatMessage]

__all__ = [
    "OpenAISystemMessage",
    "OpenAIAssistantMessage",
    "OpenAIUserMessage",
    "OpenAIChatMessage",
    "OpenAIMessage",
    "BaseMessage",
    "SystemMessage",
    "AssistantSystemMessage",
    "UserSystemMessage",
    "ChatMessage",
    "AssistantChatMessage",
    "UserChatMessage",
    "MessageType",
    "SystemMessageType",
    "ChatMessageType",
]
