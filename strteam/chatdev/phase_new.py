"""
New Phase System for WEB-AI-Startr.Team

This module contains the refactored Phase system with a unified base class and support
for recursion, replacing the old phase.py and composed_phase.py.
"""

import os
import re
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable

from ..camel.agents import RolePlaying
from ..camel.messages import ChatMessage
from ..camel.typing import TaskType, ModelType
from .chat_env import ChatEnv
from .statistics import get_info
from .utils import log_visualize, log_arguments


class Phase:
    """Base Phase class for all phases in the software development process."""
    
    @log_arguments
    def __init__(
        self,
        name: str,
        assistant_role_name: str,
        user_role_name: str,
        phase_prompt: str,
        role_prompts: Dict[str, str],
        model_type: ModelType = ModelType.GPT_3_5_TURBO,
        log_filepath: Optional[str] = None,
        **kwargs
    ):
        """Initialize the Phase.
        
        Args:
            name: Name of the phase
            assistant_role_name: Name of the assistant's role
            user_role_name: Name of the user's role
            phase_prompt: The prompt template for this phase
            role_prompts: Dictionary mapping role names to their prompt templates
            model_type: Type of LLM to use
            log_filepath: Path to log file
            **kwargs: Additional configuration
        """
        self.name = name
        self.assistant_role_name = assistant_role_name
        self.user_role_name = user_role_name
        self.phase_prompt = phase_prompt
        self.model_type = model_type
        self.log_filepath = log_filepath
        self.config = kwargs
        
        # Store role prompts
        self.assistant_role_prompt = role_prompts.get(assistant_role_name, "")
        self.user_role_prompt = role_prompts.get(user_role_name, "")
        
        # Debug logger
        self.logger = logging.getLogger(f"Phase[{name}]")
        
    def execute(self, chat_env: ChatEnv, max_turns: int = 10, with_reflection: bool = False) -> ChatEnv:
        """Execute the phase and return the updated chat environment.
        
        Args:
            chat_env: The chat environment with the current state
            max_turns: Maximum number of conversation turns
            with_reflection: Whether to include reflection at the end
            
        Returns:
            ChatEnv: The updated chat environment
        """
        # Prepare phase execution
        self._before_execution(chat_env)
        
        # Execute the core phase logic
        chat_env = self._execute_phase(chat_env, max_turns, with_reflection)
        
        # Clean up after execution
        self._after_execution(chat_env)
        
        return chat_env
    
    def _before_execution(self, chat_env: ChatEnv):
        """Set up the phase before execution.
        
        Args:
            chat_env: The chat environment to prepare
        """
        log_visualize(f"Phase: {self.name} Started")
    
    def _after_execution(self, chat_env: ChatEnv):
        """Clean up after phase execution.
        
        Args:
            chat_env: The chat environment to clean up
        """
        log_visualize(f"Phase: {self.name} Finished")
    
    def _compose_task_prompt(self, chat_env: ChatEnv) -> str:
        """Compose the full task prompt with environment variables.
        
        Args:
            chat_env: Chat environment with context
            
        Returns:
            str: The composed task prompt
        """
        task_prompt = self.phase_prompt
        
        # Replace {variables} with actual values from environment
        for key, value in chat_env.env_dict.items():
            if isinstance(value, str):
                pattern = '{' + key + '}'
                task_prompt = task_prompt.replace(pattern, value)
        
        return task_prompt
    
    def _execute_phase(self, chat_env: ChatEnv, max_turns: int, with_reflection: bool) -> ChatEnv:
        """Execute the core phase logic.
        
        This implementation handles the basic role-playing conversation.
        Override this method to change how the phase executes.
        
        Args:
            chat_env: Chat environment with context
            max_turns: Maximum number of conversation turns
            with_reflection: Whether to include reflection
            
        Returns:
            ChatEnv: Updated chat environment
        """
        # Create role-playing session
        task_prompt = self._compose_task_prompt(chat_env)
        
        role_play = RolePlaying(
            assistant_role_name=self.assistant_role_name,
            assistant_role_prompt=self.assistant_role_prompt,
            user_role_name=self.user_role_name,
            user_role_prompt=self.user_role_prompt,
            task_type=TaskType.STARTR_TEAM,
            task_prompt=task_prompt,
            with_task_specify=False,
            model_type=self.model_type,
        )

        # Log phase start details
        log_visualize(self.name, task_prompt, chat_env.log_filepath)

        # Initialize conversation
        init_assistant_msg = None
        init_user_msg = None
        
        # Get seed message for the assistant if provided in the phase config
        if "seed_message" in self.config:
            init_assistant_msg = ChatMessage(
                role_name=self.assistant_role_name,
                role="assistant",
                content=self.config["seed_message"],
            )
        
        # Run conversation
        _, user_msg = role_play.init_chat(init_assistant_msg, init_user_msg, task_prompt)
        assistant_msg = None
        
        # Conversation loop
        turns = 0
        while turns < max_turns:
            assistant_msg, user_msg = role_play.step(user_msg)
            
            # Check for stopping conditions
            if self._is_conversation_finished(assistant_msg, user_msg):
                break
                
            turns += 1
            
            # Log turn count
            self.logger.info(f"Turn {turns}/{max_turns} completed")
        
        # Process the results from conversation
        if assistant_msg is not None:
            self._process_conversation_results(chat_env, role_play, assistant_msg)
        
        # Add optional reflection
        if with_reflection:
            self._add_reflection(chat_env, role_play, task_prompt)
            
        return chat_env
    
    def _is_conversation_finished(self, assistant_msg: ChatMessage, user_msg: ChatMessage) -> bool:
        """Check if the conversation should be terminated.
        
        Args:
            assistant_msg: Last message from the assistant
            user_msg: Last message from the user
            
        Returns:
            bool: True if conversation should end, False otherwise
        """
        # Default implementation checks for 'TERMINATE' in the messages
        for msg in [assistant_msg, user_msg]:
            if msg and "TERMINATE" in msg.content:
                return True
        return False
    
    def _process_conversation_results(self, chat_env: ChatEnv, role_play: RolePlaying, assistant_msg: ChatMessage):
        """Process the results from the conversation.
        
        Args:
            chat_env: Chat environment to update
            role_play: The role playing session that was executed
            assistant_msg: The final message from the assistant
        """
        # Default implementation does nothing - override in subclasses
        pass
    
    def _add_reflection(self, chat_env: ChatEnv, role_play: RolePlaying, task_prompt: str):
        """Add reflection to the process.
        
        Args:
            chat_env: Chat environment to update
            role_play: The completed role playing session
            task_prompt: The task prompt used
        """
        reflection_prompt = (
            f"Let's reflect on the {self.name} phase we just completed. "
            f"What were the key decisions and outcomes? How could this be improved in the future? "
            f"What are the strengths and weaknesses of the current solution? "
            f"Please provide a brief reflection."
        )
        
        # Create a reflection session with the assistant
        reflection_play = RolePlaying(
            assistant_role_name=self.assistant_role_name,
            assistant_role_prompt=self.assistant_role_prompt,
            user_role_name="Reflector",  # Different role for reflection
            user_role_prompt="You help reflect on the process to improve future iterations.",
            task_type=TaskType.STARTR_TEAM,
            task_prompt=reflection_prompt,
            with_task_specify=False,
            model_type=self.model_type,
        )
        
        # Run a single reflection turn
        _, user_msg = reflection_play.init_chat(None, None, reflection_prompt)
        assistant_response, _ = reflection_play.step(user_msg)
        
        # Log the reflection
        log_visualize(f"{self.name} Reflection", assistant_response.msg.content)


