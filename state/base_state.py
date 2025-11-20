"""Base state class for LangGraph course builder."""
from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph.message import add_messages


class BaseState(TypedDict):
    """Base state class that all states should inherit from."""
    current_step: str
    errors: List[str]
    course_metadata: Dict[str, Any]


class CourseState(BaseState):
    """Complete state schema for course building workflow."""
    
    # User Input (from questions)
    course_subject: str
    learner_level: str  # "basic" | "intermediate" | "advanced"
    course_duration: str  # e.g., "4 weeks", "20 hours"
    number_of_modules: int
    graded_quizzes_per_module: int
    practice_quizzes_per_module: int
    needs_lab_module: bool
    custom_prompt: str  # Optional custom instructions for course building
    
    # Agent Outputs
    research_findings: Optional[Dict[str, Any]]  # Key areas, topics, objectives
    module_structure: Optional[Dict[str, Any]]  # Modules with lessons breakdown
    xdp_content: Optional[Dict[str, Any]]  # XDP format specification
    course_content: Optional[List[Dict[str, Any]]]  # Full lesson content
    quizzes: Optional[List[Dict[str, Any]]]  # All quizzes (graded + practice)
    video_transcripts: Optional[List[Dict[str, Any]]]  # Video transcripts for lessons
    
    # Validation & Control
    validation_results: Dict[str, Any]  # Scores and flags
    human_feedback: Dict[str, str]  # Feedback at each checkpoint
    approval_status: Dict[str, bool]  # Approval flags

