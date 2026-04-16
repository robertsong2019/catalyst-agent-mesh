# Architecture Guide — Catalyst Agent Mesh

## System Overview

```
┌─────────────────────────────────────────────────┐
│                    Client                        │
│         (HTTP API / WebSocket / Python)          │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│               FastAPI Server                     │
│          (src/main.py)                           │
│  ┌─────────────┐ ┌──────────┐ ┌─────────────┐  │
│  │ Agent EP    │ │ Task EP  │ │ Pipeline EP  │  │
│  └──────┬──────┘ └─────┬────┘ └──────┬──────┘  │
└─────────┼──────────────┼─────────────┼──────────┘
          │              │             │
┌─────────▼──────────────▼─────────────▼──────────┐
│                  AgentMesh                       │
│           (src/mesh/agent_mesh.py)               │
│  • Agent registry & discovery                    │
│  • Task routing & execution                      │
│  • Workflow management                           │
│  • WebSocket broadcast                           │
└────────┬─────────────────────────┬──────────────┘
         │                         │
┌────────▼──────────┐  ┌──────────▼───────────────┐
│   CreativeAgent   │  │    PipelineExecutor       │
│  (src/agents/)    │  │  (src/mesh/pipeline_      │
│                   │  │   executor.py)            │
│ ┌───────────────┐ │  │                          │
│ │ LLMProvider   │ │  │  Stage → Stage → Stage   │
│ │ ├─ Ollama     │ │  │   ┌─┐ ┌─┐ ┌─┐           │
│ │ ├─ OpenAI     │ │  │   │T│ │T│ │T│  (parallel) │
│ │ └─ Mock       │ │  │   └─┘ └─┘ └─┘           │
│ └───────────────┘ │  └──────────────────────────┘
└───────────────────┘
```

## Core Modules

### 1. Agents (`src/agents/creative_agents.py`)

**LLMProvider** — Abstract base with three implementations:
- `OllamaProvider` → Local LLMs via Ollama REST API
- `OpenAIProvider` → OpenAI Chat Completions API
- `MockProvider` → Returns canned responses for testing

**CreativeAgent** — Abstract base class providing:
- LLM integration via `_llm_generate()` with error tracking
- Status management (`idle`, `researching`, `writing`, etc.)
- Stats collection (task count, error count, health)
- Mesh awareness (broadcasts status changes)

**Concrete Agents:**
| Agent | Specialty | Key Capabilities |
|-------|-----------|-----------------|
| `ResearchAgent` | `research` | web_search, literature_review, data_analysis, synthesis |
| `CreativeWriterAgent` | `writing` | content_generation, storytelling, editing, tone_adjustment |
| `DesignAgent` | `design` | concept_generation, visual_design, layout, color_scheme |
| `AnalysisAgent` | `analysis` | data_analysis, pattern_recognition, trend_identification |

### 2. Agent Mesh (`src/mesh/agent_mesh.py`)

Central coordinator that manages:
- **Agent Registry** — Register/unregister agents, lookup by specialty or capability
- **Task Routing** — Automatically selects agents based on task type
- **Workflow Engine** — Sequential step execution with failure handling
- **Real-time Broadcast** — Pushes updates to all WebSocket connections
- **Convenience Pipelines** — `execute_content_creation_pipeline()`, `execute_research_pipeline()`

### 3. Pipeline Executor (`src/mesh/pipeline_executor.py`)

Enables parallel execution within sequential stages:
- **PipelineStage** — A named group of tasks with concurrency control
- **Semaphore-based parallelism** — `max_concurrent` limits parallel tasks per stage
- **Result aggregation** — Combines parallel task outputs into stage results
- **Lifecycle management** — Create, execute, monitor, cancel pipelines

### 4. API Server (`src/main.py`)

FastAPI application with:
- RESTful endpoints for agents, tasks, workflows, pipelines
- WebSocket endpoint for real-time updates
- CORS middleware for frontend integration
- Lifespan management (init/cleanup)

### 5. Configuration (`src/config.py`)

Dataclass-based config with `from_env()` for environment variable loading. See [API docs](./API.md#configuration) for all variables.

## Data Flow

### Simple Task
```
Client → POST /tasks → AgentMesh.execute_task()
  → select_agents_for_task() → CreativeAgent.process_task()
    → LLMProvider.generate() → result
  ← result ←
```

### Pipeline Execution
```
Client → POST /pipelines/{id}/execute
  → PipelineExecutor.execute_pipeline()
    → for each stage (sequential):
      → execute_stage()
        → _execute_tasks_in_parallel() (semaphore-controlled)
          → for each task: agent.process_task()
        → _combine_stage_results()
    → return combined results
```

## Design Decisions

**Why abstract LLMProvider?** Swap between mock/local/cloud without changing agent logic. Enables testing without LLM access.

**Why sequential stages with parallel tasks?** Real workflows have dependencies (research before writing), but individual steps within a stage can run concurrently.

**Why WebSocket broadcast?** Frontends can show real-time agent status, task progress, and pipeline updates without polling.

## Extending the System

### Add a New Agent Type

```python
# In src/agents/creative_agents.py
class TranslationAgent(CreativeAgent):
    def __init__(self, model_type="mock", llm_provider=None):
        super().__init__(
            name="Translation Agent",
            specialty="translation",
            capabilities=["translate", "localize", "cultural_adapt"],
            model_type=model_type,
            llm_provider=llm_provider,
        )

    async def process_task(self, task):
        self.update_status("translating")
        result = await self._llm_generate(
            f"Translate: {task.get('text')}",
            "You are a professional translator."
        )
        self.update_status("idle")
        return {"translation": result, "status": "completed"}
```

Then register it in `src/main.py`'s `agent_map`:
```python
agent_map = {
    "research": ResearchAgent,
    "writing": CreativeWriterAgent,
    "design": DesignAgent,
    "analysis": AnalysisAgent,
    "translation": TranslationAgent,  # Add here
}
```

### Add a New LLM Provider

Implement the `LLMProvider` interface:
```python
class AnthropicProvider(LLMProvider):
    async def generate(self, prompt, system="", max_tokens=2048, temperature=0.7):
        # Call Anthropic API
        ...
```

Register in `create_provider()` factory function.
