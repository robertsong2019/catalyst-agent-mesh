"""
Task Scheduler Module — Priority-based task scheduling for agent mesh
"""

import heapq
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid


class ScheduledTask:
    """A task with priority, deadline, and scheduling metadata"""

    def __init__(self, task_data: Dict[str, Any], priority: int = 0,
                 deadline: Optional[str] = None, task_id: Optional[str] = None):
        self.id = task_id or str(uuid.uuid4())
        self.data = task_data
        self.priority = priority  # lower = higher priority
        self.deadline = deadline
        self.status = "pending"  # pending | scheduled | running | completed | failed | cancelled
        self.created_at = datetime.now().isoformat()
        self.scheduled_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.result: Optional[Dict[str, Any]] = None
        self.retry_count = 0
        self.max_retries = task_data.get("max_retries", 0)

    def __lt__(self, other: 'ScheduledTask') -> bool:
        """Compare by priority (lower number = higher priority), then by creation time"""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.created_at < other.created_at


class TaskScheduler:
    """Priority-based task scheduler for the agent mesh"""

    def __init__(self, agent_mesh=None, max_concurrent: int = 5):
        self.agent_mesh = agent_mesh
        self.max_concurrent = max_concurrent
        self._queue: List[ScheduledTask] = []  # min-heap
        self._tasks: Dict[str, ScheduledTask] = {}  # id -> task
        self._running: Dict[str, ScheduledTask] = {}  # id -> task
        self._completed: Dict[str, ScheduledTask] = {}  # id -> task
        self._counter = 0

    def schedule(self, task_data: Dict[str, Any], priority: int = 0,
                 deadline: Optional[str] = None) -> str:
        """Add a task to the scheduler. Returns task ID."""
        task = ScheduledTask(task_data, priority, deadline)
        task.status = "scheduled"
        task.scheduled_at = datetime.now().isoformat()
        heapq.heappush(self._queue, task)
        self._tasks[task.id] = task
        self._counter += 1
        return task.id

    def reschedule(self, task_id: str, new_priority: Optional[int] = None,
                   new_deadline: Optional[str] = None) -> bool:
        """Update priority/deadline of a scheduled task. Returns False if not found or not reschedulable."""
        task = self._tasks.get(task_id)
        if not task or task.status not in ("pending", "scheduled"):
            return False
        if new_priority is not None:
            task.priority = new_priority
        if new_deadline is not None:
            task.deadline = new_deadline
        # Rebuild heap (priority changed)
        self._rebuild_queue()
        return True

    def cancel(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        task = self._tasks.get(task_id)
        if not task or task.status in ("completed", "failed", "cancelled", "running"):
            return False
        task.status = "cancelled"
        task.completed_at = datetime.now().isoformat()
        self._rebuild_queue()
        return True

    def next_batch(self, limit: Optional[int] = None) -> List[ScheduledTask]:
        """Pop the next batch of tasks up to max_concurrent (or limit)."""
        max_take = limit or self.max_concurrent
        available = max_take - len(self._running)
        if available <= 0:
            return []
        batch = []
        while self._queue and len(batch) < available:
            task = heapq.heappop(self._queue)
            if task.status in ("pending", "scheduled"):
                task.status = "running"
                self._running[task.id] = task
                batch.append(task)
        return batch

    def complete(self, task_id: str, result: Dict[str, Any]) -> bool:
        """Mark a running task as completed."""
        task = self._running.pop(task_id, None)
        if not task:
            return False
        task.status = "completed"
        task.completed_at = datetime.now().isoformat()
        task.result = result
        self._completed[task.id] = task
        return True

    def fail(self, task_id: str, error: str) -> bool:
        """Mark a running task as failed. Retry if retries remain."""
        task = self._running.pop(task_id, None)
        if not task:
            return False
        task.retry_count += 1
        if task.retry_count <= task.max_retries:
            # Re-schedule for retry
            task.status = "scheduled"
            heapq.heappush(self._queue, task)
            return True
        task.status = "failed"
        task.completed_at = datetime.now().isoformat()
        task.result = {"error": error}
        self._completed[task.id] = task
        return True

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task info by ID."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        return {
            "id": task.id,
            "status": task.status,
            "priority": task.priority,
            "deadline": task.deadline,
            "created_at": task.created_at,
            "scheduled_at": task.scheduled_at,
            "completed_at": task.completed_at,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "result": task.result,
        }

    def get_overdue_tasks(self) -> List[Dict[str, Any]]:
        """Get tasks that have passed their deadline."""
        now = datetime.now().isoformat()
        overdue = []
        for task in self._tasks.values():
            if task.deadline and task.status in ("pending", "scheduled") and task.deadline < now:
                overdue.append(self.get_task(task.id))
        return overdue

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        return {
            "total_scheduled": self._counter,
            "queued": len(self._queue),
            "running": len(self._running),
            "completed": len(self._completed),
            "pending": sum(1 for t in self._tasks.values() if t.status in ("pending", "scheduled")),
        }

    def clear_completed(self) -> int:
        """Remove completed/failed/cancelled tasks. Returns count removed."""
        to_remove = [tid for tid, t in self._completed.items()
                     if t.status in ("completed", "failed", "cancelled")]
        for tid in to_remove:
            del self._completed[tid]
            del self._tasks[tid]
        return len(to_remove)

    def _rebuild_queue(self):
        """Rebuild the heap after priority changes."""
        self._queue = [t for t in self._queue if t.status in ("pending", "scheduled")]
        heapq.heapify(self._queue)
