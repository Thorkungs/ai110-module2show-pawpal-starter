"""PawPal+ Streamlit UI, wired to the logic layer in pawpal_system.py.

Run with:  streamlit run app.py
"""

import os
from datetime import date, datetime, time, timedelta
from pathlib import Path

import streamlit as st

from main import build_demo_owner
from pawpal_system import PRIORITY_BADGES, Owner, Pet, Scheduler, Task, task_emoji

DATA_FILE = Path(os.environ.get("PAWPAL_DATA_FILE", "data.json"))
FREQUENCIES = ["once", "daily", "weekly"]
PRIORITIES = ["low", "medium", "high"]

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")


# ---- State: the Owner lives in st.session_state so it survives Streamlit reruns ----


def load_owner() -> Owner:
    """Load saved data from data.json if it exists, otherwise start fresh."""
    if DATA_FILE.exists():
        try:
            return Owner.load_from_json(DATA_FILE)
        except (ValueError, KeyError, OSError) as err:
            st.session_state.flash = ("error", f"Couldn't read {DATA_FILE} ({err}); starting fresh.")
    return Owner(name="Jordan")


def save_and_rerun(kind: str, message: str) -> None:
    """Persist the owner to JSON, queue a message for the next run, and refresh the page."""
    try:
        st.session_state.owner.save_to_json(DATA_FILE)
    except OSError as err:
        kind, message = "error", f"{message} (but saving failed: {err})"
    st.session_state.flash = (kind, message)
    st.rerun()


if "owner" not in st.session_state:
    st.session_state.owner = load_owner()

owner: Owner = st.session_state.owner
scheduler = Scheduler(owner)


def task_label(t: Task) -> str:
    """Human readable label for pickers."""
    return f"{t.due_date:%m/%d} {t.time}  {task_emoji(t.description)} {t.description} ({t.pet_name})"


def task_rows(tasks: list[Task]) -> list[dict]:
    """Turn tasks into table rows with emojis and badges."""
    return [
        {
            "Date": f"{t.due_date:%a %m/%d}",
            "Time": t.time,
            "Task": f"{task_emoji(t.description)} {t.description}",
            "Pet": t.pet_name,
            "Minutes": t.duration_minutes,
            "Priority": PRIORITY_BADGES[t.priority],
            "Repeats": t.frequency,
            "Status": "✅ done" if t.completed else "⬜ to do",
        }
        for t in tasks
    ]


# ---- Header and flash messages -------------------------------------------------------

st.title("🐾 PawPal+")
st.caption(f"Smart pet care planning for {owner.name}'s pets: feedings, walks, meds, and appointments.")

if "flash" in st.session_state:
    kind, message = st.session_state.pop("flash")
    getattr(st, kind)(message)

# ---- Sidebar: owner settings and data ------------------------------------------------

with st.sidebar:
    st.header("👤 Owner")
    with st.form("owner_settings"):
        name = st.text_input("Your name", value=owner.name)
        minutes = st.number_input(
            "Minutes available per day", min_value=0, max_value=1440, value=owner.available_minutes, step=5
        )
        col1, col2 = st.columns(2)
        day_start = col1.time_input("Day starts", value=datetime.strptime(owner.day_start, "%H:%M").time(), step=900)
        day_end = col2.time_input("Day ends", value=datetime.strptime(owner.day_end, "%H:%M").time(), step=900)
        if st.form_submit_button("Save settings"):
            if day_start >= day_end:
                st.error("Your day has to start before it ends.")
            elif not name.strip():
                st.error("Name can't be blank.")
            else:
                owner.name = name.strip()
                owner.available_minutes = int(minutes)
                owner.day_start, owner.day_end = day_start.strftime("%H:%M"), day_end.strftime("%H:%M")
                save_and_rerun("success", "Settings saved.")

    st.header("💾 Data")
    st.caption(f"Changes auto save to `{DATA_FILE}` and reload next time you open PawPal+.")
    col1, col2 = st.columns(2)
    if col1.button("Load sample data"):
        st.session_state.owner = build_demo_owner()
        save_and_rerun("success", "Loaded Jordan's sample pets, Biscuit and Mochi.")
    if col2.button("Clear all"):
        st.session_state.owner = Owner(name=owner.name)
        save_and_rerun("info", "Cleared all pets and tasks.")

