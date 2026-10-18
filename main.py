"""PawPal+ CLI demo: exercises every Scheduler feature in the terminal before the Streamlit UI.

Run with:  python main.py
"""

import os
import sys
import tempfile
from pathlib import Path

from tabulate import tabulate

from pawpal_system import PRIORITY_BADGES, Owner, Pet, Scheduler, Task, task_emoji

# ANSI colors only when printing to a real terminal (and NO_COLOR isn't set), so
# output piped into a file or pasted into the README stays clean.
USE_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ


def heading(text: str) -> None:
    """Print a bold cyan section heading (plain text when color is off)."""
    print(f"\n\033[1;36m{text}\033[0m" if USE_COLOR else f"\n{text}")


def build_demo_owner() -> Owner:
    """Create an owner with two pets; tasks are added out of order on purpose."""
    owner = Owner(name="Jordan", available_minutes=150, day_start="07:00", day_end="21:00")
    biscuit = owner.add_pet(Pet(name="Biscuit", species="dog", breed="Golden Retriever"))
    mochi = owner.add_pet(Pet(name="Mochi", species="cat", breed="Tabby"))

    biscuit.add_task(Task("Vet checkup", "15:00", 60, priority="high"))
    mochi.add_task(Task("Evening play", "18:00", 20, priority="low", frequency="daily"))
    mochi.add_task(Task("Flea medication", "9:00", 5, priority="high", frequency="weekly"))
    biscuit.add_task(Task("Breakfast", "08:15", 10, priority="high", frequency="daily"))
    biscuit.add_task(Task("Grooming and brushing", "17:00", 45, priority="low", frequency="weekly"))
    biscuit.add_task(Task("Morning walk", "07:30", 30, priority="high", frequency="daily"))
    mochi.add_task(Task("Breakfast", "08:30", 10, priority="high", frequency="daily"))
    # Booked at the same time as Biscuit's walk to demonstrate conflict detection.
    mochi.add_task(Task("Litter box cleanup", "07:30", 10, priority="medium", frequency="daily"))
    return owner


def task_table(tasks: list[Task]) -> str:
    """Render tasks as a table with emojis, priority badges, and status icons."""
    rows = [
        [
            f"{t.due_date:%m/%d} {t.time}",
            f"{task_emoji(t.description)} {t.description}",
            t.pet_name,
            t.duration_minutes,
            PRIORITY_BADGES[t.priority],
            t.frequency,
            "✅ done" if t.completed else "⬜ todo",
        ]
        for t in tasks
    ]
    headers = ["When", "Task", "Pet", "Min", "Priority", "Repeats", "Status"]
    return tabulate(rows, headers=headers, tablefmt="rounded_outline") if rows else "(no tasks)"


def main() -> None:
    """Walk through sorting, filtering, conflicts, planning, recurrence, and persistence."""
    owner = build_demo_owner()
    scheduler = Scheduler(owner)
    print(
        f"🐾 PawPal+ demo for {owner.name}: {len(owner.pets)} pets, {len(owner.get_all_tasks())} tasks, "
        f"{owner.available_minutes} min available ({owner.day_start} to {owner.day_end})"
    )

    heading("📅 Today's Schedule: Scheduler.sort_by_time() across all pets")
    print(task_table(scheduler.sort_by_time(scheduler.tasks_for_date())))

    heading("🔎 Filter: Scheduler.filter_tasks(pet_name='Mochi')")
    print(task_table(scheduler.sort_by_time(scheduler.filter_tasks(pet_name="Mochi"))))

    heading("⚠️  Conflict check: Scheduler.detect_conflicts()")
    conflicts = scheduler.find_conflicts()
    for warning in scheduler.detect_conflicts():
        print(warning)
    for _, later in conflicts:
        slot = scheduler.find_next_available_slot(later.duration_minutes, earliest=later.time)
        print(f"💡 Next free {later.duration_minutes} min slot after {later.time}: {slot}  (find_next_available_slot)")
    if not conflicts:
        print("✅ No conflicts today")

    heading("🏆 Priority order: Scheduler.sort_by_priority()")
    print(task_table(scheduler.sort_by_priority(scheduler.tasks_for_date())))

    heading(f"🗓️  Daily plan: Scheduler.build_daily_plan() with a {owner.available_minutes} min budget")
    plan = scheduler.build_daily_plan()
    plan_rows = [
        [
            f"{e.start:%H:%M} to {e.end:%H:%M}",
            f"{task_emoji(e.task.description)} {e.task.description}",
            e.task.pet_name,
            PRIORITY_BADGES[e.task.priority],
            ("🔀 " if e.moved else "") + e.reason,
        ]
        for e in plan.entries
    ]
    print(tabulate(plan_rows, headers=["Planned", "Task", "Pet", "Priority", "Why"], tablefmt="rounded_outline"))
    for task, why in plan.skipped:
        print(f"⏭️  Skipped {task.pet_name}'s {task.description}: {why}")
    print(plan.explain())

    heading("🔁 Recurring tasks: Scheduler.mark_task_complete()")
    walk = next(t for t in owner.get_pet("Biscuit").tasks if t.description == "Morning walk")
    upcoming = scheduler.mark_task_complete(walk.task_id)
    print(f"Marked Biscuit's Morning walk complete. Next occurrence created for {upcoming.due_date:%m/%d} at {upcoming.time}.")
    print(task_table(scheduler.sort_by_time(scheduler.filter_tasks(pet_name="Biscuit", completed=None))))

    heading("💾 Persistence: Owner.save_to_json() / Owner.load_from_json()")
    with tempfile.TemporaryDirectory() as tmp:
        path = owner.save_to_json(Path(tmp) / "data.json")
        reloaded = Owner.load_from_json(path)
        same = reloaded.to_dict() == owner.to_dict()
        print(
            f"Saved and reloaded {len(reloaded.pets)} pets / {len(reloaded.get_all_tasks())} tasks: "
            f"{'✅ round trip matches' if same else '❌ mismatch'}"
        )


if __name__ == "__main__":
    main()
