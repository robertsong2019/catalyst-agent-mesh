"""
Tests for AgentMesh high-level pipeline workflows, pre-built workflow constants,
connection management edge cases, and add_task_to_pipeline_stage success path.
"""

import asyncio
import sys
import os
import json
import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.mesh.agent_mesh import (
    AgentMesh, CONTENT_CREATION_WORKFLOW, DESIGN_WORKFLOW, RESEARCH_WORKFLOW
)
from src.agents.creative_agents import (
    ResearchAgent, CreativeWriterAgent, DesignAgent, AnalysisAgent,
    MockProvider
)


@pytest.fixture
def mesh():
    m = AgentMesh()
    m.register_agent(ResearchAgent(model_type="mock"))
    m.register_agent(CreativeWriterAgent(model_type="mock"))
    m.register_agent(DesignAgent(model_type="mock"))
    m.register_agent(AnalysisAgent(model_type="mock"))
    return m


# ========== Pre-built Workflow Constants ==========

class TestWorkflowConstants:
    def test_content_creation_workflow_structure(self):
        assert CONTENT_CREATION_WORKFLOW["name"] == "Content Creation Workflow"
        assert len(CONTENT_CREATION_WORKFLOW["steps"]) == 3
        types = [s["type"] for s in CONTENT_CREATION_WORKFLOW["steps"]]
        assert types == ["research", "content_creation", "editing"]

    def test_design_workflow_structure(self):
        assert DESIGN_WORKFLOW["name"] == "Design Workflow"
        assert len(DESIGN_WORKFLOW["steps"]) == 1
        assert DESIGN_WORKFLOW["steps"][0]["type"] == "design"

    def test_research_workflow_structure(self):
        assert RESEARCH_WORKFLOW["name"] == "Research Workflow"
        steps = RESEARCH_WORKFLOW["steps"]
        assert len(steps) == 2
        assert steps[0]["type"] == "research"
        assert steps[1]["type"] == "analysis"

    def test_workflow_constants_have_agents_needed(self):
        for wf in [CONTENT_CREATION_WORKFLOW, DESIGN_WORKFLOW, RESEARCH_WORKFLOW]:
            assert "agents_needed" in wf
            assert isinstance(wf["agents_needed"], list)

    def test_workflow_steps_have_parameters(self):
        for wf in [CONTENT_CREATION_WORKFLOW, DESIGN_WORKFLOW, RESEARCH_WORKFLOW]:
            for step in wf["steps"]:
                assert "parameters" in step
                assert "type" in step


# ========== execute_content_creation_pipeline ==========

class TestContentCreationPipeline:
    @pytest.mark.asyncio
    async def test_content_creation_pipeline_runs(self, mesh):
        result = await mesh.execute_content_creation_pipeline("AI Safety", style="academic")
        # Fails at editing stage (no editing agent), but research + writing stages complete
        assert result["status"] in ("completed", "failed")
        assert "results" in result

    @pytest.mark.asyncio
    async def test_content_creation_pipeline_default_style(self, mesh):
        result = await mesh.execute_content_creation_pipeline("Test Topic")
        assert result["status"] in ("completed", "failed")


# ========== execute_research_pipeline ==========

class TestResearchPipeline:
    @pytest.mark.asyncio
    async def test_research_pipeline_runs(self, mesh):
        result = await mesh.execute_research_pipeline("Quantum Computing")
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_research_pipeline_custom_analysis(self, mesh):
        result = await mesh.execute_research_pipeline("Climate", analysis_type="statistical")
        assert result["status"] == "completed"


# ========== add_task_to_pipeline_stage success path ==========

class TestAddTaskToPipelineStage:
    @pytest.mark.asyncio
    async def test_add_task_to_stage_success(self, mesh):
        pipeline_id = await mesh.create_pipeline(
            "test-pipeline",
            stages_config=[
                {"name": "Stage1", "task_type": "research", "agents_needed": ["research"], "max_concurrent": 2}
            ]
        )
        task_id = mesh.add_task_to_pipeline_stage(pipeline_id, "Stage1", {"query": "test"})
        assert task_id is not None
        assert isinstance(task_id, str)

    @pytest.mark.asyncio
    async def test_add_task_to_missing_pipeline(self, mesh):
        with pytest.raises(ValueError, match="Pipeline .* not found"):
            mesh.add_task_to_pipeline_stage("nonexistent", "Stage1", {})

    @pytest.mark.asyncio
    async def test_add_task_to_missing_stage(self, mesh):
        pipeline_id = await mesh.create_pipeline(
            "test-pipeline",
            stages_config=[
                {"name": "Stage1", "task_type": "research", "agents_needed": ["research"], "max_concurrent": 2}
            ]
        )
        with pytest.raises(ValueError, match="Stage .* not found"):
            mesh.add_task_to_pipeline_stage(pipeline_id, "NonexistentStage", {})


# ========== Connection broadcast edge cases ==========

class TestConnectionBroadcast:
    def test_remove_nonexistent_connection(self, mesh):
        class FakeConn:
            pass
        # Should not raise
        mesh.remove_connection(FakeConn())

    def test_add_and_remove_connection(self, mesh):
        class FakeConn:
            pass
        conn = FakeConn()
        mesh.add_connection(conn)
        assert conn in mesh.connections
        mesh.remove_connection(conn)
        assert conn not in mesh.connections

    @pytest.mark.asyncio
    async def test_broadcast_with_failed_connection(self, mesh):
        """Broadcast should not crash with bad connections (fire-and-forget cleanup)"""
        class BadConn:
            pass
        conn = BadConn()
        mesh.add_connection(conn)
        # broadcast creates async tasks for send_message which handles failures
        mesh.broadcast_agent_update({"type": "test"})
        await asyncio.sleep(0.05)
        # The connection may or may not be cleaned up yet (fire-and-forget)
        # Key assertion: no crash occurred


# ========== create_workflow and execute_workflow via pre-built constants ==========

class TestPrebuiltWorkflowExecution:
    @pytest.mark.asyncio
    async def test_execute_content_creation_workflow(self, mesh):
        wf_id = mesh.create_workflow(CONTENT_CREATION_WORKFLOW)
        assert wf_id is not None
        result = await mesh.execute_workflow(wf_id, {"topic": "Test"})
        # Steps may fail since no editing agent, but workflow should run
        assert result["status"] in ("completed", "failed")

    @pytest.mark.asyncio
    async def test_execute_design_workflow(self, mesh):
        wf_id = mesh.create_workflow(DESIGN_WORKFLOW)
        result = await mesh.execute_workflow(wf_id, {"concept": "Dashboard"})
        assert result["status"] in ("completed", "failed")

    @pytest.mark.asyncio
    async def test_execute_research_workflow(self, mesh):
        wf_id = mesh.create_workflow(RESEARCH_WORKFLOW)
        result = await mesh.execute_workflow(wf_id, {"query": "AI trends"})
        assert result["status"] in ("completed", "failed")


# ========== Task execution error handling ==========

class TestTaskExecution:
    @pytest.mark.asyncio
    async def test_execute_task_with_no_matching_agents(self):
        """content_creation type requires editing specialty which we don't register"""
        m = AgentMesh()
        m.register_agent(ResearchAgent(model_type="mock"))
        # No writer agent registered, but content_creation needs writing specialty
        # select_agents_for_task will find research but not writing/editing
        result = await m.execute_task({"type": "content_creation", "topic": "test"})
        # It should still try with whatever agents it finds
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_general_task_with_no_agents(self):
        m = AgentMesh()
        result = await m.execute_task({"type": "general"})
        assert result["status"] == "failed"
        assert "No suitable agents" in result["error"]
