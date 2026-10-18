"""Automated tests for the PawPal+ logic layer."""

from datetime import date, timedelta

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task

DAY = date(2026, 10, 18)  # fixed date so tests don't depend on when they run


@pytest.fixture
def owner() -> Owner:
    """An owner with two pets and tasks added out of chronological order."""
    o = Owner(name="Jordan", available_minutes=120)
    biscuit = o.add_pet(Pet(name="Biscuit", species="dog"))
    mochi = o.add_pet(Pet(name="Mochi", species="cat"))
    biscuit.add_task(Task("Vet checkup", "15:00", 60, priority="medium", due_date=DAY))
    mochi.add_task(Task("Flea medication", "9:00", 5, priority="high", frequency="weekly", due_date=DAY))
    biscuit.add_task(Task("Morning walk", "07:30", 30, priority="high", frequency="daily", due_date=DAY))
    mochi.add_task(Task("Breakfast", "08:30", 10, priority="high", frequency="daily", due_date=DAY))
    return o


def find(owner: Owner, pet: str, description: str) -> Task:
    """Helper: fetch a task by pet name and description."""
    return next(t for t in owner.get_pet(pet).tasks if t.description == description)


# ---- Core classes (Phase 2) ----------------------------------------------------------


def test_mark_complete_changes_status():
    """Calling mark_complete() flips a task from pending to completed."""
    task = Task("Morning walk", "07:30", 30)
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    """Adding a task to a pet grows its task list and stamps the pet's name."""
    pet = Pet(name="Biscuit", species="dog")
    assert pet.task_count() == 0
    task = pet.add_task(Task("Breakfast", "08:00", 10))
    assert pet.task_count() == 1
    assert task.pet_name == "Biscuit"


def test_remove_task_by_id():
    """remove_task() deletes only the matching task and reports success."""
    pet = Pet(name="Biscuit")
    keep = pet.add_task(Task("Breakfast", "08:00", 10))
    drop = pet.add_task(Task("Breakfast", "18:00", 10))
    assert pet.remove_task(drop.task_id) is True
    assert pet.tasks == [keep]
    assert pet.remove_task("nope") is False


def test_owner_rejects_duplicate_pet_names():
    """Pet names are the lookup key, so duplicates (any case) are refused."""
    o = Owner(name="Jordan")
    o.add_pet(Pet(name="Biscuit"))
    with pytest.raises(ValueError):
        o.add_pet(Pet(name="biscuit"))


def test_scheduler_reads_tasks_across_all_pets(owner):
    """The Scheduler sees every pet's tasks through Owner.get_all_tasks()."""
    scheduler = Scheduler(owner)
    assert {t.pet_name for t in scheduler.get_all_tasks()} == {"Biscuit", "Mochi"}
    assert len(scheduler.get_all_tasks()) == 4


@pytest.mark.parametrize("bad", ["25:00", "8am", "", "12:60"])
def test_invalid_time_is_rejected(bad):
    """Bad time strings raise a clear ValueError instead of sorting wrong later."""
    with pytest.raises(ValueError):
        Task("Walk", bad, 10)


def test_invalid_priority_and_duration_are_rejected():
    """Unknown priorities and non positive durations are refused."""
    with pytest.raises(ValueError):
        Task("Walk", "08:00", 10, priority="urgent")
    with pytest.raises(ValueError):
        Task("Walk", "08:00", 0)


# ---- Sorting and filtering (Phase 4) -------------------------------------------------


def test_sort_by_time_returns_chronological_order(owner):
    """Tasks added out of order come back sorted by time across pets."""
    times = [t.time for t in Scheduler(owner).sort_by_time()]
    assert times == ["07:30", "08:30", "09:00", "15:00"]


def test_unpadded_times_sort_correctly():
    """'9:00' is normalized to '09:00' so it sorts before '10:00'."""
    pet = Pet(name="Biscuit")
    o = Owner(name="Jordan", pets=[pet])
    pet.add_task(Task("Late", "10:00", 10, due_date=DAY))
    pet.add_task(Task("Early", "9:00", 10, due_date=DAY))
    assert [t.description for t in Scheduler(o).sort_by_time()] == ["Early", "Late"]


def test_sort_orders_by_date_before_time():
    """A task tomorrow at 06:00 comes after a task today at 20:00."""
    pet = Pet(name="Biscuit")
    o = Owner(name="Jordan", pets=[pet])
    pet.add_task(Task("Tomorrow early", "06:00", 10, due_date=DAY + timedelta(days=1)))
    pet.add_task(Task("Today late", "20:00", 10, due_date=DAY))
    assert [t.description for t in Scheduler(o).sort_by_time()] == ["Today late", "Tomorrow early"]


