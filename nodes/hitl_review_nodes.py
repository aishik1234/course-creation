"""HITL (Human-In-The-Loop) Review Nodes with interrupts."""
from typing import Dict, Any, Literal
from state.base_state import CourseState
from nodes.interrupt_handler import show_interrupt_info, get_interactive_feedback
from utils.results_saver import ResultsSaver


def _ensure_feedback_state(state: CourseState, review_type: str) -> CourseState:
    """Ensure human_feedback and approval_status are properly initialized."""
    # Map review_type to correct suggestion key
    suggestion_key_map = {
        "structure": "structure_suggestions",
        "content": "content_suggestions", 
        "quizzes": "quiz_suggestions"
    }
    suggestion_key = suggestion_key_map.get(review_type, f"{review_type}_suggestions")
    
    if "human_feedback" not in state:
        state["human_feedback"] = {}
    if "approval_status" not in state:
        state["approval_status"] = {}
    if review_type not in state["human_feedback"]:
        state["human_feedback"][review_type] = ""
    if suggestion_key not in state["human_feedback"]:
        state["human_feedback"][suggestion_key] = []
    return state


def _process_review_feedback(
    state: CourseState, 
    review_type: str, 
    feedback_data: Dict[str, Any]
) -> CourseState:
    """Process feedback and update state using LangGraph state update pattern."""
    _ensure_feedback_state(state, review_type)
    
    feedback = feedback_data[review_type]
    approval = feedback.get("approval_status")
    
    # Update feedback text
    state["human_feedback"][review_type] = feedback.get("feedback", "")
    
    # Update approval status and suggestions
    # Map review_type to correct suggestion key (handle "quizzes" -> "quiz_suggestions")
    suggestion_key_map = {
        "structure": "structure_suggestions",
        "content": "content_suggestions", 
        "quizzes": "quiz_suggestions"  # Note: singular "quiz" to match agent expectations
    }
    suggestion_key = suggestion_key_map.get(review_type, f"{review_type}_suggestions")
    
    if approval is True:
        state["approval_status"][review_type] = True
        state["current_step"] = f"{review_type}_approved"
        print(f"\n✅ {review_type.capitalize()} approved! Continuing workflow...\n")
    elif approval is False:
        state["approval_status"][review_type] = False
        state["current_step"] = f"{review_type}_rejected"
        if feedback.get("suggestions"):
            state["human_feedback"][suggestion_key] = feedback["suggestions"]
        print(f"\n🔄 {review_type.capitalize()} rejected. Will regenerate with your suggestions...\n")
    else:
        state["approval_status"][review_type] = True
        state["current_step"] = f"{review_type}_edited"
        print(f"\n✅ {review_type.capitalize()} edited. Continuing workflow...\n")
    
    return state


def human_review_structure(state: CourseState) -> CourseState:
    """
    HITL checkpoint for module structure approval.
    This node should trigger an interrupt in the graph.
    """
    _ensure_feedback_state(state, "structure")
    
    # Check if we already have feedback (resuming after interrupt)
    if state["approval_status"].get("structure") is not None:
        return state
    
    thread_id = state.get("course_metadata", {}).get("thread_id", "default")
    
    # Save results before interrupt
    saver = ResultsSaver()
    if state.get("module_structure"):
        saver.save_module_structure(state["module_structure"], thread_id)
    
    # Show interrupt information and save state
    show_interrupt_info("structure", state, thread_id)
    
    # Get interactive feedback from user
    feedback_data = get_interactive_feedback("structure", state)
    
    # Process feedback using shared function
    return _process_review_feedback(state, "structure", feedback_data)


def human_review_content(state: CourseState) -> CourseState:
    """
    HITL checkpoint for course content approval.
    This node should trigger an interrupt in the graph.
    """
    _ensure_feedback_state(state, "content")
    
    # Check if we already have feedback (resuming after interrupt)
    if state["approval_status"].get("content") is not None:
        return state
    
    thread_id = state.get("course_metadata", {}).get("thread_id", "default")
    
    # Save results before interrupt
    saver = ResultsSaver()
    if state.get("course_content"):
        saver.save_course_content(state["course_content"], thread_id)
    
    # Show interrupt information
    show_interrupt_info("content", state, thread_id)
    
    # Get interactive feedback from user
    feedback_data = get_interactive_feedback("content", state)
    
    # Process feedback using shared function
    return _process_review_feedback(state, "content", feedback_data)


def human_review_quizzes(state: CourseState) -> CourseState:
    """
    HITL checkpoint for quiz approval.
    This node should trigger an interrupt in the graph.
    """
    _ensure_feedback_state(state, "quizzes")
    
    # Check if we already have feedback (resuming after interrupt)
    if state["approval_status"].get("quizzes") is not None:
        # State already has approval status, routing function will determine next step
        print(f"\n✅ Resuming after quiz review. Approval status: {state['approval_status'].get('quizzes')}")
        print("   Routing to next step based on approval status...\n")
        return state
    
    thread_id = state.get("course_metadata", {}).get("thread_id", "default")
    
    # Save results before interrupt
    saver = ResultsSaver()
    if state.get("quizzes"):
        saver.save_quizzes(state["quizzes"], thread_id)
    
    # Show interrupt information
    show_interrupt_info("quizzes", state, thread_id)
    
    # Get interactive feedback from user
    feedback_data = get_interactive_feedback("quizzes", state)
    
    # Process feedback using shared function
    return _process_review_feedback(state, "quizzes", feedback_data)

