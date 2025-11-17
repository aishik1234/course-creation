"""Validation Agent - Validates course components at multiple checkpoints."""

from typing import Dict, Any
from state.base_state import CourseState


def validate_module_structure(state: CourseState) -> Dict[str, Any]:
    """
    Validation checkpoint A: Validate module structure quality.
    Returns validation results and determines if HITL review is needed.
    """
    validation_results = {
        "is_valid": True,
        "quality_score": 0.0,
        "issues": [],
        "recommendations": []
    }
    
    if not state.get("module_structure"):
        validation_results["is_valid"] = False
        validation_results["issues"].append("Module structure is missing")
        return validation_results
    
    modules = state["module_structure"].get("modules", [])
    
    # Check completeness
    if len(modules) != state["number_of_modules"]:
        validation_results["issues"].append(
            f"Expected {state['number_of_modules']} modules, got {len(modules)}"
        )
    # Check each module has lessons
    modules_without_lessons = []
    total_duration = 0
    
    for module in modules:
        if not module.get("lessons") or len(module.get("lessons", [])) == 0:
            modules_without_lessons.append(module.get("module_id"))
        else:
            validation_results["quality_score"] += 0.2
        
        # Check quiz plan
        quiz_plan = module.get("quiz_plan", {})
        if quiz_plan.get("graded", 0) != state["graded_quizzes_per_module"]:
            validation_results["issues"].append(
                f"Module {module.get('module_id')} quiz plan doesn't match requirements"
            )
    
    if modules_without_lessons:
        validation_results["issues"].append(
            f"Modules without lessons: {modules_without_lessons}"
        )
        validation_results["is_valid"] = False
    
    # Normalize quality score (0-1)
    validation_results["quality_score"] = min(
        validation_results["quality_score"] / max(len(modules), 1), 1.0
    )
    
    # Add base score for having structure
    if validation_results["quality_score"] > 0:
        validation_results["quality_score"] = 0.5 + (validation_results["quality_score"] * 0.5)
    
    if validation_results["quality_score"] < 0.7:
        validation_results["recommendations"].append(
            "Consider reviewing module structure for better organization"
        )
    
    return validation_results


def validate_content(state: CourseState) -> Dict[str, Any]:
    """
    Validation checkpoint B: Validate lesson content quality.
    Returns validation results and determines if HITL review is needed.
    """
    validation_results = {
        "is_valid": True,
        "quality_score": 0.0,
        "lesson_scores": {},
        "flagged_lessons": [],
        "issues": [],
        "recommendations": []
    }
    
    if not state.get("course_content"):
        validation_results["is_valid"] = False
        validation_results["issues"].append("Course content is missing")
        return validation_results
    
    required_fields = ["introduction", "main_content", "summary"]
    total_score = 0
    
    for lesson in state["course_content"]:
        lesson_id = lesson.get("lesson_id", "unknown")
        lesson_score = 0.0
        
        # Check required fields
        for field in required_fields:
            if lesson.get(field) and len(str(lesson.get(field))) > 50:
                lesson_score += 0.33
            elif not lesson.get(field):
                validation_results["issues"].append(
                    f"Lesson {lesson_id} missing {field}"
                )
        
        # Check for examples
        if lesson.get("examples") and len(lesson.get("examples", [])) > 0:
            lesson_score += 0.1
        
        # Check for exercises
        if lesson.get("practice_exercises") and len(lesson.get("practice_exercises", [])) > 0:
            lesson_score += 0.1
        
        validation_results["lesson_scores"][lesson_id] = lesson_score
        
        if lesson_score < 0.8:
            validation_results["flagged_lessons"].append(lesson_id)
        
        total_score += lesson_score
    
    # Calculate average quality score
    num_lessons = len(state["course_content"])
    if num_lessons > 0:
        validation_results["quality_score"] = total_score / num_lessons
    else:
        validation_results["quality_score"] = 0.0
        validation_results["is_valid"] = False
    
    if validation_results["quality_score"] < 0.8:
        validation_results["is_valid"] = False
        validation_results["recommendations"].append(
            "Some lessons need improvement in content quality"
        )
    
    return validation_results


def validate_quizzes(state: CourseState) -> Dict[str, Any]:
    """
    Validation checkpoint C: Validate quiz quality and alignment.
    Returns validation results and determines if HITL review is needed.
    """
    validation_results = {
        "is_valid": True,
        "quality_score": 0.0,
        "objective_coverage": 0.0,
        "quiz_scores": {},
        "flagged_quizzes": [],
        "issues": [],
        "recommendations": []
    }
    
    if not state.get("quizzes"):
        validation_results["is_valid"] = False
        validation_results["issues"].append("Quizzes are missing")
        return validation_results
    
    total_questions = 0
    valid_questions = 0
    objectives_covered = set()
    
    for quiz in state["quizzes"]:
        quiz_id = quiz.get("quiz_id", "unknown")
        quiz_score = 0.0
        questions = quiz.get("questions", [])
        
        if not questions:
            validation_results["issues"].append(f"Quiz {quiz_id} has no questions")
            continue
        
        for question in questions:
            total_questions += 1
            
            # Check question quality
            if question.get("question") and len(question.get("question", "")) > 20:
                valid_questions += 1
                quiz_score += 0.1
            
            # Check for correct answer
            if question.get("correct_answer"):
                quiz_score += 0.1
            
            # Check for explanation
            if question.get("explanation"):
                quiz_score += 0.05
            
            # Track objectives
            if question.get("learning_objective"):
                objectives_covered.add(question.get("learning_objective"))
        
        # Normalize quiz score
        if len(questions) > 0:
            quiz_score = min(quiz_score / len(questions), 1.0)
        
        validation_results["quiz_scores"][quiz_id] = quiz_score
        
        if quiz_score < 0.8:
            validation_results["flagged_quizzes"].append(quiz_id)
    
    # Calculate overall quality score
    if total_questions > 0:
        validation_results["quality_score"] = valid_questions / total_questions
    else:
        validation_results["quality_score"] = 0.0
        validation_results["is_valid"] = False
    
    # Calculate objective coverage (simplified - would need actual objectives list)
    if state.get("research_findings"):
        total_objectives = len(state["research_findings"].get("learning_objectives", []))
        if total_objectives > 0:
            validation_results["objective_coverage"] = len(objectives_covered) / total_objectives
        else:
            validation_results["objective_coverage"] = 0.5  # Default if no objectives
    
    if validation_results["quality_score"] < 0.8 or validation_results["objective_coverage"] < 0.8:
        validation_results["is_valid"] = False
        validation_results["recommendations"].append(
            "Some quizzes need improvement in quality or objective coverage"
        )
    
    return validation_results

