"""Utility to save intermediate and final results from workflow steps."""
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional


class ResultsSaver:
    """Saves results from each workflow step to JSON files."""
    
    def __init__(self, output_dir: str = "course_outputs"):
        self.output_dir = output_dir
        self.ensure_output_dir()
    
    def ensure_output_dir(self):
        """Create output directory if it doesn't exist."""
        os.makedirs(self.output_dir, exist_ok=True)
    
    def save_step_result(self, step_name: str, data: Dict[str, Any], thread_id: str = "default"):
        """
        Save result from a workflow step.
        Uses fixed filename that gets overwritten on each run.
        
        Args:
            step_name: Name of the step (e.g., "research_findings", "module_structure")
            data: Data to save
            thread_id: Thread ID for this workflow run
        """
        # Use fixed filename without timestamp - will overwrite on each run
        filename = f"{thread_id}_{step_name}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        result = {
            "step_name": step_name,
            "thread_id": thread_id,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved {step_name} to: {filepath}")
        return filepath
    
    def save_research_findings(self, findings: Dict[str, Any], thread_id: str = "default"):
        """Save research findings from researcher agent."""
        return self.save_step_result("research_findings", findings, thread_id)
    
    def save_module_structure(self, structure: Dict[str, Any], thread_id: str = "default"):
        """Save module structure from module_structure_agent."""
        return self.save_step_result("module_structure", structure, thread_id)
    
    def save_xdp_content(self, xdp: Dict[str, Any], thread_id: str = "default"):
        """Save XDP content from xdp_agent."""
        return self.save_step_result("xdp_content", xdp, thread_id)
    
    def save_course_content(self, content: list, thread_id: str = "default"):
        """Save course content from course_content_agent."""
        return self.save_step_result("course_content", {"lessons": content}, thread_id)
    
    def save_quizzes(self, quizzes: list, thread_id: str = "default"):
        """Save quizzes from quiz_curator_agent."""
        return self.save_step_result("quizzes", {"quizzes": quizzes}, thread_id)
    
    def save_final_course(self, course_data: Dict[str, Any], thread_id: str = "default"):
        """Save final course output."""
        return self.save_step_result("final_course", course_data, thread_id)
    
    def save_video_transcripts(self, transcripts: List[Dict[str, Any]], thread_id: str = "default"):
        """Save video transcripts to JSON file."""
        return self.save_step_result("video_transcripts", {"transcripts": transcripts}, thread_id)
    
    def save_interrupt_state(self, interrupt_type: str, state: Dict[str, Any], 
                           thread_id: str = "default"):
        """Save state when workflow is interrupted for human review."""
        interrupt_data = {
            "interrupt_type": interrupt_type,
            "state": state,
            "requires_human_feedback": True
        }
        return self.save_step_result(f"interrupt_{interrupt_type}", interrupt_data, thread_id)
    
    def get_latest_result(self, step_name: str, thread_id: str = "default") -> Optional[Dict]:
        """Get the latest saved result for a step."""
        # With fixed filenames, just read the file directly
        filename = f"{thread_id}_{step_name}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

