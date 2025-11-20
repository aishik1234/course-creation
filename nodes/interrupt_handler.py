"""Handle workflow interrupts and collect human feedback."""
import json
import os
from typing import Dict, Any, Optional
from utils.results_saver import ResultsSaver


def get_interactive_feedback(interrupt_type: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Interactively collect human feedback from UI or command line.
    First checks for UI feedback file (polls for it), then falls back to CLI.
    
    Args:
        interrupt_type: Type of interrupt ("structure", "content", "quizzes")
        state: Current workflow state
    
    Returns:
        Feedback dictionary
    """
    import time
    
    thread_id = state.get("course_metadata", {}).get("thread_id", "default")
    feedback_file = f"course_outputs/{thread_id}_feedback_{interrupt_type}.json"
    
    # Poll for UI feedback file (for Streamlit UI)
    # Check every 2 seconds, up to 600 seconds (10 minutes) total - reduced for faster workflow
    max_wait_time = 600
    check_interval = 2
    elapsed = 0
    
    print(f"\n⏸️  Waiting for {interrupt_type} review feedback...")
    print(f"   (If using UI, please submit feedback within 600s (10 minutes). Otherwise, this will timeout and use CLI.)")
    
    while elapsed < max_wait_time:
        if os.path.exists(feedback_file):
            print(f"\n✅ Found UI feedback for {interrupt_type}. Loading...")
            with open(feedback_file, "r", encoding="utf-8") as f:
                feedback_data = json.load(f)
            # Clean up the file after reading
            os.remove(feedback_file)
            return feedback_data
        
        time.sleep(check_interval)
        elapsed += check_interval
        if elapsed % 10 == 0:  # Print every 10 seconds
            print(f"   [{thread_id}] Still waiting for {interrupt_type} feedback... ({elapsed}s elapsed)")
    
    # If no UI feedback after timeout, use CLI (for terminal-based execution)
    print(f"\n⏰ No UI feedback received after {max_wait_time}s. Using CLI input...")
    print("\n" + "="*70)
    print(f"⏸️  HUMAN REVIEW REQUIRED - {interrupt_type.upper()}")
    print("="*70)
    
    # Show the content that needs review
    if interrupt_type == "structure":
        _show_structure_for_review(state)
    elif interrupt_type == "content":
        _show_content_for_review(state)
    elif interrupt_type == "quizzes":
        _show_quizzes_for_review(state)
    
    print("\n" + "="*70)
    
    # Ask for approval
    while True:
        response = input("\n❓ Do you approve this? (approve/reject): ").strip().lower()
        if response in ["approve", "a", "yes", "y"]:
            approval_status = True
            feedback_text = input("💬 Any comments? (press Enter to skip): ").strip()
            return {
                interrupt_type: {
                    "approval_status": True,
                    "feedback": feedback_text if feedback_text else "Approved",
                    "specific_issues": [],
                    "suggestions": []
                }
            }
        elif response in ["reject", "r", "no", "n"]:
            approval_status = False
            print("\n📝 Please provide feedback for improvement:")
            feedback_text = input("💬 What needs to be changed? ").strip()
            
            # Collect specific issues
            print("\n📋 List specific issues (press Enter after each, type 'done' when finished):")
            issues = []
            while True:
                issue = input("   Issue: ").strip()
                if issue.lower() == "done" or not issue:
                    break
                issues.append(issue)
            
            # Collect suggestions
            print("\n💡 Provide suggestions for improvement (press Enter after each, type 'done' when finished):")
            suggestions = []
            while True:
                suggestion = input("   Suggestion: ").strip()
                if suggestion.lower() == "done" or not suggestion:
                    break
                suggestions.append(suggestion)
            
            return {
                interrupt_type: {
                    "approval_status": False,
                    "feedback": feedback_text,
                    "specific_issues": issues,
                    "suggestions": suggestions
                }
            }
        else:
            print("❌ Invalid input. Please enter 'approve' or 'reject'.")


def _show_structure_for_review(state: Dict[str, Any]):
    """Display module structure for human review."""
    structure = state.get("module_structure", {})
    modules = structure.get("modules", [])
    
    print("\n📊 MODULE STRUCTURE TO REVIEW:")
    print("="*70)
    print(f"Total Modules: {len(modules)}\n")
    
    for i, module in enumerate(modules, 1):
        print(f"Module {i}: {module.get('module_name', 'N/A')}")
        print(f"  Objectives: {', '.join(module.get('module_objectives', [])[:3])}")
        if len(module.get('module_objectives', [])) > 3:
            print(f"  ... and {len(module.get('module_objectives', [])) - 3} more objectives")
        print(f"  Lessons: {len(module.get('lessons', []))}")
        print(f"  Duration: {module.get('duration_allocation', 'N/A')}")
        quiz_plan = module.get('quiz_plan', {})
        print(f"  Quizzes: {quiz_plan.get('graded', 0)} graded, {quiz_plan.get('practice', 0)} practice")
        if module.get('is_lab_module'):
            print(f"  ⚗️  Lab Module")
        print()


def _show_content_for_review(state: Dict[str, Any]):
    """Display course content for human review."""
    content = state.get("course_content", [])
    
    print("\n📚 COURSE CONTENT TO REVIEW:")
    print("="*70)
    print(f"Total Lessons: {len(content)}\n")
    
    # Show first 3 lessons in detail, then summary
    for i, lesson in enumerate(content[:3], 1):
        print(f"Lesson {i}: {lesson.get('title', 'N/A')}")
        print(f"  Module: {lesson.get('module_id', 'N/A')}")
        print(f"  Content preview: {str(lesson.get('content', ''))[:100]}...")
        if lesson.get('examples'):
            print(f"  Examples: {len(lesson.get('examples', []))} provided")
        print()
    
    if len(content) > 3:
        print(f"... and {len(content) - 3} more lessons")


def _show_quizzes_for_review(state: Dict[str, Any]):
    """Display quizzes for human review."""
    quizzes = state.get("quizzes") or []
    
    print("\n📝 QUIZZES TO REVIEW:")
    print("="*70)
    print(f"Total Quizzes: {len(quizzes)}\n")
    
    graded = [q for q in quizzes if q.get("quiz_type") == "graded"]
    practice = [q for q in quizzes if q.get("quiz_type") == "practice"]
    
    print(f"Graded Quizzes: {len(graded)}")
    print(f"Practice Quizzes: {len(practice)}\n")
    
    # Show first 2 quizzes in detail
    for i, quiz in enumerate(quizzes[:2], 1):
        quiz_name = quiz.get('quiz_id', quiz.get('title', 'N/A'))
        print(f"Quiz {i}: {quiz_name} ({quiz.get('quiz_type', 'N/A')})")
        print(f"  Module: {quiz.get('module_id', 'N/A')}")
        questions = quiz.get('questions', [])
        print(f"  Questions: {len(questions)}")
        if questions:
            # Try both 'question_text' and 'question' fields
            question_text = questions[0].get('question_text') or questions[0].get('question', 'N/A')
            if question_text != 'N/A':
                print(f"  Sample question: {question_text[:80]}...")
            else:
                print(f"  Sample question: N/A")
        print()
    
    if len(quizzes) > 2:
        print(f"... and {len(quizzes) - 2} more quizzes")


def show_interrupt_info(interrupt_type: str, state: Dict[str, Any], thread_id: str):
    """
    Display information about what needs human review at interrupt point.
    Now uses interactive CLI instead of file-based feedback.
    """
    saver = ResultsSaver()
    
    # Save results for reference
    if interrupt_type == "structure" and state.get("module_structure"):
        saver.save_interrupt_state("structure", state, thread_id)
        saver.save_module_structure(state["module_structure"], thread_id)
    elif interrupt_type == "content" and state.get("course_content"):
        saver.save_interrupt_state("content", state, thread_id)
        saver.save_course_content(state["course_content"], thread_id)
    elif interrupt_type == "quizzes" and state.get("quizzes"):
        saver.save_interrupt_state("quizzes", state, thread_id)
        saver.save_quizzes(state["quizzes"], thread_id)


def load_human_feedback(thread_id: str, interrupt_type: str) -> Optional[Dict[str, Any]]:
    """
    Load human feedback from file.
    
    Args:
        thread_id: Thread ID
        interrupt_type: Type of interrupt
    
    Returns:
        Feedback dictionary or None
    """
    feedback_file = f"course_outputs/{thread_id}_feedback_{interrupt_type}.json"
    
    if not os.path.exists(feedback_file):
        return None
    
    with open(feedback_file, "r", encoding="utf-8") as f:
        return json.load(f)


def create_feedback_template(thread_id: str, interrupt_type: str):
    """Create a template feedback file for human to fill."""
    template = {
        interrupt_type: {
            "approval_status": None,  # True = approve, False = reject, None = needs edits
            "feedback": "",
            "specific_issues": [],
            "suggestions": [],
            "edits": {}  # Specific edits to make
        }
    }
    
    feedback_file = f"course_outputs/{thread_id}_feedback_{interrupt_type}_template.json"
    os.makedirs("course_outputs", exist_ok=True)
    
    with open(feedback_file, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2)
    
    print(f"📝 Created feedback template: {feedback_file}")
    print("   Fill this file with your feedback and rename it to remove '_template'")
    return feedback_file

