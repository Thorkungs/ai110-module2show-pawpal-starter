"""Automated tests for the PawPal+ logic layer."""

from pawpal_system import Pet, Task


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
