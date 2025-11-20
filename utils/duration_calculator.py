"""Utility for calculating video durations based on course duration."""
from typing import Dict, List, Any


def parse_course_duration(duration_str: str) -> float:
    """
    Parse duration string to total hours.
    
    Examples:
    - "4 weeks" → 20 hours (4 × 5 hours/week)
    - "20 hours" → 20 hours
    - "8 weeks" → 40 hours (8 × 5 hours/week)
    - "2 months" → 40 hours (2 × 20 hours/month)
    
    Args:
        duration_str: Duration string like "4 weeks", "20 hours", etc.
    
    Returns:
        Total hours as float
    """
    duration_str = duration_str.lower().strip()
    
    # Extract number and unit
    parts = duration_str.split()
    if len(parts) < 2:
        # Try to parse as just hours
        try:
            return float(duration_str.replace("hours", "").replace("hour", "").strip())
        except:
            return 20.0  # Default to 20 hours
    
    number = float(parts[0])
    unit = parts[1]
    
    # Convert to hours
    if "week" in unit:
        return number * 5.0  # 5 hours per week
    elif "month" in unit:
        return number * 20.0  # 20 hours per month
    elif "hour" in unit:
        return number
    elif "day" in unit:
        return number * 2.0  # 2 hours per day
    else:
        # Default: assume weeks
        return number * 5.0


def calculate_video_durations(state: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate video duration for each lesson in minutes.
    
    Args:
        state: CourseState dictionary
    
    Returns:
        Dictionary mapping lesson_id to duration in minutes
        Format: {"module_1_lesson_1": 15.0, ...}
    """
    # Parse course duration
    course_duration_str = state.get("course_duration", "4 weeks")
    total_course_hours = parse_course_duration(course_duration_str)
    
    # Calculate total video hours (70% of course time)
    total_video_hours = total_course_hours * 0.7
    
    # Get all lessons
    module_structure = state.get("module_structure", {})
    modules = module_structure.get("modules", [])
    
    if not modules:
        return {}
    
    # Count total lessons
    total_lessons = 0
    module_lesson_counts = {}
    
    for module in modules:
        module_id = module.get("module_id", 0)
        lessons = module.get("lessons", [])
        lesson_count = len(lessons)
        module_lesson_counts[module_id] = lesson_count
        total_lessons += lesson_count
    
    if total_lessons == 0:
        return {}
    
    # Calculate average video time per lesson
    total_video_minutes = total_video_hours * 60
    avg_minutes_per_lesson = total_video_minutes / total_lessons
    
    # Apply constraints: min 5 minutes, max 30 minutes
    min_duration = 5.0
    max_duration = 30.0
    
    if avg_minutes_per_lesson < min_duration:
        avg_minutes_per_lesson = min_duration
    elif avg_minutes_per_lesson > max_duration:
        avg_minutes_per_lesson = max_duration
    
    # Create duration mapping for each lesson
    durations = {}
    
    for module in modules:
        module_id = module.get("module_id", 0)
        module_name = module.get("module_name", f"Module {module_id}")
        lessons = module.get("lessons", [])
        
        for lesson_idx, lesson in enumerate(lessons):
            lesson_name = lesson.get("lesson_name", f"Lesson {lesson_idx + 1}")
            lesson_id = lesson.get("lesson_id", f"lesson_{module_id}_{lesson_idx + 1}")
            
            # Use average duration (can be customized per lesson later)
            durations[lesson_id] = round(avg_minutes_per_lesson, 1)
    
    return durations

