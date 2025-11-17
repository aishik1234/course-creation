"""XDP Agent - Generates XDP (eXtended Design Pattern) format content."""
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from utils.gemini_llm import GeminiLLM
from utils.config import GOOGLE_API_KEY, GEMINI_MODEL, GEMINI_TEMPERATURE
from utils.results_saver import ResultsSaver
from utils.progress_tracker import ProgressTracker
from state.base_state import CourseState
import json
import re


def xdp_agent(state: CourseState) -> CourseState:
    """
    Agent 3: Generate XDP (eXtended Design Pattern) format content.
    Creates structured course design specification.
    """
    try:
        thread_id = state.get("course_metadata", {}).get("thread_id", "default")
        progress = ProgressTracker(thread_id)
        
        if not state.get("module_structure"):
            state["errors"].append("Module structure not available")
            progress.log_node_error("xdp_agent", "Module structure not available")
            return state
        
        progress.log_node_progress("xdp_agent", {"message": "Generating XDP format specification"})
        
        llm = GeminiLLM(
            model=GEMINI_MODEL,
            api_key=GOOGLE_API_KEY,
            temperature=GEMINI_TEMPERATURE
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in instructional design patterns.
            Your task is to convert course module structure into XDP (eXtended Design Pattern)
            format, which defines learning patterns, instructional design elements,
            content templates, and design specifications.
            
            XDP format includes:
            - Learning patterns for each module type
            - Content templates and structure specifications
            - Mapping of learning objectives to XDP components
            - Design patterns and instructional strategies"""),
            ("human", """Convert the following module structure into XDP format:

            Module Structure:
            {module_structure}
            
            Learner Level: {learner_level}
            
            Create XDP specification as JSON with:
            {{
                "xdp_specification": {{
                    "version": "1.0",
                    "design_patterns": [...],
                    "instructional_strategies": [...]
                }},
                "content_templates": {{
                    "lesson_template": {{...}},
                    "quiz_template": {{...}}
                }},
                "design_patterns": [
                    {{
                        "module_id": int,
                        "pattern_type": "string",
                        "components": [...]
                    }}
                ],
                "metadata": {{
                    "format": "XDP",
                    "version": "1.0"
                }}
            }}""")
        ])
        
        chain = prompt | llm
        response = chain.invoke({
            "module_structure": json.dumps(state["module_structure"], indent=2),
            "learner_level": state["learner_level"]
        })
        
        # Parse JSON response
        content = response.content
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            xdp_content = json.loads(json_match.group())
        else:
            # Fallback XDP structure
            xdp_content = {
                "xdp_specification": {
                    "version": "1.0",
                    "design_patterns": ["progressive_disclosure", "scaffolding", "active_learning"],
                    "instructional_strategies": ["guided_practice", "examples", "case_studies"]
                },
                "content_templates": {
                    "lesson_template": {
                        "structure": ["introduction", "main_content", "examples", "summary"],
                        "required_elements": ["objectives", "content", "exercises"]
                    },
                    "quiz_template": {
                        "question_types": ["multiple_choice", "true_false", "short_answer"],
                        "required_elements": ["question", "options", "correct_answer", "explanation"]
                    }
                },
                "design_patterns": [
                    {
                        "module_id": i + 1,
                        "pattern_type": "progressive_disclosure",
                        "components": ["intro", "concept", "example", "practice"]
                    }
                    for i in range(state["number_of_modules"])
                ],
                "metadata": {
                    "format": "XDP",
                    "version": "1.0"
                }
            }
        
        state["xdp_content"] = xdp_content
        
        # Save results
        saver = ResultsSaver()
        saver.save_xdp_content(xdp_content, thread_id)
        
        progress.log_node_complete("xdp_agent", {"message": "XDP specification generated"})
        
        state["current_step"] = "xdp_created"
        
    except Exception as e:
        state["errors"].append(f"XDP agent error: {str(e)}")
        state["current_step"] = "xdp_failed"
    
    return state

