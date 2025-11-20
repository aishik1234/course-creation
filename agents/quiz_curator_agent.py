"""Quiz Curator Agent - Generates all quizzes for the course."""
from typing import Dict, Any, Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from utils.gemini_llm import GeminiLLM
from utils.config import GOOGLE_API_KEY, GEMINI_MODEL, GEMINI_TEMPERATURE
from utils.results_saver import ResultsSaver
from utils.progress_tracker import ProgressTracker
from utils.prompt_helpers import create_feedback_preparer, create_prompt_formatter, create_json_parser
from state.base_state import CourseState
from concurrent.futures import ThreadPoolExecutor, as_completed
import json


def quiz_curator_agent(state: CourseState) -> CourseState:
    """
    Agent 5: Generate all quizzes (graded and practice) for each module.
    Creates questions aligned with learning objectives.
    """
    try:
        thread_id = state.get("course_metadata", {}).get("thread_id", "default")
        progress = ProgressTracker(thread_id)
        
        if not state.get("module_structure") or not state.get("course_content"):
            state["errors"].append("Module structure or course content not available")
            progress.log_node_error("quiz_curator_agent", "Module structure or course content not available")
            return state
        
        # Check if this is a regeneration after rejection
        is_regeneration = (
            state.get("approval_status", {}).get("quizzes") is False or
            state.get("human_feedback", {}).get("quiz_suggestions")
        )
        
        if is_regeneration:
            progress.log_node_progress("quiz_curator_agent", {
                "message": "Regenerating quizzes with feedback"
            })
            # Don't reset approval_status to None - keep it as False to indicate we're in regeneration cycle
            # This prevents the review node from calling get_interactive_feedback() again
            if "approval_status" not in state:
                state["approval_status"] = {}
            # Keep approval_status as False (don't reset to None) so review node knows we're regenerating
        else:
            progress.log_node_progress("quiz_curator_agent", {
                "message": "Starting quiz generation",
                "modules": len(state.get("module_structure", {}).get("modules", []))
            })
        
        llm = GeminiLLM(
            model=GEMINI_MODEL,
            api_key=GOOGLE_API_KEY,
            temperature=GEMINI_TEMPERATURE
        )
        
        graded_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert quiz creator. {regeneration_instruction}
Generate comprehensive graded quizzes that test understanding and application of concepts.
Create questions that align with learning objectives and are appropriate
for the learner level.{feedback_requirement}"""),
            ("human", """{creation_instruction}

Module: {module_name}
Module Objectives: {module_objectives}
Lessons: {lessons}
Learner Level: {learner_level}
{previous_quizzes_section}{feedback_section}{suggestions_section}

Generate a quiz with:
- 5-7 multiple choice questions
- 2-3 true/false questions
- 1-2 short answer questions
- 1 essay question

Each question should:
- Be clear and unambiguous
- Test specific learning objectives
- Match the learner level difficulty
- Have correct answers with explanations