class RecursivePhase(Phase):
    """A phase that can execute sub-phases recursively based on a condition."""
    
    @log_arguments
    def __init__(
        self,
        name: str,
        assistant_role_name: str,
        user_role_name: str,
        phase_prompt: str,
        role_prompts: Dict[str, str],
        sub_phases: List[Phase],
        condition_func: Callable[[ChatEnv], bool],
        max_depth: int = 3,
        model_type: ModelType = ModelType.GPT_3_5_TURBO,
        log_filepath: Optional[str] = None,
        **kwargs
    ):
        """Initialize the RecursivePhase.
        
        Args:
            name: Name of the phase
            assistant_role_name: Name of the assistant's role
            user_role_name: Name of the user's role
            phase_prompt: The prompt template for this phase
            role_prompts: Dictionary mapping role names to their prompt templates
            sub_phases: List of sub-phases to execute recursively
            condition_func: Function that determines if recursion should continue
            max_depth: Maximum recursion depth
            model_type: Type of LLM to use
            log_filepath: Path to log file
            **kwargs: Additional configuration
        """
        super().__init__(
            name=name,
            assistant_role_name=assistant_role_name,
            user_role_name=user_role_name,
            phase_prompt=phase_prompt,
            role_prompts=role_prompts,
            model_type=model_type,
            log_filepath=log_filepath,
            **kwargs
        )
        self.sub_phases = sub_phases
        self.condition_func = condition_func
        self.max_depth = max_depth
    
    def _execute_phase(self, chat_env: ChatEnv, max_turns: int, with_reflection: bool) -> ChatEnv:
        """Execute the recursive phase.
        
        Args:
            chat_env: Chat environment with context
            max_turns: Maximum number of conversation turns
            with_reflection: Whether to include reflection
            
        Returns:
            ChatEnv: Updated chat environment
        """
        # First execute the parent phase normally
        chat_env = super()._execute_phase(chat_env, max_turns, False)  # No reflection yet
        
        # Then execute sub-phases recursively
        depth = 0
        while depth < self.max_depth and not self.condition_func(chat_env):
            log_visualize(f"{self.name} - Recursion Cycle {depth + 1}/{self.max_depth}")
            
            # Execute all sub-phases in order
            for sub_phase in self.sub_phases:
                chat_env = sub_phase.execute(chat_env, max_turns, False)
            
            depth += 1
        
        # Add reflection at the end if requested
        if with_reflection:
            self._add_recursion_reflection(chat_env, depth)
            
        return chat_env
    
    def _add_recursion_reflection(self, chat_env: ChatEnv, depth_reached: int):
        """Add reflection about the recursive process.
        
        Args:
            chat_env: Chat environment to update
            depth_reached: The recursion depth that was reached
        """
        reflection_prompt = (
            f"The {self.name} phase completed after {depth_reached} recursive cycles "
            f"(maximum allowed: {self.max_depth}). "
            f"Let's reflect on this recursive process. Were all the necessary aspects addressed? "
            f"How did the solution evolve through the iterations? "
            f"What improvements could be made to the recursive approach in the future?"
        )
        
        # Create a reflection session with the assistant
        reflection_play = RolePlaying(
            assistant_role_name=self.assistant_role_name,
            assistant_role_prompt=self.assistant_role_prompt,
            user_role_name="Reflector",
            user_role_prompt="You help reflect on recursive processes to improve future iterations.",
            task_type=TaskType.STARTR_TEAM,
            task_prompt=reflection_prompt,
            with_task_specify=False,
            model_type=self.model_type,
        )
        
        # Run a single reflection turn
        _, user_msg = reflection_play.init_chat(None, None, reflection_prompt)
        assistant_response, _ = reflection_play.step(user_msg)
        
        # Log the reflection
        log_visualize(f"{self.name} Recursive Reflection", assistant_response.msg.content)


# Common condition functions for RecursivePhase
def condition_always_true(chat_env: ChatEnv) -> bool:
    """Always returns True to stop recursion after one cycle."""
    return True

def condition_always_false(chat_env: ChatEnv) -> bool:
    """Always returns False to always reach max_depth."""
    return False

def condition_task_complete(chat_env: ChatEnv) -> bool:
    """Check if the task is marked as complete in the environment."""
    return chat_env.env_dict.get("task_complete", False)