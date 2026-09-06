"""Regression tests for `tasks/service` (NUMA-142 P6).

Agent task creation. Each test names the defect it guards against, so a change
that reintroduces it fails here with the reason rather than a bare
assertion.
"""

import pytest


def test_agent_created_tasks_carry_a_priority():
    """The shared tools advertised `priority` and dropped it before the row."""
    import inspect

    from src.tasks.repository import TaskRepository
    from src.tasks.service import create_task_for_user

    assert "priority" in inspect.signature(create_task_for_user).parameters
    assert "priority" in inspect.signature(TaskRepository.upsert_agent_task).parameters


def test_master_task_tools_are_the_shared_ones():
    """The master agent re-implemented the four tools and lost `priority`."""
    import inspect

    from src.master_agent.subagents.task_agent import _task_toolset

    assert "make_task_tools" in inspect.getsource(_task_toolset)
