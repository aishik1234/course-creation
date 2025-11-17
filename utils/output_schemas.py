"""Pydantic schemas for structured outputs from agents."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class LessonStructure(BaseModel):
    """Schema for lesson structure in module."""
    lesson_name: str
    lesson_objectives: List[str]
    estimated_duration: str


class QuizPlan(BaseModel):
    """Schema for quiz plan in module."""
    graded: int = Field(default=1)
    practice: int = Field(default=2)


class ModuleStructure(BaseModel):
    """Schema for a single module."""
    module_id: int
    module_name: str
    module_objectives: List[str]
    lessons: List[LessonStructure]
    duration_allocation: str
    quiz_plan: QuizPlan
    is_lab_module: bool = Field(default=False)


class ModuleStructureOutput(BaseModel):
    """Schema for complete module structure output."""
    modules: List[ModuleStructure]


class LessonContent(BaseModel):
    """Schema for lesson content."""
    lesson_id: Optional[str] = None
    module_id: int
    lesson_name: str
    introduction: str
    main_content: str
    examples: List[str] = Field(default_factory=list)
    case_studies: List[str] = Field(default_factory=list)
    practice_exercises: List[str] = Field(default_factory=list)
    summary: str
    visual_suggestions: List[str] = Field(default_factory=list)
    lab_instructions: Optional[str] = None


class Question(BaseModel):
    """Schema for quiz question."""
    question_id: Optional[str] = None
    question: str
    type: str  # "multiple_choice" | "true_false" | "short_answer" | "essay"
    options: Optional[List[str]] = None
    correct_answer: str
    explanation: str
    learning_objective: Optional[str] = None


class Quiz(BaseModel):
    """Schema for a quiz."""
    quiz_id: Optional[str] = None
    module_id: int
    quiz_type: str  # "graded" | "practice"
    questions: List[Question]
    answer_key: Optional[Dict[str, str]] = None
    learning_objectives_covered: List[str] = Field(default_factory=list)
    difficulty_level: Optional[str] = None

