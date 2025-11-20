"""Main entry point for the Course Builder application."""
import os
import glob
from graph.course_builder_graph import create_course_builder_graph
from state.base_state import CourseState
from langgraph.checkpoint.memory import MemorySaver
from utils.progress_tracker import ProgressTracker


def initialize_state(user_input: dict, thread_id: str = "default") -> CourseState:
    """Initialize state with user input."""
    return CourseState(
        # User Input
        course_subject=user_input.get("course_subject", ""),
        learner_level=user_input.get("learner_level", "intermediate"),
        course_duration=user_input.get("course_duration", "4 weeks"),
        number_of_modules=user_input.get("number_of_modules", 4),
        graded_quizzes_per_module=user_input.get("graded_quizzes_per_module", 1),
        practice_quizzes_per_module=user_input.get("practice_quizzes_per_module", 2),
        needs_lab_module=user_input.get("needs_lab_module", False),
        custom_prompt=user_input.get("custom_prompt", ""),
        
        # Initialize empty structures
        research_findings=None,
        module_structure=None,
        xdp_content=None,
        course_content=None,
        quizzes=None,
        video_transcripts=None,
        
        # Initialize control structures
        validation_results={},
        human_feedback={},
        approval_status={},
        
        # Metadata (include thread_id for results saving)
        course_metadata={"thread_id": thread_id},
        errors=[],
        current_step="initialized"
    )


def clear_previous_run(thread_id: str, output_dir: str = "course_outputs"):
    """
    Clear previous run data for a thread_id to ensure fresh start.
    
    IMPORTANT: This only clears JSON output files, NOT LangGraph checkpoints.
    LangGraph checkpoints are stored in-memory in the MemorySaver instance
    and persist during a single workflow execution (same graph instance).
    
    Args:
        thread_id: Thread ID to clear
        output_dir: Output directory
    """
    # Clear all output files for this thread_id
    # This does NOT affect LangGraph checkpoints, which are in-memory
    pattern = os.path.join(output_dir, f"{thread_id}_*.json")
    for filepath in glob.glob(pattern):
        try:
            os.remove(filepath)
            print(f"🗑️  Cleared previous file: {os.path.basename(filepath)}")
        except Exception as e:
            print(f"⚠️  Could not remove {filepath}: {e}")