# ---- Main tabs ----------------------------------------------------------------------

tab_pets, tab_tasks, tab_schedule, tab_plan = st.tabs(["🐶 Pets", "📝 Tasks", "📅 Schedule", "🗓️ Daily plan"])

with tab_pets:
    st.subheader("Add a pet")
    with st.form("add_pet", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        pet_name = col1.text_input("Pet name", placeholder="Biscuit")
        species = col2.selectbox("Species", ["dog", "cat", "bird", "rabbit", "other"])
        breed = col3.text_input("Breed (optional)")
        if st.form_submit_button("Add pet"):
            try:
                owner.add_pet(Pet(name=pet_name, species=species, breed=breed.strip()))
                save_and_rerun("success", f"Added {pet_name.strip()} 🎉")
            except ValueError as err:
                st.error(str(err))

    st.subheader("Your pets")
    if owner.pets:
        today = date.today()
        st.dataframe(
            [
                {
                    "Pet": p.name,
                    "Species": p.species,
                    "Breed": p.breed or "",
                    "Total tasks": p.task_count(),
                    "To do today": len(scheduler.filter_tasks(pet_name=p.name, completed=False, day=today)),
                }
                for p in owner.pets
            ],
            hide_index=True,
        )
    else:
        st.info("No pets yet. Add one above, or click **Load sample data** in the sidebar.")

with tab_tasks:
    if not owner.pets:
        st.info("Add a pet first, then you can schedule tasks for it.")
    else:
        st.subheader("Schedule a task")
        with st.form("add_task", clear_on_submit=True):
            col1, col2 = st.columns([1, 2])
            pet_choice = col1.selectbox("Pet", [p.name for p in owner.pets])
            description = col2.text_input("Task", placeholder="Morning walk")
            col1, col2, col3 = st.columns(3)
            task_day = col1.date_input("Date", value=date.today())
            task_time = col2.time_input("Time", value=time(8, 0), step=300)
            duration = col3.number_input("Minutes", min_value=1, max_value=600, value=20)
            col1, col2 = st.columns(2)
            priority = col1.selectbox("Priority", PRIORITIES, index=1)
            frequency = col2.selectbox("Repeats", FREQUENCIES)
            if st.form_submit_button("Add task"):
                try:
                    task = owner.get_pet(pet_choice).add_task(
                        Task(description, task_time, int(duration), priority, frequency, due_date=task_day)
                    )
                except ValueError as err:
                    st.error(str(err))
                else:
                    clashes = [b if a is task else a for a, b in scheduler.find_conflicts(task_day) if task in (a, b)]
                    if clashes:
                        other = clashes[0]
                        slot = scheduler.find_next_available_slot(task.duration_minutes, task_day, earliest=task.time)
                        tip = f" The next free {task.duration_minutes} min slot is **{slot}**." if slot else ""
                        save_and_rerun(
                            "warning",
                            f"Added {task.description} for {task.pet_name}, but it overlaps "
                            f"{other.pet_name}'s {other.description} at {other.time}.{tip}",
                        )
                    save_and_rerun("success", f"Scheduled {task_emoji(task.description)} {task.description} for {task.pet_name}.")

        pending = scheduler.sort_by_time(scheduler.filter_tasks(completed=False))
        st.subheader("Check off or remove a task")
        if pending:
            picked = st.selectbox("Pending task", pending, format_func=task_label)
            col1, col2, _ = st.columns([1, 1, 3])
            if col1.button("✅ Mark complete"):
                upcoming = scheduler.mark_task_complete(picked.task_id)
                note = f" Next one is scheduled for {upcoming.due_date:%a %m/%d} at {upcoming.time}." if upcoming else ""
                save_and_rerun("success", f"Nice! {picked.description} for {picked.pet_name} is done.{note}")
            if col2.button("🗑️ Remove"):
                owner.get_pet(picked.pet_name).remove_task(picked.task_id)
                save_and_rerun("info", f"Removed {picked.description} for {picked.pet_name}.")
        else:
            st.info("Nothing pending. 🎉")

with tab_schedule:
    col1, col2, col3 = st.columns(3)
    view_day = col1.date_input("Day", value=date.today(), key="schedule_day")
    pet_filter = col2.selectbox("Pet", ["All pets"] + [p.name for p in owner.pets])
    status_filter = col3.radio("Show", ["Pending", "Completed", "All"], horizontal=True)

    day_tasks = scheduler.filter_tasks(day=view_day)
    done = [t for t in day_tasks if t.completed]
    m1, m2, m3 = st.columns(3)
    m1.metric("Tasks this day", len(day_tasks))
    m2.metric("Done", f"{len(done)} / {len(day_tasks)}")
    m3.metric("Minutes still to do", sum(t.duration_minutes for t in day_tasks if not t.completed))

    conflicts = scheduler.find_conflicts(view_day)
    if conflicts:
        for warning, (_, later) in zip(scheduler.detect_conflicts(view_day), conflicts):
            slot = scheduler.find_next_available_slot(later.duration_minutes, view_day, earliest=later.time)
            fix = f" 💡 Try moving {later.pet_name}'s {later.description} to **{slot}**." if slot else ""
            st.warning(warning + "." + fix)
    elif day_tasks:
        st.success("No scheduling conflicts on this day. ✅")

    completed = {"Pending": False, "Completed": True, "All": None}[status_filter]
    shown = scheduler.sort_by_time(
        scheduler.filter_tasks(
            pet_name=None if pet_filter == "All pets" else pet_filter, completed=completed, day=view_day
        )
    )
    if shown:
        st.dataframe(task_rows(shown), hide_index=True)
    else:
        st.info("No tasks match these filters.")

with tab_plan:
    col1, col2 = st.columns([1, 2])
    plan_day = col1.date_input("Plan for", value=date.today(), key="plan_day")
    plan = scheduler.build_daily_plan(plan_day)
    col2.metric(
        "Time budget used",
        f"{plan.used_minutes} / {plan.budget_minutes} min",
        help="Change your available minutes in the sidebar.",
    )
    st.progress(min(plan.used_minutes / plan.budget_minutes, 1.0) if plan.budget_minutes else 0.0)

    if plan.entries:
        st.info(plan.explain())
        st.table(
            [
                {
                    "Planned": f"{e.start:%H:%M} to {e.end:%H:%M}",
                    "Task": f"{task_emoji(e.task.description)} {e.task.description}",
                    "Pet": e.task.pet_name,
                    "Priority": PRIORITY_BADGES[e.task.priority],
                    "Why": ("🔀 " if e.moved else "") + e.reason,
                }
                for e in plan.entries
            ]
        )
    else:
        st.info("No pending tasks to plan for this day.")
    for task, why in plan.skipped:
        st.warning(f"⏭️ Skipped {task.pet_name}'s {task.description}: {why}.")

    st.subheader("Find a free slot")
    col1, col2 = st.columns([1, 2])
    need = col1.number_input("How many minutes?", min_value=1, max_value=600, value=30)
    if col2.button("Find the next free slot"):
        earliest = None
        if plan_day == date.today():  # don't suggest a time that already passed today
            now = datetime.now()
            rounded = now + timedelta(minutes=-now.minute % 5)
            earliest = rounded.strftime("%H:%M") if rounded.date() == now.date() else "23:59"
        slot = scheduler.find_next_available_slot(int(need), plan_day, earliest=earliest)
        if slot:
            st.success(f"Your next free {need} minute window on {plan_day:%a %m/%d} starts at **{slot}**.")
        else:
            st.error(f"No {need} minute gap left between {owner.day_start} and {owner.day_end}.")
