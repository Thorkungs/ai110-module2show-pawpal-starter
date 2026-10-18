"""PawPal+ logic layer: the backend classes for the pet care planner.

Classes
-------
Task       one care activity (walk, feeding, meds, appointment)
Pet        a pet plus the tasks that belong to it
Owner      the person, their pets, their daily time budget, and JSON save/load
Scheduler  the "brain" that reads every pet's tasks through the Owner
PlanEntry  one task placed in a DailyPlan, with its planned time and the reason
DailyPlan  the result of Scheduler.build_daily_plan(): what fits today and why
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields, replace
from datetime import date, datetime, time, timedelta
from itertools import combinations
from pathlib import Path
from uuid import uuid4

VALID_PRIORITIES = ("low", "medium", "high")
VALID_FREQUENCIES = ("once", "daily", "weekly")
PRIORITY_RANK = {"high": 3, "medium": 2, "low": 1}
RECURRENCE_STEP = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1)}
DATA_VERSION = 1

# ---- Presentation helpers shared by the CLI (main.py) and the Streamlit UI (app.py) ----

PRIORITY_BADGES = {"high": "🔴 high", "medium": "🟡 medium", "low": "🟢 low"}
_TASK_EMOJIS = (
    (("vet", "checkup", "appointment", "doctor"), "🩺"),
    (("med", "pill", "flea", "vaccine", "insulin", "dose"), "💊"),
    (("walk", "run", "hike"), "🦮"),
    (("breakfast", "lunch", "dinner", "feed", "food", "meal", "treat"), "🍖"),
    (("groom", "brush", "bath", "nail", "trim"), "🧼"),
    (("litter", "clean", "poop"), "🧹"),
    (("play", "toy", "fetch", "train", "enrich"), "🎾"),
    (("water",), "💧"),
)


def task_emoji(description: str) -> str:
    """Pick an emoji for a task based on keywords in its description."""
    text = description.lower()
    return next((emoji for words, emoji in _TASK_EMOJIS if any(w in text for w in words)), "🐾")


def normalize_time(value: str | time) -> str:
    """Convert '8:00', '08:00', or a datetime.time into zero padded 'HH:MM'."""
    if isinstance(value, time):
        return value.strftime("%H:%M")
    try:
        parsed = datetime.strptime(str(value).strip(), "%H:%M")
    except ValueError:
        raise ValueError(f"Invalid time {value!r}: use 24 hour HH:MM, like 08:30") from None
    return parsed.strftime("%H:%M")


def _at(day: date, hhmm: str) -> datetime:
    """Combine a date and an 'HH:MM' string into a datetime."""
    return datetime.combine(day, datetime.strptime(normalize_time(hhmm), "%H:%M").time())


def first_free_slot(
    busy: list[tuple[datetime, datetime]],
    duration: timedelta,
    earliest: datetime,
    latest: datetime,
) -> datetime | None:
    """Return the earliest start >= `earliest` where `duration` fits before `latest` without touching a busy window."""
    cursor = earliest
    for start, end in sorted(busy):
        if end <= cursor:
            continue  # this busy window is already behind us
        if start - cursor >= duration:
            break  # the gap before this window is big enough
        cursor = end  # jump past the window and keep looking
    return cursor if cursor + duration <= latest else None


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
        return _at(self.due_date, self.time)

    @property
    def end(self) -> datetime:
        """Return when the task finishes, based on its duration."""
        return self.start + timedelta(minutes=self.duration_minutes)

    def overlaps(self, other: Task) -> bool:
        """Return True if this task's time window overlaps another task's window."""
        return self.start < other.end and other.start < self.end

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def next_occurrence(self) -> Task | None:
        """Return the next instance of a recurring task, or None for one time tasks."""
        step = RECURRENCE_STEP.get(self.frequency)
        if step is None:
            return None
        return replace(
            self,
            due_date=self.due_date + step,
            completed=False,
            task_id=uuid4().hex[:8],
        )

    def to_dict(self) -> dict:
        """Serialize to a JSON friendly dict (dates become ISO strings)."""
        data = asdict(self)
        data["due_date"] = self.due_date.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        """Rebuild a Task from to_dict() output, ignoring any unknown keys."""
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


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

    def to_dict(self) -> dict:
        """Serialize the pet and its tasks to a JSON friendly dict."""
        return {
            "name": self.name,
            "species": self.species,
            "breed": self.breed,
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Pet:
        """Rebuild a Pet (and re-stamp its tasks) from to_dict() output."""
        pet = cls(name=data["name"], species=data.get("species", "dog"), breed=data.get("breed", ""))
        for task_data in data.get("tasks", []):
            pet.add_task(Task.from_dict(task_data))
        return pet


@dataclass
class Owner:
    """The pet owner: their pets, daily time budget, and the hours they're available."""

    name: str
    available_minutes: int = 120
    day_start: str = "07:00"
    day_end: str = "21:00"
    pets: list[Pet] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Normalize the day window and make sure it makes sense."""
        self.day_start = normalize_time(self.day_start)
        self.day_end = normalize_time(self.day_end)
        if self.day_start >= self.day_end:
            raise ValueError("day_start must be earlier than day_end")
        if int(self.available_minutes) < 0:
            raise ValueError("available_minutes cannot be negative")
        self.available_minutes = int(self.available_minutes)

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

    def to_dict(self) -> dict:
        """Serialize the owner, pets, and tasks to a JSON friendly dict."""
        return {
            "version": DATA_VERSION,
            "name": self.name,
            "available_minutes": self.available_minutes,
            "day_start": self.day_start,
            "day_end": self.day_end,
            "pets": [p.to_dict() for p in self.pets],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Owner:
        """Rebuild an Owner from to_dict() output."""
        owner = cls(
            name=data["name"],
            available_minutes=data.get("available_minutes", 120),
            day_start=data.get("day_start", "07:00"),
            day_end=data.get("day_end", "21:00"),
        )
        for pet_data in data.get("pets", []):
            owner.add_pet(Pet.from_dict(pet_data))
        return owner

    def save_to_json(self, path: str | Path = "data.json") -> Path:
        """Write everything to a JSON file (via a temp file so a crash can't corrupt it)."""
        path = Path(path)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(path)
        return path

    @classmethod
    def load_from_json(cls, path: str | Path = "data.json") -> Owner:
        """Load an Owner previously written by save_to_json()."""
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass
class PlanEntry:
    """One task placed in a DailyPlan, with its planned window and the reason it's there."""

    task: Task
    start: datetime
    end: datetime
    reason: str
    moved: bool = False


@dataclass
class DailyPlan:
    """What fits in the owner's day, in time order, plus what was skipped and why."""

    day: date
    budget_minutes: int
    entries: list[PlanEntry] = field(default_factory=list)
    skipped: list[tuple[Task, str]] = field(default_factory=list)

    @property
    def used_minutes(self) -> int:
        """Total minutes of care in the plan."""
        return sum(e.task.duration_minutes for e in self.entries)

    def explain(self) -> str:
        """Return a short summary of the plan and the reasoning behind it."""
        lines = [
            f"Planned {len(self.entries)} task(s) using {self.used_minutes} of "
            f"{self.budget_minutes} available minutes. Highest priority tasks were placed first."
        ]
        moved = [e for e in self.entries if e.moved]
        if moved:
            lines.append(f"{len(moved)} task(s) were moved to a free slot to avoid overlaps.")
        if self.skipped:
            lines.append(f"{len(self.skipped)} task(s) didn't fit and were skipped.")
        return " ".join(lines)


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

    # ---- Sorting and filtering -------------------------------------------------

    def sort_by_time(self, tasks: list[Task] | None = None) -> list[Task]:
        """Return tasks in chronological order (by date, then 'HH:MM' time)."""
        tasks = self.get_all_tasks() if tasks is None else tasks
        # Times are normalized to zero padded "HH:MM", so plain string order is clock order.
        return sorted(tasks, key=lambda t: (t.due_date, t.time))

    def sort_by_priority(self, tasks: list[Task] | None = None) -> list[Task]:
        """Return tasks highest priority first, breaking ties by date and then time."""
        tasks = self.get_all_tasks() if tasks is None else tasks
        return sorted(tasks, key=lambda t: (-PRIORITY_RANK[t.priority], t.due_date, t.time))

    def filter_tasks(
        self,
        pet_name: str | None = None,
        completed: bool | None = None,
        day: date | None = None,
        tasks: list[Task] | None = None,
    ) -> list[Task]:
        """Return tasks matching every filter given (pet, completion status, date); None means 'any'."""
        tasks = self.get_all_tasks() if tasks is None else tasks
        return [
            t
            for t in tasks
            if (pet_name is None or t.pet_name.lower() == pet_name.lower())
            and (completed is None or t.completed == completed)
            and (day is None or t.due_date == day)
        ]

    # ---- Recurring tasks ---------------------------------------------------------

    def _find_task(self, task_id: str) -> tuple[Pet, Task]:
        """Locate a task (and the pet that owns it) anywhere in the owner's pets."""
        for pet in self.owner.pets:
            task = pet.get_task(task_id)
            if task is not None:
                return pet, task
        raise KeyError(f"No task with id {task_id!r}")

    def mark_task_complete(self, task_id: str) -> Task | None:
        """Complete a task; if it repeats, add and return its next occurrence."""
        pet, task = self._find_task(task_id)
        if task.completed:
            return None  # completing twice must not spawn a second copy
        task.mark_complete()
        upcoming = task.next_occurrence()
        if upcoming is not None:
            pet.add_task(upcoming)
        return upcoming

    # ---- Conflict detection ------------------------------------------------------

    def find_conflicts(self, day: date | None = None) -> list[tuple[Task, Task]]:
        """Return every pair of pending tasks on a day whose time windows overlap."""
        day = day or date.today()
        pending = self.sort_by_time(self.filter_tasks(completed=False, day=day))
        return [(a, b) for a, b in combinations(pending, 2) if a.overlaps(b)]

    def detect_conflicts(self, day: date | None = None) -> list[str]:
        """Return readable warnings for overlapping tasks instead of raising errors."""
        warnings = []
        for a, b in self.find_conflicts(day):
            if a.pet_name == b.pet_name:
                warnings.append(
                    f"⚠️ {a.pet_name} has {a.description} ({a.time}, {a.duration_minutes} min) "
                    f"and {b.description} ({b.time}, {b.duration_minutes} min) at the same time"
                )
            else:
                warnings.append(
                    f"⚠️ {a.pet_name}'s {a.description} ({a.time}, {a.duration_minutes} min) "
                    f"overlaps {b.pet_name}'s {b.description} ({b.time}, {b.duration_minutes} min)"
                )
        return warnings

    # ---- Stretch: next available slot ------------------------------------------

    def find_next_available_slot(
        self,
        duration_minutes: int,
        day: date | None = None,
        earliest: str | time | None = None,
    ) -> str | None:
        """Return the first 'HH:MM' in the owner's day where a task of this length fits, or None."""
        day = day or date.today()
        window_start = _at(day, self.owner.day_start)
        start = max(window_start, _at(day, normalize_time(earliest))) if earliest else window_start
        busy = [(t.start, t.end) for t in self.filter_tasks(completed=False, day=day)]
        slot = first_free_slot(busy, timedelta(minutes=duration_minutes), start, _at(day, self.owner.day_end))
        return slot.strftime("%H:%M") if slot else None

    # ---- Stretch: priority based daily plan with time blocking -------------------

    def build_daily_plan(self, day: date | None = None) -> DailyPlan:
        """Greedily fill the owner's time budget by priority, moving lower priority clashes to free slots."""
        day = day or date.today()
        budget = self.owner.available_minutes
        plan = DailyPlan(day=day, budget_minutes=budget)
        day_end = _at(day, self.owner.day_end)

        for task in self.sort_by_priority(self.filter_tasks(completed=False, day=day)):
            remaining = budget - plan.used_minutes
            if task.duration_minutes > remaining:
                plan.skipped.append(
                    (task, f"needs {task.duration_minutes} min but only {remaining} of {budget} min left")
                )
                continue

            clash = next((e for e in plan.entries if e.start < task.end and task.start < e.end), None)
            if clash is None:
                plan.entries.append(
                    PlanEntry(task, task.start, task.end, f"{task.priority} priority, at the requested time")
                )
                continue

            busy = [(e.start, e.end) for e in plan.entries]
            duration = timedelta(minutes=task.duration_minutes)
            slot = first_free_slot(busy, duration, task.start, day_end)
            blocker = f"{clash.task.pet_name}'s {clash.task.description}"
            if slot is None:
                plan.skipped.append((task, f"overlaps {blocker} and no later slot is free before {self.owner.day_end}"))
                continue
            plan.entries.append(
                PlanEntry(
                    task,
                    slot,
                    slot + duration,
                    f"{task.priority} priority, moved from {task.time} to {slot:%H:%M} to avoid {blocker}",
                    moved=True,
                )
            )

        plan.entries.sort(key=lambda e: e.start)
        return plan
