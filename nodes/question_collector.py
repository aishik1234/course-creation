"""Question collector node to gather user input."""
from typing import Dict, Any
from state.base_state import CourseState


def collect_user_input(state: CourseState) -> CourseState:
    """
    Collect course requirements from user via questions.
    
    In a real implementation, this would interact with a UI.
    For prototype, we'll use the state if already populated,
    or raise an interrupt to get user input.
    """
    # Check if all required fields are present
    required_fields = [
        "course_subject",
        "learner_level", 
        "course_duration",
        "number_of_modules",
        "graded_quizzes_per_module",
        "practice_quizzes_per_module",
        "needs_lab_module"
    ]
    
    missing_fields = [field for field in required_fields if field not in state or state.get(field) is None]
    
    if missing_fields:
        # In real implementation, this would trigger UI to collect input
        # For now, we'll set a flag that indicates we need user input
        state["current_step"] = "collecting_user_input"
        state["errors"].append(f"Missing required fields: {', '.join(missing_fields)}")
        # This would trigger an interrupt in the graph
        return state
    
    # Validate inputs
    if state["learner_level"] not in ["basic", "intermediate", "advanced"]:
        state["errors"].append(f"Invalid learner level: {state['learner_level']}")
        return state
    
    if state["number_of_modules"] <= 0:
        state["errors"].append("Number of modules must be greater than 0")
        return state
    
    state["current_step"] = "user_input_collected"
    return state

