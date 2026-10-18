# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

Three core actions a user should be able to perform:

1. **Add a pet** (name and species) so PawPal+ knows who it is planning for.
2. **Schedule a care task** for a specific pet, with a time, duration, priority, and how often it repeats (once, daily, weekly).
3. **See today's plan**: every pet's tasks in time order, with warnings when two things are booked at once and an explanation of what fits in the owner's available time.

My initial UML (`diagrams/uml_draft.mmd`) had four classes:

- **Task**: one care activity. Holds the description, a `"HH:MM"` time, duration, priority, frequency, and a completed flag. Its only behavior is `mark_complete()`.
- **Pet**: identifying info (name, species) plus a list of Tasks. Responsible for adding, removing, and listing its own tasks.
- **Owner**: the person using the app. Holds a list of Pets and a daily time budget (`available_minutes`). Responsible for managing pets and for `get_all_tasks()`, which flattens every pet's tasks into one list.
- **Scheduler**: the "brain." It takes an Owner and reads tasks only through `Owner.get_all_tasks()`, so every algorithm (sorting, filtering, conflict detection, planning) automatically works across all pets instead of just one.

Relationships: an Owner *owns* many Pets (aggregation), a Pet *has* many Tasks (composition, since a task doesn't make sense without its pet), and the Scheduler *reads from* the Owner. I used Python dataclasses for Task, Pet, and Owner because they are mostly data, and kept Scheduler as a regular class because it is all behavior.

**b. Design changes**

Yes. I had the AI review the skeleton for missing relationships and logic bottlenecks before writing any real logic, and it surfaced problems I would have hit later:

- **Task had no date.** Recurring tasks need a `due_date` so "daily" can mean `due_date + timedelta(days=1)`. Without it there was nothing to add a day to. Added `due_date: date`.
- **Tasks lost track of their pet.** Once the Scheduler flattens everything through `Owner.get_all_tasks()`, a bare Task can't say which pet it belongs to, so the schedule couldn't print "(Biscuit)" or filter by pet. Added a `pet_name` back reference that `Pet.add_task()` stamps automatically.
- **Removing by description was ambiguous.** Two pets can both have "Breakfast," and a recurring task creates copies with the same description. Added a short `task_id` and switched `remove_task()` to use it.
- **Time strings sort wrong if they aren't padded.** `"9:00"` sorts after `"10:00"` as a string. Added `__post_init__` validation that normalizes every time to zero padded `"HH:MM"`, which also lets sorting stay a simple `lambda` key.
- **Recurrence ownership.** Instead of `Task.mark_complete()` reaching out to add a copy of itself to a pet, `Task.next_occurrence()` just *computes* the next instance and `Scheduler.mark_task_complete()` adds it to the right pet. That keeps Task ignorant of Pets.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

**Conflicts are warnings, not blockers, and they are checked pair by pair.** `Scheduler.find_conflicts()` compares every pair of pending tasks on a day with `itertools.combinations` and asks `Task.overlaps()` whether their time windows intersect (so a 30 minute walk at 07:30 conflicts with a feeding at 07:45, not just with another 07:30 task). That is O(n²) comparisons. When I asked the AI how to simplify or speed up the method, it pointed out a "sweep line" version (sort by start time, then only compare each task with the ones that start before it ends, and `break` early) which is O(n log n). I kept the `combinations` version because a pet owner has maybe 10 to 30 tasks a day, so the speed difference is microseconds, while the one line comprehension is much easier to read and obviously correct. I'd switch only if PawPal+ had to scan months of tasks at once.

The second half of the tradeoff is that conflicts never stop you from saving a task; `detect_conflicts()` returns friendly warning strings instead of raising. Sometimes overlap is intentional (feeding both pets at once), so the owner gets told and decides.

**Recurring tasks are created one instance at a time.** When a daily task is completed, `mark_task_complete()` adds exactly one copy at `due_date + timedelta(days=1)`. I did not pre-generate a month of copies. That keeps the task list short and makes "completing twice" easy to guard against, but it means if you never check off today's walk, tomorrow's walk doesn't exist yet. For a daily care checklist that felt acceptable: the unfinished task stays visible as a reminder.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
