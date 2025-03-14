# Refactoring Plan for WEB-AI-Startr.Team

Based on our code analysis, we've identified several key areas that need refactoring to reduce complexity and improve maintainability. This plan outlines concrete steps to simplify the codebase, focusing on the most complex modules first.

## Top Modules Requiring Refactoring

### 1. strteam.chatdev.phase (Complexity Score: 423.5)

This module has the highest complexity and contains numerous phase classes with duplicated logic. Problems include:

- Many similar class implementations with slight variations
- Long class methods with mixed responsibilities
- Duplicate code patterns across different phase types

**Refactoring Steps:**

1. **Create a unified Phase base class:**
   ```python
   class Phase:
       def __init__(self, name, agent_roles, prompt_template, **kwargs):
           self.name = name
           self.agent_roles = agent_roles
           self.prompt_template = prompt_template
           self.config = kwargs
           
       def execute(self, environment, max_turns=5, with_reflection=False):
           # Common execution logic
           self.before_execution(environment)
           result = self._execute_phase(environment, max_turns, with_reflection)
           self.after_execution(environment)
           return result
           
       def _execute_phase(self, environment, max_turns, with_reflection):
           # To be overridden by specific phases
           pass
           
       def before_execution(self, environment):
           # Preparation steps
           pass
           
       def after_execution(self, environment):
           # Cleanup steps
           pass
   ```

2. **Implement RecursivePhase:**
   ```python
   class RecursivePhase(Phase):
       def __init__(self, name, agent_roles, prompt_template, sub_phases, condition, max_depth=3, **kwargs):
           super().__init__(name, agent_roles, prompt_template, **kwargs)
           self.sub_phases = sub_phases
           self.condition = condition
           self.max_depth = max_depth
           
       def _execute_phase(self, environment, max_turns, with_reflection):
           depth = 0
           while depth < self.max_depth and not self._is_complete(environment):
               for sub_phase in self.sub_phases:
                   environment = sub_phase.execute(environment)
               depth += 1
           return environment
           
       def _is_complete(self, environment):
           # Evaluate condition to determine if recursion should stop
           return eval_condition(self.condition, environment)
   ```

3. **Migrate existing phases** to use these base classes, eliminating duplicate code

4. **Replace `composed_phase.py` module** with the `RecursivePhase` class

### 2. strteam.camel.agents.role_playing (Complexity Score: 195.0)

This module handles agent interactions but has become overly complex with many parameters and responsibilities.

**Refactoring Steps:**

1. **Extract interaction handler:**
   ```python
   class AgentInteractionHandler:
       def __init__(self, model_type, memory=None):
           self.model_type = model_type
           self.memory = memory
           
       def handle_interaction(self, assistant_agent, user_agent, message):
           # Process message through agents and handle response
           pass
   ```

2. **Simplify RolePlaying class:**
   ```python
   @log_arguments
   class RolePlaying:
       def __init__(
           self,
           assistant_role,
           user_role,
           task_prompt,
           model_type=ModelType.GPT_3_5_TURBO,
           with_task_planning=False,
           **kwargs
       ):
           self.assistant_role = assistant_role
           self.user_role = user_role
           self.task_prompt = task_prompt
           self.model_type = model_type
           
           # Create agents
           self.assistant_agent = self._create_assistant_agent(assistant_role, **kwargs)
           self.user_agent = self._create_user_agent(user_role, **kwargs)
           
           # Optional task planning
           self.task_plan = self._prepare_task_plan(task_prompt) if with_task_planning else None
           
           # Create interaction handler
           self.interaction_handler = AgentInteractionHandler(model_type, kwargs.get("memory"))
   ```

3. **Move critiquing logic** to a separate `CriticHandler` class

4. **Reduce the number of optional parameters** by grouping related ones into config objects

### 3. strteam.camel.agents.chat_agent (Complexity Score: 182.0)

This module has complex agent logic with too many responsibilities.

**Refactoring Steps:**

1. **Extract message handling to a separate class:**
   ```python
   class MessageProcessor:
       def __init__(self, role_name, role_type):
           self.role_name = role_name
           self.role_type = role_type
           
       def process_message(self, content):
           # Message processing logic
           pass
   ```

2. **Extract API communication logic:**
   ```python
   class ModelAPIClient:
       def __init__(self, model_type, model_config=None):
           self.model_type = model_type
           self.model_config = model_config or {}
           
       def generate_response(self, messages):
           # API interaction logic
           pass
   ```

3. **Simplify ChatAgent class by delegating responsibilities:**
   ```python
   class ChatAgent(BaseAgent):
       def __init__(self, system_message, model_type=None, model_config=None):
           self.system_message = system_message
           self.role_name = system_message.role_name
           self.role_type = system_message.role_type
           
           self.api_client = ModelAPIClient(model_type, model_config)
           self.message_processor = MessageProcessor(self.role_name, self.role_type)
           self.message_history = MessageHistory()
   ```

4. **Extract retry logic** to a separate utility decorator 

## General Refactoring Strategies

### 1. Configuration System Cleanup

Replace the multiple configuration systems with a single approach:

```
config/
├── schema.yaml          # Schema definition
├── companies/           # YAML company configurations
│   ├── Default.yaml
│   ├── Art.yaml
│   └── Human.yaml
└── recursive_flow.yaml  # New recursive flow definition
```

### 2. Module Organization

Reorganize modules for better separation of concerns:

```
strteam/
├── agents/              # Base agent system
│   ├── base.py          # Base agent classes
│   ├── messaging.py     # Message handling
│   └── specialized/     # Specialized agent types
├── phases/              # Phase system
│   ├── base.py          # Base phase classes
│   ├── recursive.py     # Recursive phase implementation
│   └── specialized/     # Specialized phase types
├── workflow/            # Workflow management
│   ├── chat_chain.py    # Main workflow engine
│   └── environment.py   # Execution environment
└── utils/              # Shared utilities
```

### 3. Code Duplication Elimination

1. **Create shared utility functions** for common operations
2. **Extract shared prompts** to a separate module
3. **Implement mixin classes** for shared behaviors

## Implementation Plan

### Phase 1: Configuration Cleanup
- Convert all JSON configs to YAML format
- Implement the new schema and validation system
- Migrate to the new unified configuration structure

### Phase 2: Core Module Refactoring
- Refactor Phase system (highest priority)
- Refactor RolePlaying system
- Refactor ChatAgent system

### Phase 3: Workflow Reimplementation
- Implement the recursive workflow model
- Migrate the ChatChain to use the new Phase system
- Update environment handling

### Phase 4: Final Cleanup
- Remove unnecessary files and deprecated code
- Update documentation to reflect new architecture
- Create tests for the refactored components

## Expected Benefits

- **Reduced complexity**: Simpler codebase with clearer responsibilities
- **Better maintainability**: Easier to understand and modify
- **Flexibility**: Recursive model allows more dynamic workflows
- **Scalability**: Cleaner architecture will support future extensions