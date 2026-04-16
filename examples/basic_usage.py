"""
Example: Basic usage of Catalyst Agent Mesh in Python
"""

import asyncio
from src.mesh.agent_mesh import AgentMesh
from src.agents.creative_agents import ResearchAgent, CreativeWriterAgent, AnalysisAgent


async def main():
    # 1. Create the mesh
    mesh = AgentMesh()
    print("Mesh created")

    # 2. Register agents
    researcher = ResearchAgent(model_type="mock")
    writer = CreativeWriterAgent(model_type="mock")
    analyst = AnalysisAgent(model_type="mock")

    mesh.register_agent(researcher)
    mesh.register_agent(writer)
    mesh.register_agent(analyst)

    # 3. Execute a single task (auto-routed to research agent)
    print("\n--- Research Task ---")
    result = await mesh.execute_task({
        "type": "research",
        "query": "AI ethics in healthcare",
        "depth": "comprehensive",
    })
    print(f"Status: {result['status']}")
    print(f"Agents used: {result.get('agents_used', [])}")

    # 4. Create and run a workflow
    print("\n--- Workflow ---")
    workflow_id = mesh.create_workflow({
        "name": "Research & Write",
        "steps": [
            {"type": "research", "parameters": {"depth": "quick"}},
            {"type": "content_creation", "parameters": {"content_type": "article"}},
        ]
    })
    wf_result = await mesh.execute_workflow(workflow_id, {"topic": "AI Safety"})
    print(f"Workflow status: {wf_result['status']}")
    print(f"Steps completed: {wf_result.get('steps_completed', 0)}")

    # 5. Check mesh status
    print("\n--- Mesh Status ---")
    status = mesh.get_mesh_status()
    print(f"Total agents: {status['total_agents']}")
    print(f"Available agents: {status['available_agents']}")
    print(f"Total tasks: {status['total_tasks']}")

    # 6. Agent stats
    print("\n--- Agent Stats ---")
    for agent in mesh.agents.values():
        stats = agent.get_stats()
        print(f"  {stats['name']}: {stats['task_count']} tasks, {stats['error_count']} errors")


if __name__ == "__main__":
    asyncio.run(main())
