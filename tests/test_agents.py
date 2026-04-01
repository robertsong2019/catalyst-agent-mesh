"""
Comprehensive test suite for Catalyst Agent Mesh
Run: python -m pytest tests/ -v
"""

import asyncio
import sys
import os
import json
import pytest
import pytest_asyncio

pytest_plugins = ('pytest_asyncio',)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.mesh.agent_mesh import AgentMesh
from src.agents.creative_agents import (
    ResearchAgent, CreativeWriterAgent, DesignAgent, AnalysisAgent,
    MockProvider, create_provider, LLMProvider
)


# ========== Fixtures ==========

@pytest.fixture
def mock_mesh():
    """Create a mesh with mock agents"""
    mesh = AgentMesh()
    mesh.register_agent(ResearchAgent(model_type="mock"))
    mesh.register_agent(CreativeWriterAgent(model_type="mock"))
    mesh.register_agent(DesignAgent(model_type="mock"))
    mesh.register_agent(AnalysisAgent(model_type="mock"))
    return mesh


# ========== Agent Tests ==========

class TestAgentCreation:
    def test_create_research_agent(self):
        agent = ResearchAgent(model_type="mock")
        assert agent.specialty == "research"
        assert agent.status == "idle"
        assert "web_search" in agent.capabilities

    def test_create_writer_agent(self):
        agent = CreativeWriterAgent(model_type="mock")
        assert agent.specialty == "writing"
        assert "content_generation" in agent.capabilities

    def test_create_design_agent(self):
        agent = DesignAgent(model_type="mock")
        assert agent.specialty == "design"

    def test_create_analysis_agent(self):
        agent = AnalysisAgent(model_type="mock")
        assert agent.specialty == "analysis"

    def test_agent_has_id(self):
        agent = ResearchAgent(model_type="mock")
        assert agent.id is not None
        assert len(agent.id) > 0

    def test_agent_to_dict(self):
        agent = ResearchAgent(model_type="mock")
        d = agent.to_dict()
        assert d["specialty"] == "research"
        assert "id" in d
        assert "capabilities" in d


class TestMockProvider:
    @pytest.mark.asyncio
    async def test_mock_provider_returns_string(self):
        provider = MockProvider()
        result = await provider.generate("test prompt")
        assert isinstance(result, str)
        assert "Mock response" in result

    @pytest.mark.asyncio
    async def test_mock_provider_tracks_calls(self):
        provider = MockProvider()
        await provider.generate("prompt 1")
        await provider.generate("prompt 2")
        assert provider.call_count == 2


class TestProviderFactory:
    def test_create_mock(self):
        p = create_provider("mock")
        assert isinstance(p, MockProvider)

    def test_create_unknown_raises(self):
        with pytest.raises(ValueError):
            create_provider("nonexistent")


# ========== Agent Processing Tests ==========

class TestAgentProcessing:
    @pytest.mark.asyncio
    async def test_research_agent_process(self):
        agent = ResearchAgent(model_type="mock")
        result = await agent.process_task({"query": "AI trends", "depth": "comprehensive"})
        assert result["status"] == "completed"
        assert result["query"] == "AI trends"

    @pytest.mark.asyncio
    async def test_writer_agent_process(self):
        agent = CreativeWriterAgent(model_type="mock")
        result = await agent.process_task({
            "topic": "AI in Healthcare",
            "style": "professional",
            "content_type": "article"
        })
        assert result["status"] == "completed"
        assert result["topic"] == "AI in Healthcare"
        assert "content" in result

    @pytest.mark.asyncio
    async def test_design_agent_process(self):
        agent = DesignAgent(model_type="mock")
        result = await agent.process_task({"concept": "Dashboard UI", "target_platform": "web"})
        assert result["status"] == "completed"
        assert "design_spec" in result

    @pytest.mark.asyncio
    async def test_analysis_agent_process(self):
        agent = AnalysisAgent(model_type="mock")
        result = await agent.process_task({"analysis_type": "trend", "data": {"x": [1, 2, 3]}})
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_agent_status_updates(self):
        agent = ResearchAgent(model_type="mock")
        assert agent.status == "idle"
        await agent.process_task({"query": "test"})
        assert agent.status == "idle"  # back to idle after processing

    @pytest.mark.asyncio
    async def test_agent_task_count(self):
        agent = ResearchAgent(model_type="mock")
        assert agent._task_count == 0
        await agent.process_task({"query": "test"})
        assert agent._task_count == 1

    @pytest.mark.asyncio
    async def test_writer_with_research_data(self):
        writer = CreativeWriterAgent(model_type="mock")
        result = await writer.process_task({
            "topic": "Quantum Computing",
            "research_data": {"findings": ["q1", "q2"]},
        })
        assert result["status"] == "completed"


