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

