"""Shared LangChain prompt helpers for agents."""
from typing import Dict, Any, Type, Union, List
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from pydantic import BaseModel, ValidationError
import json


def create_feedback_preparer(state: Dict, feedback_key: str, previous_key: str, suggestions_key: str, section_key: str = None):
    """Create a RunnableLambda that prepares feedback sections."""
    section_key = section_key or f"previous_{previous_key}_section"
    def prepare(inputs: Dict) -> Dict:
        hf = state.get("human_feedback", {})
        prev = state.get(previous_key)
        feedback = hf.get(feedback_key, "")
        suggestions = hf.get(suggestions_key, [])
        
        inputs[section_key] = (
            f"\nPREVIOUS {previous_key.upper().replace('_', ' ')} (that was rejected):\n"
            f"{json.dumps(prev[:3] if isinstance(prev, list) else prev, indent=2)}\n\n"
            f"Please create improved {previous_key.replace('_', ' ')} that addresses the issues with the above."
            if prev else ""
        )
        inputs["feedback_section"] = (
            f"\nFEEDBACK ON PREVIOUS {previous_key.upper().replace('_', ' ')}:\n{feedback}\n\n"
            "Please address all concerns mentioned in this feedback."
            if feedback else ""
        )
        inputs["suggestions_section"] = (
            f"\nSPECIFIC SUGGESTIONS FOR IMPROVEMENT:\n" + 
            "\n".join([f"- {s}" for s in suggestions]) + 
            f"\n\nPlease incorporate these suggestions into the new {previous_key.replace('_', ' ')}."
            if suggestions else ""
        )
        return inputs
    return RunnableLambda(prepare)


def create_prompt_formatter(is_regeneration: bool, creation_type: str):
    """Create a RunnableLambda that formats prompt based on regeneration status."""
    def format(inputs: Dict) -> Dict:
        has_feedback = any(inputs.get(k) for k in [
            "previous_module_structure_section", "previous_course_content_section", 
            "previous_quizzes_section", "feedback_section", "suggestions_section"
        ])
        
        if is_regeneration and has_feedback:
            inputs["regeneration_instruction"] = (
                f"Your task is to regenerate {creation_type} based on human feedback and suggestions. "
                "IMPORTANT: You must incorporate the feedback and suggestions provided."
            )
            inputs["feedback_requirement"] = "\nAddress all feedback and incorporate all suggestions."
            inputs["creation_instruction"] = (
                f"You are regenerating {creation_type} that was previously rejected. "
                "Please create an improved version that addresses all the feedback and suggestions."
            )
            inputs["regeneration_reminder"] = (
                "\n\nMake sure to address all the feedback and incorporate the suggestions provided."
            )
        else:
            inputs["regeneration_instruction"] = ""
            inputs["feedback_requirement"] = ""
            inputs["creation_instruction"] = f"Create {creation_type}."
            inputs["regeneration_reminder"] = ""
        return inputs
    return RunnableLambda(format)


def create_json_parser(array: bool = False):
    """Create LangChain JsonOutputParser with error handling."""
    parser = JsonOutputParser()
    
    def safe_parse(response) -> Union[Dict, List]:
        """Parse response with error handling using LangChain parser."""
        try:
            # Extract content from AIMessage or use string directly
            content = response.content if hasattr(response, 'content') else str(response)
            parsed = parser.parse(content)
            return parsed if parsed else ([] if array else {})
        except Exception:
            return [] if array else {}
    
    return RunnableLambda(safe_parse)


def create_structured_parser(schema: Type[BaseModel], array: bool = False):
    """Create PydanticOutputParser for structured outputs with validation."""
    parser = PydanticOutputParser(pydantic_object=schema)
    
    def parse(response) -> Union[BaseModel, List]:
        """Parse and validate response against Pydantic schema."""
        try:
            content = response.content if hasattr(response, 'content') else str(response)
            if array:
                # For arrays, parse as list of schemas
                parsed = parser.parse(content)
                return parsed if isinstance(parsed, list) else [parsed] if parsed else []
            else:
                parsed = parser.parse(content)
                return parsed if parsed else schema()
        except (ValidationError, json.JSONDecodeError, Exception):
            # Return empty schema instance on parse/validation failure
            return [] if array else schema()
    
    return RunnableLambda(parse)

