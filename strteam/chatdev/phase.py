"""Phase management for conversational development processes.

This module implements a flexible and DRY approach to phases in the development
process, using dataclasses and duck typing for minimal repetition.
"""

import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List, Set, ClassVar, Callable, Type, Union
from functools import wraps
import inspect

from ..camel.agents import RolePlaying
from ..camel.messages import ChatMessage
from ..camel.typing import TaskType, ModelType
from .chat_env import ChatEnv
from .statistics import get_info
from .utils import log_visualize
from ..config.config_loader import config_loader


@dataclass
class ConversationMessage:
    """Represents a message in a conversation between agents."""
    content: str
    role_name: str
    

@dataclass
class ConversationContext:
    """Holds the context for a conversation between agents."""
    assistant_role_name: str
    user_role_name: str
    phase_name: str
    turn: int
    assistant_message: Optional[ChatMessage] = None
    user_message: Optional[ChatMessage] = None
    terminated: bool = False
    conclusion: Optional[str] = None
    
    def log_messages(self, role_play_session: RolePlaying) -> None:
        """Logs messages from both participants in the conversation."""
        if not (self.assistant_message or self.user_message):
            return
            
        conversation_meta = (
            f"**{self.assistant_role_name}<->{self.user_role_name} on : "
            f"{self.phase_name}, turn {self.turn}**\n\n"
        )
        
        # Log assistant message if available
        if self.assistant_message:
            log_visualize(
                role_play_session.assistant_agent.role_name,
                conversation_meta
                + "["
                + role_play_session.user_agent.system_message.content
                + "]\n"
                + self.assistant_message.content,
            )
            
        # Log user message if available
        if self.user_message:
            log_visualize(
                role_play_session.user_agent.role_name,
                conversation_meta
                + "["
                + role_play_session.assistant_agent.system_message.content
                + "]\n"
                + self.user_message.content,
            )
    
    def update_from_response(self, assistant_response, user_response) -> bool:
        """Updates the context based on agent responses."""
        should_end = False
        
        # Process assistant response
        if hasattr(assistant_response, 'msg') and isinstance(assistant_response.msg, ChatMessage):
            self.assistant_message = assistant_response.msg
            self.terminated = self.terminated or assistant_response.terminated
            
            # Check if there's an info marker in the message
            if hasattr(assistant_response, 'info') and assistant_response.info.get("info", False):
                self.conclusion = assistant_response.msg.content
                should_end = True
        
        # Process user response
        if hasattr(user_response, 'msg') and isinstance(user_response.msg, ChatMessage):
            self.user_message = user_response.msg
            self.terminated = self.terminated or user_response.terminated
            
            # Check if there's an info marker in the message
            if hasattr(user_response, 'info') and user_response.info.get("info", False):
                self.conclusion = user_response.msg.content
                should_end = True
        
        return should_end


@dataclass
class PhaseConfig:
    """Configuration for a phase."""
    name: str
    assistant_role: str
    user_role: str
    prompt: str
    role_prompts: Dict[str, str]
    model_type: ModelType
    max_turn_step: int = field(default_factory=lambda: config_loader.get_value('phase_config', 'default_turn_step', default=3))
    need_reflect: bool = False
    required_inputs: List[str] = field(default_factory=list)
    expected_outputs: List[str] = field(default_factory(list))


@dataclass
class PhaseEnvironment:
    """Environment context for a phase execution."""
    # Common fields used across phases
    task: str = ""
    description: str = ""
    modality: str = ""
    ideas: str = ""
    language: str = ""
    codes: str = ""
    
    # Additional fields for specific phases
    gui: str = ""
    comments: str = ""
    images: str = ""
    unimplemented_file: str = "" 
    test_reports: str = ""
    error_summary: str = ""
    review_comments: str = ""
    requirements: str = ""
    exist_bugs_flag: bool = False
    
    # Tracking state
    cycle_index: int = 0
    cycle_num: int = 1
    
    def update(self, data_dict: Dict[str, Any]) -> None:
        """Update environment with values from a dictionary."""
        for key, value in data_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert environment to a dictionary, filtering out empty values."""
        return {k: v for k, v in asdict(self).items() if v}


def log_arguments(func):
    """Decorator to log function arguments."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Skip detailed logging in production
        return func(*args, **kwargs)
    return wrapper


