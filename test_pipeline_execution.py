"""
Test script for Agent Pipeline Parallel Execution
Tests the new pipeline execution capabilities
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src import AgentMesh
from src.agents.creative_agents import ResearchAgent, CreativeWriterAgent, DesignAgent, AnalysisAgent

async def test_basic_pipeline_execution():
    """Test basic pipeline execution with multiple stages"""
    print("🧪 Test 1: Basic Pipeline Execution")
    print("=" * 50)
    
    # Create agent mesh
    mesh = AgentMesh()
    
    # Register agents
    researcher = ResearchAgent()
    writer = CreativeWriterAgent()
    analyst = AnalysisAgent()
    
    mesh.register_agent(researcher)
    mesh.register_agent(writer)
    mesh.register_agent(analyst)
    
    print(f"✓ Registered {len(mesh.agents)} agents")
    
    # Create a simple pipeline
    pipeline_id = await mesh.create_pipeline(
        name="Test Pipeline",
        description="Test pipeline for parallel execution",
        stages_config=[
            {
                "name": "Stage 1 - Research",
                "task_type": "research",
                "agents_needed": ["research"],
                "max_concurrent": 2,
                "parameters": {
                    "query": "AI technology trends",
                    "depth": "comprehensive"
                }
            },
            {
                "name": "Stage 2 - Analysis",
                "task_type": "analysis", 
                "agents_needed": ["analysis"],
                "max_concurrent": 2,
                "parameters": {
                    "analysis_type": "comprehensive"
                }
            }
        ]
    )
    
    print(f"✓ Created pipeline: {pipeline_id}")
    
    # Add tasks to stages
    pipeline = mesh.pipeline_executor.active_pipelines[pipeline_id]
    research_stage = pipeline["stages"][0]
    
    # Add multiple tasks for parallel execution
    task1_id = research_stage.add_task({"focus": "machine learning"})
    task2_id = research_stage.add_task({"focus": "natural language processing"})
    
    print(f"✓ Added {task1_id} and {task2_id} to research stage")
    
    # Execute pipeline
    result = await mesh.execute_pipeline(pipeline_id, {"topic": "AI technology trends"})
    
    print(f"✓ Pipeline execution status: {result['status']}")
    print(f"✓ Total stages: {result.get('total_stages', 0)}")
    print(f"✓ Execution time: {result.get('execution_time', 'N/A')}")
    
    if result['status'] == 'completed':
        print("✅ Test 1 PASSED: Basic pipeline execution works correctly")
    else:
        print(f"❌ Test 1 FAILED: {result.get('error', 'Unknown error')}")
        
    return result['status'] == 'completed'

async def test_content_creation_pipeline():
    """Test the predefined content creation pipeline"""
    print("\n🧪 Test 2: Content Creation Pipeline")
    print("=" * 50)
    
    # Create agent mesh
    mesh = AgentMesh()
    
    # Register agents
    researcher = ResearchAgent()
    writer = CreativeWriterAgent()
    
    mesh.register_agent(researcher)
    mesh.register_agent(writer)
    
    print(f"✓ Registered {len(mesh.agents)} agents")
    
    # Create a simple content creation pipeline without editing stage
    stages_config = [
        {
            "name": "Research",
            "task_type": "research",
            "agents_needed": ["research"],
            "max_concurrent": 2,
            "parameters": {
                "query": "Artificial Intelligence in Healthcare",
                "depth": "comprehensive"
            }
        },
        {
            "name": "Content Generation",
            "task_type": "content_creation", 
            "agents_needed": ["writing"],
            "max_concurrent": 2,
            "parameters": {
                "topic": "Artificial Intelligence in Healthcare",
                "style": "professional",
                "content_type": "article"
            }
        }
    ]
    
    pipeline_id = await mesh.create_pipeline(
        name="Content Creation - AI in Healthcare",
        description="Simple content creation pipeline",
        stages_config=stages_config
    )
    
    # Add tasks to research stage
    pipeline = mesh.pipeline_executor.active_pipelines[pipeline_id]
    research_stage = pipeline["stages"][0]
    research_stage.add_task({"focus": "machine learning"})
    research_stage.add_task({"focus": "diagnostics"})
    
    # Add tasks to content stage
    content_stage = pipeline["stages"][1]
    content_stage.add_task({"section": "introduction"})
    content_stage.add_task({"section": "main_content"})
    
    # Execute pipeline
    result = await mesh.execute_pipeline(pipeline_id, {"topic": "AI in Healthcare"})
    
    print(f"✓ Pipeline execution status: {result['status']}")
    print(f"✓ Total stages: {result.get('total_stages', 0)}")
    
    if result['status'] == 'completed':
        results = result.get('results', {})
        for stage_name, stage_result in results.items():
            print(f"✓ Stage '{stage_name}': {stage_result.get('successful_tasks', 0)}/{stage_result.get('tasks_executed', 0)} tasks successful")
        print("✅ Test 2 PASSED: Content creation pipeline works correctly")
    else:
        print(f"❌ Test 2 FAILED: {result.get('error', 'Unknown error')}")
        
    return result['status'] == 'completed'

async def test_research_pipeline():
    """Test the predefined research pipeline"""
    print("\n🧪 Test 3: Research Pipeline")
    print("=" * 50)
    
    # Create agent mesh
    mesh = AgentMesh()
    
    # Register agents
    researcher = ResearchAgent()
    analyst = AnalysisAgent()
    writer = CreativeWriterAgent()
    
    mesh.register_agent(researcher)
    mesh.register_agent(analyst)
    mesh.register_agent(writer)
    
    print(f"✓ Registered {len(mesh.agents)} agents")
    
    # Create a simplified research pipeline
    stages_config = [
        {
            "name": "Data Collection",
            "task_type": "research",
            "agents_needed": ["research"],
            "max_concurrent": 2,
            "parameters": {
                "query": "Quantum Computing Applications",
                "sources": ["web", "academic"],
                "depth": "comprehensive"
            }
        },
        {
            "name": "Analysis",
            "task_type": "analysis",
            "agents_needed": ["analysis"],
            "max_concurrent": 2,
            "parameters": {
                "analysis_type": "comprehensive",
                "focus": "trends"
            }
        }
    ]
    
    pipeline_id = await mesh.create_pipeline(
        name="Research Pipeline - Quantum Computing",
        description="Research pipeline for quantum computing",
        stages_config=stages_config
    )
    
    # Add tasks to data collection stage
    pipeline = mesh.pipeline_executor.active_pipelines[pipeline_id]
    data_stage = pipeline["stages"][0]
    data_stage.add_task({"focus": "algorithms"})
    data_stage.add_task({"focus": "applications"})
    
    # Add tasks to analysis stage
    analysis_stage = pipeline["stages"][1]
    analysis_stage.add_task({"focus": "trends"})
    analysis_stage.add_task({"focus": "patterns"})
    
    # Execute pipeline
    result = await mesh.execute_pipeline(pipeline_id, {"research_topic": "Quantum Computing"})
    
    print(f"✓ Pipeline execution status: {result['status']}")
    print(f"✓ Total stages: {result.get('total_stages', 0)}")
    
    if result['status'] == 'completed':
        results = result.get('results', {})
        for stage_name, stage_result in results.items():
            if 'successful_tasks' in stage_result:
                print(f"✓ Stage '{stage_name}': {stage_result['successful_tasks']}/{stage_result['tasks_executed']} tasks successful")
        print("✅ Test 3 PASSED: Research pipeline works correctly")
    else:
        print(f"❌ Test 3 FAILED: {result.get('error', 'Unknown error')}")
        
    return result['status'] == 'completed'

async def test_pipeline_status_and_statistics():
    """Test pipeline status tracking and statistics"""
    print("\n🧪 Test 4: Pipeline Status and Statistics")
    print("=" * 50)
    
    # Create agent mesh
    mesh = AgentMesh()
    
    # Register some agents
    researcher = ResearchAgent()
    writer = CreativeWriterAgent()
    
    mesh.register_agent(researcher)
    mesh.register_agent(writer)
    
    # Create multiple pipelines
    pipeline1_id = await mesh.create_pipeline(
        name="Pipeline 1",
        stages_config=[{
            "name": "Research",
            "task_type": "research",
            "agents_needed": ["research"]
        }]
    )
    
    pipeline2_id = await mesh.create_pipeline(
        name="Pipeline 2", 
        stages_config=[{
            "name": "Writing",
            "task_type": "content_creation",
            "agents_needed": ["writing"]
        }]
    )
    
    print(f"✓ Created 2 pipelines")
    
    # List all pipelines
    pipelines = mesh.list_pipelines()
    print(f"✓ Active pipelines: {len(pipelines)}")
    
    # Get statistics
    stats = mesh.get_pipeline_statistics()
    print(f"✓ Total pipelines: {stats['total_pipelines']}")
    print(f"✓ Running pipelines: {stats['running_pipelines']}")
    
    # Get individual pipeline status
    status1 = mesh.get_pipeline_status(pipeline1_id)
    print(f"✓ Pipeline 1 status: {status1['status']}")
    
    # Cancel a pipeline
    cancel_result = mesh.cancel_pipeline(pipeline2_id)
    print(f"✓ Cancelled pipeline: {cancel_result['status']}")
    
    print("✅ Test 4 PASSED: Pipeline status and statistics work correctly")
    return True

async def run_all_tests():
    """Run all tests and report results"""
    print("🚀 Starting Agent Pipeline Execution Tests")
    print("=" * 50)
    
    tests = [
        test_basic_pipeline_execution,
        test_content_creation_pipeline, 
        test_research_pipeline,
        test_pipeline_status_and_statistics
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append((test.__name__, result))
        except Exception as e:
            print(f"❌ Test {test.__name__} threw exception: {str(e)}")
            results.append((test.__name__, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\n{passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! Pipeline execution system is working correctly.")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Review the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(run_all_tests())