"""Progress tracker that streams updates to a file in real-time."""
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional


class ProgressTracker:
    """Tracks workflow progress and streams updates to a file."""
    
    def __init__(self, thread_id: str = "default", output_dir: str = "course_outputs"):
        self.thread_id = thread_id
        self.output_dir = output_dir
        self.progress_file = os.path.join(output_dir, f"{thread_id}_progress.jsonl")
        self.ensure_output_dir()
        self.start_time = datetime.now()
    
    def ensure_output_dir(self):
        """Create output directory if it doesn't exist."""
        os.makedirs(self.output_dir, exist_ok=True)
    
    def log_step(self, step_name: str, status: str, details: Optional[Dict[str, Any]] = None):
        """
        Log a step with status and details. Streams to file immediately.
        
        Args:
            step_name: Name of the step/node
            status: Status (e.g., "started", "completed", "failed", "in_progress")
            details: Optional additional details
        """
        timestamp = datetime.now().isoformat()
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        log_entry = {
            "timestamp": timestamp,
            "elapsed_seconds": round(elapsed, 2),
            "step": step_name,
            "status": status,
            "details": details or {}
        }
        
        # Write as JSONL (one JSON object per line) for streaming
        with open(self.progress_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            f.flush()  # Force write to disk immediately
        
        # Also print to console
        status_emoji = {
            "started": "🚀",
            "completed": "✅",
            "failed": "❌",
            "in_progress": "⏳",
            "waiting": "⏸️"
        }.get(status, "📝")
        
        print(f"{status_emoji} [{step_name}] {status} ({elapsed:.1f}s)")
        if details:
            for key, value in details.items():
                if isinstance(value, (list, dict)):
                    print(f"   {key}: {len(value) if isinstance(value, list) else 'dict'}")
                else:
                    print(f"   {key}: {value}")
    
    def log_node_start(self, node_name: str):
        """Log when a node starts executing."""
        self.log_step(node_name, "started")
    
    def log_node_complete(self, node_name: str, details: Optional[Dict[str, Any]] = None):
        """Log when a node completes."""
        self.log_step(node_name, "completed", details)
    
    def log_node_progress(self, node_name: str, progress_info: Dict[str, Any]):
        """Log progress within a node (e.g., batch processing)."""
        self.log_step(node_name, "in_progress", progress_info)
    
    def log_node_error(self, node_name: str, error: str):
        """Log when a node fails."""
        self.log_step(node_name, "failed", {"error": error})
    
    def log_interrupt(self, interrupt_type: str, message: str):
        """Log when workflow is interrupted."""
        self.log_step(f"interrupt_{interrupt_type}", "waiting", {"message": message})
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get summary of all progress so far."""
        if not os.path.exists(self.progress_file):
            return {"steps": [], "total_steps": 0, "completed_steps": 0}
        
        steps = []
        with open(self.progress_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    steps.append(json.loads(line))
        
        completed = [s for s in steps if s.get("status") == "completed"]
        
        return {
            "steps": steps,
            "total_steps": len(steps),
            "completed_steps": len(completed),
            "last_step": steps[-1] if steps else None
        }

