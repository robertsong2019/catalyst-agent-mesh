"""
Catalyst Agent Mesh - Core Module

A decentralized, collaborative AI agent network for creative workflows.
"""

__version__ = "1.0.0"
__author__ = "Catalyst Agent Mesh Team"
__email__ = "team@catalystagentmesh.com"

from .mesh.agent_mesh import AgentMesh, CONTENT_CREATION_WORKFLOW, DESIGN_WORKFLOW, RESEARCH_WORKFLOW
from .agents.creative_agents import (
    CreativeAgent,
    ResearchAgent,
    CreativeWriterAgent,
    DesignAgent,
    AnalysisAgent
)

__all__ = [
    "AgentMesh",
    "CreativeAgent",
    "ResearchAgent",
    "CreativeWriterAgent",
    "DesignAgent",
    "AnalysisAgent",
    "CONTENT_CREATION_WORKFLOW",
    "DESIGN_WORKFLOW",
    "RESEARCH_WORKFLOW"
]