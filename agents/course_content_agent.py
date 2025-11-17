"""Course Content Agent - Generates full detailed lesson content."""
from typing import Dict, Any, List
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


def course_content_agent(state: CourseState) -> CourseState:
    """
    Agent 4: Generate full detailed content for all lessons.
    Creates comprehensive lesson content including introduction, main body,
    examples, case studies, practice exercises, and summaries.
    """
    try:
        if not state.get("module_structure"):
            state["errors"].append("Module structure not available")
            return state
        
        llm = GeminiLLM(
            model=GEMINI_MODEL,
            api_key=GOOGLE_API_KEY,
            temperature=GEMINI_TEMPERATURE
        )
        course_content = []
        
        # Initialize progress tracker
        thread_id = state.get("course_metadata", {}).get("thread_id", "default")
        progress = ProgressTracker(thread_id)
        
        # Check if this is a regeneration after rejection
        is_regeneration = (
            state.get("approval_status", {}).get("content") is False or
            state.get("human_feedback", {}).get("content_suggestions")
        )
        
        if is_regeneration:
            progress.log_node_progress("course_content_agent", {
                "message": "Regenerating course content with feedback"
            })
            if "approval_status" not in state:
                state["approval_status"] = {}
            state["approval_status"]["content"] = None
        else:
            progress.log_node_progress("course_content_agent", {
                "message": "Creating course content"
            })
        
        # Process lessons in batches (for efficiency)
        all_lessons = []
        for module in state["module_structure"].get("modules", []):
            for lesson in module.get("lessons", []):
                lesson["module_id"] = module["module_id"]
                lesson["module_name"] = module["module_name"]
                all_lessons.append(lesson)
        
        total_lessons = len(all_lessons)
        progress.log_node_progress("course_content_agent", {
            "total_lessons": total_lessons,
            "message": f"Starting to generate content for {total_lessons} lessons"
        })
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert course content creator. {regeneration_instruction}
Generate comprehensive, engaging lesson content that is appropriate for the learner level.
Create content that includes introduction, main body, examples, case studies,
practice exercises, and summaries.{feedback_requirement}"""),
            ("human", """{creation_instruction}

Lessons to generate:
{lessons}

Learner Level: {learner_level}
Course Subject: {course_subject}
{previous_course_content_section}{feedback_section}{suggestions_section}

For each lesson, create:
- introduction: Engaging hook, overview, and objectives
- main_content: Detailed explanations, concepts, theories
- examples: Real-world examples and applications
- case_studies: Relevant case studies (if applicable)
- practice_exercises: Exercises and activities
- summary: Key takeaways and summary
- visual_suggestions: Suggestions for diagrams, charts, infographics
- lab_instructions: Lab instructions if it's a lab module

