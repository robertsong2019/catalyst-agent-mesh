"""
Tests for PipelineExecutor - parallel pipeline execution
"""
import asyncio
import sys
import os
import pytest
import pytest_asyncio

pytest_plugins = ('pytest_asyncio',)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.mesh.pipeline_executor import PipelineExecutor, PipelineStage
from src.mesh.agent_mesh import AgentMesh
from src.agents.creative_agents import ResearchAgent, CreativeWriterAgent


@pytest.fixture
def mesh():
    m = AgentMesh()
    m.register_agent(ResearchAgent(model_type="mock"))
    m.register_agent(CreativeWriterAgent(model_type="mock"))
    return m


@pytest.fixture
def executor(mesh):
    return PipelineExecutor(mesh)


class TestPipelineStage:
    def test_stage_creation(self):
        stage = PipelineStage("test-stage", "research", ["researcher"])
        assert stage.name == "test-stage"
        assert stage.task_type == "research"
        assert stage.status == "pending"
        assert stage.tasks == []

    def test_stage_add_task(self):
        stage = PipelineStage("test-stage", "research", ["researcher"])
        task_id = stage.add_task({"query": "test"})
        assert len(stage.tasks) == 1
        assert stage.tasks[0]["id"] == task_id
        assert stage.tasks[0]["parameters"]["query"] == "test"

    def test_stage_max_concurrent_default(self):
        stage = PipelineStage("s", "general", ["agent"])
        assert stage.max_concurrent == 3

    def test_stage_custom_max_concurrent(self):
        stage = PipelineStage("s", "general", ["agent"], max_concurrent=5)
        assert stage.max_concurrent == 5


class TestPipelineExecutorCRUD:
    @pytest.mark.asyncio
    async def test_create_pipeline(self, executor):
        pid = await executor.create_pipeline("test-pipeline", stages_config=[])
        assert pid in executor.active_pipelines
        assert executor.active_pipelines[pid]["name"] == "test-pipeline"
        assert executor.active_pipelines[pid]["status"] == "created"

    @pytest.mark.asyncio
    async def test_create_pipeline_with_stages(self, executor):
        pid = await executor.create_pipeline("multi-stage", stages_config=[
            {"name": "research", "task_type": "research", "agents_needed": ["research"]},
            {"name": "writing", "task_type": "creative", "agents_needed": ["creative"]},
        ])
        pipeline = executor.active_pipelines[pid]
        assert len(pipeline["stages"]) == 2

    @pytest.mark.asyncio
    async def test_list_pipelines_empty(self, executor):
        assert executor.list_pipelines() == []

    @pytest.mark.asyncio
    async def test_list_pipelines(self, executor):
        await executor.create_pipeline("p1")
        await executor.create_pipeline("p2")
        pipelines = executor.list_pipelines()
        assert len(pipelines) == 2

    @pytest.mark.asyncio
    async def test_get_pipeline_status_not_found(self, executor):
        result = executor.get_pipeline_status("nonexistent")
        assert result["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_cancel_pipeline(self, executor):
        pid = await executor.create_pipeline("to-cancel")
        result = executor.cancel_pipeline(pid)
        assert result["status"] == "cancelled"
        assert executor.active_pipelines[pid]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_pipeline(self, executor):
        result = executor.cancel_pipeline("nonexistent")
        assert result["status"] == "not_found"


class TestPipelineStatistics:
    @pytest.mark.asyncio
    async def test_statistics_empty(self, executor):
        stats = executor.get_pipeline_statistics()
        assert stats["total_pipelines"] == 0
        assert stats["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_active_count(self, executor):
        await executor.create_pipeline("p1")
        await executor.create_pipeline("p2")
        assert executor.get_active_pipelines_count() == 2


class TestPipelineExecution:
    @pytest.mark.asyncio
    async def test_execute_nonexistent_pipeline(self, executor):
        result = await executor.execute_pipeline("nonexistent")
        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_execute_empty_pipeline(self, executor):
        pid = await executor.create_pipeline("empty", stages_config=[])
        result = await executor.execute_pipeline(pid)
        assert result["status"] == "completed"
        assert result["total_stages"] == 0
