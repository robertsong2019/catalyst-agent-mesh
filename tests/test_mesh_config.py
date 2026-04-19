"""Tests for AgentMesh workflows, status, config, and connection management."""

import os
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.mesh.agent_mesh import AgentMesh
from src.agents.creative_agents import ResearchAgent, CreativeWriterAgent, AnalysisAgent
from src.config import MeshConfig


class TestMeshStatus:
    def test_empty_mesh_status(self):
        mesh = AgentMesh()
        status = mesh.get_mesh_status()
        assert status["total_agents"] == 0
        assert status["available_agents"] == 0
        assert status["busy_agents"] == 0
        assert status["total_tasks"] == 0
        assert status["active_tasks"] == 0

    def test_mesh_status_with_agents(self):
        mesh = AgentMesh()
        mesh.register_agent(ResearchAgent(model_type="mock"))
        mesh.register_agent(CreativeWriterAgent(model_type="mock"))
        status = mesh.get_mesh_status()
        assert status["total_agents"] == 2
        assert status["available_agents"] == 2

    def test_find_agents_by_specialty_none(self):
        mesh = AgentMesh()
        assert mesh.find_agents_by_specialty("research") == []

    def test_find_agents_by_capability_none(self):
        mesh = AgentMesh()
        assert mesh.find_agents_by_capability("web_search") == []


class TestWorkflowManagement:
    def test_create_workflow(self):
        mesh = AgentMesh()
        wid = mesh.create_workflow({
            "name": "Test Workflow",
            "description": "A test",
            "steps": [{"type": "research"}, {"type": "analysis"}]
        })
        assert wid is not None
        assert wid in mesh.workflows

    def test_workflow_has_correct_fields(self):
        mesh = AgentMesh()
        wid = mesh.create_workflow({"name": "My WF", "steps": [{"type": "research"}]})
        wf = mesh.workflows[wid]
        assert wf["name"] == "My WF"
        assert wf["status"] == "active"
        assert len(wf["steps"]) == 1

    def test_execute_nonexistent_workflow(self):
        mesh = AgentMesh()
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            mesh.execute_workflow("nonexistent", {})
        )
        assert result["status"] == "failed"
        assert "not found" in result["error"]


class TestAgentRegistration:
    def test_register_and_unregister(self):
        mesh = AgentMesh()
        agent = ResearchAgent(model_type="mock")
        mesh.register_agent(agent)
        assert agent.id in mesh.agents
        mesh.unregister_agent(agent.id)
        assert agent.id not in mesh.agents

    def test_unregister_nonexistent(self):
        mesh = AgentMesh()
        # Should not raise
        mesh.unregister_agent("nonexistent-id")

    def test_get_available_agents_after_status_change(self):
        mesh = AgentMesh()
        agent = ResearchAgent(model_type="mock")
        mesh.register_agent(agent)
        assert len(mesh.get_available_agents()) == 1
        agent.update_status("executing")
        assert len(mesh.get_available_agents()) == 0
        agent.update_status("idle")
        assert len(mesh.get_available_agents()) == 1


class TestMeshConfig:
    def test_default_config(self):
        config = MeshConfig()
        assert config.default_provider == "mock"
        assert config.port == 8000
        assert config.max_workers == 10
        assert config.debug is False

    def test_from_env_defaults(self):
        config = MeshConfig.from_env()
        assert isinstance(config, MeshConfig)
        assert config.default_provider in ("mock", "ollama", "openai")

    def test_from_env_custom(self):
        os.environ["MESH_PORT"] = "9999"
        os.environ["MESH_DEBUG"] = "true"
        try:
            config = MeshConfig.from_env()
            assert config.port == 9999
            assert config.debug is True
        finally:
            del os.environ["MESH_PORT"]
            del os.environ["MESH_DEBUG"]


class TestConnectionManagement:
    def test_add_remove_connection(self):
        mesh = AgentMesh()
        class FakeConn:
            pass
        conn = FakeConn()
        mesh.add_connection(conn)
        assert conn in mesh.connections
        mesh.remove_connection(conn)
        assert conn not in mesh.connections

    def test_remove_nonexistent_connection(self):
        mesh = AgentMesh()
        class FakeConn:
            pass
        mesh.remove_connection(FakeConn())  # should not raise
