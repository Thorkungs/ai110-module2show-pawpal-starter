"""Automated tests for the PawPal+ logic layer."""

from datetime import date, timedelta

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task, task_emoji

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


# ---- Stretch: priority sorting, next available slot, daily plan ---------------------


def test_sort_by_priority_puts_high_first_then_time():
    """Priority beats time; ties fall back to chronological order."""
    pet = Pet(name="Biscuit")
    o = Owner(name="Jordan", pets=[pet])
    pet.add_task(Task("Low early", "06:00", 10, priority="low", due_date=DAY))
    pet.add_task(Task("High late", "20:00", 10, priority="high", due_date=DAY))
    pet.add_task(Task("High early", "07:00", 10, priority="high", due_date=DAY))
    pet.add_task(Task("Medium", "12:00", 10, priority="medium", due_date=DAY))
    order = [t.description for t in Scheduler(o).sort_by_priority()]
    assert order == ["High early", "High late", "Medium", "Low early"]


def test_next_available_slot_finds_first_gap(owner):
    """The finder skips busy windows: 07:30 walk ends 08:00, Mochi eats 08:30."""
    scheduler = Scheduler(owner)
    assert scheduler.find_next_available_slot(20, day=DAY, earliest="07:30") == "08:00"
    # 40 minutes doesn't fit between 08:00 and 08:30, so it lands after breakfast.
    assert scheduler.find_next_available_slot(40, day=DAY, earliest="07:30") == "09:05"


def test_next_available_slot_starts_at_owner_day_start(owner):
    """With no 'earliest', the search begins when the owner's day starts."""
    assert Scheduler(owner).find_next_available_slot(15, day=DAY) == "07:00"


def test_next_available_slot_none_when_day_is_full():
    """Edge case: nothing fits, so the finder returns None instead of a bad time."""
    pet = Pet(name="Biscuit")
    o = Owner(name="Jordan", day_start="08:00", day_end="10:00", pets=[pet])
    pet.add_task(Task("Long hike", "08:00", 110, due_date=DAY))
    assert Scheduler(o).find_next_available_slot(15, day=DAY) is None
    assert Scheduler(o).find_next_available_slot(10, day=DAY) == "09:50"


def test_daily_plan_respects_budget_and_priority():
    """Higher priority tasks claim the time budget first; the rest are skipped with a reason."""
    pet = Pet(name="Biscuit")
    o = Owner(name="Jordan", available_minutes=60, pets=[pet])
    pet.add_task(Task("Grooming", "07:00", 40, priority="low", due_date=DAY))
    pet.add_task(Task("Meds", "09:00", 5, priority="high", due_date=DAY))
    pet.add_task(Task("Walk", "10:00", 45, priority="high", due_date=DAY))
    plan = Scheduler(o).build_daily_plan(DAY)
    assert [e.task.description for e in plan.entries] == ["Meds", "Walk"]  # in time order
    assert plan.used_minutes == 50
    assert [(t.description, "only 10 of 60" in why) for t, why in plan.skipped] == [("Grooming", True)]


def test_daily_plan_moves_lower_priority_clash_without_mutating_task(owner):
    """Time blocking: a clashing medium task is moved after the high one; the task itself keeps its time."""
    litter = owner.get_pet("Mochi").add_task(Task("Litter box", "07:30", 10, priority="medium", due_date=DAY))
    owner.available_minutes = 500
    plan = Scheduler(owner).build_daily_plan(DAY)
    entry = next(e for e in plan.entries if e.task is litter)
    assert entry.moved is True
    assert entry.start.strftime("%H:%M") == "08:00"
    assert "Morning walk" in entry.reason
    assert litter.time == "07:30"  # the original request is untouched
    # Core time blocking guarantee: planned windows are in order and never overlap.
    assert all(a.end <= b.start for a, b in zip(plan.entries, plan.entries[1:]))


def test_daily_plan_skips_clash_when_no_slot_is_left():
    """If a clashing task can't be moved before the day ends, it's skipped with an explanation."""
    pet = Pet(name="Biscuit")
    o = Owner(name="Jordan", available_minutes=500, day_end="09:00", pets=[pet])
    pet.add_task(Task("Walk", "08:00", 60, priority="high", due_date=DAY))
    pet.add_task(Task("Brush", "08:30", 15, priority="low", due_date=DAY))
    plan = Scheduler(o).build_daily_plan(DAY)
    assert [e.task.description for e in plan.entries] == ["Walk"]
    assert "no later slot" in plan.skipped[0][1]


def test_daily_plan_ignores_completed_tasks(owner):
    """Completed tasks don't use up the time budget."""
    find(owner, "Biscuit", "Vet checkup").mark_complete()
    plan = Scheduler(owner).build_daily_plan(DAY)
    assert "Vet checkup" not in [e.task.description for e in plan.entries]
    assert plan.used_minutes == 45


# ---- Stretch: JSON persistence and formatting -----------------------------------------


def test_save_and_load_round_trip(owner, tmp_path):
    """Everything saved to JSON comes back identical, including recurrence state."""
    walk = find(owner, "Biscuit", "Morning walk")
    Scheduler(owner).mark_task_complete(walk.task_id)
    path = owner.save_to_json(tmp_path / "data.json")
    loaded = Owner.load_from_json(path)
    assert loaded.to_dict() == owner.to_dict()
    restored = loaded.get_pet("Biscuit").get_task(walk.task_id)
    assert restored.completed is True and restored.due_date == DAY and restored.pet_name == "Biscuit"


def test_load_ignores_unknown_fields(tmp_path):
    """Older or newer JSON with extra keys still loads."""
    o = Owner(name="Jordan")
    o.add_pet(Pet(name="Biscuit")).add_task(Task("Walk", "07:00", 20, due_date=DAY))
    data = o.to_dict()
    data["pets"][0]["tasks"][0]["mood"] = "excited"
    loaded = Owner.from_dict(data)
    assert loaded.get_all_tasks()[0].description == "Walk"


@pytest.mark.parametrize(
    "description, emoji",
    [("Morning walk", "🦮"), ("Breakfast", "🍖"), ("Flea medication", "💊"), ("Vet checkup", "🩺"), ("Nap", "🐾")],
)
def test_task_emoji_matches_keywords(description, emoji):
    """Formatting helper picks an emoji by keyword, with a paw print fallback."""
    assert task_emoji(description) == emoji
