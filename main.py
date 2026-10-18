"""PawPal+ CLI demo: a testing ground for the logic layer before the Streamlit UI."""

from pawpal_system import Owner, Pet, Scheduler, Task


def build_demo_owner() -> Owner:
    """Create an owner with two pets; tasks are added out of order on purpose."""
    owner = Owner(name="Jordan", available_minutes=120)
    biscuit = owner.add_pet(Pet(name="Biscuit", species="dog", breed="Golden Retriever"))
    mochi = owner.add_pet(Pet(name="Mochi", species="cat", breed="Tabby"))

    biscuit.add_task(Task("Vet checkup", "15:00", 60, priority="medium"))
    mochi.add_task(Task("Flea medication", "9:00", 5, priority="high", frequency="weekly"))
    biscuit.add_task(Task("Breakfast", "08:15", 10, priority="high", frequency="daily"))
    biscuit.add_task(Task("Morning walk", "07:30", 30, priority="high", frequency="daily"))
    mochi.add_task(Task("Breakfast", "08:30", 10, priority="high", frequency="daily"))
    # Booked at the same time as Biscuit's walk to demonstrate conflict detection.
    mochi.add_task(Task("Litter box cleanup", "07:30", 10, priority="medium", frequency="daily"))
    return owner


def print_tasks(title: str, tasks: list[Task]) -> None:
    """Print a list of tasks as aligned rows."""
    print(f"\n{title}")
    print("-" * 64)
    for t in tasks:
        status = "done" if t.completed else "todo"
        print(
            f"{t.due_date:%m/%d} {t.time}  {t.description:<20} {t.pet_name:<8}"
            f" {t.duration_minutes:>3} min  {t.priority:<6} {t.frequency:<6} {status}"
        )


def main() -> None:
    """Demonstrate sorting, filtering, recurrence, and conflict detection."""
    owner = build_demo_owner()
    scheduler = Scheduler(owner)

    print(f"PawPal+ demo for {owner.name}: {len(owner.pets)} pets, {len(owner.get_all_tasks())} tasks")

    print_tasks("Today's Schedule (sorted by time, all pets)", scheduler.sort_by_time(scheduler.tasks_for_date()))
    print_tasks("Filter: Mochi's tasks only", scheduler.sort_by_time(scheduler.filter_tasks(pet_name="Mochi")))

    print("\nConflict check")
    print("-" * 64)
    for warning in scheduler.detect_conflicts() or ["No conflicts today"]:
        print(warning)

    walk = next(t for t in owner.get_pet("Biscuit").tasks if t.description == "Morning walk")
    upcoming = scheduler.mark_task_complete(walk.task_id)
    print(f"\nMarked Biscuit's Morning walk complete. Next occurrence: {upcoming.due_date:%m/%d} at {upcoming.time}")

    print_tasks("Filter: completed tasks", scheduler.filter_tasks(completed=True))
    print_tasks("Filter: Biscuit's pending tasks", scheduler.sort_by_time(scheduler.filter_tasks(pet_name="Biscuit", completed=False)))


if __name__ == "__main__":
    main()
