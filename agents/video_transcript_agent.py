"""Video Transcript Agent - Generates video transcripts for all lessons."""
from typing import Dict, Any, List, Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from utils.gemini_llm import GeminiLLM
from utils.config import GOOGLE_API_KEY, GEMINI_MODEL, GEMINI_TEMPERATURE
from utils.results_saver import ResultsSaver
from utils.progress_tracker import ProgressTracker
from utils.duration_calculator import calculate_video_durations
from utils.prompt_helpers import create_json_parser
from state.base_state import CourseState
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import re
from datetime import datetime


def format_list_field(items: list) -> str:
    """
    Safely format a list field (examples, case_studies, practice_exercises) to string.
    Handles both string lists and dictionary lists.
    
    Args:
        items: List that may contain strings or dictionaries
    
    Returns:
        Comma-separated string representation
    """
    if not items:
        return "None"
    
    formatted_items = []
    for item in items:
        if isinstance(item, str):
            formatted_items.append(item)
        elif isinstance(item, dict):
            # Try to extract meaningful text from dict
            text = item.get('title') or item.get('description') or item.get('text') or item.get('name') or str(item)
            formatted_items.append(str(text))
        else:
            # Convert anything else to string
            formatted_items.append(str(item))
    
    return ', '.join(formatted_items) if formatted_items else "None"


