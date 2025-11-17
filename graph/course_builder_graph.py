"""LangGraph workflow definition for course builder."""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Literal
from state.base_state import CourseState

# Import nodes
from nodes.question_collector import collect_user_input
from agents.researcher_agent import researcher_agent
from agents.module_structure_agent import module_structure_agent
from agents.xdp_agent import xdp_agent
from agents.course_content_agent import course_content_agent
from agents.quiz_curator_agent import quiz_curator_agent
from nodes.validation_agent import (
    validate_module_structure,
    validate_content,
    validate_quizzes
)
from nodes.hitl_review_nodes import (
    human_review_structure,
    human_review_content,
    human_review_quizzes
)
from nodes.finalizer import finalize_course


def update_validation_results(state: CourseState, validation_type: str, validator_func):
    """Update validation results using LangGraph state update pattern."""
    if "validation_results" not in state:
        state["validation_results"] = {}
    state["validation_results"][validation_type] = validator_func(state)
    return state


def route_after_structure_validation(state: CourseState) -> Literal["pass", "review"]:
    """Route after module structure validation."""
    validation = state.get("validation_results", {}).get("module_structure", {})
    
    quality_score = validation.get("quality_score", 0.0)
    is_valid = validation.get("is_valid", False)
    
    if quality_score >= 0.7 and is_valid:
        return "pass"
    else:
        return "review"


def route_after_structure_review(state: CourseState) -> Literal["approve", "reject", "continue"]:
    """Route after human review of structure."""
    approval_status = state.get("approval_status", {}).get("structure")
    feedback = state.get("human_feedback", {}).get("structure", "").lower()
    
    if approval_status is True:
        return "approve"
    elif approval_status is False or "reject" in feedback:
        return "reject"  # Regenerate
    else:
        return "continue"  # Use edited version


def route_after_content_validation(state: CourseState) -> Literal["pass", "review"]:
    """Route after content validation."""
    validation = state.get("validation_results", {}).get("content", {})
    
    quality_score = validation.get("quality_score", 0.0)
    flagged_lessons = validation.get("flagged_lessons", [])
    
    if quality_score >= 0.8 and len(flagged_lessons) == 0:
        return "pass"
    else:
        return "review"


def route_after_content_review(state: CourseState) -> Literal["approve", "reject", "continue"]:
    """Route after human review of content."""
    approval_status = state.get("approval_status", {}).get("content")
    feedback = state.get("human_feedback", {}).get("content", "").lower()
    
    if approval_status is True:
        return "approve"
    elif approval_status is False or "reject" in feedback:
        return "reject"  # Regenerate
    else:
        return "continue"  # Use edited version


def route_after_quiz_validation(state: CourseState) -> Literal["pass", "review"]:
    """Route after quiz validation."""
    validation = state.get("validation_results", {}).get("quizzes", {})
    
    quality_score = validation.get("quality_score", 0.0)
    objective_coverage = validation.get("objective_coverage", 0.0)
    
    if quality_score >= 0.8 and objective_coverage >= 0.8:
        return "pass"
    else:
        return "review"


def route_after_quiz_review(state: CourseState) -> Literal["approve", "reject", "continue"]:
    """Route after human review of quizzes."""
    approval_status = state.get("approval_status", {}).get("quizzes")
    feedback = state.get("human_feedback", {}).get("quizzes", "").lower()
    
    print(f"\n🔀 Routing after quiz review:")
    print(f"   Approval status: {approval_status}")
    print(f"   Feedback: {feedback[:50] if feedback else 'None'}...")
    
    if approval_status is True:
        print("   → Routing to: finalize_course (approve)")
        return "approve"
    elif approval_status is False or "reject" in feedback:
        print("   → Routing to: quiz_curator_agent (reject)")
        return "reject"  # Regenerate
    else:
        print("   → Routing to: finalize_course (continue)")
        return "continue"  # Use edited version


def create_course_builder_graph():
    """Create and configure the course builder LangGraph."""
    
    # Create state graph
    workflow = StateGraph(CourseState)
    
    # Add nodes
    workflow.add_node("collect_user_input", collect_user_input)
    workflow.add_node("researcher_agent", researcher_agent)
    workflow.add_node("module_structure_agent", module_structure_agent)
    workflow.add_node("validate_module_structure", 
                     lambda state: update_validation_results(state, "module_structure", validate_module_structure))
    workflow.add_node("human_review_structure", human_review_structure)
    workflow.add_node("xdp_agent", xdp_agent)
    workflow.add_node("course_content_agent", course_content_agent)
    workflow.add_node("validate_content",
                     lambda state: update_validation_results(state, "content", validate_content))
    workflow.add_node("human_review_content", human_review_content)
    workflow.add_node("quiz_curator_agent", quiz_curator_agent)
    workflow.add_node("validate_quizzes",
                     lambda state: update_validation_results(state, "quizzes", validate_quizzes))
    workflow.add_node("human_review_quizzes", human_review_quizzes)
    workflow.add_node("finalize_course", finalize_course)
    
    # Set entry point
    workflow.set_entry_point("collect_user_input")
    
    # Add edges
    workflow.add_edge("collect_user_input", "researcher_agent")
    workflow.add_edge("researcher_agent", "module_structure_agent")
    workflow.add_edge("module_structure_agent", "validate_module_structure")
    
    # Conditional edge after structure validation
    workflow.add_conditional_edges(
        "validate_module_structure",
        route_after_structure_validation,
        {
            "pass": "xdp_agent",
            "review": "human_review_structure"
        }
    )
    
    # Conditional edge after structure review (with interrupt)
    workflow.add_conditional_edges(
        "human_review_structure",
        route_after_structure_review,
        {
            "approve": "xdp_agent",
            "reject": "module_structure_agent",
            "continue": "xdp_agent"
        }
    )
    
    workflow.add_edge("xdp_agent", "course_content_agent")
    workflow.add_edge("course_content_agent", "validate_content")
    
    # Conditional edge after content validation
    workflow.add_conditional_edges(
        "validate_content",
        route_after_content_validation,
        {
            "pass": "quiz_curator_agent",
            "review": "human_review_content"
        }
    )
    
    # Conditional edge after content review (with interrupt)
    workflow.add_conditional_edges(
        "human_review_content",
        route_after_content_review,
        {
            "approve": "quiz_curator_agent",
            "reject": "course_content_agent",
            "continue": "quiz_curator_agent"
        }
    )
    
    workflow.add_edge("quiz_curator_agent", "validate_quizzes")
    
    # Conditional edge after quiz validation
    workflow.add_conditional_edges(
        "validate_quizzes",
        route_after_quiz_validation,
        {
            "pass": "finalize_course",
            "review": "human_review_quizzes"
        }
    )
    
    # Conditional edge after quiz review (with interrupt)
    workflow.add_conditional_edges(
        "human_review_quizzes",
        route_after_quiz_review,
        {
            "approve": "finalize_course",
            "reject": "quiz_curator_agent",
            "continue": "finalize_course"
        }
    )
    
    workflow.add_edge("finalize_course", END)
    
    # Compile graph with checkpointing and interrupts for HITL
    memory = MemorySaver()
    app = workflow.compile(
        checkpointer=memory,
        interrupt_after=["human_review_structure", "human_review_content", "human_review_quizzes"]
    )
    
    return app


# Export the graph
if __name__ == "__main__":
    graph = create_course_builder_graph()
    print("Course Builder Graph created successfully!")

