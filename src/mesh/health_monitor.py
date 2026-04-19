"""
Health Monitor — tracks agent health, detects failures, auto-disables unhealthy agents
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
import uuid


class HealthCheck:
    """A single health check record"""

    def __init__(self, agent_id: str, healthy: bool, latency_ms: float = 0.0,
                 message: str = "", check_id: Optional[str] = None):
        self.id = check_id or str(uuid.uuid4())
        self.agent_id = agent_id
        self.healthy = healthy
        self.latency_ms = latency_ms
        self.message = message
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "healthy": self.healthy,
            "latency_ms": self.latency_ms,
            "message": self.message,
            "timestamp": self.timestamp,
        }


class HealthMonitor:
    """Monitors agent health with configurable thresholds and history"""

    def __init__(self, failure_threshold: int = 3, recovery_threshold: int = 2,
                 history_size: int = 100):
        self.failure_threshold = failure_threshold
        self.recovery_threshold = recovery_threshold
        self.history_size = history_size
        self._checks: Dict[str, List[HealthCheck]] = {}  # agent_id -> checks
        self._health_scores: Dict[str, float] = {}  # agent_id -> 0..1
        self._disabled_agents: set = set()
        self._checkers: Dict[str, Callable] = {}  # agent_id -> health check fn

    def register_checker(self, agent_id: str, checker: Callable[[], bool]):
        """Register a health check function for an agent."""
        self._checkers[agent_id] = checker

    def record(self, agent_id: str, healthy: bool, latency_ms: float = 0.0,
               message: str = "") -> HealthCheck:
        """Record a health check result."""
        check = HealthCheck(agent_id, healthy, latency_ms, message)
        if agent_id not in self._checks:
            self._checks[agent_id] = []
        history = self._checks[agent_id]
        history.append(check)
        # Trim to history_size
        if len(history) > self.history_size:
            self._checks[agent_id] = history[-self.history_size:]
        self._update_score(agent_id)
        self._check_thresholds(agent_id)
        return check

    def run_check(self, agent_id: str) -> Optional[HealthCheck]:
        """Run the registered health checker for an agent."""
        checker = self._checkers.get(agent_id)
        if not checker:
            return None
        try:
            healthy = checker()
            return self.record(agent_id, healthy, message="auto-check")
        except Exception as e:
            return self.record(agent_id, False, message=f"check error: {e}")

    def is_healthy(self, agent_id: str) -> bool:
        """Check if an agent is healthy (not disabled)."""
        return agent_id not in self._disabled_agents

    def get_score(self, agent_id: str) -> float:
        """Get health score (0..1) for an agent."""
        return self._health_scores.get(agent_id, 1.0)

    def get_history(self, agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent health check history for an agent."""
        checks = self._checks.get(agent_id, [])
        return [c.to_dict() for c in checks[-limit:]]

    def get_unhealthy_agents(self) -> List[str]:
        """Get list of disabled/unhealthy agent IDs."""
        return list(self._disabled_agents)

    def force_recover(self, agent_id: str) -> bool:
        """Manually recover a disabled agent."""
        if agent_id in self._disabled_agents:
            self._disabled_agents.discard(agent_id)
            self._health_scores[agent_id] = 1.0
            return True
        return False

    def force_disable(self, agent_id: str) -> bool:
        """Manually disable an agent."""
        self._disabled_agents.add(agent_id)
        self._health_scores[agent_id] = 0.0
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get overall health monitor statistics."""
        total = len(self._health_scores) or 1
        healthy = total - len(self._disabled_agents)
        scores = list(self._health_scores.values()) or [1.0]
        return {
            "total_agents": len(self._health_scores),
            "healthy_agents": healthy,
            "unhealthy_agents": len(self._disabled_agents),
            "avg_score": sum(scores) / len(scores),
            "total_checks": sum(len(h) for h in self._checks.values()),
        }

    def reset(self):
        """Reset all state."""
        self._checks.clear()
        self._health_scores.clear()
        self._disabled_agents.clear()
        self._checkers.clear()

    def _update_score(self, agent_id: str):
        """Recalculate health score based on recent checks."""
        checks = self._checks.get(agent_id, [])
        if not checks:
            self._health_scores[agent_id] = 1.0
            return
        recent = checks[-20:]  # last 20 checks
        healthy_count = sum(1 for c in recent if c.healthy)
        self._health_scores[agent_id] = healthy_count / len(recent)

    def _check_thresholds(self, agent_id: str):
        """Check if agent should be disabled or recovered."""
        checks = self._checks.get(agent_id, [])
        if len(checks) < self.failure_threshold:
            return

        # Check for consecutive failures
        recent = checks[-self.failure_threshold:]
        if all(not c.healthy for c in recent):
            self._disabled_agents.add(agent_id)

        # Check for recovery (if currently disabled)
        if agent_id in self._disabled_agents and len(checks) >= self.recovery_threshold:
            recovery_window = checks[-self.recovery_threshold:]
            if all(c.healthy for c in recovery_window):
                self._disabled_agents.discard(agent_id)