def generate_module_transcripts(module_data: Dict[str, Any], state: CourseState, durations: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Generate transcripts for all lessons in a module.
    
    Args:
        module_data: Dictionary with module info and lessons
        state: CourseState
        durations: Dictionary mapping lesson_id to duration in minutes
    
    Returns:
        List of transcript dictionaries
    """
    module_id = module_data["module_id"]
    module_name = module_data["module_name"]
    lessons = module_data["lessons"]
    
    llm = GeminiLLM(
        model=GEMINI_MODEL,
        api_key=GOOGLE_API_KEY,
        temperature=GEMINI_TEMPERATURE
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert video script writer. Create natural, engaging 
video transcripts that are suitable for narration. The transcript should be 
conversational, clear, and match the target duration. Write as if you are speaking 
directly to students in a friendly, engaging manner."""),
        ("human", """Generate a video transcript for this lesson:

Lesson: {lesson_name}
Module: {module_name}
Target Duration: {video_duration_minutes} minutes
Target Speaking Rate: ~150 words per minute
Estimated Word Count: {estimated_word_count} words
Learner Level: {learner_level}
Course Subject: {course_subject}

Lesson Content:
{lesson_content}

The transcript should:
1. Be natural and conversational (as if speaking to students)
2. Include engaging introduction and smooth transitions
3. Cover all key concepts from the lesson content
4. Be approximately {estimated_word_count} words (±10% variance)
5. Be suitable for video narration
6. Use clear, simple language appropriate for {learner_level} learners
7. Include natural pauses and emphasis where needed

Return JSON:
{{
    "transcript": "Full transcript text...",
    "word_count": 2250,
    "estimated_duration_minutes": 15
}}""")
    ])
    
    transcripts = []
    thread_id = state.get("course_metadata", {}).get("thread_id", "default")
    progress = ProgressTracker(thread_id)
    
    for lesson in lessons:
        lesson_id = lesson.get("lesson_id", f"lesson_{module_id}_{lessons.index(lesson)}")
        lesson_name = lesson.get("lesson_name", "Lesson")
        
        # Get duration for this lesson
        video_duration = durations.get(lesson_id, 15.0)
        estimated_word_count = int(video_duration * 150)  # 150 words per minute
        
        # Get lesson content from course_content
        lesson_content_data = None
        if state.get("course_content"):
            for content in state["course_content"]:
                if content.get("lesson_id") == lesson_id or content.get("lesson_name") == lesson_name:
                    lesson_content_data = content
                    break
        
        if not lesson_content_data:
            # Fallback: use lesson structure
            lesson_content = json.dumps(lesson, indent=2)
        else:
            # Format lesson content nicely - safely handle list fields
            examples = format_list_field(lesson_content_data.get('examples', []))
            case_studies = format_list_field(lesson_content_data.get('case_studies', []))
            practice_exercises = format_list_field(lesson_content_data.get('practice_exercises', []))
            
            lesson_content = f"""
Introduction: {lesson_content_data.get('introduction', '')}

Main Content: {lesson_content_data.get('main_content', '')}

Examples: {examples}

Case Studies: {case_studies}

Practice Exercises: {practice_exercises}

Summary: {lesson_content_data.get('summary', '')}
"""
        
        try:
            chain = (
                RunnablePassthrough.assign(
                    lesson_name=lambda _: lesson_name,
                    module_name=lambda _: module_name,
                    video_duration_minutes=lambda _: video_duration,
                    estimated_word_count=lambda _: estimated_word_count,
                    learner_level=lambda _: state["learner_level"],
                    course_subject=lambda _: state["course_subject"],
                    lesson_content=lambda _: lesson_content
                )
                | prompt
                | llm
            )
            
            # Get raw LLM response first
            raw_response = chain.invoke({})
            
            # Extract content from response
            if hasattr(raw_response, 'content'):
                response_content = raw_response.content
            elif hasattr(raw_response, 'text'):
                response_content = raw_response.text
            else:
                response_content = str(raw_response)
            
            # Try to parse JSON from response
            result = {}
            try:
                # First try direct JSON parsing
                json_match = re.search(r'\{[^{}]*"transcript"[^{}]*\}', response_content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    # Try to find JSON block
                    json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                    else:
                        # If no JSON found, try parsing the whole response
                        result = json.loads(response_content)
            except (json.JSONDecodeError, Exception) as parse_error:
                # If JSON parsing fails, try to extract transcript from text
                # Look for transcript field in various formats
                transcript_match = re.search(r'"transcript"\s*:\s*"([^"]+)"', response_content, re.DOTALL)
                if not transcript_match:
                    transcript_match = re.search(r'transcript["\']?\s*:\s*["\']([^"\']+)["\']', response_content, re.DOTALL)
                
                if transcript_match:
                    extracted_transcript = transcript_match.group(1)
                    # Unescape newlines and other escape sequences
                    extracted_transcript = extracted_transcript.replace('\\n', '\n').replace('\\"', '"')
                    result = {
                        "transcript": extracted_transcript,
                        "word_count": len(extracted_transcript.split()),
                        "estimated_duration_minutes": video_duration
                    }
                else:
                    # If we can't extract, use the raw response as transcript (might be plain text)
                    if len(response_content.strip()) > 50:  # Only use if substantial content
                        result = {
                            "transcript": response_content.strip(),
                            "word_count": len(response_content.split()),
                            "estimated_duration_minutes": video_duration
                        }
            
            # Validate and use result
            if result and result.get("transcript") and len(result.get("transcript", "").strip()) > 50:
                transcript_text = result.get("transcript", "").strip()
                transcript = {
                    "transcript_id": f"transcript_{module_id}_{lesson_id}",
                    "module_id": int(module_id),
                    "module_name": module_name,
                    "lesson_id": lesson_id,
                    "lesson_name": lesson_name,
                    "video_duration_minutes": video_duration,
                    "transcript": transcript_text,
                    "word_count": result.get("word_count", len(transcript_text.split())),
                    "estimated_duration_minutes": result.get("estimated_duration_minutes", video_duration),
                    "speaking_rate": "normal",
                    "generated_at": datetime.now().isoformat()
                }
                transcripts.append(transcript)
            else:
                # Log the issue but don't use fallback - retry with better prompt
                progress.log_node_progress("video_transcript_agent", {
                    "lesson": lesson_id,
                    "warning": "Short or missing transcript, retrying with explicit format",
                    "response_length": len(response_content) if 'response_content' in locals() else 0
                })
                
                # Retry with more explicit JSON format request
                retry_prompt = ChatPromptTemplate.from_messages([
                    ("system", """You are an expert video script writer. Create natural, engaging 
video transcripts that are suitable for narration. The transcript should be 
conversational, clear, and match the target duration. Write as if you are speaking 
directly to students in a friendly, engaging manner. IMPORTANT: You MUST return valid JSON format."""),
                    ("human", """Generate a video transcript for this lesson. You MUST return ONLY valid JSON.

Lesson: {lesson_name}
Module: {module_name}
Target Duration: {video_duration_minutes} minutes
Target Speaking Rate: ~150 words per minute
Estimated Word Count: {estimated_word_count} words
Learner Level: {learner_level}
Course Subject: {course_subject}

Lesson Content:
{lesson_content}

The transcript should:
1. Be natural and conversational (as if speaking to students)
2. Include engaging introduction and smooth transitions
3. Cover all key concepts from the lesson content
4. Be approximately {estimated_word_count} words (±10% variance)
5. Be suitable for video narration
6. Use clear, simple language appropriate for {learner_level} learners
7. Include natural pauses and emphasis where needed

Return ONLY valid JSON (no markdown, no code blocks, no extra text):
{{
    "transcript": "Full transcript text here...",
    "word_count": 2250,
    "estimated_duration_minutes": 15
}}""")
                ])
                
                retry_chain = (
                    RunnablePassthrough.assign(
                        lesson_name=lambda _: lesson_name,
                        module_name=lambda _: module_name,
                        video_duration_minutes=lambda _: video_duration,
                        estimated_word_count=lambda _: estimated_word_count,
                        learner_level=lambda _: state["learner_level"],
                        course_subject=lambda _: state["course_subject"],
                        lesson_content=lambda _: lesson_content
                    )
                    | retry_prompt
                    | llm
                )
                
                retry_response = retry_chain.invoke({})
                retry_content = retry_response.content if hasattr(retry_response, 'content') else str(retry_response)
                
                # Parse retry response
                try:
                    json_match = re.search(r'\{.*\}', retry_content, re.DOTALL)
                    if json_match:
                        retry_result = json.loads(json_match.group())
                        if retry_result.get("transcript") and len(retry_result.get("transcript", "").strip()) > 50:
                            transcript_text = retry_result.get("transcript", "").strip()
                            transcript = {
                                "transcript_id": f"transcript_{module_id}_{lesson_id}",
                                "module_id": int(module_id),
                                "module_name": module_name,
                                "lesson_id": lesson_id,
                                "lesson_name": lesson_name,
                                "video_duration_minutes": video_duration,
                                "transcript": transcript_text,
                                "word_count": retry_result.get("word_count", len(transcript_text.split())),
                                "estimated_duration_minutes": retry_result.get("estimated_duration_minutes", video_duration),
                                "speaking_rate": "normal",
                                "generated_at": datetime.now().isoformat()
                            }
                            transcripts.append(transcript)
                        else:
                            raise ValueError("Retry also failed to produce valid transcript")
                    else:
                        raise ValueError("No JSON found in retry response")
                except Exception as retry_error:
                    # Final fallback - use a more detailed transcript based on lesson content
                    fallback_transcript = f"""Welcome to this lesson on {lesson_name}. In this module, {module_name}, we will explore the key concepts and practical applications.

{lesson_content_data.get('introduction', '')[:200] if lesson_content_data else ''}

Let's begin with an overview of the main topics we'll cover in this lesson. We'll dive deep into the concepts, work through examples, and ensure you have a solid understanding by the end."""
                    
                    transcript = {
                        "transcript_id": f"transcript_{module_id}_{lesson_id}",
                        "module_id": int(module_id),
                        "module_name": module_name,
                        "lesson_id": lesson_id,
                        "lesson_name": lesson_name,
                        "video_duration_minutes": video_duration,
                        "transcript": fallback_transcript,
                        "word_count": len(fallback_transcript.split()),
                        "estimated_duration_minutes": video_duration,
                        "speaking_rate": "normal",
                        "generated_at": datetime.now().isoformat(),
                        "error": f"JSON parsing failed: {str(retry_error)}"
                    }
                    transcripts.append(transcript)
                
        except Exception as e:
            # Create fallback transcript on error
            fallback_transcript = f"""Welcome to this lesson on {lesson_name}. In this module, {module_name}, we will explore the key concepts and practical applications.

{lesson_content_data.get('introduction', '')[:200] if lesson_content_data else ''}

Let's begin with an overview of the main topics we'll cover."""
            
            transcript = {
                "transcript_id": f"transcript_{module_id}_{lesson_id}",
                "module_id": int(module_id),
                "module_name": module_name,
                "lesson_id": lesson_id,
                "lesson_name": lesson_name,
                "video_duration_minutes": video_duration,
                "transcript": fallback_transcript,
                "word_count": len(fallback_transcript.split()),
                "estimated_duration_minutes": video_duration,
                "speaking_rate": "normal",
                "generated_at": datetime.now().isoformat(),
                "error": str(e)
            }
            transcripts.append(transcript)
    
    return transcripts


def video_transcript_agent(state: CourseState) -> CourseState:
    """
    Agent: Generate video transcripts for all lessons.
    Creates natural, spoken-style transcripts suitable for narration.
    """
    try:
        thread_id = state.get("course_metadata", {}).get("thread_id", "default")
        progress = ProgressTracker(thread_id)
        
        if not state.get("module_structure") or not state.get("course_content"):
            state["errors"].append("Module structure or course content not available")
            progress.log_node_error("video_transcript_agent", "Module structure or course content not available")
            return state
        
        progress.log_node_progress("video_transcript_agent", {
            "message": "Starting video transcript generation"
        })
        
        # Calculate video durations for all lessons
        durations = calculate_video_durations(state)
        
        # Prepare module tasks
        module_structure = state.get("module_structure", {})
        modules = module_structure.get("modules", [])
        
        total_lessons = sum(len(module.get("lessons", [])) for module in modules)
        
        progress.log_node_progress("video_transcript_agent", {
            "total_modules": len(modules),
            "total_lessons": total_lessons,
            "message": f"Generating transcripts for {total_lessons} lessons across {len(modules)} modules"
        })
        
        # Process modules in parallel
        all_transcripts = []
        max_workers = min(4, len(modules))  # Limit concurrency
        completed = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all module tasks
            future_to_module = {
                executor.submit(generate_module_transcripts, {
                    "module_id": module.get("module_id"),
                    "module_name": module.get("module_name", f"Module {module.get('module_id')}"),
                    "lessons": module.get("lessons", [])
                }, state, durations): module.get("module_id")
                for module in modules
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_module):
                module_id = future_to_module[future]
                try:
                    module_transcripts = future.result()
                    all_transcripts.extend(module_transcripts)
                    completed += 1
                    
                    progress.log_node_progress("video_transcript_agent", {
                        "module": module_id,
                        "transcripts_generated": len(module_transcripts),
                        "total_generated": len(all_transcripts),
                        "completed_modules": completed,
                        "total_modules": len(modules),
                        "message": f"Module {module_id} completed: {len(module_transcripts)} transcripts"
                    })
                except Exception as e:
                    progress.log_node_progress("video_transcript_agent", {
                        "module": module_id,
                        "error": str(e),
                        "message": f"Module {module_id} failed: {str(e)}"
                    })
        
        # Sort transcripts by module_id and lesson_id
        all_transcripts.sort(key=lambda x: (x.get("module_id", 0), x.get("lesson_id", "")))
        
        state["video_transcripts"] = all_transcripts
        state["current_step"] = "video_transcripts_created"
        
        # Save results
        saver = ResultsSaver()
        saver.save_video_transcripts(all_transcripts, thread_id)
        
        total_duration = sum(t.get("video_duration_minutes", 0) for t in all_transcripts)
        progress.log_node_complete("video_transcript_agent", {
            "total_transcripts": len(all_transcripts),
            "total_duration_minutes": round(total_duration, 1),
            "message": f"Successfully generated {len(all_transcripts)} video transcripts"
        })
        
    except Exception as e:
        error_msg = f"Video transcript agent error: {str(e)}"
        state["errors"].append(error_msg)
        state["current_step"] = "video_transcripts_failed"
        if "video_transcripts" not in state or state.get("video_transcripts") is None:
            state["video_transcripts"] = []
        progress.log_node_error("video_transcript_agent", error_msg)
        print(f"❌ Error in video_transcript_agent: {error_msg}")
        import traceback
        traceback.print_exc()
    
    return state