def run_course_builder(user_input: dict, thread_id: str = "default", clear_existing: bool = True):
    """
    Run the course builder workflow.
    
    Args:
        user_input: Dictionary with course requirements
        thread_id: Thread ID for checkpointing/resumability
        clear_existing: If True, clear previous run data for fresh start
    
    Returns:
        Final state with complete course
    """
    # Clear previous run data if requested (only clears JSON output files, NOT LangGraph checkpoints)
    if clear_existing:
        clear_previous_run(thread_id)
    
    # Create graph with MemorySaver for checkpointing
    # Note: MemorySaver is in-memory and persists checkpoints during this workflow execution
    # The same 'app' instance is used throughout, so interrupts and feedback loops work correctly
    app = create_course_builder_graph()
    
    # Initialize state
    initial_state = initialize_state(user_input, thread_id)
    
    # Configuration for checkpointing
    config = {"configurable": {"thread_id": thread_id}}
    
    # Initialize progress tracker
    progress = ProgressTracker(thread_id)
    progress.log_step("workflow", "started", {"thread_id": thread_id})
    
    # Run the workflow
    final_state = None
    for state_update in app.stream(initial_state, config=config):
        # Handle state update - can be dict or tuple
        if isinstance(state_update, dict):
            state_dict = state_update
        else:
            state_dict = dict(state_update)
        
        # Check if this is an interrupt (workflow paused after node)
        if "__interrupt__" in state_dict:
            # Feedback already collected in the node, just continue streaming from checkpoint
            progress.log_step("workflow", "in_progress", {"action": "continuing_after_interrupt"})
            print("\n" + "="*70)
            print("🔄 CONTINUING WORKFLOW AFTER REVIEW")
            print("="*70 + "\n")
            # Continue streaming from where we left off
            # Use a while loop to handle nested interrupts and ensure we continue until workflow completes
            while True:
                stream_ended = True
                for state_update in app.stream(None, config=config):
                    stream_ended = False
                    if isinstance(state_update, dict):
                        state_dict = state_update
                    else:
                        state_dict = dict(state_update)
                    
                    # Handle nested interrupts recursively
                    if "__interrupt__" in state_dict:
                        progress.log_step("workflow", "in_progress", {"action": "continuing_after_interrupt"})
                        print("\n🔄 Continuing workflow after review...\n")
                        break  # Break inner loop, continue outer while loop
                    
                    # LangGraph streams return {node_name: full_state_after_node}
                    # Extract node name and full state
                    for node_name, node_state in state_dict.items():
                        # node_state is the FULL state after this node executes
                        if isinstance(node_state, dict):
                            state_data = node_state
                        elif isinstance(node_state, tuple):
                            state_data = node_state[1] if len(node_state) > 1 else {}
                        else:
                            state_data = {}
                        
                        # Only process if we have valid state data
                        if not isinstance(state_data, dict) or not state_data:
                            continue
                        
                        progress.log_node_start(node_name)
                        print(f"Step: {node_name}")
                        
                        # Special handling for routing nodes (they don't appear in stream but affect flow)
                        if node_name == "human_review_quizzes" and state_data.get("approval_status", {}).get("quizzes") is not None:
                            print(f"  Quiz review completed. Approval: {state_data['approval_status'].get('quizzes')}")
                            print(f"  Waiting for routing to next step...")
                        
                        if "current_step" in state_data:
                            print(f"  Status: {state_data['current_step']}")
                        
                        # Display detailed results - check the FULL state for outputs
                        details = {}
                        if state_data.get("module_structure"):
                            modules = state_data["module_structure"].get("modules", [])
                            print(f"  Modules created: {len(modules)}")
                            total_lessons = sum(len(m.get("lessons", [])) for m in modules)
                            print(f"  Total lessons: {total_lessons}")
                            details = {"modules": len(modules), "total_lessons": total_lessons}
                        
                        if state_data.get("course_content"):
                            lessons = state_data["course_content"]
                            print(f"  Lessons generated: {len(lessons)}")
                            details = {"lessons": len(lessons)}
                        
                        if state_data.get("quizzes"):
                            quizzes = state_data["quizzes"]
                            print(f"  Quizzes created: {len(quizzes)}")
                            details = {"quizzes": len(quizzes)}
                        
                        if state_data.get("xdp_content"):
                            print(f"  XDP content generated")
                            details = {"xdp_content": "generated"}
                        
                        if state_data.get("course_metadata"):
                            print(f"  Course finalized")
                            details = {"course_finalized": True}
                        
                        if details:
                            progress.log_node_complete(node_name, details)
                        elif "current_step" in state_data:
                            progress.log_node_complete(node_name, {"status": state_data['current_step']})
                        
                        # Log any errors
                        if state_data.get("errors"):
                            print(f"  Error: {state_data['errors'][-1]}")
                            progress.log_node_error(node_name, str(state_data["errors"][-1]))
                    
                    final_state = state_dict
                
                # If stream ended, check if we need to continue
                if stream_ended:
                    # Check if finalize_course has run by checking for course_metadata
                    if final_state and isinstance(final_state, dict):
                        # Check all node states in final_state
                        for node_name, node_state in final_state.items():
                            if node_name == "__interrupt__":
                                continue
                            if isinstance(node_state, dict):
                                state_data = node_state
                            elif isinstance(node_state, tuple):
                                state_data = node_state[1] if len(node_state) > 1 else {}
                            else:
                                state_data = {}
                            
                            if state_data.get("course_metadata"):
                                print("\n✅ Course finalized detected. Workflow complete.")
                                break
                    
                    # Break out of while loop if stream ended
                    break
            
            progress.log_step("workflow", "completed", {"final": True})
            return final_state, thread_id
        
        # Log and print current step
        for node_name, node_state in state_dict.items():
            # node_state is the FULL state after this node executes
            if isinstance(node_state, dict):
                state_data = node_state
            elif isinstance(node_state, tuple):
                state_data = node_state[1] if len(node_state) > 1 else {}
            else:
                state_data = {}
            
            # Only process if we have valid state data
            if not isinstance(state_data, dict) or not state_data:
                continue
            
            progress.log_node_start(node_name)
            print(f"Step: {node_name}")
            
            if "current_step" in state_data:
                print(f"  Status: {state_data['current_step']}")
            
            # Display detailed results - check the FULL state for outputs
            details = {}
            if state_data.get("module_structure"):
                modules = state_data["module_structure"].get("modules", [])
                print(f"  Modules created: {len(modules)}")
                total_lessons = sum(len(m.get("lessons", [])) for m in modules)
                print(f"  Total lessons: {total_lessons}")
                details = {"modules": len(modules), "total_lessons": total_lessons}
            
            if state_data.get("course_content"):
                lessons = state_data["course_content"]
                print(f"  Lessons generated: {len(lessons)}")
                details = {"lessons": len(lessons)}
            
            if state_data.get("quizzes"):
                quizzes = state_data["quizzes"]
                print(f"  Quizzes created: {len(quizzes)}")
                details = {"quizzes": len(quizzes)}
            
            if state_data.get("xdp_content"):
                print(f"  XDP content generated")
                details = {"xdp_content": "generated"}
            
            if state_data.get("course_metadata"):
                print(f"  Course finalized")
                details = {"course_finalized": True}
            
            if details:
                progress.log_node_complete(node_name, details)
            elif "current_step" in state_data:
                progress.log_node_complete(node_name, {"status": state_data['current_step']})
            
            # Log any errors
            if state_data.get("errors"):
                print(f"  Error: {state_data['errors'][-1]}")
                progress.log_node_error(node_name, str(state_data["errors"][-1]))
        
        final_state = state_dict
    
    # When stream ends, check if END was reached (finalize_course completed)
    # In LangGraph, END is not an executable node - when a node routes to END, the stream ends
    print("\n" + "="*70)
    print("📊 STREAM ENDED - Checking if END node was reached...")
    print("="*70)
    
    end_reached = False
    if final_state and isinstance(final_state, dict):
        for node_name, node_state in final_state.items():
            if node_name == "__interrupt__":
                continue
            if isinstance(node_state, dict):
                state_data = node_state
            elif isinstance(node_state, tuple):
                state_data = node_state[1] if len(node_state) > 1 else {}
            else:
                state_data = {}
            
            if isinstance(state_data, dict) and state_data.get("course_metadata"):
                end_reached = True
                print("\n✅ Workflow reached END node successfully!")
                print("   (END is not an executable node - stream ending after finalize_course confirms END was reached)")
                break
    
    if end_reached:
        progress.log_step("workflow", "completed", {"reached_end": True, "final": True})
        print("\n✅ Workflow completed successfully. Exiting...")
    else:
        progress.log_step("workflow", "completed", {"reached_end": False, "final": True})
        print("⚠️ Warning: Stream ended but END node may not have been reached.")
        print("   This might indicate the workflow did not complete successfully.")
        print("   Final state keys:", list(final_state.keys()) if final_state else "None")
    
    print("="*70 + "\n")
    return final_state, thread_id


