"""Streamlit UI for Course Builder - Coursera-like interface."""
import streamlit as st
import json
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import run_course_builder, initialize_state
from utils.results_saver import ResultsSaver
from ui.progress_display import display_progress_ui
from ui.real_time_updates import display_step_progress, display_content_as_ready


# Page configuration - Coursera-inspired
st.set_page_config(
    page_title="AI Course Builder",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "AI Course Builder - Create comprehensive online courses with AI assistance"
    }
)

# Custom CSS for Coursera-like styling
st.markdown("""
<style>
    /* Coursera-inspired theme */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a73e8;
        margin-bottom: 1rem;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    }
    
    /* Module cards - Coursera style */
    .module-card {
        background: white;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        border-left: 4px solid #1a73e8;
        transition: box-shadow 0.3s ease;
    }
    
    .module-card:hover {
        box-shadow: 0 3px 6px rgba(0,0,0,0.16), 0 3px 6px rgba(0,0,0,0.23);
    }
    
    /* Lesson items */
    .lesson-item {
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        background: #f8f9fa;
        border-radius: 4px;
        border-left: 3px solid #34a853;
        transition: background-color 0.2s ease;
    }
    
    .lesson-item:hover {
        background: #e8f0fe;
    }
    
    /* Quiz badges - Coursera style */
    .quiz-badge {
        display: inline-block;
        padding: 0.375rem 0.875rem;
        border-radius: 16px;
        font-size: 0.875rem;
        font-weight: 500;
        margin: 0.25rem;
        letter-spacing: 0.3px;
    }
    
    .graded-badge {
        background: #ea4335;
        color: white;
        box-shadow: 0 1px 2px rgba(234, 67, 53, 0.3);
    }
    
    .practice-badge {
        background: #fbbc04;
        color: #202124;
        box-shadow: 0 1px 2px rgba(251, 188, 4, 0.3);
    }
    
    /* Progress bar */
    .progress-bar {
        height: 8px;
        background: #e0e0e0;
        border-radius: 4px;
        margin: 1rem 0;
        overflow: hidden;
    }
    
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #1a73e8 0%, #4285f4 100%);
        border-radius: 4px;
        transition: width 0.3s ease;
    }
    
    /* Coursera-style buttons */
    .stButton > button {
        background-color: #1a73e8;
        color: white;
        border-radius: 4px;
        border: none;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
        transition: background-color 0.2s ease, box-shadow 0.2s ease;
    }
    
    .stButton > button:hover {
        background-color: #1557b0;
        box-shadow: 0 2px 4px rgba(26, 115, 232, 0.3);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* Main content area */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 600;
        color: #1a73e8;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #202124;
    }
    
    /* Input fields */
    .stTextInput > div > div > input {
        border-radius: 4px;
        border: 1px solid #dadce0;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #1a73e8;
        box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.1);
    }
    
    /* Selectbox styling */
    .stSelectbox > div > div {
        border-radius: 4px;
    }
    
    /* Info boxes */
    .stInfo {
        background-color: #e8f0fe;
        border-left: 4px solid #1a73e8;
        border-radius: 4px;
    }
    
    .stSuccess {
        background-color: #e6f4ea;
        border-left: 4px solid #34a853;
        border-radius: 4px;
    }
    
    .stWarning {
        background-color: #fef7e0;
        border-left: 4px solid #fbbc04;
        border-radius: 4px;
    }
    
    .stError {
        background-color: #fce8e6;
        border-left: 4px solid #ea4335;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)


def display_module_card(module, module_num):
    """Display a module card in Coursera-like style."""
    # Use XDP module name if available, otherwise use regular module name
    module_name = module.get('xdp_module_name') or module.get('module_name', 'Untitled')
    
    st.markdown(f"""
    <div class="module-card">
        <h3 style="color: #1a73e8; margin-bottom: 0.5rem;">Module {module_num}: {module_name}</h3>
        <p style="color: #666; margin-bottom: 1rem;">{module.get('duration_allocation', 'N/A')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Display XDP module description if available
    xdp_description = module.get('xdp_module_description')
    if xdp_description:
        st.markdown(f"""
        <div style="background: #f8f9fa; padding: 1rem; border-radius: 4px; margin-bottom: 1rem; border-left: 3px solid #1a73e8;">
            <p style="color: #5f6368; margin: 0; line-height: 1.6;"><strong>Module Overview:</strong> {xdp_description}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Module objectives
    if module.get('module_objectives'):
        with st.expander("📋 Module Objectives", expanded=False):
            for obj in module.get('module_objectives', []):
                st.markdown(f"• {obj}")
    
    # Lessons
    lessons = module.get('lessons', [])
    if lessons:
        st.markdown("### 📖 Lessons")
        for i, lesson in enumerate(lessons, 1):
            st.markdown(f"""
            <div class="lesson-item">
                <strong>Lesson {i}: {lesson.get('lesson_name', 'Untitled')}</strong><br>
                <small>Duration: {lesson.get('estimated_duration', 'N/A')}</small>
            </div>
            """, unsafe_allow_html=True)
            
            # Lesson objectives
            if lesson.get('lesson_objectives'):
                with st.expander(f"Objectives for Lesson {i}", expanded=False):
                    for obj in lesson.get('lesson_objectives', []):
                        st.markdown(f"• {obj}")
    
    # Quiz plan
    quiz_plan = module.get('quiz_plan', {})
    if quiz_plan:
        graded = quiz_plan.get('graded', 0)
        practice = quiz_plan.get('practice', 0)
        if graded > 0 or practice > 0:
            st.markdown("### 📝 Assessments")
            if graded > 0:
                st.markdown(f'<span class="quiz-badge graded-badge">Graded: {graded}</span>', unsafe_allow_html=True)
            if practice > 0:
                st.markdown(f'<span class="quiz-badge practice-badge">Practice: {practice}</span>', unsafe_allow_html=True)
    
    st.markdown("---")


def display_lesson_content(lesson, transcript=None):
    """Display detailed lesson content."""
    st.markdown(f"### {lesson.get('lesson_name', 'Untitled Lesson')}")
    
    # Video Transcript (show first if available)
    if transcript or lesson.get('video_transcript'):
        transcript_data = transcript or lesson.get('video_transcript')
        if transcript_data and transcript_data.get('transcript'):
            st.markdown("#### 🎥 Video Transcript")
            duration = transcript_data.get('video_duration_minutes', 0)
            word_count = transcript_data.get('word_count', 0)
            
            st.info(f"⏱️ **Duration:** {duration} minutes | 📝 **Words:** {word_count}")
            
            with st.expander("📄 View Full Transcript", expanded=False):
                st.markdown(transcript_data['transcript'])
            
            st.markdown("---")
    
    # Introduction
    if lesson.get('introduction'):
        st.markdown("#### 📌 Introduction")
        st.markdown(lesson['introduction'])
    
    # Main content
    if lesson.get('main_content'):
        st.markdown("#### 📚 Main Content")
        st.markdown(lesson['main_content'])
    
    # Examples
    if lesson.get('examples'):
        st.markdown("#### 💡 Examples")
        for example in lesson['examples']:
            st.markdown(f"- {example}")
    
    # Case studies
    if lesson.get('case_studies'):
        st.markdown("#### 🔬 Case Studies")
        for case in lesson['case_studies']:
            st.markdown(f"- {case}")
    
    # Practice exercises
    if lesson.get('practice_exercises'):
        st.markdown("#### ✏️ Practice Exercises")
        for exercise in lesson['practice_exercises']:
            st.markdown(f"- {exercise}")
    
    # Summary
    if lesson.get('summary'):
        st.markdown("#### 📝 Summary")
        st.markdown(lesson['summary'])
    
    # Visual suggestions
    if lesson.get('visual_suggestions'):
        st.markdown("#### 🎨 Visual Suggestions")
        for visual in lesson['visual_suggestions']:
            st.markdown(f"- {visual}")


def display_quiz(quiz):
    """Display quiz in a structured format."""
    quiz_type = quiz.get('quiz_type', 'unknown')
    badge_class = "graded-badge" if quiz_type == "graded" else "practice-badge"
    
    st.markdown(f"""
    <div class="module-card">
        <h4 style="color: #1a73e8;">
            <span class="quiz-badge {badge_class}">{quiz_type.upper()}</span>
            {quiz.get('quiz_id', 'Quiz')}
        </h4>
        <p>Module: {quiz.get('module_id', 'N/A')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    questions = quiz.get('questions', [])
    if questions:
        st.markdown(f"**Total Questions: {len(questions)}**")
        
        with st.expander("View Questions", expanded=False):
            for i, question in enumerate(questions, 1):
                st.markdown(f"**Q{i}: {question.get('question_text', question.get('question', 'N/A'))}**")
                
                # Options for multiple choice
                if question.get('options'):
                    options = question['options']
                    if isinstance(options, list) and len(options) > 0:
                        if isinstance(options[0], dict):
                            # Structured options
                            for opt in options:
                                st.markdown(f"  - {opt.get('option_text', opt.get('option', 'N/A'))}")
                        else:
                            # Simple list
                            for opt in options:
                                st.markdown(f"  - {opt}")
                
                # Correct answer
                if question.get('correct_answer'):
                    with st.expander("Show Answer", expanded=False):
                        st.markdown(f"**Answer:** {question['correct_answer']}")
                
                # Explanation
                if question.get('explanation'):
                    with st.expander("Explanation", expanded=False):
                        st.markdown(question['explanation'])
                
                st.markdown("---")


def main():
    """Main Streamlit app."""
    st.markdown('<h1 class="main-header">📚 AI Course Builder</h1>', unsafe_allow_html=True)
    
    # Sidebar for navigation
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Select Page",
            ["🏠 Home", "📝 Create Course", "📊 View Course"]
        )
    
    # Initialize session state
    if 'course_data' not in st.session_state:
        st.session_state.course_data = None
    if 'workflow_state' not in st.session_state:
        st.session_state.workflow_state = None
    if 'workflow_running' not in st.session_state:
        st.session_state.workflow_running = False
    if 'workflow_complete' not in st.session_state:
        st.session_state.workflow_complete = False
    if 'thread_id' not in st.session_state:
        st.session_state.thread_id = 'default'
    
    # Home page
    if page == "🏠 Home":
        st.markdown("""
        ## Welcome to AI Course Builder
        
        This tool helps you create comprehensive online courses with:
        - 📚 Structured modules and lessons
        - 📝 Graded and practice quizzes
        - 🎯 Learning objectives
        - 💡 Examples and case studies
        
        ### Getting Started
        1. Go to **Create Course** to input your requirements
        2. Review the generated course structure
        3. Provide feedback at review checkpoints
        4. View the final course in **View Course**
        """)
    
    # Create Course page
    elif page == "📝 Create Course":
        st.header("Create New Course")
        
        with st.form("course_input_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                course_subject = st.text_input(
                    "Course Subject",
                    placeholder="e.g., Python Programming, Data Science",
                    help="The main topic of your course"
                )
                
                learner_level = st.selectbox(
                    "Learner Level",
                    ["basic", "intermediate", "advanced"],
                    help="Target audience skill level"
                )
                
                course_duration = st.text_input(
                    "Course Duration",
                    placeholder="e.g., 4 weeks, 20 hours",
                    help="Total time commitment for the course"
                )
            
            with col2:
                number_of_modules = st.number_input(
                    "Number of Modules",
                    min_value=1,
                    max_value=20,
                    value=4,
                    help="How many modules should the course have?"
                )
                
                graded_quizzes = st.number_input(
                    "Graded Quizzes per Module",
                    min_value=0,
                    max_value=5,
                    value=1,
                    help="Number of graded assessments per module"
                )
                
                practice_quizzes = st.number_input(
                    "Practice Quizzes per Module",
                    min_value=0,
                    max_value=10,
                    value=2,
                    help="Number of practice quizzes per module"
                )
            
            needs_lab = st.checkbox(
                "Include Lab Module",
                value=False,
                help="Add a hands-on lab module for practical exercises"
            )
            
            custom_prompt = st.text_area(
                "Custom Instructions (Optional)",
                placeholder="e.g., Focus on practical examples, include real-world case studies, emphasize hands-on learning...",
                help="Provide any specific instructions or requirements for how the course should be structured or what it should emphasize",
                height=100
            )
            
            submitted = st.form_submit_button("🚀 Generate Course", type="primary")
            
            if submitted:
                if not course_subject:
                    st.error("Please enter a course subject")
                else:
                    user_input = {
                        "course_subject": course_subject,
                        "learner_level": learner_level,
                        "course_duration": course_duration,
                        "number_of_modules": number_of_modules,
                        "graded_quizzes_per_module": graded_quizzes,
                        "practice_quizzes_per_module": practice_quizzes,
                        "needs_lab_module": needs_lab,
                        "custom_prompt": custom_prompt.strip() if custom_prompt else ""
                    }
                    
                    # Generate new thread_id for fresh start
                    import uuid
                    new_thread_id = str(uuid.uuid4())[:8]
                    
                    # Store input and mark workflow as running with new thread_id
                    st.session_state.user_input = user_input
                    st.session_state.thread_id = new_thread_id
                    st.session_state.workflow_running = True
                    st.session_state.workflow_complete = False
                    st.rerun()
        
        # Check for interrupts and show inline review UI FIRST (before workflow execution)
        thread_id = st.session_state.get('thread_id', 'default')
        saver = ResultsSaver()
        
        # Add manual refresh button for interrupt detection
        if st.session_state.get('workflow_running') and not st.session_state.get('workflow_complete'):
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🔄 Check for Review", help="Click to check if review is needed"):
                    st.rerun()
        
        interrupt_structure = saver.get_latest_result("interrupt_structure", thread_id)
        interrupt_content = saver.get_latest_result("interrupt_content", thread_id)
        interrupt_quizzes = saver.get_latest_result("interrupt_quizzes", thread_id)
        
        # Determine which interrupt is active (most recent)
        # Priority: quizzes > content > structure (workflow order)
        active_interrupt = None
        active_type = None
        
        # Determine active interrupt (most recent one)
        if interrupt_quizzes:
            active_interrupt = interrupt_quizzes
            active_type = "quizzes"
        elif interrupt_content:
            active_interrupt = interrupt_content
            active_type = "content"
        elif interrupt_structure:
            active_interrupt = interrupt_structure
            active_type = "structure"
        
        # Show review UI if active interrupt detected - THIS MUST APPEAR BEFORE WORKFLOW SECTION
        if active_interrupt:
            st.markdown("---")
            st.markdown("## ⏸️ Review Required")
            st.warning("⚠️ **Workflow is waiting for your feedback!** Please review and submit below.")
            
            feedback_submitted = False
            
            # Structure review
            if active_type == "structure" and interrupt_structure:
                st.markdown("### 1️⃣ Module Structure Review")
                structure_data = interrupt_structure.get('data', {}).get('state', {})
                modules = structure_data.get('module_structure', {}).get('modules', [])
                
                if modules:
                    from ui.components import render_module_structure_review, get_feedback_form
                    render_module_structure_review(modules)
                    
                    feedback = get_feedback_form("structure")
                    
                    if st.button("✅ Submit Structure Feedback", type="primary", key="submit_structure"):
                        # Save feedback to file for workflow to pick up
                        feedback_file = f"course_outputs/{thread_id}_feedback_structure.json"
                        os.makedirs("course_outputs", exist_ok=True)
                        with open(feedback_file, "w", encoding="utf-8") as f:
                            json.dump({"structure": feedback}, f, indent=2)
                        st.success("✅ Feedback submitted! Workflow will continue...")
                        st.session_state.structure_feedback_submitted = True
                        feedback_submitted = True
                        st.rerun()
            
            # Content review
            elif active_type == "content" and interrupt_content:
                st.markdown("### 2️⃣ Content Review")
                content_data = interrupt_content.get('data', {}).get('state', {})
                lessons = content_data.get('course_content', [])
                
                if lessons:
                    from ui.components import render_content_review, get_feedback_form
                    render_content_review(lessons)
                    
                    feedback = get_feedback_form("content")
                    
                    if st.button("✅ Submit Content Feedback", type="primary", key="submit_content"):
                        feedback_file = f"course_outputs/{thread_id}_feedback_content.json"
                        os.makedirs("course_outputs", exist_ok=True)
                        with open(feedback_file, "w", encoding="utf-8") as f:
                            json.dump({"content": feedback}, f, indent=2)
                        st.success("✅ Feedback submitted! Workflow will continue...")
                        st.session_state.content_feedback_submitted = True
                        feedback_submitted = True
                        st.rerun()
            
            # Quiz review
            elif active_type == "quizzes" and interrupt_quizzes:
                st.markdown("### 3️⃣ Quiz Review")
                quiz_data = interrupt_quizzes.get('data', {}).get('state', {})
                quizzes = quiz_data.get('quizzes', [])
                
                if quizzes:
                    from ui.components import render_quiz_review, get_feedback_form
                    render_quiz_review(quizzes)
                    
                    feedback = get_feedback_form("quizzes")
                    
                    if st.button("✅ Submit Quiz Feedback", type="primary", key="submit_quizzes"):
                        feedback_file = f"course_outputs/{thread_id}_feedback_quizzes.json"
                        os.makedirs("course_outputs", exist_ok=True)
                        with open(feedback_file, "w", encoding="utf-8") as f:
                            json.dump({"quizzes": feedback}, f, indent=2)
                        st.success("✅ Feedback submitted! Workflow will continue...")
                        st.session_state.quiz_feedback_submitted = True
                        feedback_submitted = True
                        st.rerun()
            
            # Don't run workflow if waiting for feedback
            if not feedback_submitted:
                return
        
        # Run workflow in a separate section to persist across navigation
        if st.session_state.get('workflow_running') and not st.session_state.get('workflow_complete'):
            # Check if we're waiting for feedback
            if active_interrupt:
                st.warning("⏸️ **Workflow is paused waiting for your review!** Scroll up to see the review form and provide feedback.")
                st.info("💡 **Tip:** If you don't see the review form above, click the '🔄 Check for Review' button or refresh the page (F5).")
                return
            
            thread_id = st.session_state.get('thread_id', 'default')
            
            # Create containers for step-by-step updates
            progress_container = st.empty()
            content_container = st.container()
            
            # Display current step progress (disappears when content is ready)
            message_showing = display_step_progress(thread_id, progress_container)
            
            # Display content as it becomes available
            display_content_as_ready(thread_id, content_container)
            
            st.info("💡 **Tip:** This page auto-refreshes every 2 seconds to show latest progress. Stay on this page.")
            
            # Check if workflow has been started
            if not st.session_state.get('workflow_started', False):
                st.session_state.workflow_started = True
                try:
                    user_input = st.session_state.get('user_input')
                    thread_id = st.session_state.get('thread_id', 'default')
                    
                    # Run workflow (this will block, but progress is shown via progress file)
                    final_state, thread_id = run_course_builder(user_input, thread_id)
                    st.session_state.course_data = final_state
                    st.session_state.thread_id = thread_id
                    st.session_state.workflow_running = False
                    st.session_state.workflow_complete = True
                    st.session_state.workflow_started = False
                    st.success("✅ Course generated successfully!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error generating course: {str(e)}")
                    st.session_state.workflow_running = False
                    st.session_state.workflow_started = False
                    st.exception(e)
            else:
                # Auto-refresh every 2 seconds to show updates
                import time
                time.sleep(2)
                st.rerun()
    
    # View Course page
    elif page == "📊 View Course":
        st.header("View Generated Course")
        
        thread_id = st.session_state.get('thread_id', 'default')
        saver = ResultsSaver()
        
        # Load course data
        module_structure = saver.get_latest_result("module_structure", thread_id)
        course_content = saver.get_latest_result("course_content", thread_id)
        quizzes = saver.get_latest_result("quizzes", thread_id)
        final_course = saver.get_latest_result("final_course", thread_id)
        xdp_content = saver.get_latest_result("xdp_content", thread_id)
        video_transcripts = saver.get_latest_result("video_transcripts", thread_id)
        
        if not module_structure:
            st.info("No course data found. Please create a course first.")
        else:
            # Extract data - handle both possible structures defensively
            # Structure 1: data.modules (current format)
            # Structure 2: data.module_structure.modules (legacy format)
            data = module_structure.get('data', {})
            modules_data = data.get('modules', [])
            if not modules_data:
                # Try legacy structure
                modules_data = data.get('module_structure', {}).get('modules', [])
            
            # Extract XDP design patterns for module names and descriptions
            xdp_design_patterns = {}
            if xdp_content:
                xdp_data = xdp_content.get('data', {})
                if isinstance(xdp_data, dict):
                    design_patterns = xdp_data.get('design_patterns', [])
                    for pattern in design_patterns:
                        module_id = pattern.get('module_id')
                        if module_id:
                            xdp_design_patterns[module_id] = {
                                'module_name': pattern.get('module_name', ''),
                                'module_description': pattern.get('module_description', '')
                            }
            
            # Enhance modules_data with XDP information if available
            for module in modules_data:
                module_id = module.get('module_id')
                if module_id in xdp_design_patterns:
                    xdp_info = xdp_design_patterns[module_id]
                    # Use XDP module_name if available and different
                    if xdp_info.get('module_name'):
                        module['xdp_module_name'] = xdp_info['module_name']
                    # Add XDP description
                    if xdp_info.get('module_description'):
                        module['xdp_module_description'] = xdp_info['module_description']
            
            # Handle course content - check multiple possible structures
            content_data = []
            if course_content:
                # Try different possible structures
                if 'data' in course_content:
                    data = course_content['data']
                    if 'lessons' in data:
                        content_data = data['lessons']
                    elif isinstance(data, list):
                        content_data = data
                elif isinstance(course_content, list):
                    content_data = course_content
            
            # Handle quizzes
            quizzes_data = []
            if quizzes:
                if 'data' in quizzes:
                    data = quizzes['data']
                    if 'quizzes' in data:
                        quizzes_data = data['quizzes']
                    elif isinstance(data, list):
                        quizzes_data = data
                elif isinstance(quizzes, list):
                    quizzes_data = quizzes
            
            # Handle video transcripts
            transcripts_data = []
            if video_transcripts:
                if 'data' in video_transcripts:
                    data = video_transcripts['data']
                    if 'transcripts' in data:
                        transcripts_data = data['transcripts']
                    elif isinstance(data, list):
                        transcripts_data = data
                elif isinstance(video_transcripts, list):
                    transcripts_data = video_transcripts
            
            # Create a mapping of lesson_id/module_id to transcript for quick lookup
            transcript_map = {}
            for transcript in transcripts_data:
                lesson_id = transcript.get('lesson_id', '')
                lesson_name = transcript.get('lesson_name', '')
                module_id = transcript.get('module_id')
                key = (module_id, lesson_id, lesson_name)
                transcript_map[key] = transcript
            
            # Show debug info if content is missing
            if not content_data and course_content:
                st.warning(f"⚠️ Course content structure: {list(course_content.keys()) if isinstance(course_content, dict) else 'Not a dict'}")
            
            # Get course info from final course or module structure
            course_info = {}
            if final_course:
                course_info = final_course.get('data', {}).get('course_info', {})
            else:
                # Fallback: get from saved state or use defaults
                course_info = {
                    "title": module_structure.get('data', {}).get('course_subject', 'Course'),
                    "level": module_structure.get('data', {}).get('learner_level', 'intermediate'),
                    "duration": module_structure.get('data', {}).get('course_duration', '4 weeks')
                }
            
            # Calculate statistics
            total_modules = len(modules_data)
            total_lessons = len(content_data) if content_data else sum(len(m.get('lessons', [])) for m in modules_data)
            total_quizzes = len(quizzes_data)
            graded_quizzes = len([q for q in quizzes_data if q.get('quiz_type') == 'graded'])
            practice_quizzes = len([q for q in quizzes_data if q.get('quiz_type') == 'practice'])
            
            # Course title and description (Coursera style) - shown first
            course_title = course_info.get('title', 'Course')
            course_description = course_info.get('description', f'Comprehensive course on {course_title}')
            
            st.markdown(f"""
            <div style="margin-bottom: 2rem;">
                <h1 style="font-size: 2.5rem; font-weight: 700; color: #202124; margin-bottom: 1rem;">
                    {course_title}
                </h1>
                <p style="font-size: 1.1rem; color: #5f6368; line-height: 1.6; max-width: 800px;">
                    {course_description}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Coursera-style statistics card (white card with rounded corners)
            st.markdown("""
            <div style="background: white; border-radius: 8px; padding: 1.5rem 2rem; margin: 2rem 0; box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);">
            """, unsafe_allow_html=True)
            
            # Create 5 columns for statistics (like Coursera)
            stat_cols = st.columns(5)
            
            with stat_cols[0]:
                st.markdown(f"""
                <div style="text-align: center; padding: 1rem;">
                    <div style="font-size: 2.5rem; font-weight: 700; color: #1a73e8; margin-bottom: 0.5rem;">
                        {total_modules}
                    </div>
                    <div style="font-size: 0.9rem; color: #5f6368; font-weight: 500; margin-bottom: 0.25rem;">
                        modules
                    </div>
                    <div style="font-size: 0.75rem; color: #80868b; line-height: 1.4;">
                        Gain insight into a topic and learn the fundamentals.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with stat_cols[1]:
                # Calculate average lesson duration
                avg_lesson_duration = "30 min"  # Default
                if modules_data:
                    durations = [l.get('estimated_duration', '30 min') for m in modules_data for l in m.get('lessons', [])]
                    if durations:
                        avg_lesson_duration = durations[0]  # Use first as example
                
                st.markdown(f"""
                <div style="text-align: center; padding: 1rem;">
                    <div style="font-size: 2.5rem; font-weight: 700; color: #1a73e8; margin-bottom: 0.5rem;">
                        {total_lessons}
                    </div>
                    <div style="font-size: 0.9rem; color: #5f6368; font-weight: 500; margin-bottom: 0.25rem;">
                        lessons
                    </div>
                    <div style="font-size: 0.75rem; color: #80868b; line-height: 1.4;">
                        Comprehensive content with examples and exercises.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with stat_cols[2]:
                learner_level = course_info.get('level', 'intermediate').capitalize()
                level_description = {
                    'Basic': 'No prior experience required',
                    'Intermediate': 'Some foundational knowledge recommended',
                    'Advanced': 'Prior experience in the field recommended'
                }
                desc = level_description.get(learner_level, 'Appropriate for all levels')
                
                st.markdown(f"""
                <div style="text-align: center; padding: 1rem;">
                    <div style="font-size: 1.5rem; font-weight: 600; color: #1a73e8; margin-bottom: 0.5rem;">
                        {learner_level} level
                    </div>
                    <div style="font-size: 0.75rem; color: #80868b; line-height: 1.4;">
                        {desc}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with stat_cols[3]:
                duration = course_info.get('duration', '4 weeks')
                # Estimate hours per week (rough calculation)
                hours_per_week = "10"
                if "week" in duration.lower():
                    weeks = int(''.join(filter(str.isdigit, duration)) or 4)
                    estimated_hours = total_lessons * 1.5  # Assume 1.5 hours per lesson
                    hours_per_week = str(int(estimated_hours / weeks)) if weeks > 0 else "10"
                
                st.markdown(f"""
                <div style="text-align: center; padding: 1rem;">
                    <div style="font-size: 1.2rem; font-weight: 600; color: #1a73e8; margin-bottom: 0.5rem;">
                        Flexible schedule
                    </div>
                    <div style="font-size: 0.75rem; color: #80868b; line-height: 1.4;">
                        {duration} at {hours_per_week} hours per week<br>
                        Learn at your own pace
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with stat_cols[4]:
                st.markdown(f"""
                <div style="text-align: center; padding: 1rem;">
                    <div style="font-size: 2.5rem; font-weight: 700; color: #1a73e8; margin-bottom: 0.5rem;">
                        {total_quizzes}
                    </div>
                    <div style="font-size: 0.9rem; color: #5f6368; font-weight: 500; margin-bottom: 0.25rem;">
                        assessments
                    </div>
                    <div style="font-size: 0.75rem; color: #80868b; line-height: 1.4;">
                        {graded_quizzes} graded, {practice_quizzes} practice quizzes
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Add video transcripts statistics if available
            if transcripts_data:
                total_transcripts = len(transcripts_data)
                total_video_duration = sum(t.get('video_duration_minutes', 0) for t in transcripts_data)
                total_video_hours = round(total_video_duration / 60, 1)
                
                st.markdown("---")
                st.markdown("### 🎥 Video Content")
                transcript_cols = st.columns(3)
                
                with transcript_cols[0]:
                    st.metric("Video Transcripts", total_transcripts)
                
                with transcript_cols[1]:
                    st.metric("Total Video Duration", f"{total_video_hours} hours")
                
                with transcript_cols[2]:
                    avg_duration = round(total_video_duration / total_transcripts, 1) if total_transcripts > 0 else 0
                    st.metric("Average Duration", f"{avg_duration} min/lesson")
            
            # Close the statistics card div
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Show all course content in a dedicated section if available
            if content_data:
                st.markdown("## 📚 Full Course Content")
                st.success(f"✅ **{len(content_data)} lessons** available. Browse by module below or view all content here.")
                st.markdown("---")
            
            # Module tabs
            if modules_data:
                tab_names = [f"Module {i+1}" for i in range(len(modules_data))]
                tabs = st.tabs(tab_names)
                
                for tab, module in zip(tabs, modules_data):
                    with tab:
                        display_module_card(module, modules_data.index(module) + 1)
                        
                        # Show lesson content if available
                        module_id = module.get('module_id')
                        # Handle both int and string module_id
                        module_lessons = [
                            l for l in content_data 
                            if (l.get('module_id') == module_id or 
                                str(l.get('module_id')) == str(module_id) or
                                int(l.get('module_id', 0)) == int(module_id))
                        ]
                        
                        if module_lessons:
                            st.markdown("### 📚 Full Lesson Content")
                            st.info(f"📖 {len(module_lessons)} lesson(s) available for this module. Click to expand and view full content.")
                            for lesson in module_lessons:
                                lesson_name = lesson.get('lesson_name', lesson.get('title', 'Untitled Lesson'))
                                lesson_id = lesson.get('lesson_id', '')
                                # Find transcript for this lesson
                                transcript = None
                                for key, t in transcript_map.items():
                                    mod_id, lid, lname = key
                                    if (mod_id == module_id and 
                                        (lid == lesson_id or lname == lesson_name)):
                                        transcript = t
                                        break
                                
                                with st.expander(f"📖 {lesson_name}", expanded=False):
                                    display_lesson_content(lesson, transcript)
                        elif content_data:
                            st.warning(f"⚠️ No lesson content found for Module {module_id}. Available lessons have module_ids: {list(set([l.get('module_id') for l in content_data[:10]]))}")
                        else:
                            st.info("⏳ Lesson content is being generated. Please wait...")
                        
                        # Show quizzes for this module
                        module_quizzes = [q for q in quizzes_data if q.get('module_id') == module_id]
                        if module_quizzes:
                            st.markdown("### 📝 Quizzes")
                            for quiz in module_quizzes:
                                display_quiz(quiz)
    
if __name__ == "__main__":
    main()

