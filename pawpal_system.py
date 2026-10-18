"""PawPal+ logic layer: the backend classes for the pet care planner.

Classes
-------
Task       one care activity (walk, feeding, meds, appointment)
Pet        a pet plus the tasks that belong to it
Owner      the person, their pets, and their daily time budget
Scheduler  the "brain" that reads every pet's tasks through the Owner
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from uuid import uuid4

VALID_PRIORITIES = ("low", "medium", "high")
VALID_FREQUENCIES = ("once", "daily", "weekly")


def normalize_time(value: str | time) -> str:
    """Convert '8:00', '08:00', or a datetime.time into zero padded 'HH:MM'."""
    if isinstance(value, time):
        return value.strftime("%H:%M")
    try:
        parsed = datetime.strptime(str(value).strip(), "%H:%M")
    except ValueError:
        raise ValueError(f"Invalid time {value!r}: use 24 hour HH:MM, like 08:30") from None
    return parsed.strftime("%H:%M")


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
        self.description = self.description.strip()
        if not self.description:
            raise ValueError("Task description cannot be empty")
        self.time = normalize_time(self.time)
        if int(self.duration_minutes) <= 0:
            raise ValueError("Task duration must be a positive number of minutes")
        self.duration_minutes = int(self.duration_minutes)
        self.priority = self.priority.lower()
        if self.priority not in VALID_PRIORITIES:
            raise ValueError(f"Priority must be one of {VALID_PRIORITIES}")
        self.frequency = self.frequency.lower()
        if self.frequency not in VALID_FREQUENCIES:
            raise ValueError(f"Frequency must be one of {VALID_FREQUENCIES}")
        if isinstance(self.due_date, str):
            self.due_date = date.fromisoformat(self.due_date)

    @property
    def start(self) -> datetime:
        """Return the task's start as a full datetime (due date + time)."""
        return datetime.combine(self.due_date, datetime.strptime(self.time, "%H:%M").time())

    @property
    def end(self) -> datetime:
        """Return when the task finishes, based on its duration."""
        return self.start + timedelta(minutes=self.duration_minutes)

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def next_occurrence(self) -> Task | None:
        """Return the next instance of a recurring task, or None for one time tasks."""
        raise NotImplementedError  # Phase 4


@dataclass
class Pet:
    """A pet and the list of care tasks that belong to it."""

    name: str
    species: str = "dog"
    breed: str = ""
    tasks: list[Task] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Require a non blank pet name."""
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("Pet name cannot be empty")

    def add_task(self, task: Task) -> Task:
        """Attach a task to this pet and stamp it with the pet's name."""
        task.pet_name = self.name
        self.tasks.append(task)
        return task

    def remove_task(self, task_id: str) -> bool:
        """Remove a task by id; return True if something was removed."""
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.task_id != task_id]
        return len(self.tasks) < before

    def get_task(self, task_id: str) -> Task | None:
        """Look up one of this pet's tasks by id."""
        return next((t for t in self.tasks if t.task_id == task_id), None)

    def list_tasks(self, include_completed: bool = True) -> list[Task]:
        """Return this pet's tasks, optionally hiding completed ones."""
        return [t for t in self.tasks if include_completed or not t.completed]

    def task_count(self) -> int:
        """Return how many tasks this pet has."""
        return len(self.tasks)


@dataclass
class Owner:
    """The pet owner, who has one or more pets and a daily time budget."""

    name: str
    available_minutes: int = 120
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> Pet:
        """Add a pet; pet names must be unique for this owner."""
        if self.get_pet(pet.name) is not None:
            raise ValueError(f"{self.name} already has a pet named {pet.name}")
        self.pets.append(pet)
        return pet

    def get_pet(self, name: str) -> Pet | None:
        """Look up a pet by name (case insensitive)."""
        return next((p for p in self.pets if p.name.lower() == name.strip().lower()), None)

    def get_all_tasks(self) -> list[Task]:
        """Return every task across every pet."""
        return [task for pet in self.pets for task in pet.tasks]


class Scheduler:
    """The 'brain' that organizes tasks across all of an owner's pets."""

    def __init__(self, owner: Owner) -> None:
        """Wrap an Owner; the Scheduler never stores its own copy of tasks."""
        self.owner = owner

    def get_all_tasks(self) -> list[Task]:
        """Read tasks through the Owner so every algorithm spans all pets."""
        return self.owner.get_all_tasks()

    def tasks_for_date(self, day: date | None = None) -> list[Task]:
        """Return all tasks due on a given day (default: today)."""
        day = day or date.today()
        return [t for t in self.get_all_tasks() if t.due_date == day]

    def sort_by_time(self, tasks: list[Task] | None = None) -> list[Task]:
        """Return tasks in chronological order."""
        raise NotImplementedError  # Phase 4

    def filter_tasks(self, pet_name: str | None = None, completed: bool | None = None) -> list[Task]:
        """Return tasks matching a pet name and/or completion status."""
        raise NotImplementedError  # Phase 4

    def mark_task_complete(self, task_id: str) -> Task | None:
        """Complete a task and schedule its next occurrence if it repeats."""
        raise NotImplementedError  # Phase 4

    def detect_conflicts(self) -> list[str]:
        """Return warning messages for tasks booked at the same time."""
        raise NotImplementedError  # Phase 4
