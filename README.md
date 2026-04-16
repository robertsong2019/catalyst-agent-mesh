# Catalyst Agent Mesh

A decentralized, collaborative AI agent network for creative workflows that enhances human creativity through specialized agent collaboration.

## 🚀 Project Overview

**Catalyst Agent Mesh** is a cutting-edge framework that enables multiple specialized AI agents to work together in a decentralized network, providing privacy-focused, scalable, and intelligent creative workflow automation.

### Core Features

- 🎨 **Multi-Agent Collaboration**: Specialized agents work together seamlessly
- 🔒 **Privacy-First**: Local-first architecture with optional cloud integration
- ⚡ **Lightweight & Fast**: Optimized for both cloud and edge devices
- 🎯 **Creative Workflows**: Pre-built workflows for content creation, design, research, and coding
- 📊 **Real-time Visualization**: Live monitoring of agent networks and workflows
- 🔌 **Embedded AI Support**: Run agents on Raspberry Pi, Arduino, and other edge devices

## 🎯 Creative Applications

### 1. Content Creation Studio
```
Research Agent → Creative Writer → Editor → Final Output
```
- Automated research synthesis
- Creative content generation
- Quality assurance and refinement

### 2. Design Automation
```
Concept Agent → Design Agent → Asset Agent → Final Design
```
- Creative concept generation
- Design iteration and improvement
- Asset creation and optimization

### 3. Research Assistant Network
```
Literature Agent → Analysis Agent → Synthesis Agent → Report
```
- Multi-disciplinary research
- Data analysis and visualization
- Automated report generation

### 4. Creative Coding Assistant
```
Idea Agent → Coding Agent → Testing Agent → Documentation
```
- Algorithm generation and optimization
- Code review and improvement
- Automated testing and documentation

## 🛠️ Technical Architecture

### Stack
- **Backend**: Python (FastAPI + asyncio)
- **Frontend**: Next.js 15 + React
- **AI Models**: Local (Ollama) + Cloud APIs
- **Database**: PostgreSQL + Redis
- **Real-time**: WebSocket communication
- **Deployment**: Docker + Kubernetes

### Key Components

#### Agent Framework
```python
class CreativeAgent:
    """Base class for creative AI agents"""
    
    def __init__(self, specialty, capabilities, model_type="local"):
        self.specialty = specialty
        self.capabilities = capabilities
        self.model_type = model_type
        self.mesh_network = AgentMesh()
    
    def collaborate(self, task, agents):
        """Collaborate with other agents"""
        # Multi-agent collaboration logic
```

#### Agent Mesh Network
- P2P communication and discovery
- Load balancing and resource optimization
- Health monitoring and failure recovery

#### Workflow Orchestrator
- Pre-built creative workflows
- Dynamic task distribution
- Performance optimization

## 🎨 Design Philosophy

### Creative Principles
1. **Modularity**: Agents as interchangeable components
2. **Collaboration**: Synergy through specialized expertise
3. **Transparency**: Visible reasoning and decision-making
4. **Adaptability**: Dynamic resource allocation
5. **Creativity Enhancement**: Amplify human creativity

### User Experience
- Intuitive workflow builder
- Real-time collaboration visualization
- Performance monitoring
- Educational resources for agent development

## 📊 Project Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Basic agent framework
- [ ] Agent registration and discovery
- [ ] Simple communication protocol
- [ ] Prototype dashboard

### Phase 2: Core Features (Week 3-4)
- [ ] Multi-agent collaboration system
- [ ] Pre-built creative workflows
- [ ] Local/remote model integration
- [ ] Enhanced visualization

### Phase 3: Advanced Features (Week 5-6)
- [ ] Embedded AI support
- [ ] Advanced optimization algorithms
- [ ] API marketplace for agent services
- [ ] Production deployment

## 📚 Documentation

| Doc | Description |
|-----|-------------|
| [Tutorial](docs/TUTORIAL.md) | 10-minute getting started guide |
| [API Reference](docs/API.md) | Complete REST API documentation |
| [Architecture](docs/ARCHITECTURE.md) | System design and internals |

Examples: [`examples/basic_usage.py`](examples/basic_usage.py) · [`examples/pipeline_example.py`](examples/pipeline_example.py)

---

## 🔧 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend only)
- Docker (optional)
- Ollama or OpenAI API key (optional — mock provider works without LLM)

### Quick Start

```bash
git clone https://github.com/robertsong2019/catalyst-agent-mesh.git
cd catalyst-agent-mesh
pip install -r requirements.txt

# Start with mock provider (no LLM needed)
uvicorn src.main:app --reload

# Or with Ollama
MESH_LLM_PROVIDER=ollama uvicorn src.main:app --reload

# Or with OpenAI
OPENAI_API_KEY=sk-... MESH_LLM_PROVIDER=openai uvicorn src.main:app --reload
```

API docs available at `http://localhost:8000/docs`

### Python Usage

```python
import asyncio
from src.mesh.agent_mesh import AgentMesh
from src.agents.creative_agents import ResearchAgent, CreativeWriterAgent

async def main():
    mesh = AgentMesh()
    mesh.register_agent(ResearchAgent(model_type="mock"))
    mesh.register_agent(CreativeWriterAgent(model_type="mock"))

    result = await mesh.execute_task({
        "type": "content_creation",
        "topic": "AI ethics",
        "style": "professional",
    })
    print(result)

asyncio.run(main())
```

See the [Tutorial](docs/TUTORIAL.md) for the full walkthrough.

## 📈 Performance Metrics

### Technical Goals
- Agent response time < 2 seconds
- 90% workflow completion rate
- Support for 10+ agent types
- 5+ embedded device integrations

### Creative Goals
- 80% user satisfaction with creative outputs
- 50% reduction in creative task time
- Support for 10+ creative workflows
- Active community of creative developers

## 🤝 Contributing

We welcome contributions from the creative AI community! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Ways to Contribute
- Create new agent specializations
- Develop creative workflows
- Improve the visualization dashboard
- Add embedded device support
- Write documentation and tutorials

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🌟 Community

- **Discord**: Join our community for discussions and support
- **GitHub**: Star ⭐ the repository and contribute
- **Documentation**: Read our detailed docs at [docs](https://robertsong2019.github.io/catalyst-agent-mesh)

## 🎯 Vision

**Catalyst Agent Mesh** represents a new paradigm for creative AI collaboration - where specialized agents work together in a decentralized network to enhance human creativity. The project combines cutting-edge AI research with practical creative applications, making advanced AI accessible to creative professionals while maintaining privacy and control.

---

*Created with 🧪 Catalyst - The Digital Familiar*  
*Last Updated: March 28, 2026*