class Phase(ABC):
    """Base class for all conversation phases."""
    
    # Standard environment field mappings
    STANDARD_ENV_FIELDS: ClassVar[Dict[str, str]] = {
        'task': 'task_prompt',
        'description': 'task_description',
        'modality': 'modality',
        'ideas': 'ideas',
        'language': 'language'
    }
    
    # Method-based environment field mappings
    COMPLEX_ENV_FIELDS: ClassVar[Dict[str, str]] = {
        'codes': 'get_codes',
        'requirements': 'get_requirements'
    }
    
    def __init__(self, config: PhaseConfig):
        """Initialize with configuration."""
        self.config = config
        self.env = PhaseEnvironment()
        self.seminar_conclusion = None
        
        # Get phase definition from config
        phase_def = self._get_phase_def(config.name)
        
        # Extract inputs and outputs
        self.required_inputs = phase_def.get('inputs', [])
        self.expected_outputs = phase_def.get('outputs', [])
    
    def _get_phase_def(self, phase_name: str) -> Dict[str, Any]:
        """Get phase definition from config by name."""
        phase_configs = config_loader.load_config('phase_config').get('phases', [])
        
        # Find the phase config
        for phase_config in phase_configs:
            if phase_name in phase_config:
                return phase_config[phase_name]
        
        # Return empty dict if phase not found
        return {}
    
    def __getattr__(self, name):
        """Forward attribute access to config when not found on Phase."""
        try:
            return getattr(self.config, name)
        except AttributeError:
            raise AttributeError(f"{self.__class__.__name__} has no attribute '{name}'")
    
    def update_phase_env(self, chat_env: ChatEnv) -> None:
        """Update phase environment from chat environment."""
        env_data = {}
        
        # Add standard fields from env_dict
        for env_field, dict_key in self.STANDARD_ENV_FIELDS.items():
            if env_field in self.required_inputs and dict_key in chat_env.env_dict:
                env_data[env_field] = chat_env.env_dict[dict_key]
        
        # Add fields requiring method calls
        for env_field, method_name in self.COMPLEX_ENV_FIELDS.items():
            if env_field in self.required_inputs and hasattr(chat_env, method_name):
                method = getattr(chat_env, method_name)
                if callable(method):
                    env_data[env_field] = method()
                else:
                    env_data[env_field] = method
        
        # Update phase environment with data
        self.env.update(env_data)
    
    @abstractmethod
    def update_chat_env(self, chat_env: ChatEnv) -> ChatEnv:
        """Update chat environment with phase results."""
        pass
    
    @log_arguments
    def chatting(self, chat_env: ChatEnv, **kwargs) -> str:
        """Execute a conversation between agents."""
        # Extract or set defaults for key parameters
        task_prompt = chat_env.env_dict["task_prompt"]
        assistant_role = self.config.assistant_role
        user_role = self.config.user_role
        max_turns = kwargs.get('chat_turn_limit', self.config.max_turn_step)
        need_reflect = kwargs.get('need_reflect', self.config.need_reflect)
        memory = chat_env.memory if hasattr(chat_env, 'memory') else None
        placeholders = kwargs.get('placeholders', self.env.to_dict())
        
        # Validate roles exist
        if not chat_env.exist_employee(assistant_role):
            raise ValueError(f"{assistant_role} not recruited in ChatEnv.")
        if not chat_env.exist_employee(user_role):
            raise ValueError(f"{user_role} not recruited in ChatEnv.")
        
        # Initialize role play session
        role_play_session = RolePlaying(
            assistant_role_name=assistant_role,
            user_role_name=user_role,
            task_prompt=task_prompt,
            memory=memory,
            model_type=self.config.model_type,
            background_prompt=chat_env.config.background_prompt,
        )
        
        # Start conversation
        _, input_user_msg = role_play_session.init_chat(
            None, placeholders, self.config.prompt
        )
        
        # Handle conversation turns
        seminar_conclusion = None
        for turn in range(max_turns):
            # Get responses from both agents
            assistant_response, user_response = role_play_session.step(
                input_user_msg, max_turns == 1
            )
            
            # Process conversation
            context = ConversationContext(
                assistant_role_name=assistant_role,
                user_role_name=user_role,
                phase_name=self.config.name,
                turn=turn
            )
            
            # Update context and check if conversation should end
            should_end = context.update_from_response(assistant_response, user_response)
            context.log_messages(role_play_session)
            
            if should_end:
                seminar_conclusion = context.conclusion
                break
            elif context.terminated:
                break
            
            # Continue conversation if appropriate
            if max_turns > 1 and isinstance(user_response.msg, ChatMessage):
                input_user_msg = user_response.msg
            else:
                break
        
        # Handle reflection if needed
        if need_reflect and (not seminar_conclusion or seminar_conclusion == ""):
            reflection = self._reflect(task_prompt, role_play_session, chat_env)
            seminar_conclusion = f"<INFO> {reflection}"
        else:
            seminar_conclusion = assistant_response.msg.content
        
        # Log and extract conclusion
        log_visualize("**[Seminar Conclusion]**:\n\n {}".format(seminar_conclusion))
        if "<INFO>" in seminar_conclusion:
            seminar_conclusion = seminar_conclusion.split("<INFO>")[-1].strip()
            
        return seminar_conclusion
    
    def _reflect(self, task_prompt: str, role_play_session: RolePlaying, chat_env: ChatEnv) -> str:
        """Perform reflection on conversation results."""
        # Get conversation messages
        longer_messages = (
            role_play_session.assistant_agent.stored_messages
            if len(role_play_session.assistant_agent.stored_messages) >= len(role_play_session.user_agent.stored_messages)
            else role_play_session.user_agent.stored_messages
        )
        
        # Format messages for reflection
        formatted_messages = [
            f"{msg.role_name}: {msg.content.replace('\n\n', '\n')}"
            for msg in longer_messages
        ]
        messages_text = "\n\n".join(formatted_messages)
        
        # Get reflection question based on phase name
        reflection_config = config_loader.load_config('phase_config').get('reflection_questions', {})
        question = reflection_config.get(
            self.config.name,
            f"Based on the conversation, summarize the key conclusions about {self.config.name}."
        )
        
        # Get reflection prompt from config
        reflection_prompt = config_loader.load_config('phase_config').get(
            'reflection_prompt',
            "Here is a conversation between two roles: {conversations} {question}"
        )
        
        # Create reflection config
        reflection_config = PhaseConfig(
            name="Reflection",
            assistant_role="Chief Executive Officer",
            user_role="Counselor",
            prompt=reflection_prompt,
            role_prompts=self.config.role_prompts,
            model_type=self.config.model_type,
            max_turn_step=1,
            need_reflect=False
        )
        
        # Use a temporary reflection phase
        reflection_phase = SimplePhase(reflection_config)
        
        # Get reflection
        reflected_content = reflection_phase.chatting(
            chat_env=chat_env,
            task_prompt=task_prompt,
            placeholders={"conversations": messages_text, "question": question},
            memory=chat_env.memory
        )
        
        return reflected_content
    
    def execute(self, chat_env: ChatEnv) -> ChatEnv:
        """Execute the phase."""
        # Update environment with context
        self.update_phase_env(chat_env)
        
        # Execute conversation
        self.seminar_conclusion = self.chatting(
            chat_env=chat_env,
            chat_turn_limit=self.config.max_turn_step,
            need_reflect=self.config.need_reflect
        )
        
        # Update chat environment with results
        return self.update_chat_env(chat_env)


