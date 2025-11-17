"""Researcher Agent - Identifies key areas to cover based on learner level."""
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from utils.gemini_llm import GeminiLLM
from utils.config import GOOGLE_API_KEY, GEMINI_MODEL, GEMINI_TEMPERATURE
from utils.results_saver import ResultsSaver
from utils.progress_tracker import ProgressTracker
from state.base_state import CourseState


def researcher_agent(state: CourseState) -> CourseState:
    """
    Agent 1: Research and identify key areas that should be covered
    in the course based on the level of learner.
    """
    try:
        thread_id = state.get("course_metadata", {}).get("thread_id", "default")
        progress = ProgressTracker(thread_id)
        progress.log_node_progress("researcher_agent", {
            "message": "Starting research analysis",
            "subject": state.get("course_subject"),
            "level": state.get("learner_level")
        })
        
        # Initialize Gemini using google-generativeai directly
        llm = GeminiLLM(
            model=GEMINI_MODEL,
            api_key=GOOGLE_API_KEY,
            temperature=GEMINI_TEMPERATURE
        )
        
        # Create prompt for research
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert course researcher and instructional designer.
            Your task is to identify the key areas, topics, and learning objectives
            that should be covered in a course based on the subject and learner level.
            
            Provide a comprehensive analysis including:
            1. Key topic areas that must be covered
            2. Detailed topic breakdown
            3. Learning objectives for the course
            4. Prerequisites needed
            5. Depth mapping for each topic based on learner level"""),
            ("human", """Course Subject: {course_subject}
            Learner Level: {learner_level}
            Course Duration: {course_duration}
            Number of Modules: {number_of_modules}
            
            Please provide a comprehensive research analysis of what should be covered
            in this course. Format your response as JSON with the following structure:
            {{
                "key_areas": ["area1", "area2", ...],
                "topics": {{
                    "area1": ["topic1", "topic2", ...],
                    ...
                }},
                "learning_objectives": ["objective1", "objective2", ...],
                "prerequisites": ["prereq1", "prereq2", ...],
                "depth_mapping": {{
                    "topic1": "depth_level",
                    ...
                }}
            }}""")
        ])
        
        # Invoke LLM
        chain = prompt | llm
        response = chain.invoke({
            "course_subject": state["course_subject"],
            "learner_level": state["learner_level"],
            "course_duration": state["course_duration"],
            "number_of_modules": state["number_of_modules"]
        })
        
        # Parse response (in production, use proper JSON parsing)
        import json
        import re
        
        # Extract JSON from response - handle different response formats
        # LangChain returns AIMessage objects, so we need to extract content properly
        if hasattr(response, 'content'):
            content = response.content
        elif hasattr(response, 'text'):
            content = response.text
        elif isinstance(response, str):
            content = response
        elif hasattr(response, 'generations') and len(response.generations) > 0:
            # Handle ChatResult format
            message = response.generations[0].message
            content = message.content if hasattr(message, 'content') else str(message)
        else:
            # Try to get content from AIMessage if response is a message object
            content = str(response)
        
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            research_findings = json.loads(json_match.group())
        else:
            # Fallback: create basic structure
            research_findings = {
                "key_areas": [state["course_subject"]],
                "topics": {state["course_subject"]: ["Introduction", "Core Concepts", "Advanced Topics"]},
                "learning_objectives": [f"Understand {state['course_subject']} at {state['learner_level']} level"],
                "prerequisites": [],
                "depth_mapping": {}
            }
        
        state["research_findings"] = research_findings
        state["current_step"] = "research_completed"
        
        # Save results
        saver = ResultsSaver()
        saver.save_research_findings(research_findings, thread_id)
        
        progress.log_node_complete("researcher_agent", {
            "key_areas": len(research_findings.get("key_areas", [])),
            "objectives": len(research_findings.get("learning_objectives", []))
        })
        
    except Exception as e:
        error_msg = f"Researcher agent error: {str(e)}"
        state["errors"].append(error_msg)
        state["current_step"] = "research_failed"
        print(f"❌ Error in researcher_agent: {error_msg}")
        import traceback
        traceback.print_exc()
    
    return state

