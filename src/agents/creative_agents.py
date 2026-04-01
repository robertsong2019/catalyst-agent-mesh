"""
Creative Agents Module - Real LLM-backed agents for creative workflows
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json
import logging
import os

logger = logging.getLogger(__name__)

# LLM provider abstraction
class LLMProvider(ABC):
    """Abstract base for LLM providers"""
    @abstractmethod
    async def generate(self, prompt: str, system: str = "", max_tokens: int = 2048, temperature: float = 0.7) -> str:
        pass

class OllamaProvider(LLMProvider):
    """Local Ollama provider"""
    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self._client = None

    async def _get_client(self):
        if self._client is None:
            try:
                import httpx
                self._client = httpx.AsyncClient(timeout=120.0)
            except ImportError:
                raise RuntimeError("httpx required for Ollama provider")
        return self._client

    async def generate(self, prompt: str, system: str = "", max_tokens: int = 2048, temperature: float = 0.7) -> str:
        client = await self._get_client()
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": temperature}
        }
        try:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

class OpenAIProvider(LLMProvider):
    """OpenAI API provider"""
    def __init__(self, model: str = "gpt-4o-mini", api_key: str = None):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = None

    async def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("openai package required for OpenAI provider")
        return self._client

    async def generate(self, prompt: str, system: str = "", max_tokens: int = 2048, temperature: float = 0.7) -> str:
        client = await self._get_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            resp = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise

class MockProvider(LLMProvider):
    """Mock provider for testing without LLM"""
    def __init__(self):
        self.call_count = 0
        self.last_prompt = ""

    async def generate(self, prompt: str, system: str = "", max_tokens: int = 2048, temperature: float = 0.7) -> str:
        self.call_count += 1
        self.last_prompt = prompt
        return f"[Mock response #{self.call_count}] Generated content for: {prompt[:100]}..."

def create_provider(provider_type: str = "mock", **kwargs) -> LLMProvider:
    """Factory function to create LLM provider"""
    providers = {
        "ollama": OllamaProvider,
        "openai": OpenAIProvider,
        "mock": MockProvider,
    }
    cls = providers.get(provider_type)
    if cls is None:
        raise ValueError(f"Unknown provider: {provider_type}. Available: {list(providers.keys())}")
    return cls(**kwargs)


class CreativeAgent(ABC):
    """Base class for creative AI agents with real LLM backing"""

    def __init__(self, name: str, specialty: str, capabilities: List[str],
                 model_type: str = "mock", llm_provider: LLMProvider = None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.specialty = specialty
        self.capabilities = capabilities
        self.model_type = model_type
        self.status = "idle"
        self.created_at = datetime.now()
        self.last_active = datetime.now()
        self.health = 1.0
        self.mesh = None
        self._llm = llm_provider or create_provider(model_type)
        self._task_count = 0
        self._error_count = 0

    def set_mesh(self, mesh):
        self.mesh = mesh

    def set_llm(self, provider: LLMProvider):
        """Swap the LLM provider at runtime"""
        self._llm = provider

    @abstractmethod
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        pass

    async def collaborate(self, task: Dict[str, Any], agents: List['CreativeAgent']) -> Dict[str, Any]:
        result = await self.process_task(task)
        return {
            "collaboration_type": f"{self.specialty}_to_others",
            "agent_name": self.name,
            "task_result": result,
            "collaborated_with": [a.name for a in agents if a.id != self.id]
        }

    def update_status(self, status: str):
        self.status = status
        self.last_active = datetime.now()
        if self.mesh:
            self.mesh.broadcast_agent_update({
                "id": self.id, "name": self.name,
                "status": status, "specialty": self.specialty
            })

    async def _llm_generate(self, prompt: str, system: str = "", **kwargs) -> str:
        """Safe wrapper around LLM generation with error tracking"""
        try:
            result = await self._llm.generate(prompt, system, **kwargs)
            self._task_count += 1
            return result
        except Exception as e:
            self._error_count += 1
            logger.error(f"Agent {self.name} LLM error: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "specialty": self.specialty,
            "status": self.status,
            "task_count": self._task_count,
            "error_count": self._error_count,
            "health": self.health,
            "model_type": self.model_type,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "specialty": self.specialty,
            "capabilities": self.capabilities,
            "model_type": self.model_type,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "health": self.health,
            "task_count": self._task_count,
            "error_count": self._error_count,
        }


class ResearchAgent(CreativeAgent):
    """Research-specialized agent with real LLM research synthesis"""

    def __init__(self, model_type: str = "mock", llm_provider: LLMProvider = None):
        super().__init__(
            name="Research Agent",
            specialty="research",
            capabilities=["web_search", "literature_review", "data_analysis",
                         "synthesis", "citation_generation"],
            model_type=model_type,
            llm_provider=llm_provider,
        )

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        self.update_status("researching")
        query = task.get("query", task.get("topic", "general research"))
        depth = task.get("depth", "comprehensive")

        system = (
            "You are a thorough research analyst. Provide structured research findings "
            "with key insights, related topics, and actionable summaries. "
            "Be concise but comprehensive."
        )
        prompt = (
            f"Research topic: {query}\n"
            f"Depth: {depth}\n"
            f"Focus area: {task.get('focus', 'general')}\n\n"
            f"Provide:\n"
            f"1. Key findings (3-5 bullet points)\n"
            f"2. Related topics\n"
            f"3. Summary paragraph"
        )

        try:
            llm_response = await self._llm_generate(prompt, system)
        except Exception:
            # Fallback to structured response
            llm_response = None

        result = {
            "query": query,
            "depth": depth,
            "key_findings": self._parse_findings(llm_response) if llm_response else [
                f"Research finding for {query}"
            ],
            "summary": llm_response or f"Research completed for: {query}",
            "related_topics": [],
            "status": "completed"
        }

        self.update_status("idle")
        return result

    def _parse_findings(self, text: str) -> List[str]:
        """Extract bullet-point findings from LLM response"""
        findings = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith(("- ", "* ", "• ")):
                findings.append(line.lstrip("-*• ").strip())
            elif findings and line and not line.startswith("#"):
                # continuation
                findings[-1] += " " + line
        return findings[:10] or [text[:200]]


class CreativeWriterAgent(CreativeAgent):
    """Creative writing agent with real LLM content generation"""

    def __init__(self, model_type: str = "mock", llm_provider: LLMProvider = None):
        super().__init__(
            name="Creative Writer",
            specialty="writing",
            capabilities=["content_generation", "storytelling", "editing",
                         "refinement", "tone_adjustment"],
            model_type=model_type,
            llm_provider=llm_provider,
        )

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        self.update_status("writing")
        topic = task.get("topic", task.get("query", ""))
        style = task.get("style", "professional")
        content_type = task.get("content_type", "article")
        research_data = task.get("research_data", {})
        section = task.get("section", "full")

        system = (
            f"You are a skilled {style} writer. Generate high-quality {content_type} content. "
            f"Be engaging, accurate, and well-structured."
        )

        context = ""
        if research_data and isinstance(research_data, dict):
            context = f"\nResearch context: {json.dumps(research_data, ensure_ascii=False)[:1000]}"

        prompt = (
            f"Topic: {topic}\n"
            f"Section: {section}\n"
            f"Style: {style}\n"
            f"Content type: {content_type}\n"
            f"{context}\n\n"
            f"Write the {section} section. Be concise and impactful."
        )

        try:
            content = await self._llm_generate(prompt, system, max_tokens=1500)
        except Exception:
            content = f"[Draft] {style} {content_type} about {topic}"

        result = {
            "content_type": content_type,
            "topic": topic,
            "style": style,
            "section": section,
            "content": content,
            "word_count": len(content.split()),
            "status": "completed",
            "created_at": datetime.now().isoformat(),
        }

        self.update_status("idle")
        return result


class DesignAgent(CreativeAgent):
    """Design-specialized agent with concept generation"""

    def __init__(self, model_type: str = "mock", llm_provider: LLMProvider = None):
        super().__init__(
            name="Design Agent",
            specialty="design",
            capabilities=["concept_generation", "visual_design", "layout_optimization",
                         "color_scheme", "typography"],
            model_type=model_type,
            llm_provider=llm_provider,
        )

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        self.update_status("designing")
        concept = task.get("concept", "")
        target_platform = task.get("target_platform", "web")

        system = "You are an expert UI/UX designer. Provide structured design specifications."
        prompt = (
            f"Generate a design concept for: {concept}\n"
            f"Target platform: {target_platform}\n\n"
            f"Provide:\n"
            f"1. Color scheme (primary, secondary, accent hex codes)\n"
            f"2. Typography recommendations\n"
            f"3. Layout principles\n"
            f"4. Design rationale"
        )

        try:
            llm_output = await self._llm_generate(prompt, system)
        except Exception:
            llm_output = None

        result = {
            "concept": concept,
            "target_platform": target_platform,
            "design_spec": llm_output or "Default design specification",
            "status": "completed",
        }

        self.update_status("idle")
        return result


class AnalysisAgent(CreativeAgent):
    """Analysis-specialized agent with real LLM reasoning"""

    def __init__(self, model_type: str = "mock", llm_provider: LLMProvider = None):
        super().__init__(
            name="Analysis Agent",
            specialty="analysis",
            capabilities=["data_analysis", "pattern_recognition", "trend_identification",
                         "statistical_analysis", "insight_generation"],
            model_type=model_type,
            llm_provider=llm_provider,
        )

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        self.update_status("analyzing")
        data = task.get("data", task.get("input", {}))
        analysis_type = task.get("analysis_type", "general")
        focus = task.get("focus", "insights")

        system = (
            "You are a data analyst. Analyze the provided data and extract "
            "key insights, patterns, and actionable recommendations."
        )
        prompt = (
            f"Analysis type: {analysis_type}\n"
            f"Focus: {focus}\n"
            f"Data: {json.dumps(data, ensure_ascii=False)[:2000] if isinstance(data, (dict, list)) else str(data)[:2000]}\n\n"
            f"Provide:\n"
            f"1. Key insights (3-5)\n"
            f"2. Patterns identified\n"
            f"3. Recommendations"
        )

        try:
            llm_output = await self._llm_generate(prompt, system)
        except Exception:
            llm_output = None

        result = {
            "analysis_type": analysis_type,
            "focus": focus,
            "insights": llm_output or f"Analysis completed for {analysis_type}",
            "status": "completed",
        }

        self.update_status("idle")
        return result
