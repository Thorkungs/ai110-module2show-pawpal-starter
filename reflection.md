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

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

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
