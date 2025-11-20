"""Module Structure Agent - Creates detailed module breakdown."""
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from utils.gemini_llm import GeminiLLM
from utils.config import GOOGLE_API_KEY, GEMINI_MODEL, GEMINI_TEMPERATURE
from utils.results_saver import ResultsSaver
from utils.progress_tracker import ProgressTracker
from utils.prompt_helpers import create_feedback_preparer, create_prompt_formatter, create_json_parser
from state.base_state import CourseState
import json


def module_structure_agent(state: CourseState) -> CourseState:
    """
    Agent 2: Create detailed module structure based on research findings
    and user requirements.
    """
    try:
        thread_id = state.get("course_metadata", {}).get("thread_id", "default")
        progress = ProgressTracker(thread_id)
        
        if not state.get("research_findings"):
            state["errors"].append("Research findings not available")
            progress.log_node_error("module_structure_agent", "Research findings not available")
            return state
        
        # Check if this is a regeneration after rejection
        is_regeneration = (
            state.get("approval_status", {}).get("structure") is False or
            state.get("human_feedback", {}).get("structure_suggestions")
        )
        
        if is_regeneration:
            progress.log_node_progress("module_structure_agent", {
                "message": "Regenerating module structure with feedback",
                "target_modules": state.get("number_of_modules")
            })
            # Don't reset approval_status to None - keep it as False to indicate we're in regeneration cycle
            # This prevents the review node from calling get_interactive_feedback() again
            if "approval_status" not in state:
                state["approval_status"] = {}
            # Keep approval_status as False (don't reset to None) so review node knows we're regenerating
        else:
            progress.log_node_progress("module_structure_agent", {
                "message": "Creating module structure",
                "target_modules": state.get("number_of_modules")
            })
        
        llm = GeminiLLM(
            model=GEMINI_MODEL,
            api_key=GOOGLE_API_KEY,
            temperature=GEMINI_TEMPERATURE
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert instructional designer specializing in
creating well-structured course modules. {regeneration_instruction}

Create a structure that:
1. Distributes topics logically across modules
2. Ensures smooth learning progression
3. Allocates time appropriately
4. Plans quiz placement strategically{feedback_requirement}"""),
            ("human", """{creation_instruction}

Research Findings:
{research_findings}

Requirements:
- Number of modules: {number_of_modules}
- Course duration: {course_duration}
- Graded quizzes per module: {graded_quizzes}
- Practice quizzes per module: {practice_quizzes}
- Lab module needed: {needs_lab}
{previous_module_structure_section}{feedback_section}{suggestions_section}

Create a JSON structure with modules, each containing:
- module_id: integer
- module_name: string
- module_objectives: list of strings
- lessons: list of lesson objects (each with lesson_name, lesson_objectives, estimated_duration)
- duration_allocation: string
- quiz_plan: {{"graded": number, "practice": number}}
- is_lab_module: boolean (only true for lab module if needed)

Format as JSON with "modules" as the root key.{regeneration_reminder}""")
        ])
        
        # Compose chain using LangChain features
        chain = (
            RunnablePassthrough.assign(
                research_findings=lambda _: json.dumps(state["research_findings"], indent=2),
                number_of_modules=lambda _: state["number_of_modules"],
                course_duration=lambda _: state["course_duration"],
                graded_quizzes=lambda _: state["graded_quizzes_per_module"],
                practice_quizzes=lambda _: state["practice_quizzes_per_module"],
                needs_lab=lambda _: state["needs_lab_module"]
            )
            | create_feedback_preparer(state, "structure", "module_structure", "structure_suggestions", "previous_module_structure_section")
            | create_prompt_formatter(is_regeneration, "module structure")
            | prompt
            | llm
            | create_json_parser()
        )
        
        module_structure = chain.invoke({})
        
        if not module_structure or not module_structure.get("modules"):
            # Fallback structure
            module_structure = {
                "modules": [
                    {
                        "module_id": i + 1,
                        "module_name": f"Module {i + 1}",
                        "module_objectives": [f"Learn module {i + 1} concepts"],
                        "lessons": [
                            {
                                "lesson_name": f"Lesson {j + 1}",
                                "lesson_objectives": [f"Understand lesson {j + 1}"],
                                "estimated_duration": "30 minutes"
                            }
                            for j in range(3)
                        ],
                        "duration_allocation": "2 hours",
                        "quiz_plan": {
                            "graded": state["graded_quizzes_per_module"],
                            "practice": state["practice_quizzes_per_module"]
                        },
                        "is_lab_module": False
                    }
                    for i in range(state["number_of_modules"])
                ]
            }
            
            # Add lab module if needed
            if state["needs_lab_module"]:
                module_structure["modules"].append({
                    "module_id": state["number_of_modules"] + 1,
                    "module_name": "Lab Module",
                    "module_objectives": ["Apply learned concepts in practical scenarios"],
                    "lessons": [
                        {
                            "lesson_name": "Lab Exercise",
                            "lesson_objectives": ["Complete hands-on exercises"],
                            "estimated_duration": "1 hour"
                        }
                    ],
                    "duration_allocation": "2 hours",
                    "quiz_plan": {"graded": 0, "practice": 1},
                    "is_lab_module": True
                })
        
        state["module_structure"] = module_structure
        
        # Save results
        saver = ResultsSaver()
        saver.save_module_structure(module_structure, thread_id)
        
        modules = module_structure.get("modules", [])
        progress.log_node_complete("module_structure_agent", {
            "modules_created": len(modules),
            "total_lessons": sum(len(m.get("lessons", [])) for m in modules)
        })
        
        state["current_step"] = "module_structure_created"
        
        # After successful regeneration, reset approval_status to None
        # This allows validation to determine next step, and if validation fails,
        # the review node can get feedback on the regenerated version
        if is_regeneration:
            if "approval_status" not in state:
                state["approval_status"] = {}
            state["approval_status"]["structure"] = None
        
    except Exception as e:
        state["errors"].append(f"Module structure agent error: {str(e)}")
        state["current_step"] = "module_structure_failed"
        # Ensure module_structure is initialized even on error
        if "module_structure" not in state or state.get("module_structure") is None:
            state["module_structure"] = {"modules": []}
    
    return state

