"""
Specialized Phase Implementations for WEB-AI-Startr.Team

This module contains specialized Phase implementations for different development tasks.
These classes extend the base Phase class with specific behavior for each development phase.
"""

import re
import os
from typing import Dict, List, Any, Optional

from ..camel.agents import RolePlaying
from ..camel.messages import ChatMessage
from ..camel.typing import ModelType
from .chat_env import ChatEnv
from .phase_new import Phase
from .utils import log_visualize


class TaskDesignPhase(Phase):
    """Phase for designing a task solution."""
    
    def _process_conversation_results(self, chat_env: ChatEnv, role_play: RolePlaying, assistant_msg: ChatMessage):
        """Extract design decisions from conversation."""
        content = assistant_msg.content
        
        # Extract and store high-level design in environment
        chat_env.env_dict["high_level_design"] = content
        log_visualize("High-level design stored in environment")


class DesignReviewPhase(Phase):
    """Phase for reviewing and refining a design."""
    
    def _process_conversation_results(self, chat_env: ChatEnv, role_play: RolePlaying, assistant_msg: ChatMessage):
        """Process design review feedback."""
        content = assistant_msg.content
        
        # Store design review feedback
        if "design_feedback" not in chat_env.env_dict:
            chat_env.env_dict["design_feedback"] = []
        
        chat_env.env_dict["design_feedback"].append(content)
        log_visualize(f"Design review #{len(chat_env.env_dict['design_feedback'])} stored")


class CodingPhase(Phase):
    """Phase for implementing code based on a design."""
    
    def _process_conversation_results(self, chat_env: ChatEnv, role_play: RolePlaying, assistant_msg: ChatMessage):
        """Process and extract code from conversation."""
        content = assistant_msg.content
        
        # Try to find code blocks with filename headers
        file_pattern = r"```[\w\s]*\n(?:#\s*([^\n]+)|\/\/\s*([^\n]+)|\/\*\s*([^\n]+)\s*\*\/|\"\"\"\s*([^\n]+)\s*\"\"\"|<!--\s*([^\n]+)\s*-->)\n(.*?)```"
        code_blocks = re.finditer(file_pattern, content, re.DOTALL)
        
        # Process each code block
        for match in code_blocks:
            # Extract filename and code content
            filename = next(filter(None, match.groups()[0:5]), "unnamed_file.txt")
            filename = filename.strip()
            code_content = match.group(6)
            
            # Clean up filename if needed
            if ":" in filename:
                filename = filename.split(":", 1)[1].strip()
            
            # Store the code in chat environment
            chat_env.codes.add_code(filename, code_content)
            log_visualize(f"Code added for file: {filename}")
        
        # Check if any code was extracted
        if chat_env.codes.get_all_codes():
            log_visualize("Code implementation captured and stored")
        else:
            log_visualize("No code implementation found in the message")


class CodeReviewPhase(Phase):
    """Phase for reviewing code quality and correctness."""
    
    def _process_conversation_results(self, chat_env: ChatEnv, role_play: RolePlaying, assistant_msg: ChatMessage):
        """Process code review feedback."""
        content = assistant_msg.content
        
        # Store code review feedback
        if "code_reviews" not in chat_env.env_dict:
            chat_env.env_dict["code_reviews"] = []
        
        chat_env.env_dict["code_reviews"].append(content)
        log_visualize(f"Code review #{len(chat_env.env_dict['code_reviews'])} stored")
        
        # Try to extract specific code suggestions
        suggestion_pattern = r"```[\w\s]*\n(?:#\s*([^\n]+)|\/\/\s*([^\n]+)|\/\*\s*([^\n]+)\s*\*\/|\"\"\"\s*([^\n]+)\s*\"\"\"|<!--\s*([^\n]+)\s*-->)\n(.*?)```"
        suggestions = re.finditer(suggestion_pattern, content, re.DOTALL)
        
        for match in suggestions:
            # Extract filename and suggested code
            filename = next(filter(None, match.groups()[0:5]), "").strip()
            if ":" in filename:
                filename = filename.split(":", 1)[1].strip()
            
            if filename in chat_env.codes.get_codes_filenames():
                code_content = match.group(6)
                # Store the suggested revision for later reference
                if "code_suggestions" not in chat_env.env_dict:
                    chat_env.env_dict["code_suggestions"] = {}
                
                if filename not in chat_env.env_dict["code_suggestions"]:
                    chat_env.env_dict["code_suggestions"][filename] = []
                
                chat_env.env_dict["code_suggestions"][filename].append(code_content)
                log_visualize(f"Code suggestion for {filename} stored")


class DebugPhase(Phase):
    """Phase for debugging code and fixing issues."""
    
    def _process_conversation_results(self, chat_env: ChatEnv, role_play: RolePlaying, assistant_msg: ChatMessage):
        """Process debugging results and apply fixes."""
        content = assistant_msg.content
        
        # Extract code fixes
        file_pattern = r"```[\w\s]*\n(?:#\s*([^\n]+)|\/\/\s*([^\n]+)|\/\*\s*([^\n]+)\s*\*\/|\"\"\"\s*([^\n]+)\s*\"\"\"|<!--\s*([^\n]+)\s*-->)\n(.*?)```"
        code_blocks = re.finditer(file_pattern, content, re.DOTALL)
        
        fixed_files = []
        for match in code_blocks:
            # Extract filename and code content
            filename = next(filter(None, match.groups()[0:5]), "").strip()
            if ":" in filename:
                filename = filename.split(":", 1)[1].strip()
            
            if filename in chat_env.codes.get_codes_filenames():
                code_content = match.group(6)
                # Apply the fix directly
                chat_env.codes.update_code(filename, code_content)
                fixed_files.append(filename)
                log_visualize(f"Fixed code in: {filename}")
        
        # Store debugging session
        if "debug_sessions" not in chat_env.env_dict:
            chat_env.env_dict["debug_sessions"] = []
        
        session_info = {
            "description": content,
            "fixed_files": fixed_files
        }
        chat_env.env_dict["debug_sessions"].append(session_info)
        log_visualize(f"Debug session #{len(chat_env.env_dict['debug_sessions'])} stored")