Return JSON:
{{
    "quiz_id": "string",
    "module_id": int,
    "quiz_type": "graded",
    "questions": [...],
    "answer_key": {{"question_id": "answer"}},
    "learning_objectives_covered": ["obj1", "obj2"],
    "difficulty_level": "string"
}}{regeneration_reminder}""")
        ])
        
        practice_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert quiz creator. {regeneration_instruction}
Generate practice quizzes that help learners reinforce concepts without high stakes.{feedback_requirement}"""),
            ("human", """{creation_instruction}

Module: {module_name}
Learner Level: {learner_level}
{previous_quizzes_section}{feedback_section}{suggestions_section}

Generate a practice quiz with:
- 3-5 multiple choice questions
- 2-3 true/false questions
- Immediate feedback and explanations

Return JSON format similar to graded quiz but with quiz_type: "practice".{regeneration_reminder}""")
        ])
        
        all_quizzes = []
        modules = state["module_structure"].get("modules", [])
        total_modules = len(modules)
        
        # Collect all quiz generation tasks
        quiz_tasks = []
        for module_num, module in enumerate(modules, 1):
            module_id = module["module_id"]
            quiz_plan = module.get("quiz_plan", {})
            graded_count = quiz_plan.get("graded", state["graded_quizzes_per_module"])
            practice_count = quiz_plan.get("practice", state["practice_quizzes_per_module"])
            
            # Get module lessons for context
            module_lessons = [
                lesson for lesson in state["course_content"]
                if lesson.get("module_id") == module_id
            ]
            
            # Add graded quiz tasks
            for quiz_num in range(graded_count):
                quiz_tasks.append(("graded", module, module_id, quiz_num + 1, module_lessons))
            
            # Add practice quiz tasks
            for quiz_num in range(practice_count):
                quiz_tasks.append(("practice", module, module_id, quiz_num + 1, module_lessons))
        
        progress.log_node_progress("quiz_curator_agent", {
            "total_quizzes": len(quiz_tasks),
            "total_modules": total_modules,
            "message": f"Starting parallel generation of {len(quiz_tasks)} quizzes"
        })
        
        def generate_quiz(task_data):
            """Generate a single quiz."""
            quiz_type, module, module_id, quiz_num, module_lessons = task_data
            try:
                if quiz_type == "graded":
                    chain = (
                        RunnablePassthrough.assign(
                            module_id=lambda _: module_id,
                            quiz_num=lambda _: quiz_num,
                            module_name=lambda _: module.get("module_name", "Module"),
                            module_objectives=lambda _: json.dumps(module.get("module_objectives", [])),
                            lessons=lambda _: json.dumps(module_lessons, indent=2),
                            learner_level=lambda _: state["learner_level"]
                        )
                        | create_feedback_preparer(state, "quizzes", "quizzes", "quiz_suggestions", "previous_quizzes_section")
                        | create_prompt_formatter(is_regeneration, f"graded quiz for Module {module_id}, Quiz {quiz_num}")
                        | graded_prompt
                        | llm
                        | create_json_parser()
                    )
                else:  # practice
                    chain = (
                        RunnablePassthrough.assign(
                            module_id=lambda _: module_id,
                            quiz_num=lambda _: quiz_num,
                            module_name=lambda _: module.get("module_name", "Module"),
                            learner_level=lambda _: state["learner_level"]
                        )
                        | create_feedback_preparer(state, "quizzes", "quizzes", "quiz_suggestions", "previous_quizzes_section")
                        | create_prompt_formatter(is_regeneration, f"practice quiz for Module {module_id}, Quiz {quiz_num}")
                        | practice_prompt
                        | llm
                        | create_json_parser()
                    )
                
                quiz = chain.invoke({})
                if quiz:
                    # Ensure module_id is an integer for consistency
                    quiz["module_id"] = int(module_id) if isinstance(module_id, str) else module_id
                    quiz["quiz_id"] = f"{quiz_type}_quiz_{module_id}_{quiz_num}"
                    quiz["quiz_type"] = quiz_type
                    return quiz, None
                else:
                    return None, "Empty quiz response"
            except Exception as e:
                return None, str(e)
        
        # Process quizzes in parallel (max 5 concurrent to avoid rate limits)
        max_workers = min(5, len(quiz_tasks))
        completed = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all quiz tasks
            future_to_task = {
                executor.submit(generate_quiz, task): task
                for task in quiz_tasks
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                quiz_type, module, module_id, quiz_num, _ = task
                completed += 1
                
                try:
                    quiz, error = future.result()
                    if error:
                        progress.log_node_progress("quiz_curator_agent", {
                            "module_id": module_id,
                            "quiz_type": quiz_type,
                            "quiz_num": quiz_num,
                            "error": error,
                            "completed": completed,
                            "total": len(quiz_tasks),
                            "message": f"Quiz generation failed: {error}"
                        })
                    elif quiz:
                        all_quizzes.append(quiz)
                        progress.log_node_progress("quiz_curator_agent", {
                            "module_id": module_id,
                            "quiz_type": quiz_type,
                            "quiz_num": quiz_num,
                            "completed": completed,
                            "total": len(quiz_tasks),
                            "total_generated": len(all_quizzes),
                            "message": f"Generated {quiz_type} quiz {quiz_num} for module {module_id} ({completed}/{len(quiz_tasks)})"
                        })
                except Exception as e:
                    progress.log_node_progress("quiz_curator_agent", {
                        "module_id": module_id,
                        "quiz_type": quiz_type,
                        "quiz_num": quiz_num,
                        "error": str(e),
                        "message": f"Exception generating quiz: {str(e)}"
                    })
        
        # Sort quizzes by module_id and quiz_type for consistency
        # Ensure module_id is always an integer for proper sorting
        def sort_key(quiz):
            module_id = quiz.get("module_id", 0)
            # Convert to int if it's a string to avoid type comparison errors
            if isinstance(module_id, str):
                try:
                    module_id = int(module_id)
                except (ValueError, TypeError):
                    module_id = 0
            return (module_id, quiz.get("quiz_type", ""), quiz.get("quiz_id", ""))
        
        all_quizzes.sort(key=sort_key)
        
        state["quizzes"] = all_quizzes
        
        # Save results
        saver = ResultsSaver()
        saver.save_quizzes(all_quizzes, thread_id)
        
        graded = len([q for q in all_quizzes if q.get("quiz_type") == "graded"])
        practice = len([q for q in all_quizzes if q.get("quiz_type") == "practice"])
        
        progress.log_node_complete("quiz_curator_agent", {
            "total_quizzes": len(all_quizzes),
            "graded": graded,
            "practice": practice
        })
        
        state["current_step"] = "quizzes_created"
        
        # After successful regeneration, reset approval_status to None
        # This allows validation to determine next step, and if validation fails,
        # the review node can get feedback on the regenerated version
        if is_regeneration:
            if "approval_status" not in state:
                state["approval_status"] = {}
            state["approval_status"]["quizzes"] = None
        
    except Exception as e:
        state["errors"].append(f"Quiz curator agent error: {str(e)}")
        state["current_step"] = "quizzes_failed"
        # Ensure quizzes is initialized even on error
        if "quizzes" not in state or state.get("quizzes") is None:
            state["quizzes"] = []
    
    return state

