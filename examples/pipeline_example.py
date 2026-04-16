"""
Example: Pipeline execution with parallel stages
"""

import asyncio
from src.mesh.agent_mesh import AgentMesh
from src.agents.creative_agents import ResearchAgent, CreativeWriterAgent, AnalysisAgent


async def main():
    mesh = AgentMesh()

    # Register multiple agents for parallel work
    mesh.register_agent(ResearchAgent(model_type="mock"))
    mesh.register_agent(ResearchAgent(model_type="mock"))
    mesh.register_agent(CreativeWriterAgent(model_type="mock"))
    mesh.register_agent(AnalysisAgent(model_type="mock"))

    # Create a 3-stage pipeline
    pipeline_id = await mesh.create_pipeline(
        name="Full Research Pipeline",
        description="Parallel data collection → analysis → writing",
        stages_config=[
            {
                "name": "Data Collection",
                "task_type": "research",
                "agents_needed": ["research"],
                "max_concurrent": 2,
                "parameters": {"depth": "comprehensive"},
            },
            {
                "name": "Analysis",
                "task_type": "analysis",
                "agents_needed": ["analysis"],
                "max_concurrent": 2,
                "parameters": {"analysis_type": "comprehensive"},
            },
            {
                "name": "Report Writing",
                "task_type": "content_creation",
                "agents_needed": ["writing"],
                "max_concurrent": 1,
                "parameters": {"content_type": "report", "style": "academic"},
            },
        ],
    )

    # Add tasks to the first stage (will run in parallel)
    stages = mesh.pipeline_executor.active_pipelines[pipeline_id]["stages"]
    data_stage_id = stages[0].id
    data_stage = mesh.pipeline_executor.stage_executors[data_stage_id]

    data_stage.add_task({"query": "AI safety trends", "focus": "industry"})
    data_stage.add_task({"query": "AI regulation landscape", "focus": "policy"})
    data_stage.add_task({"query": "AI alignment research", "focus": "academic"})

    print(f"Pipeline created: {pipeline_id}")
    print(f"Stage 1 tasks: {len(data_stage.tasks)}")

    # Execute
    result = await mesh.execute_pipeline(pipeline_id, {"topic": "AI Safety 2026"})
    print(f"\nPipeline status: {result['status']}")
    print(f"Total stages: {result.get('total_stages', 0)}")

    # Get detailed status
    status = mesh.get_pipeline_status(pipeline_id)
    print(f"\nStage details:")
    for stage_name, stage_status in status.get("stages", {}).items():
        print(f"  {stage_name}: {stage_status}")

    # Pipeline statistics
    stats = mesh.get_pipeline_statistics()
    print(f"\nPipeline stats: {stats}")


if __name__ == "__main__":
    asyncio.run(main())