def resume_after_interrupt(thread_id: str, config: dict = None):
    """
    Resume workflow after HITL interrupt.
    With interrupt_after, feedback is already collected, so just continue.
    
    Args:
        thread_id: Thread ID from interrupted workflow
        config: Optional configuration
    
    Returns:
        Updated state
    """
    app = create_course_builder_graph()
    
    if config is None:
        config = {"configurable": {"thread_id": thread_id}}
    
    # Continue workflow from checkpoint
    final_state = None
    for state_update in app.stream(None, config=config):
        if isinstance(state_update, dict):
            state_dict = state_update
        else:
            state_dict = dict(state_update)
        
        for node_name, node_state in state_dict.items():
            if node_name == "__interrupt__":
                continue
                
            print(f"Step: {node_name}")
            
            if isinstance(node_state, dict):
                state_data = node_state
            elif isinstance(node_state, tuple):
                state_data = node_state[1] if len(node_state) > 1 else {}
            else:
                state_data = {}
            
            if isinstance(state_data, dict) and "current_step" in state_data:
                print(f"  Status: {state_data['current_step']}")
        
        final_state = state_dict
    
    return final_state, thread_id


if __name__ == "__main__":
    # Example usage
    print("Course Builder - AI-Powered Course Authoring")
    print("=" * 50)
    
    # Example user input (in production, this would come from UI)
    user_input = {
        "course_subject": "Python Programming",
        "learner_level": "intermediate",
        "course_duration": "4 weeks",
        "number_of_modules": 4,
        "graded_quizzes_per_module": 1,
        "practice_quizzes_per_module": 2,
        "needs_lab_module": True
    }
    
    print("\nStarting course generation...")
    print(f"Subject: {user_input['course_subject']}")
    print(f"Level: {user_input['learner_level']}")
    print(f"Modules: {user_input['number_of_modules']}\n")
    
    final_state, thread_id = run_course_builder(user_input)
    
    if final_state:
        # Check if we have a complete course
        for node_name, state in final_state.items():
            # Handle state - can be dict or tuple
            if isinstance(state, dict):
                state_data = state
            elif isinstance(state, tuple):
                state_data = state[1] if len(state) > 1 else {}
            else:
                state_data = {}
            
            if isinstance(state_data, dict) and state_data.get("course_metadata"):
                print("\n✅ Course generation completed!")
                print(f"\nCourse Statistics:")
                stats = state_data["course_metadata"].get("statistics", {})
                for key, value in stats.items():
                    print(f"  {key}: {value}")
                
                # Final course is already saved by finalizer
                print(f"\n✅ Course generation completed!")
                print(f"📁 All results saved in: course_outputs/")
                print(f"   - Research findings")
                print(f"   - Module structure")
                print(f"   - XDP content")
                print(f"   - Course content")
                print(f"   - Quizzes")
                print(f"   - Final course")