def test_filter_by_pet_and_status(owner):
    """filter_tasks() combines pet name and completion status filters."""
    scheduler = Scheduler(owner)
    assert {t.description for t in scheduler.filter_tasks(pet_name="mochi")} == {"Flea medication", "Breakfast"}
    find(owner, "Mochi", "Breakfast").mark_complete()
    pending_mochi = scheduler.filter_tasks(pet_name="Mochi", completed=False)
    assert [t.description for t in pending_mochi] == ["Flea medication"]
    assert [t.description for t in scheduler.filter_tasks(completed=True)] == ["Breakfast"]


def test_empty_owner_and_pet_with_no_tasks_do_not_crash():
    """Edge case: no pets, or a pet with no tasks, gives empty results everywhere."""
    empty = Scheduler(Owner(name="Nobody"))
    assert empty.sort_by_time() == []
    assert empty.detect_conflicts(DAY) == []
    lonely = Owner(name="Jordan")
    lonely.add_pet(Pet(name="Biscuit"))
    assert Scheduler(lonely).filter_tasks(pet_name="Biscuit") == []


# ---- Recurring tasks (Phase 4) -------------------------------------------------------


def test_completing_daily_task_creates_next_day(owner):
    """Marking a daily task complete adds a fresh copy due the following day."""
    scheduler = Scheduler(owner)
    walk = find(owner, "Biscuit", "Morning walk")
    upcoming = scheduler.mark_task_complete(walk.task_id)
    assert walk.completed is True
    assert upcoming is not None
    assert upcoming.due_date == DAY + timedelta(days=1)
    assert (upcoming.time, upcoming.completed, upcoming.pet_name) == ("07:30", False, "Biscuit")
    assert upcoming.task_id != walk.task_id
    assert upcoming in owner.get_pet("Biscuit").tasks


def test_completing_weekly_task_creates_next_week(owner):
    """Weekly tasks recur seven days later."""
    meds = find(owner, "Mochi", "Flea medication")
    upcoming = Scheduler(owner).mark_task_complete(meds.task_id)
    assert upcoming.due_date == DAY + timedelta(weeks=1)


def test_one_time_task_does_not_recur(owner):
    """A 'once' task is completed with no follow up instance."""
    vet = find(owner, "Biscuit", "Vet checkup")
    before = owner.get_pet("Biscuit").task_count()
    assert Scheduler(owner).mark_task_complete(vet.task_id) is None
    assert owner.get_pet("Biscuit").task_count() == before


def test_completing_twice_does_not_duplicate(owner):
    """Edge case: double clicking 'complete' must not spawn two future copies."""
    scheduler = Scheduler(owner)
    walk = find(owner, "Biscuit", "Morning walk")
    scheduler.mark_task_complete(walk.task_id)
    assert scheduler.mark_task_complete(walk.task_id) is None
    assert len(scheduler.filter_tasks(pet_name="Biscuit", day=DAY + timedelta(days=1))) == 1


def test_mark_unknown_task_raises(owner):
    """Completing a task id that doesn't exist raises KeyError."""
    with pytest.raises(KeyError):
        Scheduler(owner).mark_task_complete("missing")


# ---- Conflict detection (Phase 4) ----------------------------------------------------


def test_conflict_detected_for_same_time_different_pets(owner):
    """Two pets booked at the exact same time are flagged."""
    owner.get_pet("Mochi").add_task(Task("Litter box", "07:30", 10, due_date=DAY))
    warnings = Scheduler(owner).detect_conflicts(DAY)
    assert len(warnings) == 1
    assert "Morning walk" in warnings[0] and "Litter box" in warnings[0]


def test_conflict_detected_for_overlapping_durations(owner):
    """A task starting during another task's window is a conflict, even with a different start time."""
    owner.get_pet("Biscuit").add_task(Task("Brush teeth", "07:45", 5, due_date=DAY))
    pairs = Scheduler(owner).find_conflicts(DAY)
    assert [(a.description, b.description) for a, b in pairs] == [("Morning walk", "Brush teeth")]
    assert "Biscuit has" in Scheduler(owner).detect_conflicts(DAY)[0]  # same pet wording


def test_back_to_back_tasks_are_not_conflicts(owner):
    """A task that starts exactly when another ends does not overlap."""
    owner.get_pet("Mochi").add_task(Task("Play", "08:00", 15, due_date=DAY))  # walk ends 08:00
    assert Scheduler(owner).detect_conflicts(DAY) == []


def test_completed_tasks_are_ignored_by_conflict_check(owner):
    """Once one of two clashing tasks is done, the warning goes away."""
    clash = owner.get_pet("Mochi").add_task(Task("Litter box", "07:30", 10, due_date=DAY))
    clash.mark_complete()
    assert Scheduler(owner).detect_conflicts(DAY) == []
