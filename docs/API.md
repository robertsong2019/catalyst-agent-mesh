# API Reference — Catalyst Agent Mesh

Base URL: `http://localhost:8000`

All endpoints accept and return JSON. The API is powered by FastAPI with async support.

---

## Agents

### List Agents
```
GET /agents
```
Returns all registered agents.

**Response:**
```json
{
  "agents": [
    {
      "id": "uuid",
      "name": "Research Agent",
      "specialty": "research",
      "capabilities": ["web_search", "literature_review", ...],
      "model_type": "mock",
      "status": "idle",
      "created_at": "...",
      "last_active": "...",
      "health": 1.0,
      "task_count": 0,
      "error_count": 0
    }
  ]
}
```

### Create Agent
```
POST /agents
```
Create and register a new specialized agent.

**Body:**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | _(by specialty)_ | Display name |
| `specialty` | string | **required** | One of: `research`, `writing`, `design`, `analysis` |
| `capabilities` | string[] | _(by specialty)_ | Override default capabilities |
| `model_type` | string | `"mock"` | `mock`, `ollama`, or `openai` |

**Example:**
```json
{
  "name": "My Researcher",
  "specialty": "research",
  "model_type": "ollama"
}
```

### Get Agent
```
GET /agents/{agent_id}
```

### Delete Agent
```
DELETE /agents/{agent_id}
```

---

## Tasks

### List Tasks
```
GET /tasks
```

### Create & Execute Task
```
POST /tasks
```
Creates a task, selects appropriate agents, and executes immediately.

**Body:**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `title` | string | **required** | Task title |
| `description` | string | `""` | Detailed description |
| `task_type` | string | `"general"` | `content_creation`, `design`, `research`, `analysis`, `collaborative` |
| `parameters` | object | `{}` | Task-specific parameters (passed to agent) |

**Example — Research task:**
```json
{
  "title": "AI Ethics Research",
  "task_type": "research",
  "parameters": {
    "query": "AI ethics in healthcare",
    "depth": "comprehensive",
    "focus": "privacy"
  }
}
```

**Example — Writing task:**
```json
{
  "title": "Write Article",
  "task_type": "content_creation",
  "parameters": {
    "topic": "Sustainable AI",
    "style": "professional",
    "content_type": "article"
  }
}
```

---

## Workflows

### List Workflows
```
GET /workflows
```

### Create Workflow
```
POST /workflows
```
Define a multi-step workflow.

**Body:**
```json
{
  "name": "Content Pipeline",
  "description": "Research → Write → Edit",
  "steps": [
    {"type": "research", "parameters": {"depth": "comprehensive"}},
    {"type": "content_creation", "parameters": {"content_type": "article"}},
    {"type": "editing", "parameters": {"focus": "quality"}}
  ]
}
```

### Execute Workflow
```
POST /workflows/{workflow_id}/execute
```
**Body:**
```json
{
  "input_data": {
    "topic": "AI Ethics",
    "style": "professional"
  }
}
```

---

## Pipelines

Pipelines enable **parallel execution** across stages. Each stage runs multiple tasks concurrently.

### List Pipelines
```
GET /pipelines
```

### Create Pipeline
```
POST /pipelines
```
**Body:**
```json
{
  "name": "Parallel Research",
  "description": "Multi-source parallel research",
  "stages": [
    {
      "name": "Data Collection",
      "task_type": "research",
      "agents_needed": ["research"],
      "max_concurrent": 4,
      "parameters": {"depth": "comprehensive"}
    },
    {
      "name": "Analysis",
      "task_type": "analysis",
      "agents_needed": ["analysis"],
      "max_concurrent": 3,
      "parameters": {"analysis_type": "trend"}
    }
  ]
}
```

### Execute Pipeline
```
POST /pipelines/{pipeline_id}/execute
```
**Body:**
```json
{
  "input_data": {"topic": "AI trends 2026"}
}
```

### Get Pipeline Status
```
GET /pipelines/{pipeline_id}
```

### Cancel Pipeline
```
DELETE /pipelines/{pipeline_id}
```

---

## Stats & Health

### Mesh Statistics
```
GET /stats
```
Returns agent stats, pipeline statistics, and mesh overview.

### Health Check
```
GET /health
```
```json
{"status": "healthy", "timestamp": "2026-04-12T04:00:00"}
```

---

## WebSocket

### Real-time Updates
```
WS /ws
```
Connect to receive real-time updates for agent status, task progress, and workflow changes.

**Messages received:**
| Type | Description |
|------|-------------|
| `init` | Initial mesh state on connect |
| `agent_update` | Agent registered/removed/status change |
| `task_update` | Task created/progress/completed |
| `workflow_update` | Workflow created/executed |
| `status` | Response to `get_status` command |

**Send commands:**
```json
{"action": "get_status"}
```

---

## Configuration

Configure via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MESH_LLM_PROVIDER` | `mock` | Default LLM: `mock`, `ollama`, `openai` |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `OPENAI_API_KEY` | _(none)_ | OpenAI API key |
| `MESH_HOST` | `0.0.0.0` | Server bind address |
| `MESH_PORT` | `8000` | Server port |
| `MESH_DEBUG` | `false` | Enable debug mode |
| `MESH_LOG_LEVEL` | `INFO` | Logging level |
