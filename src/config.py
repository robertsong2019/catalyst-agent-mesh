"""
Configuration for Catalyst Agent Mesh
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MeshConfig:
    """Central configuration"""
    # LLM Settings
    default_provider: str = "mock"  # "mock", "ollama", "openai"
    ollama_model: str = "llama3.2"
    ollama_base_url: str = "http://localhost:11434"
    openai_model: str = "gpt-4o-mini"
    openai_api_key: Optional[str] = None

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Pipeline Settings
    max_workers: int = 10
    default_max_concurrent: int = 3

    # Logging
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "MeshConfig":
        """Load config from environment variables"""
        return cls(
            default_provider=os.getenv("MESH_LLM_PROVIDER", "mock"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            host=os.getenv("MESH_HOST", "0.0.0.0"),
            port=int(os.getenv("MESH_PORT", "8000")),
            debug=os.getenv("MESH_DEBUG", "").lower() in ("1", "true", "yes"),
            log_level=os.getenv("MESH_LOG_LEVEL", "INFO"),
        )
