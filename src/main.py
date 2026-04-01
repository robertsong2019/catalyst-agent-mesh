"""
Catalyst Agent Mesh API Server
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import json
import uuid
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from mesh.agent_mesh import AgentMesh
from agents.creative_agents import (
    CreativeAgent, ResearchAgent, CreativeWriterAgent,
    DesignAgent, AnalysisAgent, create_provider, LLMProvider
)

logger = logging.getLogger(__name__)

# --- Pydantic Models ---
class AgentCreateRequest(BaseModel):
    name: str
    specialty: str
    capabilities: List[str] = []
    model_type: str = "mock"

class TaskCreateRequest(BaseModel):
    title: str
    description: str = ""
    task_type: str = "general"
    parameters: Dict[str, Any] = {}

class WorkflowCreateRequest(BaseModel):
    name: str
    description: str = ""
    steps: List[Dict[str, Any]] = []

class PipelineCreateRequest(BaseModel):
    name: str
    description: str = ""
    stages: List[Dict[str, Any]] = []

class PipelineExecuteRequest(BaseModel):
    input_data: Dict[str, Any] = {}

# --- Global State ---
mesh: Optional[AgentMesh] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mesh
    mesh = AgentMesh()
    logger.info("Catalyst Agent Mesh initialized")
    yield
    logger.info("Catalyst Agent Mesh shutting down")

app = FastAPI(title="Catalyst Agent Mesh API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Agent endpoints ---
@app.get("/agents")
async def list_agents():
    return {"agents": [a.to_dict() for a in mesh.agents.values()]}

@app.post("/agents")
async def create_agent(req: AgentCreateRequest):
    """Create and register a new agent"""
    agent_map = {
        "research": ResearchAgent,
        "writing": CreativeWriterAgent,
        "design": DesignAgent,
        "analysis": AnalysisAgent,
    }
    cls = agent_map.get(req.specialty)
    if cls is None:
        raise HTTPException(400, f"Unknown specialty: {req.specialty}. Available: {list(agent_map.keys())}")
    agent = cls(model_type=req.model_type)
    if req.name:
        agent.name = req.name
    mesh.register_agent(agent)
    return {"id": agent.id, "agent": agent.to_dict()}

@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    if agent_id not in mesh.agents:
        raise HTTPException(404, "Agent not found")
    return mesh.agents[agent_id].to_dict()

@app.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    if agent_id not in mesh.agents:
        raise HTTPException(404, "Agent not found")
    mesh.unregister_agent(agent_id)
    return {"status": "deleted"}

# --- Task endpoints ---
@app.get("/tasks")
async def list_tasks():
    return {"tasks": list(mesh.tasks.values())}

@app.post("/tasks")
async def create_and_execute_task(req: TaskCreateRequest):
    task = {
        "title": req.title,
        "description": req.description,
        "type": req.task_type,
        **req.parameters,
    }
    result = await mesh.execute_task(task)
    return result

# --- Workflow endpoints ---
@app.get("/workflows")
async def list_workflows():
    return {"workflows": list(mesh.workflows.values())}

@app.post("/workflows")
async def create_workflow(req: WorkflowCreateRequest):
    config = {
        "name": req.name,
        "description": req.description,
        "steps": req.steps,
    }
    wid = mesh.create_workflow(config)
    return {"id": wid, "workflow": mesh.workflows[wid]}

@app.post("/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, req: PipelineExecuteRequest):
    result = await mesh.execute_workflow(workflow_id, req.input_data)
    return result

# --- Pipeline endpoints ---
@app.get("/pipelines")
async def list_pipelines():
    return {"pipelines": mesh.list_pipelines()}

@app.post("/pipelines")
async def create_pipeline(req: PipelineCreateRequest):
    pid = await mesh.create_pipeline(req.name, req.description, req.stages)
    return {"id": pid, "status": mesh.get_pipeline_status(pid)}

@app.post("/pipelines/{pipeline_id}/execute")
async def execute_pipeline(pipeline_id: str, req: PipelineExecuteRequest):
    result = await mesh.execute_pipeline(pipeline_id, req.input_data)
    return result

@app.get("/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    status = mesh.get_pipeline_status(pipeline_id)
    if status.get("status") == "not_found":
        raise HTTPException(404, "Pipeline not found")
    return status

@app.delete("/pipelines/{pipeline_id}")
async def cancel_pipeline(pipeline_id: str):
    return mesh.cancel_pipeline(pipeline_id)

# --- Stats ---
@app.get("/stats")
async def get_stats():
    mesh_status = mesh.get_mesh_status()
    pipeline_stats = mesh.get_pipeline_statistics()
    agent_stats = [a.get_stats() for a in mesh.agents.values()]
    return {
        "mesh": mesh_status,
        "pipelines": pipeline_stats,
        "agents": agent_stats,
    }

# --- Health ---
@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# --- WebSocket ---
@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    mesh.add_connection(websocket)
    try:
        # Send initial state
        await websocket.send_text(json.dumps({
            "type": "init",
            "data": mesh.get_mesh_status(),
            "timestamp": datetime.now().isoformat(),
        }))
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            # Handle commands
            if msg.get("action") == "get_status":
                await websocket.send_text(json.dumps({
                    "type": "status",
                    "data": mesh.get_mesh_status(),
                }))
    except WebSocketDisconnect:
        mesh.remove_connection(websocket)

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)
