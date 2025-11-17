"""Error Handler Node - Catches and handles errors gracefully."""
from typing import Dict, Any
from state.base_state import CourseState
import time


def handle_errors(state: CourseState) -> CourseState:
    """
    Error handler that catches errors from any node and attempts recovery.
    """
    if not state.get("errors"):
        return state
    
    # Log errors with context
    error_context = {
        "current_step": state.get("current_step", "unknown"),
        "errors": state["errors"],
        "timestamp": time.time()
    }
    
    # Attempt recovery based on error type
    recoverable_errors = [
        "API", "timeout", "rate limit", "network", "temporary"
    ]
    
    critical_errors = [
        "missing", "invalid", "corrupt", "fatal"
    ]
    
    has_recoverable = any(
        any(keyword in error.lower() for keyword in recoverable_errors)
        for error in state["errors"]
    )
    
    has_critical = any(
        any(keyword in error.lower() for keyword in critical_errors)
        for error in state["errors"]
    )
    
    if has_recoverable:
        state["current_step"] = "error_recoverable"
        # In production, would implement retry logic with exponential backoff
    elif has_critical:
        state["current_step"] = "error_critical"
        # Would trigger HITL for critical errors
    else:
        state["current_step"] = "error_handled"
    
    return state

