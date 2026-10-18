# AI Interactions Log

> Stretch features only. The Prompt Comparison (SF11) section was not attempted and has been removed.

---

## Agent Workflow (SF7)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

I gave Claude (running as an agent with file editing, a terminal, and a browser) the link to the PawPal+ project page and asked it to do the project. It read the full assignment and the Project 2 grading rubric in the browser, cloned the starter repo, and worked through all six phases plus the stretch features. For the advanced algorithm, the specific goal was a **"next available slot" finder** and a **priority based daily plan that respects the owner's time budget and moves lower priority tasks out of overlapping slots** (time blocking).

**What did the agent do?**

Files created or modified:

| File | What changed |
|------|--------------|
| `pawpal_system.py` | Skeleton from UML, then the full Task / Pet / Owner / Scheduler implementation; sorting, filtering, recurrence, and conflict detection; then the stretch layer: `first_free_slot()`, `Scheduler.find_next_available_slot()`, `Scheduler.sort_by_priority()`, `Scheduler.build_daily_plan()` with the new `DailyPlan` and `PlanEntry` classes, JSON `to_dict` / `from_dict` / `save_to_json` / `load_from_json`, and the `task_emoji()` / `PRIORITY_BADGES` formatting helpers. |
| `main.py` | CLI demo: two pets, eight tasks added out of order with one double booking; prints every feature with `tabulate` tables. |
| `app.py` | Streamlit UI: `st.session_state` for the Owner, four tabs, conflict warnings with a suggested slot, mark complete with recurrence, the daily plan, a free slot finder, auto save to `data.json`. |
| `tests/test_pawpal.py`, `pytest.ini` | 39 tests; config so tests import from the project root. |
| `diagrams/uml_draft.mmd`, `uml_final.mmd`, `uml.mmd` | Draft and final Mermaid UML. |
| `README.md`, `reflection.md`, `requirements.txt`, `.gitignore` | Docs, reflection, `tabulate` / `wcwidth` dependencies, `data.json` ignored. |

Commands it ran: created a virtual environment and installed requirements, ran `python main.py` and `python -m pytest` after each phase, ran a mutation check (six injected bugs, all caught), drove the UI with Streamlit's `AppTest` harness, booted `streamlit run app.py` headless to confirm the server starts, and cross-checked the final UML against the code with a script. It committed after every phase.

**What did you have to verify or fix manually?**

Things that were caught in review and corrected before they were committed:

- **Planner design**: the first plan design returned modified Tasks; it was changed so planning returns `PlanEntry` objects and never edits a task's requested time (otherwise the moved time would also carry into the task's next recurrence).
- **A test that couldn't fail**: an early version of the time blocking test asserted on the tasks' requested windows instead of the planned windows. It was rewritten to check the real guarantee: planned windows are in order and never overlap.
- **Streamlit deprecation**: the `AppTest` run flagged `use_container_width` as deprecated in the current Streamlit; it was removed.
- **Awkward suggestion times**: the free slot finder suggested "13:53" when searching from the current time; the app now rounds "now" up to the next 5 minutes.
