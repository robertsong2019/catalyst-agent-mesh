"""Tests for TaskScheduler — priority queue scheduling, retry, stats"""

import pytest
from src.mesh.task_scheduler import TaskScheduler, ScheduledTask


# --- ScheduledTask unit tests ---

class TestScheduledTask:
    def test_default_fields(self):
        t = ScheduledTask({"type": "research"})
        assert t.status == "pending"
        assert t.priority == 0
        assert t.deadline is None
        assert t.retry_count == 0
        assert t.max_retries == 0

    def test_custom_priority(self):
        t = ScheduledTask({}, priority=5, deadline="2026-12-31T23:59:59")
        assert t.priority == 5
        assert t.deadline == "2026-12-31T23:59:59"

    def test_lt_by_priority(self):
        high = ScheduledTask({}, priority=0)
        low = ScheduledTask({}, priority=10)
        assert high < low

    def test_lt_same_priority_by_time(self):
        t1 = ScheduledTask({})
        t2 = ScheduledTask({})
        # Both created nearly simultaneously, but t1 has earlier created_at
        t2.created_at = "2099-01-01T00:00:00"
        assert t1 < t2

    def test_custom_id(self):
        t = ScheduledTask({}, task_id="my-id")
        assert t.id == "my-id"

    def test_max_retries_from_data(self):
        t = ScheduledTask({"max_retries": 3})
        assert t.max_retries == 3


# --- TaskScheduler core tests ---

class TestTaskScheduler:
    def test_schedule_returns_id(self):
        s = TaskScheduler()
        tid = s.schedule({"type": "research"})
        assert tid
        assert s.get_task(tid) is not None

    def test_schedule_sets_status_scheduled(self):
        s = TaskScheduler()
        tid = s.schedule({})
        assert s.get_task(tid)["status"] == "scheduled"

    def test_schedule_with_priority(self):
        s = TaskScheduler()
        tid = s.schedule({}, priority=10)
        assert s.get_task(tid)["priority"] == 10

    def test_next_batch_respects_max_concurrent(self):
        s = TaskScheduler(max_concurrent=2)
        s.schedule({})
        s.schedule({})
        s.schedule({})
        batch = s.next_batch()
        assert len(batch) == 2

    def test_next_batch_marks_running(self):
        s = TaskScheduler(max_concurrent=3)
        s.schedule({})
        batch = s.next_batch()
        assert batch[0].status == "running"

    def test_next_batch_empty_queue(self):
        s = TaskScheduler()
        assert s.next_batch() == []

    def test_next_batch_respects_running_slots(self):
        s = TaskScheduler(max_concurrent=2)
        s.schedule({})
        s.schedule({})
        batch1 = s.next_batch()  # takes 2
        s.schedule({})
        batch2 = s.next_batch()  # 2 running, 0 available
        assert len(batch2) == 0

    def test_complete_task(self):
        s = TaskScheduler()
        tid = s.schedule({})
        batch = s.next_batch()
        ok = s.complete(batch[0].id, {"status": "done"})
        assert ok
        assert s.get_task(batch[0].id)["status"] == "completed"
        assert s.get_task(batch[0].id)["result"] == {"status": "done"}

    def test_complete_nonexistent(self):
        s = TaskScheduler()
        assert s.complete("fake-id", {}) is False

    def test_fail_task_no_retry(self):
        s = TaskScheduler()
        s.schedule({})
        batch = s.next_batch()
        s.fail(batch[0].id, "error")
        assert s.get_task(batch[0].id)["status"] == "failed"

    def test_fail_task_with_retry(self):
        s = TaskScheduler()
        s.schedule({"max_retries": 2})
        batch = s.next_batch()
        result = s.fail(batch[0].id, "transient error")
        assert result is True  # retried
        assert s.get_task(batch[0].id)["retry_count"] == 1
        assert s.get_task(batch[0].id)["status"] == "scheduled"

    def test_fail_task_exhausts_retries(self):
        s = TaskScheduler()
        s.schedule({"max_retries": 1})
        batch = s.next_batch()
        s.fail(batch[0].id, "error 1")  # retry
        # Re-fetch from queue
        batch2 = s.next_batch()
        s.fail(batch2[0].id, "error 2")  # exhausted
        assert s.get_task(batch[0].id)["status"] == "failed"
        assert s.get_task(batch[0].id)["retry_count"] == 2

    def test_reschedule_priority(self):
        s = TaskScheduler()
        tid = s.schedule({}, priority=5)
        ok = s.reschedule(tid, new_priority=1)
        assert ok
        assert s.get_task(tid)["priority"] == 1

    def test_reschedule_deadline(self):
        s = TaskScheduler()
        tid = s.schedule({})
        ok = s.reschedule(tid, new_deadline="2026-12-31T00:00:00")
        assert ok
        assert s.get_task(tid)["deadline"] == "2026-12-31T00:00:00"

    def test_reschedule_completed_fails(self):
        s = TaskScheduler()
        tid = s.schedule({})
        batch = s.next_batch()
        s.complete(batch[0].id, {})
        assert s.reschedule(tid, new_priority=1) is False

    def test_cancel_task(self):
        s = TaskScheduler()
        tid = s.schedule({})
        assert s.cancel(tid) is True
        assert s.get_task(tid)["status"] == "cancelled"

    def test_cancel_running_fails(self):
        s = TaskScheduler()
        s.schedule({})
        batch = s.next_batch()
        assert s.cancel(batch[0].id) is False

    def test_cancel_nonexistent(self):
        s = TaskScheduler()
        assert s.cancel("fake") is False

    def test_priority_ordering(self):
        s = TaskScheduler(max_concurrent=3)
        low = s.schedule({"name": "low"}, priority=10)
        high = s.schedule({"name": "high"}, priority=0)
        mid = s.schedule({"name": "mid"}, priority=5)
        batch = s.next_batch()
        names = [t.data["name"] for t in batch]
        assert names == ["high", "mid", "low"]

    def test_get_stats(self):
        s = TaskScheduler()
        s.schedule({})
        s.schedule({})
        batch = s.next_batch()
        s.complete(batch[0].id, {})
        stats = s.get_stats()
        assert stats["total_scheduled"] == 2
        assert stats["completed"] == 1
        assert stats["queued"] == 0  # both popped

    def test_clear_completed(self):
        s = TaskScheduler()
        s.schedule({})
        batch = s.next_batch()
        s.complete(batch[0].id, {})
        removed = s.clear_completed()
        assert removed == 1
        assert s.get_task(batch[0].id) is None

    def test_get_overdue_tasks(self):
        s = TaskScheduler()
        s.schedule({}, deadline="2020-01-01T00:00:00")
        overdue = s.get_overdue_tasks()
        assert len(overdue) == 1

    def test_get_overdue_empty(self):
        s = TaskScheduler()
        s.schedule({}, deadline="2099-01-01T00:00:00")
        assert s.get_overdue_tasks() == []

    def test_get_task_nonexistent(self):
        s = TaskScheduler()
        assert s.get_task("nobody") is None