class SimplePhase(Phase):
    """Basic phase implementation."""
    
    def update_chat_env(self, chat_env: ChatEnv) -> ChatEnv:
        """Default implementation extracts first expected output."""
        if self.expected_outputs and len(self.expected_outputs) > 0:
            main_output = self.expected_outputs[0]
            chat_env.env_dict[main_output] = self.seminar_conclusion
        return chat_env


class DemandAnalysis(SimplePhase):
    """Analyze user demands to determine product modality."""
    
    def update_chat_env(self, chat_env: ChatEnv) -> ChatEnv:
        if self.seminar_conclusion:
            chat_env.env_dict["modality"] = (
                self.seminar_conclusion.lower().replace(".", "").strip()
            )
        return chat_env


class ChooseLanguage(SimplePhase):
    """Select programming language for implementation."""
    
    def update_chat_env(self, chat_env: ChatEnv) -> ChatEnv:
        if self.seminar_conclusion:
            chat_env.env_dict["language"] = (
                self.seminar_conclusion.lower().replace(".", "").strip()
            )
        else:
            # Get default from config
            default_language = config_loader.load_config('phase_config').get('default_language', 'Python')
            chat_env.env_dict["language"] = default_language
        return chat_env


class Coding(SimplePhase):
    """Implement code based on requirements."""
    
    def update_phase_env(self, chat_env: ChatEnv) -> None:
        # Call parent implementation first
        super().update_phase_env(chat_env)
        
        # Add GUI information if enabled
        if chat_env.config.gui_design:
            language = chat_env.env_dict.get("language", "").lower()
            
            # Get framework options from config
            gui_config = config_loader.load_config('phase_config').get('gui_frameworks', {})
            
            # Find appropriate frameworks for this language
            frameworks = []
            for lang, options in gui_config.items():
                if lang in language:
                    frameworks = options
                    break
            
            if not frameworks:
                frameworks = gui_config.get('default', ['appropriate GUI framework'])
            
            # Format GUI message
            template = config_loader.load_config('phase_config').get(
                'gui_prompt', 
                "The software should have a graphical user interface (GUI) using {frameworks}."
            )
            self.env.gui = template.format(frameworks=", ".join(frameworks))
    
    def update_chat_env(self, chat_env: ChatEnv) -> ChatEnv:
        # Update code with conclusion
        chat_env.update_codes(self.seminar_conclusion)
        
        # Handle case where no valid code was extracted
        if len(chat_env.codes.codebooks) == 0:
            language = chat_env.env_dict.get("language", "").lower()
            task = chat_env.env_dict.get("task_prompt", "")
            
            # Log the issue
            log_visualize("**[Warning]**: No valid code blocks were parsed from the agent's response.")
            
            # Get fallback templates from config
            templates = config_loader.load_config('phase_config').get('fallback_templates', {})
            
            # Determine appropriate template and file extension
            template = templates.get('default', "// No code was generated. Please implement: {task}")
            ext = "txt"
            
            for lang, lang_template in templates.items():
                if lang in language:
                    template = lang_template
                    ext = templates.get(f"{lang}_ext", lang)
                    break
            
            # Create fallback file
            chat_env.codes.codebooks[f"main.{ext}"] = template.format(task=task)
            log_visualize("**[Recovery]**: Created basic starter file.")
        
        # Save code to files
        chat_env.rewrite_codes("Coding Complete")
        
        # Log software info
        log_visualize(
            "**[Software Info]**:\n\n {}".format(
                get_info(chat_env.env_dict["directory"], "")
            )
        )
        
        return chat_env


