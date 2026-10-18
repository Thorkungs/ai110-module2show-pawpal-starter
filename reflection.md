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

Relationships: an Owner *owns* many Pets (aggregation), a Pet *has* many Tasks (composition, since a task doesn't make sense without its pet), and the Scheduler *reads from* the Owner. Task, Pet, and Owner are Python dataclasses because they are mostly data; Scheduler is a regular class because it is all behavior.

**b. Design changes**

Yes. Before any real logic was written, the skeleton went through an AI review for missing relationships and logic bottlenecks, and it surfaced problems that would have hit later:

- **Task had no date.** Recurring tasks need a `due_date` so "daily" can mean `due_date + timedelta(days=1)`. Without it there was nothing to add a day to. Added `due_date: date`.
- **Tasks lost track of their pet.** Once the Scheduler flattens everything through `Owner.get_all_tasks()`, a bare Task can't say which pet it belongs to, so the schedule couldn't print "(Biscuit)" or filter by pet. Added a `pet_name` back reference that `Pet.add_task()` stamps automatically.
- **Removing by description was ambiguous.** Two pets can both have "Breakfast," and a recurring task creates copies with the same description. Added a short `task_id` and switched `remove_task()` to use it.
- **Time strings sort wrong if they aren't padded.** `"9:00"` sorts after `"10:00"` as a string. Added `__post_init__` validation that normalizes every time to zero padded `"HH:MM"`, which also lets sorting stay a simple `lambda` key.
- **Recurrence ownership.** Instead of `Task.mark_complete()` reaching out to add a copy of itself to a pet, `Task.next_occurrence()` just *computes* the next instance and `Scheduler.mark_task_complete()` adds it to the right pet. That keeps Task ignorant of Pets.

The biggest change came later. The draft's `generate_plan()` returned a `list[Task]`. When time blocking was added (moving a lower priority task out of an overlapping slot), returning Tasks would have meant *overwriting* the task's requested time. That change would also have leaked into its next recurrence, so tomorrow's litter box cleanup would quietly move too. The design was changed to `build_daily_plan()`, which returns a separate `DailyPlan` made of `PlanEntry` objects (task + planned start/end + reason). Planning never edits a Task. Both classes are in `diagrams/uml_final.mmd`, along with the `Owner.day_start` / `day_end` window and JSON save/load that were added for the stretch features.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers:

- **Time**: each task's date, `"HH:MM"` start, and duration, which together give it a real time window (`Task.start`, `Task.end`).
- **The owner's time budget**: `Owner.available_minutes`, the total minutes of care they can give in a day.
- **The owner's available hours**: `day_start` to `day_end`, used when looking for a free slot.
- **Priority**: low, medium, high.
- **Completion and recurrence**: completed tasks drop out of conflict checks and planning; daily/weekly tasks regenerate.

Priority matters most, because missing a medication or a meal is worse than missing a grooming session, so `build_daily_plan()` places tasks highest priority first. The time budget comes second because it's a hard limit: when minutes run out, the lowest priority tasks are skipped, with the exact shortfall given as the reason. The owner's requested time comes third: a task keeps its requested time unless it would overlap something more important, and then it only moves *later*, never earlier, because giving meds or food early can be worse than a short delay.

**b. Tradeoffs**

**Conflicts are warnings, not blockers, and they are checked pair by pair.** `Scheduler.find_conflicts()` compares every pair of pending tasks on a day with `itertools.combinations` and asks `Task.overlaps()` whether their time windows intersect (so a 30 minute walk at 07:30 conflicts with a feeding at 07:45, not just with another 07:30 task). That is O(n²) comparisons. In the Phase 4 "how could this be simplified" review, the AI pointed out a "sweep line" version (sort by start time, then only compare each task with the ones that start before it ends, and `break` early) which is O(n log n). The `combinations` version was kept because a pet owner has maybe 10 to 30 tasks a day, so the speed difference is microseconds, while the one line comprehension is much easier to read and obviously correct. It would only be worth switching if PawPal+ had to scan months of tasks at once.

The second half of that tradeoff is that conflicts never stop you from saving a task; `detect_conflicts()` returns friendly warning strings instead of raising. Sometimes overlap is intentional (feeding both pets at once), so the owner gets told, gets a suggested free slot, and decides.

**The daily plan is greedy, not optimal.** `build_daily_plan()` takes tasks in priority order and keeps each one if it fits. It never backtracks, so it can skip a 45 minute low priority task even when dropping two other low priority tasks would have made room. A true optimum is a knapsack problem; greedy by priority is easy to explain ("high priority first, then whatever fits"), which matters because the plan has to explain itself to the owner.

**Recurring tasks are created one instance at a time.** When a daily task is completed, `mark_task_complete()` adds exactly one copy at `due_date + timedelta(days=1)`. A month of copies is never pre-generated. That keeps the task list short and makes "completing twice" easy to guard against, but it means if you never check off today's walk, tomorrow's walk doesn't exist yet. For a daily care checklist that felt acceptable: the unfinished task stays visible as a reminder.

---

## 3. AI Collaboration

**a. How you used AI**

I used Claude as an AI agent for the whole build. I gave it the CodePath assignment page and it read the full instructions and the grading rubric in the browser itself, so the rubric was part of its context from the start. From there it worked phase by phase the way the assignment lays out: brainstorming the four classes and drafting the Mermaid UML, generating dataclass skeletons, reviewing the skeleton for gaps, implementing the classes, wiring Streamlit, adding the algorithms, planning and writing tests, and writing the docs, with a git commit at the end of each phase.

What helped most:

- **Giving it the real requirements as context** (context engineering). Because the agent had read the rubric line by line, it designed for things like "the Scheduler must read from an Owner method" and "Mermaid source, not just a PNG" up front instead of fixing them later.
- **Review style prompts**: "review this skeleton for missing relationships or logic bottlenecks" produced the five design changes in section 1b.
- **Edge case prompts**: "what are the most important edge cases for a pet scheduler with sorting and recurring tasks?" produced the less obvious tests, like back to back tasks, unpadded times, and completing the same task twice.
- **Letting it run things**: the agent could run `python main.py` and `python -m pytest` itself after every change, so mistakes showed up immediately instead of at the end.

**b. Judgment and verification**

AI suggestions that were not accepted as-is:

- **The planner design.** The obvious version of `generate_plan()` would have rewritten each task's time to resolve overlaps. That was rejected because it corrupts the owner's original request and its future recurrences; the `DailyPlan` / `PlanEntry` design replaced it (section 1b).
- **The faster conflict check.** The sweep line algorithm was the more "optimized" suggestion, but the simpler `combinations` version was kept for readability (section 2b).
- **A weak test.** One of the first drafts of the time blocking test asserted something about the tasks' *requested* windows, which would have passed no matter what the planner did. It was replaced with the real guarantee: the *planned* windows come back in order and never overlap.

How things were verified:

- Running `main.py` after every phase and reading the output (that's how the out of order schedule in Phase 2 showed sorting was needed).
- 39 pytest tests, all with a fixed date.
- **Mutation testing**: six bugs were deliberately injected into `pawpal_system.py` (no time padding, `<=` in the overlap check, no double complete guard, a two day "daily" step, sorting without the date, completed tasks counted as conflicts). The suite failed on every one, which showed the tests check real behavior.
- Streamlit's `AppTest` harness to click through the UI: add pets, a duplicate pet, a conflicting task, mark complete, invalid settings, and reloading saved data in a brand new session. This caught a deprecated Streamlit parameter and a free slot suggestion of "13:53" that was rounded to the next 5 minutes.
- A script that checks every attribute and method in the code appears in `uml_final.mmd`.

---

## 4. Testing and Verification

**a. What you tested**

- **Core behavior**: `mark_complete()`, adding/removing tasks, duplicate pet names, and that the Scheduler sees tasks from every pet.
- **Input validation**: invalid times (`"25:00"`, `"8am"`, `"12:60"`, blank), unknown priorities, zero durations.
- **Sorting**: chronological order across pets, `"9:00"` vs `"10:00"`, date before time, priority order.
- **Filtering**: by pet, status, and both; empty cases (no pets, a pet with no tasks).
- **Recurrence**: daily (+1 day), weekly (+7 days), one time (no copy), completing twice (no duplicate), unknown id (KeyError).
- **Conflicts**: same time, overlapping durations, back to back (not a conflict), completed tasks ignored.
- **Stretch features**: next free slot (gaps, day window, full day), daily plan (budget, priority, time blocking without mutation, skipping, completed tasks), JSON round trip, unknown JSON keys, emoji formatting.

These matter because they are exactly the places a scheduler goes quietly wrong: a string sort that looks right until 9 AM meets 10 AM, a "conflict" check that misses a walk that's still in progress, or a recurring task that doubles every time someone double clicks.

**b. Confidence**

**4 out of 5.** Every scheduling behavior has a passing test, the edge cases most likely to break are covered, and the mutation check shows the tests aren't just passing by accident. It isn't 5 because the UI checks were run during development rather than committed to the suite, and some situations aren't tested yet.

Edge cases I would test next:

- Tasks that cross midnight (a 23:45 task lasting 30 minutes).
- Completing an overdue recurring task: if a daily walk from three days ago is checked off today, its next occurrence is already in the past.
- Renaming a pet after it has tasks, since `pet_name` is a copied string, not a live reference.
- Owners with an `available_minutes` of 0, and very large task lists for performance.
- Committing the `AppTest` UI checks as a `tests/test_app.py`.

---

## 5. Reflection

**a. What went well**

The decision to make the Scheduler read everything through `Owner.get_all_tasks()`. Because of that one rule, every algorithm (sorting, filtering, conflicts, the planner) worked across multiple pets automatically, with no special cases. I'm also happy that the daily plan explains itself: each entry says *why* it's there or why it moved, and skipped tasks say exactly how many minutes were missing.

**b. What you would improve**

- Give pets a stable id and have tasks reference that, so renaming a pet can't orphan its tasks.
- Handle overdue recurring tasks by rolling the next occurrence forward to today instead of a date in the past.
- Let users edit an existing task in the UI (right now it's remove and re-add).
- Try a smarter planner that can swap out lower priority tasks to fit more total care, and compare it with greedy.

**c. Key takeaway**

Being the "lead architect" with AI is less about typing code and more about two things: setting the design rules (like "planning never mutates a task") and setting the bar for proof. The AI produced working code fast, and almost all of it passed on the first run, but "it passed" only meant something once the tests were shown to fail on injected bugs. The human job is deciding what *correct* means and checking the AI against it.

---

## 6. AI Strategy

- **Most effective AI features**: agent mode that could edit several files and run commands (`main.py`, `pytest`, the Streamlit test harness) in one loop, and the browser tool that read the assignment and rubric directly, so the work was aimed at the grading criteria from the first commit.
- **A suggestion that was modified**: the plan design. Returning modified Tasks from the planner was replaced with `DailyPlan` / `PlanEntry` objects to keep the original schedule and recurrences clean.
- **Organizing the work**: instead of separate chat sessions, this was one long agent session organized by phase, with a task list, a checkpoint, and a commit at the end of each phase. That kept each phase's changes separate in the history. The downside of one session is that the same agent wrote the code *and* the tests, so they could share blind spots; the mutation check was the counterweight. Next time I'd review the tests in a fresh session that hasn't seen the implementation.
- **What I learned as lead architect**: AI is very good at generating and iterating, but the architecture decisions and the verification standard have to come from the human directing it.
