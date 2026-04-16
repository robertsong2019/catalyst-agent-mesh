"""
Agent Pipeline Parallel Execution Module
Handles parallel execution of tasks in pipeline stages
"""

import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

class PipelineStage:
    """Represents a single stage in a pipeline"""
    
    def __init__(self, name: str, task_type: str, agents_needed: List[str], 
                 parameters: Dict[str, Any] = None, max_concurrent: int = 3):
        self.id = str(uuid.uuid4())
        self.name = name
        self.task_type = task_type
        self.agents_needed = agents_needed
        self.parameters = parameters or {}
        self.max_concurrent = max_concurrent
        self.tasks: List[Dict[str, Any]] = []
        self.results: List[Dict[str, Any]] = []
        self.status = "pending"
        
    def add_task(self, task_data: Dict[str, Any]) -> str:
        """Add a task to this pipeline stage"""
        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "stage_id": self.id,
            "stage_name": self.name,
            "task_type": self.task_type,
            "parameters": {**self.parameters, **task_data},
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        self.tasks.append(task)
        return task_id

class PipelineExecutor:
    """Handles parallel execution of pipeline stages"""
    
    def __init__(self, agent_mesh, max_workers: int = 10):
        self.agent_mesh = agent_mesh
        self.max_workers = max_workers
        self.active_pipelines: Dict[str, Dict[str, Any]] = {}
        self.stage_executors: Dict[str, PipelineStage] = {}
        
    async def create_pipeline(self, name: str, description: str = "", 
                             stages_config: List[Dict[str, Any]] = None) -> str:
        """Create a new pipeline"""
        pipeline_id = str(uuid.uuid4())
        
        pipeline = {
            "id": pipeline_id,
            "name": name,
            "description": description,
            "stages": [],
            "status": "created",
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "results": {}
        }
        
        # Create stages
        stages = []
        for i, stage_config in enumerate(stages_config or []):
            stage = PipelineStage(
                name=stage_config.get("name", f"Stage {i+1}"),
                task_type=stage_config.get("task_type", "general"),
                agents_needed=stage_config.get("agents_needed", []),
                parameters=stage_config.get("parameters", {}),
                max_concurrent=stage_config.get("max_concurrent", 3)
            )
            self.stage_executors[stage.id] = stage
            stages.append(stage)
            
        pipeline["stages"] = stages
        self.active_pipelines[pipeline_id] = pipeline
        
        return pipeline_id
        
    async def execute_pipeline(self, pipeline_id: str, input_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a pipeline with parallel stage execution"""
        if pipeline_id not in self.active_pipelines:
            return {
                "status": "failed",
                "error": "Pipeline not found"
            }
            
        pipeline = self.active_pipelines[pipeline_id]
        pipeline["status"] = "running"
        pipeline["started_at"] = datetime.now().isoformat()
        
        try:
            # Execute stages sequentially
            for stage in pipeline["stages"]:
                stage_result = await self.execute_stage(stage, input_data or {})
                pipeline["results"][stage.name] = stage_result
                
                # Prepare input for next stage
                if stage_result.get("status") == "completed":
                    input_data = stage_result.get("output", input_data)
                else:
                    # Stop pipeline if stage fails
                    pipeline["status"] = "failed"
                    pipeline["completed_at"] = datetime.now().isoformat()
                    return {
                        "status": "failed",
                        "error": f"Stage {stage.name} failed",
                        "failed_stage": stage.name,
                        "results": pipeline["results"]
                    }
                    
            pipeline["status"] = "completed"
            pipeline["completed_at"] = datetime.now().isoformat()
            
            return {
                "status": "completed",
                "pipeline_id": pipeline_id,
                "results": pipeline["results"],
                "total_stages": len(pipeline["stages"]),
                "execution_time": self._calculate_execution_time(pipeline)
            }
            
        except Exception as e:
            pipeline["status"] = "failed"
            pipeline["completed_at"] = datetime.now().isoformat()
            return {
                "status": "failed",
                "error": str(e),
                "pipeline_id": pipeline_id,
                "results": pipeline["results"]
            }
            
    async def execute_stage(self, stage: PipelineStage, input_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a single pipeline stage with parallel task execution"""
        stage.status = "running"
        
        # Get available agents for this stage
        available_agents = []
        for agent_type in stage.agents_needed:
            if agent_type == "general":
                available_agents.extend(self.agent_mesh.get_available_agents())
            else:
                available_agents.extend(self.agent_mesh.find_agents_by_specialty(agent_type))
                
        if not available_agents:
            return {
                "status": "failed",
                "error": f"No available agents for stage {stage.name}",
                "stage_name": stage.name
            }
            
        # Distribute tasks among agents
        tasks_per_agent = max(1, len(stage.tasks) // len(available_agents))
        
        # Create parallel tasks
        tasks_to_execute = []
        for i, task in enumerate(stage.tasks):
            # Assign task to an agent (round-robin)
            agent = available_agents[i % len(available_agents)]
            
            task_with_input = {
                **task,
                "input": input_data,
                "assigned_agent": agent.name,
                "assigned_agent_id": agent.id
            }
            tasks_to_execute.append(task_with_input)
            
        # Execute tasks in parallel
        stage_results = await self._execute_tasks_in_parallel(tasks_to_execute, stage.max_concurrent)
        
        # Combine results
        combined_result = {
            "status": "completed",
            "stage_name": stage.name,
            "tasks_executed": len(tasks_to_execute),
            "successful_tasks": len([r for r in stage_results if r.get("status") == "completed"]),
            "failed_tasks": len([r for r in stage_results if r.get("status") == "failed"]),
            "results": stage_results,
            "output": self._combine_stage_results(stage_results),
            "execution_time": datetime.now().isoformat()
        }
        
        stage.status = "completed"
        stage.results = stage_results
        
        return combined_result
        
    async def _execute_tasks_in_parallel(self, tasks: List[Dict[str, Any]], max_concurrent: int) -> List[Dict[str, Any]]:
        """Execute multiple tasks in parallel with concurrency control"""
        results = []
        
        # Use semaphore to control concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_single_task(task: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                agent = None
                try:
                    # Find the assigned agent
                    assigned_agent_id = task["assigned_agent_id"]
                    agent = self.agent_mesh.agents.get(assigned_agent_id)
                    
                    if not agent:
                        return {
                            "status": "failed",
                            "error": f"Agent {assigned_agent_id} not found",
                            "task_id": task["id"]
                        }
                    
                    # Update agent status
                    agent.update_status("executing")
                    
                    # Execute task
                    result = await agent.process_task(task["input"])
                    
                    # Update agent status
                    agent.update_status("idle")
                    
                    return {
                        "status": "completed",
                        "task_id": task["id"],
                        "agent_name": agent.name,
                        "result": result,
                        "execution_time": datetime.now().isoformat()
                    }
                    
                except Exception as e:
                    # Update agent status even if task fails
                    if agent:
                        agent.update_status("idle")
                        
                    return {
                        "status": "failed",
                        "error": str(e),
                        "task_id": task["id"],
                        "execution_time": datetime.now().isoformat()
                    }
        
        # Execute all tasks concurrently
        task_coroutines = [execute_single_task(task) for task in tasks]
        task_results = await asyncio.gather(*task_coroutines, return_exceptions=True)
        
        # Process results
        for result in task_results:
            if isinstance(result, Exception):
                results.append({
                    "status": "failed",
                    "error": str(result),
                    "execution_time": datetime.now().isoformat()
                })
            else:
                results.append(result)
                
        return results
        
    def _combine_stage_results(self, stage_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine results from multiple tasks in a stage"""
        successful_results = [r for r in stage_results if r.get("status") == "completed"]
        failed_results = [r for r in stage_results if r.get("status") == "failed"]
        
        combined = {
            "total_tasks": len(stage_results),
            "successful_tasks": len(successful_results),
            "failed_tasks": len(failed_results),
            "combined_data": [],
            "errors": [r.get("error", "Unknown error") for r in failed_results]
        }
        
        # Combine data from successful tasks
        for result in successful_results:
            if "result" in result:
                combined["combined_data"].append(result["result"])
                
        return combined
        
    def _calculate_execution_time(self, pipeline: Dict[str, Any]) -> str:
        """Calculate total execution time for pipeline"""
        if pipeline["started_at"] and pipeline["completed_at"]:
            start = datetime.fromisoformat(pipeline["started_at"])
            end = datetime.fromisoformat(pipeline["completed_at"])
            return str(end - start)
        return "N/A"
        
    def get_pipeline_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Get status of a specific pipeline"""
        if pipeline_id not in self.active_pipelines:
            return {
                "status": "not_found",
                "error": "Pipeline not found"
            }
            
        pipeline = self.active_pipelines[pipeline_id]
        
        # Calculate stage status
        stage_status = {}
        for stage in pipeline["stages"]:
            stage_status[stage.name] = stage.status
            
        return {
            "pipeline_id": pipeline_id,
            "name": pipeline["name"],
            "status": pipeline["status"],
            "stages": stage_status,
            "created_at": pipeline["created_at"],
            "started_at": pipeline["started_at"],
            "completed_at": pipeline["completed_at"],
            "total_stages": len(pipeline["stages"]),
            "results_summary": self._generate_results_summary(pipeline["results"])
        }
        
    def _generate_results_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of pipeline results"""
        summary = {
            "total_stages": len(results),
            "successful_stages": 0,
            "failed_stages": 0,
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0
        }
        
        for stage_name, stage_result in results.items():
            if stage_result.get("status") == "completed":
                summary["successful_stages"] += 1
                if "tasks_executed" in stage_result:
                    summary["total_tasks"] += stage_result["tasks_executed"]
                    summary["successful_tasks"] += stage_result.get("successful_tasks", 0)
                    summary["failed_tasks"] += stage_result.get("failed_tasks", 0)
            else:
                summary["failed_stages"] += 1
                
        return summary
        
    def cancel_pipeline(self, pipeline_id: str) -> Dict[str, Any]:
        """Cancel a running pipeline"""
        if pipeline_id not in self.active_pipelines:
            return {
                "status": "not_found",
                "error": "Pipeline not found"
            }
            
        pipeline = self.active_pipelines[pipeline_id]
        pipeline["status"] = "cancelled"
        pipeline["completed_at"] = datetime.now().isoformat()
        
        return {
            "status": "cancelled",
            "pipeline_id": pipeline_id,
            "message": "Pipeline has been cancelled"
        }
        
    def list_pipelines(self) -> List[Dict[str, Any]]:
        """List all active pipelines"""
        pipelines = []
        for pipeline_id, pipeline in self.active_pipelines.items():
            pipelines.append({
                "id": pipeline_id,
                "name": pipeline["name"],
                "status": pipeline["status"],
                "total_stages": len(pipeline["stages"]),
                "created_at": pipeline["created_at"],
                "started_at": pipeline["started_at"],
                "completed_at": pipeline["completed_at"]
            })
        return pipelines
        
    def get_active_pipelines_count(self) -> int:
        """Get count of active pipelines"""
        return len([p for p in self.active_pipelines.values() if p["status"] in ["running", "created"]])
        
    def get_pipeline_statistics(self) -> Dict[str, Any]:
        """Get overall pipeline execution statistics"""
        total_pipelines = len(self.active_pipelines)
        completed_pipelines = len([p for p in self.active_pipelines.values() if p["status"] == "completed"])
        failed_pipelines = len([p for p in self.active_pipelines.values() if p["status"] == "failed"])
        running_pipelines = len([p for p in self.active_pipelines.values() if p["status"] == "running"])
        
        return {
            "total_pipelines": total_pipelines,
            "completed_pipelines": completed_pipelines,
            "failed_pipelines": failed_pipelines,
            "running_pipelines": running_pipelines,
            "success_rate": completed_pipelines / max(1, total_pipelines) * 100
        }