"""Tests for HealthMonitor — health tracking, auto-disable, recovery"""

import pytest
from src.mesh.health_monitor import HealthMonitor, HealthCheck


class TestHealthCheck:
    def test_to_dict(self):
        hc = HealthCheck("agent-1", True, latency_ms=12.5, message="ok")
        d = hc.to_dict()
        assert d["agent_id"] == "agent-1"
        assert d["healthy"] is True
        assert d["latency_ms"] == 12.5

    def test_custom_id(self):
        hc = HealthCheck("a", False, check_id="my-check")
        assert hc.id == "my-check"


class TestHealthMonitor:
    def test_record_check(self):
        m = HealthMonitor()
        c = m.record("a1", True)
        assert c.healthy is True

    def test_default_healthy(self):
        m = HealthMonitor()
        assert m.is_healthy("a1") is True

    def test_score_starts_at_1(self):
        m = HealthMonitor()
        assert m.get_score("a1") == 1.0

    def test_score_after_healthy_checks(self):
        m = HealthMonitor()
        for _ in range(5):
            m.record("a1", True)
        assert m.get_score("a1") == 1.0

    def test_score_mixed(self):
        m = HealthMonitor()
        m.record("a1", True)
        m.record("a1", False)
        assert 0.0 < m.get_score("a1") < 1.0

    def test_auto_disable_after_consecutive_failures(self):
        m = HealthMonitor(failure_threshold=3)
        for _ in range(3):
            m.record("a1", False)
        assert m.is_healthy("a1") is False
        assert "a1" in m.get_unhealthy_agents()

    def test_no_disable_below_threshold(self):
        m = HealthMonitor(failure_threshold=3)
        m.record("a1", False)
        m.record("a1", False)
        assert m.is_healthy("a1") is True

    def test_interleaved_failures_no_disable(self):
        m = HealthMonitor(failure_threshold=3)
        m.record("a1", False)
        m.record("a1", True)
        m.record("a1", False)
        assert m.is_healthy("a1") is True

    def test_auto_recovery(self):
        m = HealthMonitor(failure_threshold=3, recovery_threshold=2)
        for _ in range(3):
            m.record("a1", False)
        assert m.is_healthy("a1") is False
        for _ in range(2):
            m.record("a1", True)
        assert m.is_healthy("a1") is True

    def test_force_recover(self):
        m = HealthMonitor(failure_threshold=3)
        for _ in range(3):
            m.record("a1", False)
        assert m.force_recover("a1") is True
        assert m.is_healthy("a1") is True

    def test_force_recover_non_disabled(self):
        m = HealthMonitor()
        assert m.force_recover("a1") is False

    def test_force_disable(self):
        m = HealthMonitor()
        m.force_disable("a1")
        assert m.is_healthy("a1") is False

    def test_get_history(self):
        m = HealthMonitor()
        for i in range(5):
            m.record("a1", i % 2 == 0)
        history = m.get_history("a1", limit=3)
        assert len(history) == 3

    def test_get_history_empty(self):
        m = HealthMonitor()
        assert m.get_history("a1") == []

    def test_register_and_run_checker(self):
        m = HealthMonitor()
        m.register_checker("a1", lambda: True)
        check = m.run_check("a1")
        assert check is not None
        assert check.healthy is True

    def test_run_checker_exception(self):
        m = HealthMonitor()
        m.register_checker("a1", lambda: 1 / 0)
        check = m.run_check("a1")
        assert check is not None
        assert check.healthy is False

    def test_run_checker_not_registered(self):
        m = HealthMonitor()
        assert m.run_check("a1") is None

    def test_stats(self):
        m = HealthMonitor()
        m.record("a1", True)
        m.record("a2", False)
        stats = m.get_stats()
        assert stats["total_agents"] == 2
        assert stats["total_checks"] == 2

    def test_stats_empty(self):
        m = HealthMonitor()
        stats = m.get_stats()
        assert stats["total_agents"] == 0
        assert stats["avg_score"] == 1.0

    def test_reset(self):
        m = HealthMonitor()
        m.record("a1", True)
        m.reset()
        assert m.get_score("a1") == 1.0
        assert m.get_history("a1") == []

    def test_history_trim(self):
        m = HealthMonitor(history_size=5)
        for i in range(10):
            m.record("a1", True)
        assert len(m._checks["a1"]) == 5