class CodeReviewComment(SimplePhase):
    """Generate code review comments."""
    
    def update_phase_env(self, chat_env: ChatEnv) -> None:
        super().update_phase_env(chat_env)
        self.env.images = ", ".join(getattr(chat_env, 'incorporated_images', []))
    
    def update_chat_env(self, chat_env: ChatEnv) -> ChatEnv:
        chat_env.env_dict["review_comments"] = self.seminar_conclusion
        return chat_env


class CodeReviewModification(SimplePhase):
    """Implement modifications based on code review."""
    
    def update_phase_env(self, chat_env: ChatEnv) -> None:
        super().update_phase_env(chat_env)
        self.env.comments = chat_env.env_dict.get("review_comments", "")
    
    def update_chat_env(self, chat_env: ChatEnv) -> ChatEnv:
        if "```" in self.seminar_conclusion.lower():
            chat_env.update_codes(self.seminar_conclusion)
            chat_env.rewrite_codes(f"Review #{self.env.cycle_index} Complete")
            
            log_visualize(
                "**[Software Info]**:\n\n {}".format(
                    get_info(chat_env.env_dict["directory"], "")
                )
            )
        
        return chat_env


class TestErrorSummary(SimplePhase):
    """Analyze test results and summarize errors."""
    
    def update_phase_env(self, chat_env: ChatEnv) -> None:
        super().update_phase_env(chat_env)
        
        # Run tests and collect results
        chat_env.generate_images_from_codes()
        exist_bugs, test_reports = chat_env.exist_bugs()
        
        self.env.test_reports = test_reports
        self.env.exist_bugs_flag = exist_bugs
        
        log_visualize("**[Test Reports]**:\n\n{}".format(test_reports))
    
    def execute(self, chat_env: ChatEnv) -> ChatEnv:
        """Handle special case for module errors."""
        self.update_phase_env(chat_env)
        
        # Handle module not found errors automatically
        if "ModuleNotFoundError" in self.env.test_reports:
            chat_env.fix_module_not_found_error(self.env.test_reports)
            log_visualize(f"Software Test Engineer found ModuleNotFoundError:\n{self.env.test_reports}\n")
            
            # Extract module names from error messages
            module_names = [
                match.group(1) 
                for match in re.finditer(r"No module named '(\S+)'", self.env.test_reports, re.DOTALL)
            ]
            
            # Generate and log pip commands
            if module_names:
                pip_commands = [f"pip install {module}" for module in module_names]
                pip_display = "\n".join([f"```bash\n{cmd}\n```" for cmd in pip_commands])
                log_visualize(f"Programmer resolving dependencies:\n{pip_display}\n")
            
            self.seminar_conclusion = "Dependencies installed"
        else:
            # Normal processing
            self.seminar_conclusion = self.chatting(chat_env=chat_env)
        
        return self.update_chat_env(chat_env)
    
    def update_chat_env(self, chat_env: ChatEnv) -> ChatEnv:
        chat_env.env_dict["error_summary"] = self.seminar_conclusion
        chat_env.env_dict["test_reports"] = self.env.test_reports
        return chat_env


