# AI Course Builder

An intelligent, AI-powered course authoring system that automatically generates comprehensive online courses with research, structured modules, detailed content, quizzes, and video transcripts. Built with LangGraph for workflow orchestration and Streamlit for an interactive UI.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage Guide](#usage-guide)
- [Backend Architecture](#backend-architecture)
- [Special Features](#special-features)
- [Project Structure](#project-structure)
- [Configuration](#configuration)

## Features

### 🎯 Core Capabilities

1. **Automated Research & Analysis**
   - AI-powered research agent identifies key topics and learning objectives
   - Analyzes course subject and learner level to determine appropriate content depth
   - Generates comprehensive research findings with key areas, topics, and objectives

2. **Intelligent Module Structure Generation**
   - Creates well-organized course modules with logical topic distribution
   - Allocates time appropriately across modules
   - Plans quiz placement strategically
   - Supports optional lab modules for hands-on learning

3. **XDP Specification Generation**
   - Generates XDP (eXtended Data Protocol) format specifications
   - Ensures compatibility with course delivery platforms
   - Creates structured metadata for course deployment

4. **Comprehensive Content Generation**
   - Generates detailed lesson content including:
     - Engaging introductions with hooks and objectives
     - Main content with detailed explanations and concepts
     - Real-world examples and applications
     - Case studies (when applicable)
     - Practice exercises and activities
     - Key takeaways and summaries
     - Visual suggestions (diagrams, charts, infographics)
     - Lab instructions for lab modules
   - Parallel processing for efficient content generation across multiple lessons

5. **Quiz Creation**
   - Generates both graded and practice quizzes
   - Multiple question types:
     - 5-7 multiple choice questions
     - 2-3 true/false questions
     - 1-2 short answer questions
     - 1 essay question
   - Questions aligned with learning objectives
   - Parallel generation for multiple modules

6. **Video Transcript Generation**
   - Creates detailed video transcripts for all lessons
   - Includes speaker notes and timing information
   - Calculates estimated video durations
   - Formats transcripts for video production

7. **Human-in-the-Loop (HITL) Review System**
   - Interactive review checkpoints at three stages:
     - Module structure review
     - Course content review
     - Quiz review
   - Options to approve, reject (with regeneration), or continue with edits
   - 10-minute timeout window for feedback collection
   - Seamless workflow continuation after review

8. **Quality Validation**
   - Automated validation at multiple stages:
     - Module structure validation (quality score ≥ 0.7)
     - Content validation (quality score ≥ 0.8, no flagged lessons)
     - Quiz validation (quality score ≥ 0.8, objective coverage ≥ 0.8)
   - Conditional routing based on validation results

9. **Interactive Streamlit UI**
   - Modern, Coursera-inspired interface
   - Real-time progress tracking with animated spinners
   - Auto-refresh every 10 seconds
   - Detailed progress bar showing:
     - Overall completion percentage
     - Step-by-step status (pending, active, completed, failed)
     - Time estimates for long-running steps
     - Visual indicators with CSS-animated spinners
   - Module and lesson display with organized tabs
   - Quiz review interface with question-by-question display
   - Review forms for structure, content, and quizzes

10. **Progress Tracking & Logging**
    - Real-time progress logging to JSONL files
    - Detailed step tracking with timestamps
    - Error logging and reporting
    - Workflow state persistence

11. **Result Persistence**
    - All intermediate results saved as JSON files
    - Organized output structure in `course_outputs/` directory
    - Thread-based file naming for multiple concurrent courses
    - Final course compilation with complete metadata

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key
- pip package manager

### Installation

1. **Clone the repository** (or navigate to the project directory)

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API key:**
   - Edit `utils/config.py` and set your `GOOGLE_API_KEY`
   - Or set it as an environment variable

4. **Run the Streamlit UI:**
   ```bash
   streamlit run ui/app.py
   ```

5. **Access the application:**
   - Open your browser to `http://localhost:8501`

## Usage Guide

### Creating a Course via UI

1. **Navigate to "Create Course" page** in the Streamlit sidebar

2. **Fill in the course form:**
   - **Course Subject**: The main topic of your course (e.g., "Python Programming", "Machine Learning")
   - **Learner Level**: Choose from "basic", "intermediate", or "advanced"
   - **Course Duration**: Specify duration (e.g., "4 weeks", "20 hours")
   - **Number of Modules**: How many modules the course should have
   - **Graded Quizzes per Module**: Number of graded assessments per module
   - **Practice Quizzes per Module**: Number of practice quizzes per module
   - **Needs Lab Module**: Check if the course requires hands-on lab exercises
   - **Custom Prompt** (optional): Additional instructions for course generation

3. **Submit the form** - The workflow will start automatically

4. **Monitor Progress:**
   - Watch the progress bar at the top of the page
   - The UI auto-refreshes every 10 seconds
   - See real-time updates as each step completes

5. **Review Checkpoints:**
   - When validation fails or quality thresholds aren't met, review forms will appear
   - Review the generated content (structure, lessons, or quizzes)
   - Choose one of three options:
     - **Approve**: Accept the content and continue
     - **Reject**: Request regeneration with feedback
     - **Continue**: Use the content as-is (if you've made edits)

6. **View Final Course:**
   - Once complete, navigate to "View Course" in the sidebar
   - Browse modules, lessons, and quizzes
   - All content is saved in `course_outputs/` directory

### Creating a Course via CLI

You can also run the course builder programmatically:

```python
from main import run_course_builder

user_input = {
    "course_subject": "Python Programming",
    "learner_level": "intermediate",
    "course_duration": "4 weeks",
    "number_of_modules": 4,
    "graded_quizzes_per_module": 1,
    "practice_quizzes_per_module": 2,
    "needs_lab_module": True,
    "custom_prompt": "Focus on practical examples and real-world applications"
}

final_state, thread_id = run_course_builder(user_input, thread_id="my_course_001")
```

### Workflow Steps

The course builder follows this workflow:

1. **Collect User Input** - Gathers course requirements
2. **Research Phase** - AI analyzes the subject and identifies key topics
3. **Module Structure** - Creates organized module breakdown
4. **Validate Structure** - Checks structure quality (routes to review if needed)
5. **Review Structure** (Optional) - Human review checkpoint
6. **XDP Specification** - Generates XDP format specification
7. **Course Content** - Creates detailed lesson content (parallel processing)
8. **Validate Content** - Validates content quality (routes to review if needed)
9. **Review Content** (Optional) - Human review checkpoint
10. **Quiz Creation** - Generates quizzes (parallel processing)
11. **Validate Quizzes** - Validates quiz quality (routes to review if needed)
12. **Review Quizzes** (Optional) - Human review checkpoint
13. **Video Transcripts** - Generates video transcripts for all lessons
14. **Finalize Course** - Compiles final course with metadata

### Output Files

All results are saved in the `course_outputs/` directory with the following naming pattern:

- `{thread_id}_research_findings.json` - Research analysis results
- `{thread_id}_module_structure.json` - Module structure breakdown
- `{thread_id}_xdp_content.json` - XDP specification
- `{thread_id}_course_content.json` - All lesson content
- `{thread_id}_quizzes.json` - All quizzes (graded + practice)
- `{thread_id}_video_transcripts.json` - Video transcripts
- `{thread_id}_final_course.json` - Complete compiled course
- `{thread_id}_progress.jsonl` - Progress log (JSONL format)

## Backend Architecture

### LangGraph Workflow

The system uses **LangGraph** for workflow orchestration, providing:

- **State Management**: TypedDict-based state (`CourseState`) that flows through the workflow
- **Checkpointing**: In-memory checkpointing with `MemorySaver` for workflow resumability
- **Interrupts**: Built-in interrupt mechanism for HITL review checkpoints
- **Conditional Routing**: Smart routing based on validation results and user feedback
- **Node-based Architecture**: Modular nodes that can be easily extended or modified

### State Schema

The `CourseState` TypedDict includes:

- **User Input**: Course requirements (subject, level, duration, etc.)
- **Agent Outputs**: Research findings, module structure, content, quizzes, transcripts
- **Validation Results**: Quality scores and flags from validation agents
- **Human Feedback**: Feedback collected at review checkpoints
- **Approval Status**: Approval flags for each review type
- **Metadata**: Thread ID, errors, current step tracking

### Agent Architecture

Each agent is a self-contained function that:

- Takes `CourseState` as input
- Performs its specific task (research, content generation, etc.)
- Updates the state with results
- Logs progress using `ProgressTracker`
- Saves results using `ResultsSaver`
- Handles errors gracefully

### Parallel Processing

The system uses `ThreadPoolExecutor` for parallel processing in:

- **Course Content Generation**: Processes lessons in batches of 4
- **Quiz Generation**: Generates multiple quizzes concurrently
- **Video Transcript Generation**: Processes modules in parallel

This significantly reduces total generation time for large courses.

### Validation System

Three validation agents check quality at different stages:

1. **Module Structure Validation**:
   - Checks quality score (threshold: 0.7)
   - Validates structure completeness
   - Routes to review if quality is insufficient

2. **Content Validation**:
   - Checks quality score (threshold: 0.8)
   - Flags lessons with issues
   - Routes to review if quality is insufficient or lessons are flagged

3. **Quiz Validation**:
   - Checks quality score (threshold: 0.8)
   - Validates objective coverage (threshold: 0.8)
   - Routes to review if quality or coverage is insufficient

## Special Features

### 1. Human-in-the-Loop (HITL) Interrupts

The workflow pauses at three review checkpoints using LangGraph's `interrupt_after` feature:

- **Structure Review**: After module structure validation
- **Content Review**: After content validation
- **Quiz Review**: After quiz validation

**How it works:**
- Workflow pauses and waits for user feedback (up to 10 minutes)
- UI polls for feedback file or falls back to CLI input
- User can approve, reject (with feedback), or continue
- Workflow resumes from checkpoint after feedback is collected

**Regeneration Logic:**
- If user rejects, `approval_status` is set to `False`
- Workflow routes back to the generating agent
- Agent regenerates content incorporating feedback
- After successful regeneration, `approval_status` is reset to `None`
- This allows validation to determine next steps and prevents infinite loops

### 2. Real-Time Progress Tracking

The system uses a JSONL-based progress log (`_progress.jsonl`) that:

- Logs every workflow step with timestamps
- Tracks node start, progress, completion, and errors
- Enables real-time UI updates via file polling
- Provides detailed progress history for debugging

The UI reads this log to display:
- Overall completion percentage
- Current active step
- Step-by-step status with visual indicators
- Time estimates for long-running steps

### 3. Auto-Refresh UI

The Streamlit UI automatically refreshes every 10 seconds using `streamlit-autorefresh`:

- No manual refresh needed
- Progress bar updates automatically
- Review forms appear automatically when interrupts occur
- Seamless user experience

### 4. CSS-Animated Spinners

Instead of static emojis, the progress bar uses CSS-animated spinners for:

- **Active steps**: Animated spinner indicating work in progress
- **Waiting steps**: Pulsing spinner for review checkpoints
- **Completed steps**: Green checkmark (✅)
- **Failed steps**: Red X (❌)

### 5. Error Handling & Recovery

- Each agent has try-except blocks for error handling
- Errors are logged to state and progress tracker
- Workflow continues even if individual steps fail
- Fallback content generation if LLM parsing fails
- Graceful degradation with default structures

### 6. Thread-Based Isolation

Each course run uses a unique `thread_id`:

- Isolates results and progress logs
- Enables multiple concurrent course generations
- Prevents file conflicts
- Supports checkpointing and resumability

### 7. Smart Routing Logic

Conditional edges in the workflow graph enable:

- **Validation-based routing**: Pass to next step or route to review
- **Feedback-based routing**: Approve, reject (regenerate), or continue
- **State-aware decisions**: Routing functions check approval status and feedback

### 8. Duration Calculation

The system includes a `DurationCalculator` utility that:

- Parses duration strings (e.g., "30 minutes", "2 hours")
- Calculates total course duration
- Estimates video durations for transcripts
- Ensures time allocation consistency

### 9. JSON Parsing with Fallbacks

All LLM responses are parsed as JSON with:

- Multiple retry attempts with adjusted prompts
- Fallback to default structures if parsing fails
- Error logging for debugging
- Graceful handling of malformed responses

### 10. Results Persistence

The `ResultsSaver` utility provides:

- Consistent file naming patterns
- JSON serialization with proper formatting
- Thread-based file organization
- Error handling for file operations

## Project Structure

```
.
├── agents/                    # AI agent implementations
│   ├── researcher_agent.py    # Research and topic identification
│   ├── module_structure_agent.py  # Module structure generation
│   ├── xdp_agent.py           # XDP specification generation
│   ├── course_content_agent.py    # Lesson content generation
│   ├── quiz_curator_agent.py  # Quiz generation
│   └── video_transcript_agent.py   # Video transcript generation
│
├── nodes/                     # Workflow nodes
│   ├── question_collector.py  # User input collection
│   ├── validation_agent.py    # Quality validation logic
│   ├── hitl_review_nodes.py   # Human review checkpoints
│   ├── interrupt_handler.py   # HITL interrupt handling
│   ├── finalizer.py           # Course finalization
│   └── error_handler.py       # Error handling utilities
│
├── graph/                     # LangGraph workflow definition
│   └── course_builder_graph.py # Main workflow graph
│
├── state/                     # State management
│   └── base_state.py          # CourseState TypedDict definition
│
├── ui/                        # Streamlit UI
│   ├── app.py                 # Main UI application
│   ├── components.py          # Reusable UI components
│   ├── progress_display.py    # Progress bar and tracking
│   └── real_time_updates.py   # Real-time update display
│
├── utils/                     # Utility modules
│   ├── config.py              # Configuration (API keys, settings)
│   ├── gemini_llm.py          # Gemini LLM wrapper
│   ├── progress_tracker.py    # Progress logging
│   ├── results_saver.py       # Result file persistence
│   ├── duration_calculator.py # Duration parsing/calculation
│   ├── prompt_helpers.py      # Prompt formatting utilities
│   └── output_schemas.py      # Output schema definitions
│
├── course_outputs/            # Generated course files (created at runtime)
├── main.py                    # Main entry point and workflow runner
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Configuration

### API Configuration

Edit `utils/config.py` to configure:

```python
GOOGLE_API_KEY = "your-api-key-here"
GEMINI_MODEL = "gemini-2.5-pro"  # or "gemini-pro", "gemini-1.5-pro", etc.
GEMINI_TEMPERATURE = 0.7  # 0.0 to 1.0, controls creativity
```

### Interrupt Timeout

The interrupt timeout (time to wait for user feedback) is configured in `nodes/interrupt_handler.py`:

```python
max_wait_time = 600  # 10 minutes in seconds
```

### UI Auto-Refresh Interval

The UI auto-refresh interval is configured in `ui/app.py`:

```python
count = st_autorefresh(interval=10*1000, key="refresh_timer")  # 10 seconds
```

### Validation Thresholds

Validation thresholds are configured in `graph/course_builder_graph.py`:

- Structure validation: `quality_score >= 0.7`
- Content validation: `quality_score >= 0.8` and `flagged_lessons == 0`
- Quiz validation: `quality_score >= 0.8` and `objective_coverage >= 0.8`

### Parallel Processing Batch Size

Batch sizes for parallel processing are configured in the agent files:

- Course content: `batch_size = 4` (in `agents/course_content_agent.py`)
- Quiz generation: Processes all quizzes in parallel (in `agents/quiz_curator_agent.py`)
- Video transcripts: Processes modules in parallel (in `agents/video_transcript_agent.py`)

---

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

## Support

[Add support information here]