# ========== Agent Collaboration Tests ==========

class TestAgentCollaboration:
    @pytest.mark.asyncio
    async def test_basic_collaboration(self):
        researcher = ResearchAgent(model_type="mock")
        writer = CreativeWriterAgent(model_type="mock")
        result = await researcher.collaborate(
            {"query": "AI trends"},
            [researcher, writer]
        )
        assert "collaborated_with" in result
        assert writer.name in result["collaborated_with"]


# ========== Mesh Tests ==========

class TestAgentMesh:
    def test_register_agent(self, mock_mesh):
        assert len(mock_mesh.agents) == 4

    def test_find_by_specialty(self, mock_mesh):
        research = mock_mesh.find_agents_by_specialty("research")
        assert len(research) == 1
        assert research[0].specialty == "research"

    def test_find_by_capability(self, mock_mesh):
        agents = mock_mesh.find_agents_by_capability("content_generation")
        assert len(agents) >= 1

    def test_get_available_agents(self, mock_mesh):
        available = mock_mesh.get_available_agents()
        assert len(available) == 4  # all idle

    def test_unregister_agent(self, mock_mesh):
        aid = list(mock_mesh.agents.keys())[0]
        mock_mesh.unregister_agent(aid)
        assert len(mock_mesh.agents) == 3

    def test_mesh_status(self, mock_mesh):
        status = mock_mesh.get_mesh_status()
        assert status["total_agents"] == 4
        assert status["available_agents"] == 4

    @pytest.mark.asyncio
    async def test_execute_task_no_agents(self):
        mesh = AgentMesh()  # empty mesh
        result = await mesh.execute_task({"type": "research", "query": "test"})
        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_execute_research_task(self, mock_mesh):
        result = await mock_mesh.execute_task({
            "type": "research",
            "query": "AI trends 2026",
            "depth": "comprehensive"
        })
        assert result["status"] == "completed"
        assert "agents_used" in result

    @pytest.mark.asyncio
    async def test_execute_content_creation_task(self, mock_mesh):
        result = await mock_mesh.execute_task({
            "type": "content_creation",
            "topic": "Machine Learning",
            "style": "professional"
        })
        assert result["status"] == "completed"


# ========== Workflow Tests ==========

class TestWorkflows:
    @pytest.mark.asyncio
    async def test_create_and_execute_workflow(self, mock_mesh):
        wid = mock_mesh.create_workflow({
            "name": "Test Workflow",
            "description": "Simple research workflow",
            "steps": [
                {"type": "research", "parameters": {"query": "AI", "depth": "quick"}},
            ]
        })
        assert wid is not None
        result = await mock_mesh.execute_workflow(wid, {"query": "AI trends"})
        assert result["status"] == "completed"

    def test_workflow_not_found(self, mock_mesh):
        import asyncio as aio
        result = aio.get_event_loop().run_until_complete(
            mock_mesh.execute_workflow("nonexistent", {})
        )
        assert result["status"] == "failed"


# ========== Pipeline Tests ==========

