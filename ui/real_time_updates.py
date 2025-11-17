"""Real-time step-by-step updates for UI."""
import json
import os
import time
from typing import Dict, Any, Optional, List
import streamlit as st
from utils.results_saver import ResultsSaver


def get_current_step_status(thread_id: str) -> Dict[str, Any]:
    """Get current step status from progress file."""
    progress_file = os.path.join("course_outputs", f"{thread_id}_progress.jsonl")
    
    if not os.path.exists(progress_file):
        return {"status": "waiting", "step": None, "message": "Waiting for workflow to start..."}
    
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
    
    if not steps:
        return {"status": "waiting", "step": None, "message": "Waiting for workflow to start..."}
    
    # Get latest step
    latest = steps[-1]
    step_name = latest.get("step", "unknown")
    status = latest.get("status", "unknown")
    details = latest.get("details", {})
    
    # Find active (non-completed) steps
    active_steps = [s for s in steps if s.get("status") not in ["completed", "failed"]]
    if active_steps:
        latest = active_steps[-1]
        step_name = latest.get("step", "unknown")
        status = latest.get("status", "unknown")
        details = latest.get("details", {})
    
    return {
        "status": status,
        "step": step_name,
        "details": details,
        "message": _get_step_message(step_name, status, details)
    }


def _get_step_message(step_name: str, status: str, details: Dict[str, Any]) -> str:
    """Generate user-friendly message for current step."""
    if step_name == "researcher_agent":
        return "🔍 Researching course topics and gathering information..."
    elif step_name == "module_structure_agent":
        if status == "in_progress" and "message" in details:
            return details["message"]
        return "📚 Creating course module structure..."
    elif step_name == "validate_module_structure":
        return "✅ Validating module structure..."
    elif step_name == "human_review_structure":
        return "⏸️ Waiting for structure review..."
    elif step_name == "xdp_agent":
        return "📋 Generating XDP specification..."
    elif step_name == "course_content_agent":
        if status == "in_progress":
            if "message" in details:
                return f"📝 {details['message']}"
            if "batch" in details and "total_batches" in details:
                batch = details.get("batch", 0)
                total = details.get("total_batches", 0)
                completed = details.get("completed", 0)
                return f"📝 Generating course content... Batch {batch}/{total} ({completed}/{total} completed)"
            if "total_lessons" in details:
                return f"📝 Generating content for {details['total_lessons']} lessons..."
        return "📝 Generating detailed course content..."
    elif step_name == "validate_content":
        return "✅ Validating course content..."
    elif step_name == "human_review_content":
        return "⏸️ Waiting for content review..."
    elif step_name == "quiz_curator_agent":
        if status == "in_progress":
            if "message" in details:
                return f"📝 {details['message']}"
            if "completed" in details and "total" in details:
                completed = details.get("completed", 0)
                total = details.get("total", 0)
                return f"📝 Creating quizzes... {completed}/{total} completed"
        return "📝 Creating quizzes for all modules..."
    elif step_name == "validate_quizzes":
        return "✅ Validating quizzes..."
    elif step_name == "human_review_quizzes":
        return "⏸️ Waiting for quiz review..."
    elif step_name == "finalize_course":
        return "🎉 Finalizing course..."
    elif step_name == "workflow":
        if status == "completed":
            return "✅ Course generation complete!"
        return "🔄 Workflow in progress..."
    else:
        return f"🔄 {step_name.replace('_', ' ').title()}..."


def check_content_available(thread_id: str) -> Dict[str, Any]:
    """Check what content is available to display."""
    saver = ResultsSaver()
    available = {
        "module_structure": False,
        "xdp_content": False,
        "course_content": False,
        "quizzes": False,
        "final_course": False
    }
    
    # Check for module structure
    structure = saver.get_latest_result("module_structure", thread_id)
    if structure and structure.get("data", {}).get("modules"):
        available["module_structure"] = True
    
    # Check for XDP
    xdp = saver.get_latest_result("xdp_content", thread_id)
    if xdp and xdp.get("data"):
        available["xdp_content"] = True
    
    # Check for course content
    content = saver.get_latest_result("course_content", thread_id)
    if content and content.get("data", {}).get("lessons"):
        available["course_content"] = True
    
    # Check for quizzes
    quizzes = saver.get_latest_result("quizzes", thread_id)
    if quizzes and quizzes.get("data", {}).get("quizzes"):
        available["quizzes"] = True
    
    # Check for final course
    final = saver.get_latest_result("final_course", thread_id)
    if final and final.get("data"):
        available["final_course"] = True
    
    return available


def display_step_progress(thread_id: str, container):
    """Display current step progress message in a container."""
    status_info = get_current_step_status(thread_id)
    content_available = check_content_available(thread_id)
    
    # Only show message if content is not yet available for that step
    step = status_info.get("step")
    message = status_info.get("message", "")
    
    # Map steps to content types
    step_to_content = {
        "module_structure_agent": "module_structure",
        "xdp_agent": "xdp_content",
        "course_content_agent": "course_content",
        "quiz_curator_agent": "quizzes",
        "finalize_course": "final_course"
    }
    
    content_type = step_to_content.get(step)
    
    # If content is available, don't show the message
    if content_type and content_available.get(content_type):
        return False  # Content ready, message should disappear
    
    # Show progress message
    if message and status_info.get("status") != "completed":
        with container:
            st.info(f"💭 {message}")
            # Show progress bar if available
            details = status_info.get("details", {})
            if "completed" in details and "total" in details:
                completed = details.get("completed", 0)
                total = details.get("total", 1)
                progress_pct = (completed / total * 100) if total > 0 else 0
                st.progress(progress_pct / 100)
                st.caption(f"Progress: {completed}/{total} ({progress_pct:.1f}%)")
    
    return True  # Message is showing


def display_content_as_ready(thread_id: str, st_container):
    """Display content as it becomes available."""
    saver = ResultsSaver()
    
    # Module Structure
    structure = saver.get_latest_result("module_structure", thread_id)
    if structure and structure.get("data", {}).get("modules"):
        modules = structure["data"]["modules"]
        with st_container:
            st.success("✅ **Module Structure Created**")
            st.markdown(f"**Total Modules:** {len(modules)}")
            for i, module in enumerate(modules, 1):
                st.markdown(f"**Module {i}:** {module.get('module_name', 'N/A')}")
                lessons = module.get("lessons", [])
                if lessons:
                    st.caption(f"  {len(lessons)} lessons planned")
    
    # XDP Content
    xdp = saver.get_latest_result("xdp_content", thread_id)
    if xdp and xdp.get("data"):
        with st_container:
            st.success("✅ **XDP Specification Generated**")
    
    # Course Content
    content = saver.get_latest_result("course_content", thread_id)
    if content and content.get("data", {}).get("lessons"):
        lessons = content["data"]["lessons"]
        with st_container:
            st.success(f"✅ **Course Content Generated** ({len(lessons)} lessons)")
    
    # Quizzes
    quizzes = saver.get_latest_result("quizzes", thread_id)
    if quizzes and quizzes.get("data", {}).get("quizzes"):
        quiz_list = quizzes["data"]["quizzes"]
        graded = len([q for q in quiz_list if q.get("quiz_type") == "graded"])
        practice = len([q for q in quiz_list if q.get("quiz_type") == "practice"])
        with st_container:
            st.success(f"✅ **Quizzes Created** ({graded} graded, {practice} practice)")
    
    # Final Course
    final = saver.get_latest_result("final_course", thread_id)
    if final and final.get("data"):
        with st_container:
            st.success("🎉 **Course Finalized!**")

