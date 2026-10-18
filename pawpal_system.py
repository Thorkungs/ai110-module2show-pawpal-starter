"""PawPal+ logic layer: the backend classes for the pet care planner.

Phase 1 skeleton generated from diagrams/uml_draft.mmd.
Attributes are defined; method bodies are stubs to be implemented in Phase 2.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Task:
    """A single pet care activity, like a walk, a feeding, or a medication."""

    description: str
    time: str  # "HH:MM"
    duration_minutes: int = 15
    priority: str = "medium"  # low | medium | high
    frequency: str = "once"  # once | daily | weekly
    completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as done."""
        raise NotImplementedError


@dataclass
class Pet:
    """A pet and the list of care tasks that belong to it."""

    name: str
    species: str = "dog"
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a task to this pet."""
        raise NotImplementedError

    def remove_task(self, description: str) -> None:
        """Remove a task from this pet."""
        raise NotImplementedError

    def list_tasks(self) -> list[Task]:
        """Return this pet's tasks."""
        raise NotImplementedError


@dataclass
class Owner:
    """The pet owner, who has one or more pets and a daily time budget."""

    name: str
    available_minutes: int = 120
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        raise NotImplementedError

    def get_pet(self, name: str) -> Pet:
        """Look up a pet by name."""
        raise NotImplementedError

    def get_all_tasks(self) -> list[Task]:
        """Return every task across every pet."""
        raise NotImplementedError


class Scheduler:
    """The 'brain' that organizes tasks across all of an owner's pets."""

    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    def sort_by_time(self) -> list[Task]:
        """Return all tasks in chronological order."""
        raise NotImplementedError

    def filter_tasks(self, pet_name: str | None = None, completed: bool | None = None) -> list[Task]:
        """Return tasks matching a pet name and/or completion status."""
        raise NotImplementedError

    def detect_conflicts(self) -> list[str]:
        """Return warning messages for tasks scheduled at the same time."""
        raise NotImplementedError

    def generate_plan(self) -> list[Task]:
        """Build today's plan from the owner's tasks."""
        raise NotImplementedError
