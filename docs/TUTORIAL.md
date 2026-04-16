# Tutorial: Getting Started with Catalyst Agent Mesh

## What You'll Learn

In 10 minutes, you'll:
1. Start the API server
2. Create specialized agents
3. Execute tasks and workflows
4. Use pipelines for parallel processing

---

## Prerequisites

- Python 3.10+
- `pip install -r requirements.txt`

> **No LLM needed to start** — the default `mock` provider works without any external service.

---

## Step 1: Start the Server

```bash
cd catalyst-agent-mesh
uvicorn src.main:app --reload
```

Verify it's running:
```bash
curl http://localhost:8000/health
# {"status":"healthy","timestamp":"..."}
```

The interactive API docs are available at `http://localhost:8000/docs` (Swagger UI).

---

## Step 2: Create Agents

Agents are specialized workers. Create one for each role:

```bash
# Research specialist
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{"name": "Researcher", "specialty": "research", "model_type": "mock"}'

# Creative writer
curl -X POST http://localhost:8000/agents \
  -d '{"name": "Writer", "specialty": "writing", "model_type": "mock"}'

# Analyst
curl -X POST http://localhost:8000/agents \
  -d '{"name": "Analyst", "specialty": "analysis", "model_type": "mock"}'
```

Check your agents:
```bash
curl http://localhost:8000/agents
```

---

## Step 3: Execute a Task

Give a task to the mesh — it will automatically route to the right agent:

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Research AI Ethics",
    "task_type": "research",
    "parameters": {
      "query": "Ethical considerations in AI healthcare",
      "depth": "comprehensive"
    }
  }'
```

The mesh selects the research agent, executes the task, and returns results.

---

## Step 4: Create a Workflow

Workflows chain multiple steps together — research → write → edit:

```bash
# Create the workflow
curl -X POST http://localhost:8000/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Content Pipeline",
    "steps": [
      {"type": "research", "parameters": {"depth": "comprehensive"}},
      {"type": "content_creation", "parameters": {"content_type": "article", "style": "professional"}}
    ]
  }'

# Note the workflow_id from the response, then execute:
curl -X POST http://localhost:8000/workflows/{workflow_id}/execute \
  -d '{"input_data": {"topic": "AI in Healthcare", "style": "professional"}}'
```

---

## Step 5: Use Pipelines for Parallel Processing

Pipelines execute multiple tasks **concurrently** within each stage:

```bash
# Create a pipeline with parallel stages
curl -X POST http://localhost:8000/pipelines \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Parallel Research",
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
        "max_concurrent": 3
      }
    ]
  }'

# Execute
curl -X POST http://localhost:8000/pipelines/{pipeline_id}/execute \
  -d '{"input_data": {"research_topic": "AI trends"}}'
```

`max_concurrent` controls how many tasks run simultaneously within a stage.

---

## Step 6: Connect via WebSocket

For real-time updates:

```python
import asyncio
import websockets
import json

async def listen():
    async with websockets.connect("ws://localhost:8000/ws") as ws:
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            print(f"[{data['type']}] {json.dumps(data['data'], indent=2)[:200]}")

asyncio.run(listen())
```

You'll receive live updates as agents change status, tasks progress, and workflows execute.

---

## Step 7: Switch to Real LLMs

When ready to use real language models:

### Option A: Ollama (Local)
```bash
# Install and start Ollama
ollama serve
ollama pull llama3.2

# Start with Ollama
MESH_LLM_PROVIDER=ollama uvicorn src.main:app --reload
```

### Option B: OpenAI
```bash
OPENAI_API_KEY=sk-... MESH_LLM_PROVIDER=openai uvicorn src.main:app --reload
```

All agents will now use real LLMs for generation. No code changes needed.

---

## Programmatic Usage (Python)

You can also use the mesh directly in Python:

```python
import asyncio
from src.mesh.agent_mesh import AgentMesh
from src.agents.creative_agents import ResearchAgent, CreativeWriterAgent

async def main():
    mesh = AgentMesh()

    # Register agents
    mesh.register_agent(ResearchAgent(model_type="mock"))
    mesh.register_agent(CreativeWriterAgent(model_type="mock"))

    # Execute a task
    result = await mesh.execute_task({
        "type": "content_creation",
        "topic": "The Future of AI",
        "style": "engaging",
    })
    print(result)

    # Check mesh status
    print(mesh.get_mesh_status())

asyncio.run(main())
```

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Agent** | A specialized worker (research, writing, design, analysis) backed by an LLM |
| **Task** | A single unit of work routed to the appropriate agent |
| **Workflow** | A sequence of steps executed in order |
| **Pipeline** | Stages executed sequentially, with **parallel tasks within each stage** |
| **Mesh** | The central coordinator that manages agents, tasks, and communication |

---

## Next Steps

- Read the [API Reference](./API.md) for complete endpoint documentation
- Check the [Architecture Guide](./ARCHITECTURE.md) for internals
- Explore `examples/` for more usage patterns
