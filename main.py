"""PawPal+ CLI demo: a testing ground for the logic layer before the Streamlit UI."""

from pawpal_system import Owner, Pet, Scheduler, Task


def build_demo_owner() -> Owner:
    """Create an owner with two pets and a handful of care tasks."""
    owner = Owner(name="Jordan", available_minutes=120)
    biscuit = owner.add_pet(Pet(name="Biscuit", species="dog", breed="Golden Retriever"))
    mochi = owner.add_pet(Pet(name="Mochi", species="cat", breed="Tabby"))

    biscuit.add_task(Task("Morning walk", "07:30", 30, priority="high", frequency="daily"))
    biscuit.add_task(Task("Breakfast", "08:15", 10, priority="high", frequency="daily"))
    mochi.add_task(Task("Breakfast", "08:30", 10, priority="high", frequency="daily"))
    mochi.add_task(Task("Flea medication", "09:00", 5, priority="high", frequency="weekly"))
    biscuit.add_task(Task("Vet checkup", "15:00", 60, priority="medium"))
    return owner


def main() -> None:
    """Print today's schedule for every pet."""
    owner = build_demo_owner()
    scheduler = Scheduler(owner)

    print(f"Today's Schedule for {owner.name}'s pets")
    print("=" * 52)
    for task in scheduler.tasks_for_date():
        status = "done" if task.completed else "todo"
        print(
            f"{task.time}  {task.description:<18} {task.pet_name:<8}"
            f" {task.duration_minutes:>3} min  [{task.priority}] ({status})"
        )


if __name__ == "__main__":
    main()