class TestModification(SimplePhase):
    """Implement fixes based on test results."""
    
    def update_phase_env(self, chat_env: ChatEnv) -> None:
        super().update_phase_env(chat_env)
        self.env.test_reports = chat_env.env_dict.get("test_reports", "")
        self.env.error_summary = chat_env.env_dict.get("error_summary", "")
    
    def update_chat_env(self, chat_env: ChatEnv) -> ChatEnv:
        if "```" in self.seminar_conclusion.lower():
            chat_env.update_codes(self.seminar_conclusion)
            chat_env.rewrite_codes(f"Test #{self.env.cycle_index} Complete")
            
            log_visualize(
                "**[Software Info]**:\n\n {}".format(
                    get_info(chat_env.env_dict["directory"], "")
                )
            )
        
        return chat_env


class EnvironmentDescription(SimplePhase):
    """Generate environment description and requirements."""
    
    def update_chat_env(self, chat_env: ChatEnv) -> ChatEnv:
        chat_env._update_requirements(self.seminar_conclusion)
        chat_env.rewrite_requirements()
        
        log_visualize(
            "**[Software Info]**:\n\n {}".format(
                get_info(chat_env.env_dict["directory"], "")
            )
        )
        
        return chat_env


class ComposedPhase(Phase):
    """A phase that contains and executes subphases."""
    
    def __init__(self, config: PhaseConfig, subphases: List[Phase] = None):
        """Initialize with config and optional subphases."""
        super().__init__(config)
        self.subphases = subphases or []
        
        # Load cycle count from config
        phase_def = self._get_phase_def(config.name)
        self.cycle_num = phase_def.get('cycleNum', 1)
        self.max_depth = phase_def.get('max_depth', 3)
    
    def add_subphase(self, phase: Phase) -> None:
        """Add a subphase to this composed phase."""
        self.subphases.append(phase)
    
    def update_chat_env(self, chat_env: ChatEnv) -> ChatEnv:
        """Default implementation returns unmodified environment."""
        return chat_env
    
    def execute(self, chat_env: ChatEnv) -> ChatEnv:
        """Execute all subphases in sequence."""
        self.update_phase_env(chat_env)
        
        # Execute each subphase for the specified number of cycles
        for cycle in range(self.cycle_num):
            # Update cycle index in environment
            self.env.cycle_index = cycle + 1
            self.env.cycle_num = self.cycle_num
            
            for subphase in self.subphases:
                # Pass cycle information to subphase
                subphase.env.cycle_index = cycle + 1
                subphase.env.cycle_num = self.cycle_num
                
                # Execute subphase
                chat_env = subphase.execute(chat_env)
        
        return chat_env


