from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json
import asyncio
from ..agents.creative_agents import CreativeAgent, ResearchAgent, CreativeWriterAgent, DesignAgent, AnalysisAgent
from .pipeline_executor import PipelineExecutor, PipelineStage

class AgentMesh:
    """Central mesh network for agent coordination"""
    
    def __init__(self):
        self.agents: Dict[str, CreativeAgent] = {}
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.pipeline_executor = PipelineExecutor(self)
        self.connections: List[Any] = []  # WebSocket or other connection types
        
    def register_agent(self, agent: CreativeAgent):
        """Register an agent in the mesh"""
        agent.set_mesh(self)
        self.agents[agent.id] = agent
        self.broadcast_agent_update(agent)
        print(f"Agent {agent.name} registered successfully")
        
    def unregister_agent(self, agent_id: str):
        """Unregister an agent from the mesh"""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            del self.agents[agent_id]
            self.broadcast_agent_update({
                "type": "agent_removed",
                "data": {"id": agent_id, "name": agent.name}
            })
            print(f"Agent {agent.name} unregistered")
            
    def find_agents_by_specialty(self, specialty: str) -> List[CreativeAgent]:
        """Find agents by specialty"""
        return [agent for agent in self.agents.values() if agent.specialty == specialty]
        
    def find_agents_by_capability(self, capability: str) -> List[CreativeAgent]:
        """Find agents by capability"""
        return [agent for agent in self.agents.values() if capability in agent.capabilities]
        
    def get_available_agents(self) -> List[CreativeAgent]:
        """Get all available (idle) agents"""
        return [agent for agent in self.agents.values() if agent.status == "idle"]
        
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task using available agents"""
        task_id = str(uuid.uuid4())
        task["id"] = task_id
        task["created_at"] = datetime.now().isoformat()
        task["status"] = "pending"
        
        self.tasks[task_id] = task
        self.broadcast_task_update(task)
        
        try:
            # Determine task type and select appropriate agents
            task_type = task.get("type", "general")
            agents_needed = self.select_agents_for_task(task_type, task)
            
            if not agents_needed:
                return {
                    "status": "failed",
                    "error": "No suitable agents found for this task",
                    "task_id": task_id
                }
            
            # Execute task with selected agents
            result = await self.execute_with_agents(task, agents_needed)
            
            # Update task status
            task["status"] = "completed"
            task["result"] = result
            task["completed_at"] = datetime.now().isoformat()
            
            self.tasks[task_id] = task
            self.broadcast_task_update(task)
            
            return result
            
        except Exception as e:
            task["status"] = "failed"
            task["error"] = str(e)
            task["completed_at"] = datetime.now().isoformat()
            
            self.tasks[task_id] = task
            self.broadcast_task_update(task)
            
            return {
                "status": "failed",
                "error": str(e),
                "task_id": task_id
            }
            
    def select_agents_for_task(self, task_type: str, task: Dict[str, Any]) -> List[CreativeAgent]:
        """Select appropriate agents for a task based on type and requirements"""
        selected_agents = []
        
        if task_type == "content_creation":
            # Research agent for background research
            research_agents = self.find_agents_by_specialty("research")
            if research_agents:
                selected_agents.append(research_agents[0])
            
            # Writer agent for content generation
            writer_agents = self.find_agents_by_specialty("writing")
            if writer_agents:
                selected_agents.append(writer_agents[0])
            
            # Editor agent for refinement
            editor_agents = self.find_agents_by_specialty("editing")
            if editor_agents:
                selected_agents.append(editor_agents[0])
                
        elif task_type == "design":
            design_agents = self.find_agents_by_specialty("design")
            if design_agents:
                selected_agents.append(design_agents[0])
                
        elif task_type == "research":
            research_agents = self.find_agents_by_specialty("research")
            if research_agents:
                selected_agents.append(research_agents[0])
                
        elif task_type == "analysis":
            analysis_agents = self.find_agents_by_specialty("analysis")
            if analysis_agents:
                selected_agents.append(analysis_agents[0])
                
        elif task_type == "collaborative":
            # For collaborative tasks, select multiple capable agents
            capable_agents = self.get_available_agents()[:3]  # Use first 3 available
            selected_agents = capable_agents
            
        return selected_agents
        
    async def execute_with_agents(self, task: Dict[str, Any], agents: List[CreativeAgent]) -> Dict[str, Any]:
        """Execute a task with the selected agents"""
        task["status"] = "executing"
        self.broadcast_task_update(task)
        
        results = {}
        
        # Update agent status
        for agent in agents:
            agent.update_status("executing")
            
        # Execute the task
        if len(agents) == 1:
            # Single agent execution
            result = await agents[0].process_task(task)
            results[agents[0].id] = result
        else:
            # Multi-agent collaboration
            result = await agents[0].collaborate(task, agents)
            results[agents[0].id] = result
            
        # Update agent status
        for agent in agents:
            agent.update_status("idle")
            
        return {
            "status": "completed",
            "agents_used": [agent.name for agent in agents],
            "results": results,
            "task_id": task["id"]
        }
        
    def create_workflow(self, workflow_config: Dict[str, Any]) -> str:
        """Create a reusable workflow"""
        workflow_id = str(uuid.uuid4())
        workflow = {
            "id": workflow_id,
            "name": workflow_config.get("name", "Untitled Workflow"),
            "description": workflow_config.get("description", ""),
            "agents_needed": workflow_config.get("agents_needed", []),
            "steps": workflow_config.get("steps", []),
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        self.workflows[workflow_id] = workflow
        self.broadcast_workflow_update(workflow)
        
        return workflow_id
        
    async def execute_workflow(self, workflow_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a predefined workflow"""
        if workflow_id not in self.workflows:
            return {
                "status": "failed",
                "error": "Workflow not found"
            }
            
        workflow = self.workflows[workflow_id]
        results = {}
        
        # Execute each step
        for i, step in enumerate(workflow["steps"]):
            step_result = await self.execute_task({
                "type": step.get("type", "general"),
                "step": i + 1,
                "total_steps": len(workflow["steps"]),
                **task_data,
                **step.get("parameters", {})
            })
            
            results[f"step_{i}"] = step_result
            
            # Check if step failed
            if step_result.get("status") == "failed":
                return {
                    "status": "failed",
                    "error": f"Step {i + 1} failed",
                    "failed_step": i + 1,
                    "results": results
                }
                
        return {
            "status": "completed",
            "workflow_id": workflow_id,
            "results": results,
            "steps_completed": len(workflow["steps"])
        }
        
    def get_mesh_status(self) -> Dict[str, Any]:
        """Get overall mesh status"""
        return {
            "total_agents": len(self.agents),
            "available_agents": len([a for a in self.agents.values() if a.status == "idle"]),
            "busy_agents": len([a for a in self.agents.values() if a.status == "executing"]),
            "total_tasks": len(self.tasks),
            "active_tasks": len([t for t in self.tasks.values() if t.get("status") == "executing"]),
            "total_workflows": len(self.workflows),
            "timestamp": datetime.now().isoformat()
        }
        
    def broadcast_agent_update(self, data: Any):
        """Broadcast agent updates to all connections"""
        message = {
            "type": "agent_update",
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        for connection in self.connections:
            asyncio.create_task(self.send_message(connection, message))
            
    def broadcast_task_update(self, task: Dict[str, Any]):
        """Broadcast task updates to all connections"""
        message = {
            "type": "task_update",
            "data": task,
            "timestamp": datetime.now().isoformat()
        }
        
        for connection in self.connections:
            asyncio.create_task(self.send_message(connection, message))
            
    def broadcast_workflow_update(self, workflow: Dict[str, Any]):
        """Broadcast workflow updates to all connections"""
        message = {
            "type": "workflow_update",
            "data": workflow,
            "timestamp": datetime.now().isoformat()
        }
        
        for connection in self.connections:
            asyncio.create_task(self.send_message(connection, message))
            
    async def send_message(self, connection, message: Dict[str, Any]):
        """Send message to a connection"""
        try:
            if hasattr(connection, 'send_text'):
                await connection.send_text(json.dumps(message))
            elif hasattr(connection, 'send'):
                connection.send(json.dumps(message))
        except Exception as e:
            # Remove failed connection
            if connection in self.connections:
                self.connections.remove(connection)
                
    def add_connection(self, connection):
        """Add a new connection (WebSocket, etc.)"""
        self.connections.append(connection)
        
    def add_task_to_pipeline_stage(self, pipeline_id: str, stage_name: str, task_data: Dict[str, Any]) -> str:
        """Add a task to a specific pipeline stage"""
        if pipeline_id not in self.pipeline_executor.active_pipelines:
            raise ValueError(f"Pipeline {pipeline_id} not found")
            
        pipeline = self.pipeline_executor.active_pipelines[pipeline_id]
        
        # Find the stage by name
        target_stage = None
        for stage in pipeline["stages"]:
            if stage.name == stage_name:
                target_stage = stage
                break
                
        if not target_stage:
            raise ValueError(f"Stage {stage_name} not found in pipeline {pipeline_id}")
            
        # Add task to the stage
        return target_stage.add_task(task_data)
        
    def remove_connection(self, connection):
        """Remove a connection"""
        if connection in self.connections:
            self.connections.remove(connection)
            
    # Pipeline Execution Methods
    async def create_pipeline(self, name: str, description: str = "", 
                             stages_config: List[Dict[str, Any]] = None) -> str:
        """Create a new pipeline for parallel execution"""
        return await self.pipeline_executor.create_pipeline(name, description, stages_config)
        
    async def execute_pipeline(self, pipeline_id: str, input_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a pipeline with parallel stage execution"""
        return await self.pipeline_executor.execute_pipeline(pipeline_id, input_data)
        
    def get_pipeline_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Get status of a specific pipeline"""
        return self.pipeline_executor.get_pipeline_status(pipeline_id)
        
    def cancel_pipeline(self, pipeline_id: str) -> Dict[str, Any]:
        """Cancel a running pipeline"""
        return self.pipeline_executor.cancel_pipeline(pipeline_id)
        
    def list_pipelines(self) -> List[Dict[str, Any]]:
        """List all active pipelines"""
        return self.pipeline_executor.list_pipelines()
        
    def get_pipeline_statistics(self) -> Dict[str, Any]:
        """Get overall pipeline execution statistics"""
        return self.pipeline_executor.get_pipeline_statistics()
        
    async def execute_content_creation_pipeline(self, topic: str, style: str = "professional") -> Dict[str, Any]:
        """Execute a complete content creation pipeline with parallel stages"""
        # Define pipeline stages
        stages_config = [
            {
                "name": "Research",
                "task_type": "research",
                "agents_needed": ["research"],
                "max_concurrent": 2,
                "parameters": {
                    "query": topic,
                    "sources": ["web", "academic"],
                    "depth": "comprehensive"
                }
            },
            {
                "name": "Content Generation",
                "task_type": "content_creation", 
                "agents_needed": ["writing"],
                "max_concurrent": 3,
                "parameters": {
                    "topic": topic,
                    "style": style,
                    "content_type": "article"
                }
            },
            {
                "name": "Editing & Refinement",
                "task_type": "editing",
                "agents_needed": ["editing"],
                "max_concurrent": 2,
                "parameters": {
                    "style": style,
                    "focus": "quality",
                    "iterations": 2
                }
            }
        ]
        
        # Create pipeline
        pipeline_id = await self.create_pipeline(
            name=f"Content Creation - {topic}",
            description=f"Complete content creation pipeline for {topic} in {style} style",
            stages_config=stages_config
        )
        
        # Add research tasks
        research_stage = self.pipeline_executor.stage_executors[[s.id for s in self.pipeline_executor.active_pipelines[pipeline_id]["stages"]][0]]
        for i in range(2):  # Multiple research tasks for parallel execution
            research_stage.add_task({
                "query": f"{topic} aspect {i+1}",
                "focus": f"subtopic_{i+1}"
            })
            
        # Add content generation tasks
        content_stage = self.pipeline_executor.stage_executors[[s.id for s in self.pipeline_executor.active_pipelines[pipeline_id]["stages"]][1]]
        content_stage.add_task({
            "section": "introduction",
            "length": "short"
        })
        content_stage.add_task({
            "section": "main_content", 
            "length": "detailed"
        })
        content_stage.add_task({
            "section": "conclusion",
            "length": "medium"
        })
        
        # Execute pipeline
        result = await self.execute_pipeline(pipeline_id, {"topic": topic, "style": style})
        
        return result
        
    async def execute_research_pipeline(self, research_topic: str, analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """Execute a research pipeline with parallel analysis"""
        stages_config = [
            {
                "name": "Data Collection",
                "task_type": "research",
                "agents_needed": ["research"],
                "max_concurrent": 4,
                "parameters": {
                    "query": research_topic,
                    "sources": ["web", "academic", "industry"],
                    "depth": "comprehensive"
                }
            },
            {
                "name": "Parallel Analysis",
                "task_type": "analysis",
                "agents_needed": ["analysis"],
                "max_concurrent": 3,
                "parameters": {
                    "analysis_type": analysis_type,
                    "focus": ["trends", "patterns", "insights"]
                }
            },
            {
                "name": "Synthesis",
                "task_type": "content_creation",
                "agents_needed": ["writing"],
                "max_concurrent": 2,
                "parameters": {
                    "content_type": "report",
                    "style": "academic",
                    "synthesis": True
                }
            }
        ]
        
        pipeline_id = await self.create_pipeline(
            name=f"Research Pipeline - {research_topic}",
            description=f"Comprehensive research pipeline for {research_topic}",
            stages_config=stages_config
        )
        
        # Add multiple data collection tasks
        data_stage = self.pipeline_executor.stage_executors[[s.id for s in self.pipeline_executor.active_pipelines[pipeline_id]["stages"]][0]]
        for i in range(4):
            data_stage.add_task({
                "focus_area": f"aspect_{i+1}",
                "data_type": "mixed"
            })
            
        # Add analysis tasks
        analysis_stage = self.pipeline_executor.stage_executors[[s.id for s in self.pipeline_executor.active_pipelines[pipeline_id]["stages"]][1]]
        for focus in ["trends", "patterns", "insights"]:
            analysis_stage.add_task({
                "focus_area": focus,
                "depth": "deep"
            })
            
        return await self.execute_pipeline(pipeline_id, {"research_topic": research_topic, "analysis_type": analysis_type})

# Pre-built workflows
CONTENT_CREATION_WORKFLOW = {
    "name": "Content Creation Workflow",
    "description": "Complete content creation from research to final output",
    "agents_needed": ["research", "writing", "editing"],
    "steps": [
        {
            "type": "research",
            "parameters": {
                "depth": "comprehensive",
                "sources": ["web", "academic"]
            }
        },
        {
            "type": "content_creation",
            "parameters": {
                "content_type": "article",
                "style": "professional"
            }
        },
        {
            "type": "editing",
            "parameters": {
                "focus": "quality",
                "iterations": 2
            }
        }
    ]
}

DESIGN_WORKFLOW = {
    "name": "Design Workflow",
    "description": "Complete design process from concept to implementation",
    "agents_needed": ["design"],
    "steps": [
        {
            "type": "design",
            "parameters": {
                "design_type": "ui",
                "target_platform": "web"
            }
        }
    ]
}

RESEARCH_WORKFLOW = {
    "name": "Research Workflow",
    "description": "Comprehensive research and analysis",
    "agents_needed": ["research", "analysis"],
    "steps": [
        {
            "type": "research",
            "parameters": {
                "scope": "comprehensive",
                "sources": ["web", "academic", "industry"]
            }
        },
        {
            "type": "analysis",
            "parameters": {
                "analysis_type": "comprehensive",
                "focus": "insights"
            }
        }
    ]
}