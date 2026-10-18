"""PawPal+ Streamlit UI, wired to the logic layer in pawpal_system.py."""

from datetime import date, time

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Plan your pets' care across feedings, walks, meds, and appointments.")

# Streamlit reruns this script top to bottom on every click, so the Owner lives in
# st.session_state ("the vault"). It is created once and reused on every rerun.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan")

owner: Owner = st.session_state.owner
scheduler = Scheduler(owner)

owner.name = st.text_input("Owner name", value=owner.name)

st.subheader("Pets")
with st.form("add_pet", clear_on_submit=True):
    col1, col2 = st.columns(2)
    pet_name = col1.text_input("Pet name")
    species = col2.selectbox("Species", ["dog", "cat", "other"])
    if st.form_submit_button("Add pet"):
        try:
            owner.add_pet(Pet(name=pet_name, species=species))
            st.success(f"Added {pet_name}!")
        except ValueError as err:
            st.error(str(err))

if owner.pets:
    st.write(", ".join(f"{p.name} ({p.species}, {p.task_count()} tasks)" for p in owner.pets))
else:
    st.info("No pets yet. Add one above.")

st.subheader("Tasks")
if owner.pets:
    with st.form("add_task", clear_on_submit=True):
        pet_choice = st.selectbox("Pet", [p.name for p in owner.pets])
        description = st.text_input("Task", value="Morning walk")
        col1, col2, col3 = st.columns(3)
        task_time = col1.time_input("Time", value=time(8, 0), step=300)
        duration = col2.number_input("Minutes", min_value=1, max_value=240, value=20)
        priority = col3.selectbox("Priority", ["low", "medium", "high"], index=2)
        if st.form_submit_button("Add task"):
            try:
                owner.get_pet(pet_choice).add_task(
                    Task(description, task_time, int(duration), priority=priority)
                )
                st.success(f"Scheduled {description} for {pet_choice}.")
            except ValueError as err:
                st.error(str(err))

    todays = scheduler.tasks_for_date(date.today())
    if todays:
        st.table(
            [
                {"Time": t.time, "Task": t.description, "Pet": t.pet_name,
                 "Minutes": t.duration_minutes, "Priority": t.priority}
                for t in todays
            ]
        )
    else:
        st.info("No tasks for today yet.")