class PhaseFactory:
    """Factory for creating phase instances from configuration."""
    
    @classmethod
    def create_phase(cls, phase_name: str, role_prompts: Dict[str, str], model_type: ModelType = None) -> Phase:
        """Create a phase instance based on configuration."""
        # Find phase configuration in phase_config.yaml
        phases_config = config_loader.load_config('phase_config').get('phases', [])
        phase_def = None
        
        # Scan each phase config item to find the one with our phase name
        for phase_item in phases_config:
            if phase_name in phase_item:
                phase_def = phase_item[phase_name]
                break
        
        if not phase_def:
            raise ValueError(f"Phase {phase_name} not found in configuration")
        
        # Get phase type and create appropriate phase
        phase_type = phase_def.get('phaseType')
        
        if phase_type == 'SimplePhase':
            # Create a simple phase
            config = PhaseConfig(
                name=phase_name,
                assistant_role=phase_def.get('roles', {}).get('assistant'),
                user_role=phase_def.get('roles', {}).get('user'),
                prompt=cls._get_phase_prompt(phase_name),
                role_prompts=role_prompts,
                model_type=model_type or cls._get_default_model(),
                max_turn_step=phase_def.get('max_turn_step', 3),
                need_reflect=phase_def.get('need_reflect', False),
                required_inputs=phase_def.get('inputs', []),
                expected_outputs=phase_def.get('outputs', [])
            )
            
            # Create specific phase class if available
            phase_class = cls._get_phase_class(phase_name)
            return phase_class(config)
        
        elif phase_type == 'ComposedPhase':
            # Create a composed phase with subphases
            config = PhaseConfig(
                name=phase_name,
                assistant_role="",  # Not needed for composed phases
                user_role="",  # Not needed for composed phases
                prompt="",  # Not needed for composed phases
                role_prompts=role_prompts,
                model_type=model_type or cls._get_default_model(),
                max_turn_step=phase_def.get('max_turn_step', 3),
                need_reflect=False
            )
            
            composed_phase = ComposedPhase(config)
            
            # Create and add subphases
            for subphase_def in phase_def.get('Composition', []):
                for subphase_name, _ in subphase_def.items():
                    subphase = cls.create_phase(subphase_name, role_prompts, model_type)
                    composed_phase.add_subphase(subphase)
            
            return composed_phase
        
        else:
            raise ValueError(f"Unknown phase type: {phase_type}")
    
    @classmethod
    def _get_phase_class(cls, phase_name: str) -> Type[Phase]:
        """Get the appropriate phase class for a phase name."""
        # Map phase names to classes
        phase_classes = {
            'DemandAnalysis': DemandAnalysis,
            'ChooseLanguage': ChooseLanguage,
            'Coding': Coding,
            'CodeReviewComment': CodeReviewComment,
            'CodeReviewModification': CodeReviewModification,
            'TestErrorSummary': TestErrorSummary,
            'TestModification': TestModification,
            'EnvironmentDescription': EnvironmentDescription
        }
        
        # Return specific class or fallback to SimplePhase
        return phase_classes.get(phase_name, SimplePhase)
    
    @classmethod
    def _get_phase_prompt(cls, phase_name: str) -> str:
        """Get prompt for a specific phase from config."""
        prompts_config = config_loader.load_config('phase_config').get('prompts', {})
        return prompts_config.get(phase_name, f"Execute the {phase_name} phase.")
    
    @classmethod
    def _get_default_model(cls) -> ModelType:
        """Get default model type from config."""
        model_name = config_loader.load_config('phase_config').get('default_model', "gpt-3.5-turbo")
        
        # Convert string to ModelType
        for model in ModelType:
            if model.name == model_name:
                return model
        
        # Fallback to default
        return ModelType.GPT_3_5_TURBO
