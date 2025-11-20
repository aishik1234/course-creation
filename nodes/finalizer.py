"""Course Finalizer - Compiles complete course and generates final output."""
from typing import Dict, Any
from state.base_state import CourseState
from utils.results_saver import ResultsSaver
from utils.progress_tracker import ProgressTracker
import json
from datetime import datetime


def finalize_course(state: CourseState) -> CourseState:
    """
    Finalize course by compiling all components and generating metadata.
    """
    try:
        thread_id = state.get("course_metadata", {}).get("thread_id", "default")
        progress = ProgressTracker(thread_id)
        progress.log_node_progress("finalize_course", {"message": "Compiling final course structure"})
        
        # Compile complete course structure
        complete_course = {
            "course_info": {
                "title": state["course_subject"],
                "description": f"Comprehensive course on {state['course_subject']} for {state['learner_level']} learners",
                "level": state["learner_level"],
                "duration": state["course_duration"],
                "number_of_modules": state["number_of_modules"],
                "created_at": datetime.now().isoformat(),
                "prerequisites": state.get("research_findings", {}).get("prerequisites", [])
            },
            "modules": [],
            "quizzes": state.get("quizzes", []),
            "xdp_specification": state.get("xdp_content", {})
        }
        
        # Helper function to get transcript for a lesson
        def get_transcript_for_lesson(lesson_id, lesson_name, module_id):
            """Get video transcript for a lesson."""
            transcripts = state.get("video_transcripts", [])
            for transcript in transcripts:
                if (transcript.get("lesson_id") == lesson_id or 
                    transcript.get("lesson_name") == lesson_name) and \
                   transcript.get("module_id") == module_id:
                    return transcript
            return None
        
        # Organize content by modules
        if state.get("module_structure") and state.get("course_content"):
            for module in state["module_structure"].get("modules", []):
                module_id = module["module_id"]
                module_lessons = [
                    lesson for lesson in state["course_content"]
                    if lesson.get("module_id") == module_id
                ]
                
                # Add transcripts to lessons
                lessons_with_transcripts = []
                for lesson in module_lessons:
                    lesson_id = lesson.get("lesson_id", "")
                    lesson_name = lesson.get("lesson_name", "")
                    transcript = get_transcript_for_lesson(lesson_id, lesson_name, module_id)
                    
                    lesson_with_transcript = {**lesson}
                    if transcript:
                        lesson_with_transcript["video_transcript"] = transcript
                    lessons_with_transcripts.append(lesson_with_transcript)
                
                # Get all transcripts for this module
                module_transcripts = [
                    transcript for transcript in state.get("video_transcripts", [])
                    if transcript.get("module_id") == module_id
                ]
                
                module_data = {
                    "module_id": module_id,
                    "module_name": module.get("module_name"),
                    "module_objectives": module.get("module_objectives", []),
                    "duration_allocation": module.get("duration_allocation"),
                    "is_lab_module": module.get("is_lab_module", False),
                    "lessons": lessons_with_transcripts,
                    "quizzes": [
                        quiz for quiz in state.get("quizzes", [])
                        if quiz.get("module_id") == module_id
                    ],
                    "video_transcripts": module_transcripts
                }
                complete_course["modules"].append(module_data)
        
        # Generate course summary
        summary = f"""
Course: {state['course_subject']}
Level: {state['learner_level']}
Duration: {state['course_duration']}
Modules: {state['number_of_modules']}

This course covers the fundamentals and advanced concepts of {state['course_subject']}
designed for {state['learner_level']} learners. The course is structured into
{state['number_of_modules']} modules with comprehensive lessons, examples, and assessments.
"""
        
        # Create course metadata
        course_metadata = {
            "course_info": complete_course["course_info"],
            "complete_structure": complete_course,
            "summary": summary.strip(),
            "statistics": {
                "total_modules": len(complete_course["modules"]),
                "total_lessons": len(state.get("course_content", [])),
                "total_quizzes": len(state.get("quizzes", [])),
                "graded_quizzes": len([q for q in state.get("quizzes", []) if q.get("quiz_type") == "graded"]),
                "practice_quizzes": len([q for q in state.get("quizzes", []) if q.get("quiz_type") == "practice"]),
                "total_video_transcripts": len(state.get("video_transcripts", [])),
                "total_video_duration_minutes": sum(
                    t.get("video_duration_minutes", 0) 
                    for t in state.get("video_transcripts", [])
                )
            },
            "export_format": complete_course  # JSON-ready structure
        }
        
        state["course_metadata"] = course_metadata
        state["current_step"] = "course_finalized"
        
        # Save final course
        saver = ResultsSaver()
        saver.save_final_course(course_metadata, thread_id)
        
        stats = course_metadata.get("statistics", {})
        progress.log_node_complete("finalize_course", {
            "modules": stats.get("total_modules", 0),
            "lessons": stats.get("total_lessons", 0),
            "quizzes": stats.get("total_quizzes", 0),
            "message": "Course finalized successfully"
        })
        
    except Exception as e:
        state["errors"].append(f"Finalizer error: {str(e)}")
        state["current_step"] = "finalization_failed"
    
    return state