class TestingPhase(Phase):
    """Phase for testing code and verifying functionality."""
    
    def _process_conversation_results(self, chat_env: ChatEnv, role_play: RolePlaying, assistant_msg: ChatMessage):
        """Process testing results."""
        content = assistant_msg.content
        
        # Extract test results
        test_pattern = r"(?i)TEST RESULTS?:(.*?)(?:\n\n|\Z)"
        test_match = re.search(test_pattern, content, re.DOTALL)
        
        test_results = {}
        if test_match:
            test_results["summary"] = test_match.group(1).strip()
        else:
            test_results["summary"] = "No specific test results found"
        
        # Look for test code
        file_pattern = r"```[\w\s]*\n(?:#\s*([^\n]+)|\/\/\s*([^\n]+)|\/\*\s*([^\n]+)\s*\*\/|\"\"\"\s*([^\n]+)\s*\"\"\"|<!--\s*([^\n]+)\s*-->)\n(.*?)```"
        code_blocks = re.finditer(file_pattern, content, re.DOTALL)
        
        test_files = []
        for match in code_blocks:
            # Extract filename and code content
            filename = next(filter(None, match.groups()[0:5]), "").strip()
            if ":" in filename:
                filename = filename.split(":", 1)[1].strip()
            
            # If it looks like a test file
            if "test" in filename.lower():
                code_content = match.group(6)
                # Add the test code
                chat_env.codes.add_code(filename, code_content)
                test_files.append(filename)
                log_visualize(f"Test code added: {filename}")
        
        test_results["test_files"] = test_files
        
        # Store test results
        if "test_results" not in chat_env.env_dict:
            chat_env.env_dict["test_results"] = []
        
        chat_env.env_dict["test_results"].append(test_results)
        log_visualize(f"Test results #{len(chat_env.env_dict['test_results'])} stored")
        
        # Check if all tests pass
        if "all tests pass" in content.lower() or "all test cases pass" in content.lower():
            chat_env.env_dict["tests_passing"] = True
            log_visualize("All tests are passing")
        else:
            chat_env.env_dict["tests_passing"] = False


class DocumentationPhase(Phase):
    """Phase for creating project documentation."""
    
    def _process_conversation_results(self, chat_env: ChatEnv, role_play: RolePlaying, assistant_msg: ChatMessage):
        """Process and extract documentation."""
        content = assistant_msg.content
        
        # Try to find documentation blocks
        file_pattern = r"```[\w\s]*\n(?:#\s*([^\n]+)|\/\/\s*([^\n]+)|\/\*\s*([^\n]+)\s*\*\/|\"\"\"\s*([^\n]+)\s*\"\"\"|<!--\s*([^\n]+)\s*-->)\n(.*?)```"
        doc_blocks = re.finditer(file_pattern, content, re.DOTALL)
        
        for match in doc_blocks:
            # Extract filename and doc content
            filename = next(filter(None, match.groups()[0:5]), "README.md").strip()
            if ":" in filename:
                filename = filename.split(":", 1)[1].strip()
            
            # If no extension, assume markdown
            if "." not in filename:
                filename = f"{filename}.md"
                
            doc_content = match.group(6)
            
            # Store the documentation
            chat_env.codes.add_code(filename, doc_content)
            log_visualize(f"Documentation added: {filename}")
        
        # Store general documentation content
        if "documentation" not in chat_env.env_dict:
            chat_env.env_dict["documentation"] = {}
        
        if "usage" not in chat_env.env_dict["documentation"]:
            usage_match = re.search(r"(?i)#+\s*usage\s*\n(.*?)(?:\n#+\s*|\Z)", content, re.DOTALL)
            if usage_match:
                chat_env.env_dict["documentation"]["usage"] = usage_match.group(1).strip()
        
        if "installation" not in chat_env.env_dict["documentation"]:
            install_match = re.search(r"(?i)#+\s*installation\s*\n(.*?)(?:\n#+\s*|\Z)", content, re.DOTALL)
            if install_match:
                chat_env.env_dict["documentation"]["installation"] = install_match.group(1).strip()


# Define standard conditions for recursive phases
def tests_are_passing(chat_env: ChatEnv) -> bool:
    """Check if all tests are passing."""
    return chat_env.env_dict.get("tests_passing", False)


def code_review_passed(chat_env: ChatEnv) -> bool:
    """Check if code review is successful."""
    # If no reviews yet, not passing
    if "code_reviews" not in chat_env.env_dict:
        return False
    
    # Check last review
    last_review = chat_env.env_dict["code_reviews"][-1].lower()
    
    # Look for positive indicators
    positive_indicators = ["looks good", "passes review", "code review passed", "no issues found"]
    for indicator in positive_indicators:
        if indicator in last_review:
            return True
    
    return False