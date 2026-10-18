"""PawPal+ logic layer: the backend classes for the pet care planner.

Skeleton generated from diagrams/uml_draft.mmd, then refined after a design
review (see reflection.md section 1b). Method bodies are implemented in Phase 2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from uuid import uuid4

VALID_PRIORITIES = ("low", "medium", "high")
VALID_FREQUENCIES = ("once", "daily", "weekly")


@dataclass
class Task:
    """A single pet care activity, like a walk, a feeding, or a medication."""

    description: str
    time: str  # "HH:MM", normalized to zero padded 24 hour time
    duration_minutes: int = 15
    priority: str = "medium"  # low | medium | high
    frequency: str = "once"  # once | daily | weekly
    due_date: date = field(default_factory=date.today)
    completed: bool = False
    pet_name: str = ""  # back reference, set by Pet.add_task
    task_id: str = field(default_factory=lambda: uuid4().hex[:8])

    def __post_init__(self) -> None:
        """Validate fields and normalize the time string."""
        raise NotImplementedError

    def mark_complete(self) -> None:
        """Mark this task as done."""
        raise NotImplementedError

    def next_occurrence(self) -> Task | None:
        """Return the next instance of a recurring task, or None for one time tasks."""
        raise NotImplementedError


@dataclass
class Pet:
    """A pet and the list of care tasks that belong to it."""

    name: str
    species: str = "dog"
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> Task:
        """Attach a task to this pet and stamp it with the pet's name."""
        raise NotImplementedError

    def remove_task(self, task_id: str) -> bool:
        """Remove a task by id; return True if something was removed."""
        raise NotImplementedError

    def get_task(self, task_id: str) -> Task | None:
        """Look up one of this pet's tasks by id."""
        raise NotImplementedError

    def list_tasks(self, include_completed: bool = True) -> list[Task]:
        """Return this pet's tasks."""
        raise NotImplementedError


@dataclass
class Owner:
    """The pet owner, who has one or more pets and a daily time budget."""

    name: str
    available_minutes: int = 120
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> Pet:
        """Add a pet; pet names must be unique for this owner."""
        raise NotImplementedError

    def get_pet(self, name: str) -> Pet | None:
        """Look up a pet by name."""
        raise NotImplementedError

    def get_all_tasks(self) -> list[Task]:
        """Return every task across every pet."""
        raise NotImplementedError


class Scheduler:
    """The 'brain' that organizes tasks across all of an owner's pets."""

    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    def get_all_tasks(self) -> list[Task]:
        """Read tasks through the Owner so every algorithm spans all pets."""
        raise NotImplementedError

    def sort_by_time(self, tasks: list[Task] | None = None) -> list[Task]:
        """Return tasks in chronological order."""
        raise NotImplementedError

    def filter_tasks(self, pet_name: str | None = None, completed: bool | None = None) -> list[Task]:
        """Return tasks matching a pet name and/or completion status."""
        raise NotImplementedError

    def mark_task_complete(self, task_id: str) -> Task | None:
        """Complete a task and schedule its next occurrence if it repeats."""
        raise NotImplementedError

    def detect_conflicts(self) -> list[str]:
        """Return warning messages for tasks booked at the same time."""
        raise NotImplementedError