Return JSON array with lesson objects, each containing:
{{
    "lesson_id": "string",
    "module_id": int,
    "lesson_name": "string",
    "introduction": "string",
    "main_content": "string",
    "examples": ["example1", "example2"],
    "case_studies": ["case1", "case2"],
    "practice_exercises": ["exercise1", "exercise2"],
    "summary": "string",
    "visual_suggestions": ["suggestion1", "suggestion2"],
    "lab_instructions": "string or null"
}}{regeneration_reminder}""")
        ])
        
        # Process in batches with parallelization
        batch_size = 4  # Increased batch size for better parallelization
        total_batches = (total_lessons + batch_size - 1) // batch_size
        
        # Create batches
        batches = []
        for i in range(0, len(all_lessons), batch_size):
            batches.append(all_lessons[i:i + batch_size])
        
        progress.log_node_progress("course_content_agent", {
            "total_batches": total_batches,
            "batch_size": batch_size,
            "message": f"Starting parallel generation of {total_batches} batches"
        })
        
        def generate_batch(batch_data):
            """Generate content for a single batch."""
            batch, batch_num = batch_data
            try:
                chain = (
                    RunnablePassthrough.assign(
                        lessons=lambda _: json.dumps(batch, indent=2),
                        learner_level=lambda _: state["learner_level"],
                        course_subject=lambda _: state["course_subject"]
                    )
                    | create_feedback_preparer(state, "content", "course_content", "content_suggestions", "previous_course_content_section")
                    | create_prompt_formatter(is_regeneration, "course content")
                    | prompt
                    | llm
                    | create_json_parser(array=True)
                )
                
                batch_content = chain.invoke({})
                
                if batch_content:
                    return batch_num, batch_content, None
                else:
                    # Fallback: create basic content structure
                    fallback_content = []
                    for idx, lesson in enumerate(batch):
                        fallback_content.append({
                            "lesson_id": f"lesson_{lesson.get('module_id', 0)}_{batch_num}_{idx}",
                            "module_id": lesson.get("module_id", 0),
                            "lesson_name": lesson.get("lesson_name", "Lesson"),
                            "introduction": f"Introduction to {lesson.get('lesson_name', 'lesson')}",
                            "main_content": f"Main content for {lesson.get('lesson_name', 'lesson')}",
                            "examples": ["Example 1", "Example 2"],
                            "case_studies": [],
                            "practice_exercises": ["Exercise 1", "Exercise 2"],
                            "summary": f"Summary of {lesson.get('lesson_name', 'lesson')}",
                            "visual_suggestions": ["Diagram", "Chart"],
                            "lab_instructions": lesson.get("lab_instructions") if state["needs_lab_module"] else None
                        })
                    return batch_num, fallback_content, None
            except Exception as e:
                return batch_num, None, str(e)
        
        # Process batches in parallel (max 4 concurrent batches to avoid rate limits)
        max_workers = min(4, total_batches)  # Limit concurrency to avoid API rate limits
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all batches
            future_to_batch = {
                executor.submit(generate_batch, (batch, batch_num + 1)): batch_num + 1
                for batch_num, batch in enumerate(batches)
            }
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_batch):
                batch_num = future_to_batch[future]
                try:
                    batch_num_result, batch_content, error = future.result()
                    completed += 1
                    
                    if error:
                        progress.log_node_progress("course_content_agent", {
                            "batch": batch_num_result,
                            "error": error,
                            "message": f"Batch {batch_num_result} failed: {error}"
                        })
                        # Create fallback content for failed batch
                        batch_idx = batch_num_result - 1
                        if batch_idx < len(batches):
                            batch = batches[batch_idx]
                            for idx, lesson in enumerate(batch):
                                course_content.append({
                                    "lesson_id": f"lesson_{lesson.get('module_id', 0)}_{batch_num_result}_{idx}",
                                    "module_id": lesson.get("module_id", 0),
                                    "lesson_name": lesson.get("lesson_name", "Lesson"),
                                    "introduction": f"Introduction to {lesson.get('lesson_name', 'lesson')}",
                                    "main_content": f"Main content for {lesson.get('lesson_name', 'lesson')}",
                                    "examples": ["Example 1", "Example 2"],
                                    "case_studies": [],
                                    "practice_exercises": ["Exercise 1", "Exercise 2"],
                                    "summary": f"Summary of {lesson.get('lesson_name', 'lesson')}",
                                    "visual_suggestions": ["Diagram", "Chart"],
                                    "lab_instructions": lesson.get("lab_instructions") if state["needs_lab_module"] else None
                                })
                    elif batch_content:
                        course_content.extend(batch_content)
                        progress.log_node_progress("course_content_agent", {
                            "batch": batch_num_result,
                            "lessons_generated": len(batch_content),
                            "total_generated": len(course_content),
                            "completed": completed,
                            "total_batches": total_batches,
                            "message": f"Batch {batch_num_result}/{total_batches} completed: {len(batch_content)} lessons"
                        })
                except Exception as e:
                    progress.log_node_progress("course_content_agent", {
                        "batch": batch_num,
                        "error": str(e),
                        "message": f"Batch {batch_num} exception: {str(e)}"
                    })
        
        # Sort course_content by module_id and lesson order to maintain consistency
        course_content.sort(key=lambda x: (x.get("module_id", 0), x.get("lesson_id", "")))
        
        state["course_content"] = course_content
        
        # Save results
        saver = ResultsSaver()
        saver.save_course_content(course_content, thread_id)
        
        progress.log_node_complete("course_content_agent", {
            "total_lessons": len(course_content),
            "message": f"Successfully generated content for {len(course_content)} lessons"
        })
        
        state["current_step"] = "course_content_created"
        
    except Exception as e:
        error_msg = f"Course content agent error: {str(e)}"
        state["errors"].append(error_msg)
        state["current_step"] = "course_content_failed"
        # Ensure course_content is initialized even on error
        if "course_content" not in state or state.get("course_content") is None:
            state["course_content"] = []
        progress.log_node_error("course_content_agent", error_msg)
        print(f"❌ Error in course_content_agent: {error_msg}")
        import traceback
        traceback.print_exc()
    
    return state

