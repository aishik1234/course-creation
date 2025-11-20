"""Real-time progress display for UI."""
import json
import os
import time
from typing import Dict, Any, Optional, List
import streamlit as st


def read_progress_file(thread_id: str, output_dir: str = "course_outputs") -> List[Dict[str, Any]]:
    """Read progress entries from JSONL file."""
    progress_file = os.path.join(output_dir, f"{thread_id}_progress.jsonl")
    
    if not os.path.exists(progress_file):
        return []
    
    steps = []
    try:
        with open(progress_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        steps.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass
    
    return steps


def get_latest_progress(thread_id: str) -> Optional[Dict[str, Any]]:
    """Get the latest progress entry."""
    steps = read_progress_file(thread_id)
    return steps[-1] if steps else None


def display_progress_ui(thread_id: str):
    """Display real-time progress in Streamlit UI - shows only current step."""
    steps = read_progress_file(thread_id)
    
    if not steps:
        st.info("⏳ Waiting for workflow to start...")
        return
    
    # Get latest step
    latest = steps[-1]
    current_step = latest.get("step", "unknown")
    status = latest.get("status", "unknown")
    details = latest.get("details", {})
    elapsed = latest.get("elapsed_seconds", 0)
    
    # Only show steps that are in progress, started, or waiting
    # Hide completed steps (they disappear once done)
    if status in ["completed", "failed"]:
        # Check if there's a next step starting
        # Look for the most recent step that's not completed
        active_steps = [s for s in steps if s.get("status") not in ["completed", "failed"]]
        if active_steps:
            latest = active_steps[-1]
            current_step = latest.get("step", "unknown")
            status = latest.get("status", "unknown")
            details = latest.get("details", {})
            elapsed = latest.get("elapsed_seconds", 0)
        else:
            # All steps completed, show final status
            st.success("✅ All steps completed!")
            return
    
    # Status emoji mapping
    status_emoji = {
        "started": "🚀",
        "completed": "✅",
        "failed": "❌",
        "in_progress": "⏳",
        "waiting": "⏸️"
    }.get(status, "📝")
    
    # Display current status in a prominent box
    status_color_map = {
        "started": "blue",
        "in_progress": "orange", 
        "waiting": "yellow",
        "completed": "green",
        "failed": "red"
    }
    status_color = status_color_map.get(status, "gray")
    
    # Create a prominent status box
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 1.5rem;
                border-radius: 10px;
                color: white;
                margin-bottom: 1rem;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h2 style="color: white; margin: 0;">{status_emoji} {current_step.replace('_', ' ').title()}</h2>
        <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0;">
            Status: <strong>{status.upper()}</strong> | Elapsed: {elapsed:.1f}s
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Display details in an expandable section
    if details:
        with st.expander("📋 View Details", expanded=True):
            for key, value in details.items():
                if key != "error":  # Errors shown separately
                    if isinstance(value, (list, dict)):
                        st.text(f"  • {key}: {len(value) if isinstance(value, list) else 'dict'}")
                    else:
                        st.text(f"  • {key}: {value}")
            
            # Show progress bar for in-progress operations
            if "completed" in details and "total" in details:
                completed = details.get("completed", 0)
                total = details.get("total", 1)
                progress_pct = (completed / total * 100) if total > 0 else 0
                st.progress(progress_pct / 100)
                st.caption(f"Progress: {completed}/{total} completed ({progress_pct:.1f}%)")
            
            # Show message if available
            if "message" in details:
                st.info(f"💬 {details['message']}")
    
    # Show errors if any
    if status == "failed" and details.get("error"):
        st.error(f"❌ Error: {details['error']}")
    
    # Show recent completed steps in a minimal collapsed view
    completed_steps = [s for s in steps if s.get("status") == "completed"]
    if completed_steps:
        with st.expander("✅ Completed Steps", expanded=False):
            # Group by node and show only latest status
            node_completed = {}
            for step in completed_steps:
                node = step.get("step", "unknown")
                if node not in node_completed:
                    node_completed[node] = step
            
            for node, step in list(node_completed.items())[-5:]:  # Show last 5 completed
                elapsed_time = step.get("elapsed_seconds", 0)
                st.caption(f"✅ {node.replace('_', ' ').title()} ({elapsed_time:.1f}s)")


# Workflow step order (all possible steps)
WORKFLOW_STEPS = [
    "collect_user_input",
    "researcher_agent",
    "module_structure_agent",
    "validate_module_structure",
    "human_review_structure",  # Optional - only if validation fails
    "xdp_agent",
    "course_content_agent",
    "validate_content",
    "human_review_content",  # Optional - only if validation fails
    "quiz_curator_agent",
    "validate_quizzes",
    "human_review_quizzes",  # Optional - only if validation fails
    "video_transcript_agent",
    "finalize_course"
]

# Step display names
STEP_DISPLAY_NAMES = {
    "collect_user_input": "Collect User Input",
    "researcher_agent": "Research Phase",
    "module_structure_agent": "Module Structure",
    "validate_module_structure": "Validate Structure",
    "human_review_structure": "Review Structure",
    "xdp_agent": "XDP Specification",
    "course_content_agent": "Course Content",
    "validate_content": "Validate Content",
    "human_review_content": "Review Content",
    "quiz_curator_agent": "Quiz Creation",
    "validate_quizzes": "Validate Quizzes",
    "human_review_quizzes": "Review Quizzes",
    "video_transcript_agent": "Video Transcripts",
    "finalize_course": "Finalize Course"
}

# Time estimates for steps (shown as notes)
STEP_TIME_ESTIMATES = {
    "xdp_agent": "Might take a couple of minutes",
    "course_content_agent": "Might take upto 5 mins to complete",
    "quiz_curator_agent": "Might take upto 3 mins to complete",
    "video_transcript_agent": "Might take 5 to 7 mins to complete"
}


def get_spinner_html(color: str, size: str = "20px") -> str:
    """
    Generate HTML for a CSS animated spinner.
    
    Args:
        color: Spinner color (hex code or color name)
        size: Spinner size (default: "20px")
    
    Returns:
        HTML string with spinner and CSS animation
    """
    return f'<div class="spinner" style="border: 3px solid #f3f3f3; border-top: 3px solid {color}; border-radius: 50%; width: {size}; height: {size}; animation: spin 1s linear infinite; display: inline-block; vertical-align: middle; margin-right: 0.5rem;"></div>'


# CSS for spinner animation (injected once)
SPINNER_CSS = """
<style>
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
</style>
"""


def calculate_workflow_progress(thread_id: str) -> Dict[str, Any]:
    """
    Calculate overall workflow progress.
    Handles:
    - Optional steps (review nodes) - only counts steps that have been started
    - Rejected feedback (regeneration) - doesn't decrease progress
    - Multiple interrupts - shows most recent/active interrupt
    
    Returns:
        {
            "percentage": float,  # 0.0 to 1.0
            "completed_steps": int,
            "total_started_steps": int,  # Only steps that have been started
            "current_step": str,
            "current_status": str,  # "in_progress", "waiting", "completed", "failed"
            "is_interrupted": bool,
            "interrupt_type": Optional[str],  # "structure", "content", "quizzes", None
            "steps": List[Dict]  # List of all steps with their status
        }
    """
    from utils.results_saver import ResultsSaver
    
    steps = read_progress_file(thread_id)
    
    if not steps:
        return {
            "percentage": 0.0,
            "completed_steps": 0,
            "total_started_steps": 0,
            "current_step": None,
            "current_status": "waiting",
            "is_interrupted": False,
            "interrupt_type": None,
            "steps": []
        }
    
    # Check for active interrupts (Case 3: Multiple Interrupts)
    saver = ResultsSaver()
    interrupt_structure = saver.get_latest_result("interrupt_structure", thread_id)
    interrupt_content = saver.get_latest_result("interrupt_content", thread_id)
    interrupt_quizzes = saver.get_latest_result("interrupt_quizzes", thread_id)
    
    # Also check progress entries for interrupt status
    interrupt_from_progress = None
    for step_entry in steps:
        step_name = step_entry.get("step", "")
        status = step_entry.get("status", "")
        
        # Check for interrupt or waiting status on review steps
        if "human_review" in step_name and status == "waiting":
            if "quizzes" in step_name:
                interrupt_from_progress = "quizzes"
            elif "content" in step_name:
                interrupt_from_progress = "content"
            elif "structure" in step_name:
                interrupt_from_progress = "structure"
        elif "interrupt_" in step_name and status == "waiting":
            if "quizzes" in step_name:
                interrupt_from_progress = "quizzes"
            elif "content" in step_name:
                interrupt_from_progress = "content"
            elif "structure" in step_name:
                interrupt_from_progress = "structure"
    
    # Determine most recent/active interrupt (priority: quizzes > content > structure)
    # Check both interrupt files and progress entries
    active_interrupt_type = None
    if interrupt_quizzes or interrupt_from_progress == "quizzes":
        active_interrupt_type = "quizzes"
    elif interrupt_content or interrupt_from_progress == "content":
        active_interrupt_type = "content"
    elif interrupt_structure or interrupt_from_progress == "structure":
        active_interrupt_type = "structure"
    
    is_interrupted = active_interrupt_type is not None
    
    # Build step status map
    step_status_map = {}
    step_details_map = {}
    
    for step_entry in steps:
        step_name = step_entry.get("step", "")
        status = step_entry.get("status", "")
        details = step_entry.get("details", {})
        
        # Normalize step names (handle interrupt_ prefix, etc.)
        normalized_name = step_name.replace("interrupt_", "").replace("workflow", "")
        
        # Map to workflow step if it matches
        for workflow_step in WORKFLOW_STEPS:
            if workflow_step in normalized_name or normalized_name in workflow_step:
                # Only update if this is a more recent status
                if workflow_step not in step_status_map or status in ["completed", "failed", "in_progress"]:
                    step_status_map[workflow_step] = status
                    step_details_map[workflow_step] = details
                break
        
        # Also track the exact step name for current step detection
        if step_name not in step_status_map:
            step_status_map[step_name] = status
            step_details_map[step_name] = details
    
    # Case 1: Optional Steps - Only count steps that have been started
    started_steps = []
    completed_steps = []
    
    for step in WORKFLOW_STEPS:
        if step in step_status_map:
            started_steps.append(step)
            if step_status_map[step] == "completed":
                completed_steps.append(step)
    
    # Case 2: Rejected Feedback - Don't decrease progress
    # Find the highest completed step index to maintain progress even if workflow goes back
    max_completed_index = -1
    for i, step in enumerate(WORKFLOW_STEPS):
        if step in completed_steps:
            max_completed_index = i
    
    # Calculate progress based on started steps only
    total_started = len(started_steps) if started_steps else 1
    completed_count = len(completed_steps)
    
    # If interrupted, don't count the interrupt step as completed yet
    if is_interrupted:
        interrupt_step = f"human_review_{active_interrupt_type}"
        if interrupt_step in completed_steps:
            completed_count -= 1
    
    # Calculate percentage (use max_completed_index to prevent going backwards)
    if total_started > 0:
        # Use max_completed_index + 1 to represent progress (prevents regression)
        progress_index = max(max_completed_index + 1, completed_count)
        percentage = min(progress_index / len(WORKFLOW_STEPS), 1.0)
    else:
        percentage = 0.0
    
    # Find current active step
    current_step = None
    current_status = "waiting"
    
    # If interrupted, show the interrupt step
    if is_interrupted:
        current_step = f"human_review_{active_interrupt_type}"
        current_status = "waiting"
    else:
        # Find the latest non-completed step
        for step in WORKFLOW_STEPS:
            if step in step_status_map:
                status = step_status_map[step]
                if status not in ["completed", "failed"]:
                    current_step = step
                    current_status = status
                    break
        
        # If all started steps are completed, find next step
        if current_step is None and started_steps:
            last_started = started_steps[-1]
            last_index = WORKFLOW_STEPS.index(last_started)
            if last_index < len(WORKFLOW_STEPS) - 1:
                current_step = WORKFLOW_STEPS[last_index + 1]
                current_status = "pending"
    
    # Build steps list with status
    steps_list = []
    for step in WORKFLOW_STEPS:
        status = step_status_map.get(step, "pending")
        steps_list.append({
            "name": step,
            "display_name": STEP_DISPLAY_NAMES.get(step, step.replace("_", " ").title()),
            "status": status,
            "is_started": step in started_steps,
            "is_completed": step in completed_steps
        })
    
    return {
        "percentage": percentage,
        "completed_steps": completed_count,
        "total_started_steps": total_started,
        "total_possible_steps": len(WORKFLOW_STEPS),
        "current_step": current_step,
        "current_status": current_status,
        "is_interrupted": is_interrupted,
        "interrupt_type": active_interrupt_type,
        "steps": steps_list
    }


def display_workflow_progress_bar(thread_id: str):
    """Display the main workflow progress bar component in UI."""
    progress_data = calculate_workflow_progress(thread_id)
    
    if progress_data["current_step"] is None and progress_data["percentage"] == 0.0:
        st.info("⏳ Waiting for workflow to start...")
        return
    
    percentage = progress_data["percentage"]
    completed = progress_data["completed_steps"]
    total_started = progress_data["total_started_steps"]
    total_possible = progress_data["total_possible_steps"]
    current_step = progress_data["current_step"]
    current_status = progress_data["current_status"]
    is_interrupted = progress_data["is_interrupted"]
    interrupt_type = progress_data["interrupt_type"]
    steps_list = progress_data["steps"]
    
    # Inject spinner CSS once
    st.markdown(SPINNER_CSS, unsafe_allow_html=True)
    
    # Create progress bar container
    st.markdown("---")
    st.markdown("### 📊 Workflow Progress")
    
    # Main progress bar
    col1, col2 = st.columns([3, 1])
    with col1:
        # Show progress bar
        progress_value = percentage
        st.progress(progress_value)
        
        # Status text with spinners
        if is_interrupted:
            spinner_html = get_spinner_html("#ffc107", "18px")  # Yellow spinner
            st.markdown(f"{spinner_html} **Paused for Review** - Waiting for {interrupt_type} feedback", unsafe_allow_html=True)
            st.warning("⚠️ **Workflow is waiting for your feedback!**")
        elif current_status == "waiting":
            current_display = STEP_DISPLAY_NAMES.get(current_step, current_step)
            time_estimate = STEP_TIME_ESTIMATES.get(current_step, "")
            time_note = f" ⏱️ *{time_estimate}*" if time_estimate else ""
            spinner_html = get_spinner_html("#ffc107", "18px")  # Yellow spinner
            st.markdown(f"{spinner_html} **Waiting** - {current_display}{time_note}", unsafe_allow_html=True)
        elif current_status == "in_progress":
            current_display = STEP_DISPLAY_NAMES.get(current_step, current_step)
            time_estimate = STEP_TIME_ESTIMATES.get(current_step, "")
            time_note = f" ⏱️ *{time_estimate}*" if time_estimate else ""
            spinner_html = get_spinner_html("#ff9800", "18px")  # Orange spinner
            st.markdown(f"{spinner_html} **In Progress** - {current_display}{time_note}", unsafe_allow_html=True)
        elif current_status == "completed":
            st.success("✅ **Workflow Completed!**")
        else:
            current_display = STEP_DISPLAY_NAMES.get(current_step, current_step) if current_step else "Starting..."
            time_estimate = STEP_TIME_ESTIMATES.get(current_step, "") if current_step else ""
            time_note = f" ⏱️ *{time_estimate}*" if time_estimate else ""
            spinner_html = get_spinner_html("#2196f3", "18px")  # Blue spinner
            st.markdown(f"{spinner_html} **{current_display}**{time_note}", unsafe_allow_html=True)
    
    with col2:
        st.metric("Progress", f"{percentage * 100:.1f}%")
        st.caption(f"{completed}/{total_started} steps")
    
    # Detailed step list (collapsible)
    with st.expander("📋 View All Steps", expanded=False):
        for step_info in steps_list:
            step_name = step_info["name"]
            display_name = step_info["display_name"]
            status = step_info["status"]
            is_started = step_info["is_started"]
            is_completed = step_info["is_completed"]
            
            # Determine icon/spinner and color
            use_spinner = False
            spinner_color = None
            icon_html = ""
            
            if is_completed:
                icon_html = '<span style="color: green; font-size: 1.2em;">✅</span>'
            elif status == "failed":
                icon_html = '<span style="color: red; font-size: 1.2em;">❌</span>'
            elif status == "in_progress" or (is_interrupted and step_name == current_step):
                use_spinner = True
                spinner_color = "#ff9800" if not is_interrupted else "#ffc107"  # Orange or Yellow
            elif status == "waiting":
                use_spinner = True
                spinner_color = "#ffc107"  # Yellow
            elif is_started:
                use_spinner = True
                spinner_color = "#2196f3"  # Blue
            else:
                use_spinner = True
                spinner_color = "#9e9e9e"  # Gray
            
            # Generate spinner HTML if needed
            if use_spinner:
                icon_html = get_spinner_html(spinner_color, "20px")
            
            # Highlight current step
            is_current = step_name == current_step
            style = "font-weight: bold; background-color: #f0f0f0; padding: 0.3rem;" if is_current else ""
            
            # Get time estimate if available
            time_estimate = STEP_TIME_ESTIMATES.get(step_name, "")
            time_note_html = f'<span style="color: #666; font-size: 0.85em; font-style: italic; margin-left: 0.5rem;">⏱️ {time_estimate}</span>' if time_estimate else ""
            
            # Status text color
            status_color = spinner_color if use_spinner else ("green" if is_completed else "red" if status == "failed" else "gray")
            
            # Build status text HTML
            status_html = f'<span style="color: {status_color}; margin-left: 1rem;">({status})</span>' if is_started and status != "completed" else ""
            
            # Build complete HTML string
            html_content = f'<div style="{style}">{icon_html}<span style="margin-left: 0.5rem;">{display_name}</span>{status_html}{time_note_html}</div>'
            
            st.markdown(html_content, unsafe_allow_html=True)

