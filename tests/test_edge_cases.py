"""
Edge case and regression tests for Catalyst Agent Mesh
"""

import asyncio
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.mesh.agent_mesh import AgentMesh
from src.agents.creative_agents import (
    ResearchAgent, CreativeWriterAgent, DesignAgent, AnalysisAgent,
    MockProvider, create_provider, LLMProvider
)
from src.config import MeshConfig
from src.mesh.pipeline_executor import PipelineStage


# ========== Config Tests ==========

class TestMeshConfig:
    def test_default_config(self):
        cfg = MeshConfig()
        assert cfg.default_provider == "mock"
        assert cfg.port == 8000
        assert cfg.max_workers == 10

    def test_from_env_defaults(self):
        cfg = MeshConfig.from_env()
        assert cfg.default_provider == "mock"

    def test_from_env_override(self, monkeypatch):
        monkeypatch.setenv("MESH_PORT", "9000")
        monkeypatch.setenv("MESH_DEBUG", "true")
        cfg = MeshConfig.from_env()
        assert cfg.port == 9000
        assert cfg.debug is True


# ========== PipelineStage Unit Tests ==========

class TestPipelineStage:
    def test_add_task_returns_id(self):
        stage = PipelineStage("Test", "research", ["research"])
        tid = stage.add_task({"query": "x"})
        assert isinstance(tid, str) and len(tid) > 0

    def test_add_task_preserves_params(self):
        stage = PipelineStage("Test", "research", ["research"], parameters={"depth": "deep"})
        stage.add_task({"query": "x"})
        task = stage.tasks[0]
        assert task["parameters"]["depth"] == "deep"
        assert task["parameters"]["query"] == "x"

    def test_add_task_overrides_stage_param(self):
        stage = PipelineStage("Test", "research", ["research"], parameters={"depth": "deep"})
        stage.add_task({"depth": "shallow", "query": "x"})
        assert stage.tasks[0]["parameters"]["depth"] == "shallow"

    def test_multiple_tasks(self):
        stage = PipelineStage("Test", "research", ["research"])
        for i in range(5):
            stage.add_task({"query": f"q{i}"})
        assert len(stage.tasks) == 5

    def test_default_status(self):
        stage = PipelineStage("Test", "research", ["research"])
        assert stage.status == "pending"


# ========== Mesh Edge Cases ==========

class TestMeshEdgeCases:
    def test_unregister_nonexistent(self):
        mesh = AgentMesh()
        mesh.unregister_agent("nonexistent-id")  # should not raise

    def test_find_specialty_empty(self):
        mesh = AgentMesh()
        assert mesh.find_agents_by_specialty("research") == []

    def test_find_capability_empty(self):
        mesh = AgentMesh()
        assert mesh.find_agents_by_capability("content_generation") == []

    def test_get_available_empty(self):
        mesh = AgentMesh()
        assert mesh.get_available_agents() == []

    def test_mesh_status_empty(self):
        mesh = AgentMesh()
        status = mesh.get_mesh_status()
        assert status["total_agents"] == 0
        assert status["total_tasks"] == 0

    @pytest.mark.asyncio
    async def test_execute_task_general_type(self):
        mesh = AgentMesh()
        mesh.register_agent(ResearchAgent(model_type="mock"))
        result = await mesh.execute_task({"type": "general", "query": "test"})
        # "general" type doesn't match any select_agents_for_task branch => empty list
        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_execute_task_design(self):
        mesh = AgentMesh()
        mesh.register_agent(DesignAgent(model_type="mock"))
        result = await mesh.execute_task({"type": "design", "concept": "UI"})
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_execute_task_analysis(self):
        mesh = AgentMesh()
        mesh.register_agent(AnalysisAgent(model_type="mock"))
        result = await mesh.execute_task({"type": "analysis", "data": {"x": 1}})
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_execute_collaborative_task(self):
        mesh = AgentMesh()
        mesh.register_agent(ResearchAgent(model_type="mock"))
        mesh.register_agent(AnalysisAgent(model_type="mock"))
        result = await mesh.execute_task({"type": "collaborative"})
        assert result["status"] == "completed"

    def test_connections_management(self):
        mesh = AgentMesh()
        class FakeConn:
            pass
        c1 = FakeConn()
        c2 = FakeConn()
        mesh.add_connection(c1)
        mesh.add_connection(c2)
        assert len(mesh.connections) == 2
        mesh.remove_connection(c1)
        assert len(mesh.connections) == 1
        # removing again is safe
        mesh.remove_connection(c1)
        assert len(mesh.connections) == 1