class TestPipelines:
    @pytest.mark.asyncio
    async def test_create_pipeline(self, mock_mesh):
        pid = await mock_mesh.create_pipeline(
            "Test Pipeline",
            stages_config=[
                {"name": "Research", "task_type": "research",
                 "agents_needed": ["research"], "max_concurrent": 2}
            ]
        )
        assert pid is not None

    @pytest.mark.asyncio
    async def test_execute_pipeline(self, mock_mesh):
        pid = await mock_mesh.create_pipeline(
            "Research Pipeline",
            stages_config=[
                {"name": "Research", "task_type": "research",
                 "agents_needed": ["research"], "max_concurrent": 2,
                 "parameters": {"query": "AI"}}
            ]
        )
        pipeline = mock_mesh.pipeline_executor.active_pipelines[pid]
        pipeline["stages"][0].add_task({"query": "test query"})

        result = await mock_mesh.execute_pipeline(pid, {"topic": "AI"})
        assert result["status"] == "completed"
        assert result["total_stages"] == 1

    @pytest.mark.asyncio
    async def test_multi_stage_pipeline(self, mock_mesh):
        pid = await mock_mesh.create_pipeline(
            "Multi-Stage",
            stages_config=[
                {"name": "Research", "task_type": "research",
                 "agents_needed": ["research"], "max_concurrent": 2},
                {"name": "Writing", "task_type": "content_creation",
                 "agents_needed": ["writing"], "max_concurrent": 2},
            ]
        )
        pipeline = mock_mesh.pipeline_executor.active_pipelines[pid]
        pipeline["stages"][0].add_task({"query": "quantum computing"})
        pipeline["stages"][1].add_task({"topic": "quantum computing", "section": "intro"})

        result = await mock_mesh.execute_pipeline(pid, {"topic": "Quantum"})
        assert result["status"] == "completed"
        assert result["total_stages"] == 2

    @pytest.mark.asyncio
    async def test_pipeline_not_found(self, mock_mesh):
        result = await mock_mesh.execute_pipeline("nonexistent", {})
        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_cancel_pipeline(self, mock_mesh):
        pid = await mock_mesh.create_pipeline("Cancel Test", stages_config=[])
        result = mock_mesh.cancel_pipeline(pid)
        assert result["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_list_pipelines(self, mock_mesh):
        await mock_mesh.create_pipeline("P1", stages_config=[])
        await mock_mesh.create_pipeline("P2", stages_config=[])
        pipelines = mock_mesh.list_pipelines()
        assert len(pipelines) >= 2

    @pytest.mark.asyncio
    async def test_pipeline_statistics(self, mock_mesh):
        stats = mock_mesh.get_pipeline_statistics()
        assert "total_pipelines" in stats
        assert "success_rate" in stats

    @pytest.mark.asyncio
    async def test_pipeline_status(self, mock_mesh):
        pid = await mock_mesh.create_pipeline("Status Test", stages_config=[
            {"name": "S1", "task_type": "research", "agents_needed": ["research"]}
        ])
        status = mock_mesh.get_pipeline_status(pid)
        assert status["name"] == "Status Test"


# ========== Run standalone ==========

async def run_all_tests():
    """Run tests without pytest"""
    print("🚀 Catalyst Agent Mesh Test Suite")
    print("=" * 50)

    t = TestAgentCreation()
    tests = [
        ("Agent Creation - Research", t.test_create_research_agent),
        ("Agent Creation - Writer", t.test_create_writer_agent),
        ("Agent Creation - Design", t.test_create_design_agent),
        ("Agent Creation - Analysis", t.test_create_analysis_agent),
        ("Agent to_dict", t.test_agent_to_dict),
    ]

    async_tests = [
        ("Research Process", TestAgentProcessing().test_research_agent_process),
        ("Writer Process", TestAgentProcessing().test_writer_agent_process),
        ("Analysis Process", TestAgentProcessing().test_analysis_agent_process),
    ]

    passed = 0
    failed = 0

    for name, fn in tests:
        try:
            fn()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failed += 1

    for name, fn in async_tests:
        try:
            await fn()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failed += 1

    total = passed + failed
    print(f"\n📊 {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    return passed == total


if __name__ == "__main__":
    asyncio.run(run_all_tests())
