"""Reusable UI components for course builder."""
import streamlit as st
from typing import Dict, Any, List


def render_module_structure_review(modules: List[Dict[str, Any]]):
    """Render module structure for review."""
    for i, module in enumerate(modules, 1):
        with st.expander(f"Module {i}: {module.get('module_name', 'Untitled')}", expanded=True):
            st.markdown(f"**Duration:** {module.get('duration_allocation', 'N/A')}")
            
            # Objectives
            if module.get('module_objectives'):
                st.markdown("**Objectives:**")
                for obj in module['module_objectives']:
                    st.markdown(f"- {obj}")
            
            # Lessons
            lessons = module.get('lessons', [])
            st.markdown(f"**Lessons:** {len(lessons)}")
            for j, lesson in enumerate(lessons, 1):
                st.markdown(f"  {j}. {lesson.get('lesson_name', 'Untitled')} ({lesson.get('estimated_duration', 'N/A')})")
            
            # Quiz plan
            quiz_plan = module.get('quiz_plan', {})
            if quiz_plan:
                st.markdown(f"**Quizzes:** {quiz_plan.get('graded', 0)} graded, {quiz_plan.get('practice', 0)} practice")


def render_content_review(lessons: List[Dict[str, Any]]):
    """Render lesson content for review."""
    for i, lesson in enumerate(lessons[:5], 1):  # Show first 5
        with st.expander(f"Lesson {i}: {lesson.get('lesson_name', 'Untitled')}", expanded=False):
            if lesson.get('introduction'):
                st.markdown("**Introduction:**")
                st.markdown(lesson['introduction'][:200] + "..." if len(lesson['introduction']) > 200 else lesson['introduction'])
            
            if lesson.get('main_content'):
                st.markdown("**Main Content:**")
                st.markdown(lesson['main_content'][:300] + "..." if len(lesson['main_content']) > 300 else lesson['main_content'])
    
    if len(lessons) > 5:
        st.info(f"... and {len(lessons) - 5} more lessons")


def render_quiz_review(quizzes: List[Dict[str, Any]]):
    """Render quizzes for review."""
    graded = [q for q in quizzes if q.get('quiz_type') == 'graded']
    practice = [q for q in quizzes if q.get('quiz_type') == 'practice']
    
    st.metric("Graded Quizzes", len(graded))
    st.metric("Practice Quizzes", len(practice))
    
    for i, quiz in enumerate(quizzes[:3], 1):  # Show first 3
        quiz_type = quiz.get('quiz_type', 'unknown')
        badge_color = "🔴" if quiz_type == "graded" else "🟡"
        
        with st.expander(f"{badge_color} {quiz.get('quiz_id', f'Quiz {i}')} ({quiz_type})", expanded=False):
            questions = quiz.get('questions', [])
            st.markdown(f"**Questions:** {len(questions)}")
            
            if questions:
                sample_q = questions[0]
                st.markdown("**Sample Question:**")
                st.markdown(sample_q.get('question_text', sample_q.get('question', 'N/A')))
    
    if len(quizzes) > 3:
        with st.expander(f"View all {len(quizzes)} quizzes", expanded=False):
            for i, quiz in enumerate(quizzes[3:], 4):
                quiz_type = quiz.get('quiz_type', 'unknown')
                badge_color = "🔴" if quiz_type == "graded" else "🟡"
                
                with st.expander(f"{badge_color} {quiz.get('quiz_id', f'Quiz {i}')} ({quiz_type})", expanded=False):
                    questions = quiz.get('questions', [])
                    st.markdown(f"**Questions:** {len(questions)}")
                    
                    if questions:
                        sample_q = questions[0]
                        st.markdown("**Sample Question:**")
                        st.markdown(sample_q.get('question_text', sample_q.get('question', 'N/A')))


def get_feedback_form(review_type: str) -> Dict[str, Any]:
    """Get feedback from user via form."""
    st.markdown(f"### 💬 Provide Feedback for {review_type.capitalize()}")
    
    approval = st.radio(
        "Do you approve this?",
        ["Approve", "Reject"],
        horizontal=True,
        key=f"approval_radio_{review_type}"  # Unique key for each review type
    )
    
    feedback_text = ""
    suggestions = []
    
    # Use review_type-specific session state keys
    suggestions_key = f"suggestions_{review_type}"
    
    if approval == "Reject":
        feedback_text = st.text_area(
            "What needs to be changed?",
            placeholder="Describe the issues you see...",
            height=100,
            key=f"feedback_text_{review_type}"
        )
        
        st.markdown("**Specific Suggestions:**")
        suggestion_input = st.text_input(
            "Enter a suggestion (press Enter to add more)",
            key=f"suggestion_input_{review_type}"
        )
        
        if suggestions_key not in st.session_state:
            st.session_state[suggestions_key] = []
        
        if st.button("Add Suggestion", key=f"add_suggestion_{review_type}"):
            if suggestion_input:
                st.session_state[suggestions_key].append(suggestion_input)
                st.rerun()
        
        if st.session_state[suggestions_key]:
            st.markdown("**Added Suggestions:**")
            for i, sug in enumerate(st.session_state[suggestions_key]):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"- {sug}")
                with col2:
                    if st.button("Remove", key=f"remove_{i}_{review_type}"):
                        st.session_state[suggestions_key].remove(sug)
                        st.rerun()
            
            suggestions = st.session_state[suggestions_key].copy()
        else:
            suggestions = []
    else:
        feedback_text = st.text_area(
            "Any comments? (optional)",
            placeholder="Optional feedback...",
            height=50,
            key=f"feedback_text_optional_{review_type}"
        )
        suggestions = []
    
    return {
        "approval_status": approval == "Approve",
        "feedback": feedback_text,
        "suggestions": suggestions
    }