# ========== Agent Stats & State ==========

class TestAgentStats:
    def test_get_stats(self):
        agent = ResearchAgent(model_type="mock")
        stats = agent.get_stats()
        assert stats["specialty"] == "research"
        assert stats["task_count"] == 0
        assert stats["error_count"] == 0

    @pytest.mark.asyncio
    async def test_task_count_increments(self):
        agent = ResearchAgent(model_type="mock")
        await agent.process_task({"query": "q1"})
        await agent.process_task({"query": "q2"})
        assert agent._task_count == 2

    def test_set_llm(self):
        agent = ResearchAgent(model_type="mock")
        new_provider = MockProvider()
        agent.set_llm(new_provider)
        assert agent._llm is new_provider

    @pytest.mark.asyncio
    async def test_collaborate_excludes_self(self):
        r = ResearchAgent(model_type="mock")
        w = CreativeWriterAgent(model_type="mock")
        result = await r.collaborate({"query": "x"}, [r, w])
        assert r.name not in result["collaborated_with"]
        assert w.name in result["collaborated_with"]


# ========== Pipeline Edge Cases ==========

class TestPipelineEdgeCases:
    @pytest.mark.asyncio
    async def test_pipeline_empty_stages(self):
        mesh = AgentMesh()
        pid = await mesh.create_pipeline("Empty", stages_config=[])
        result = await mesh.execute_pipeline(pid, {})
        assert result["status"] == "completed"
        assert result["total_stages"] == 0

    @pytest.mark.asyncio
    async def test_pipeline_stage_no_agents(self):
        mesh = AgentMesh()  # empty - no agents registered
        pid = await mesh.create_pipeline("No Agents", stages_config=[
            {"name": "S1", "task_type": "research", "agents_needed": ["research"]}
        ])
        pipeline = mesh.pipeline_executor.active_pipelines[pid]
        pipeline["stages"][0].add_task({"query": "x"})
        result = await mesh.execute_pipeline(pid, {})
        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_pipeline_status_not_found(self):
        mesh = AgentMesh()
        status = mesh.get_pipeline_status("nonexistent")
        assert status["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_cancel_not_found(self):
        mesh = AgentMesh()
        result = mesh.cancel_pipeline("nonexistent")
        assert result["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_add_task_to_pipeline_stage_errors(self):
        mesh = AgentMesh()
        with pytest.raises(ValueError, match="Pipeline .* not found"):
            mesh.add_task_to_pipeline_stage("bad-id", "bad-stage", {})

    @pytest.mark.asyncio
    async def test_pipeline_statistics_empty(self):
        mesh = AgentMesh()
        stats = mesh.get_pipeline_statistics()
        assert stats["total_pipelines"] == 0
        assert stats["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_stage_with_no_tasks(self):
        mesh = AgentMesh()
        mesh.register_agent(ResearchAgent(model_type="mock"))
        pid = await mesh.create_pipeline("No Tasks", stages_config=[
            {"name": "S1", "task_type": "research", "agents_needed": ["research"]}
        ])
        # Don't add any tasks to the stage
        result = await mesh.execute_pipeline(pid, {})
        assert result["status"] == "completed"


# ========== Workflow Edge Cases ==========

class TestWorkflowEdgeCases:
    @pytest.mark.asyncio
    async def test_workflow_with_failing_step(self, monkeypatch):
        mesh = AgentMesh()
        # Register agents but make the task fail by using empty mesh
        wid = mesh.create_workflow({
            "name": "Fail Test",
            "steps": [
                {"type": "research", "parameters": {"query": "AI"}},
            ]
        })
        # No agents registered => task will fail
        result = await mesh.execute_workflow(wid, {"query": "AI"})
        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_multi_step_workflow(self):
        mesh = AgentMesh()
        mesh.register_agent(ResearchAgent(model_type="mock"))
        mesh.register_agent(CreativeWriterAgent(model_type="mock"))
        wid = mesh.create_workflow({
            "name": "Two Step",
            "steps": [
                {"type": "research", "parameters": {"query": "AI"}},
                {"type": "content_creation", "parameters": {"topic": "AI"}},
            ]
        })
        result = await mesh.execute_workflow(wid, {"query": "AI"})
        assert result["status"] == "completed"
        assert result["steps_completed"] == 2
