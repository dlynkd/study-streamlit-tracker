import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# -----------------------
# Supabase setup
# -----------------------

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])
email = st.secrets["APP_EMAIL"]
password = st.secrets["APP_PASSWORD"]
user_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
session = user_response.session

# -----------------------
# Authentication
# -----------------------
with open('./config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

try:
    authenticator.login()
except Exception as e:
    st.error(e)

if st.session_state.get('authentication_status'):

    st.sidebar.success(f"Welcome {st.session_state.get("name")}")
    authenticator.logout("Logout", "sidebar")

    # -----------------------
    # DB functions
    # -----------------------
    def get_tasks():
        tasks_data = supabase.table("tasks").select("*").execute().data
        df = pd.DataFrame(tasks_data)
        if not df.empty:
            df["target_date"] = pd.to_datetime(df["target_date"]).dt.date
            df["completed_date"] = pd.to_datetime(df["completed_date"]).dt.date
        return df

    def mark_complete(task_id):
        today = str(date.today())
        supabase.table("tasks").update({"completed_date": today}).eq("id", task_id).execute()
        
        # res.data contains the updated row(s)
        # print(res.data)  # should show the row if RLS allows it
        st.success("Task marked complete!")
        get_tasks.clear()
        st.rerun()

        
    st.title("RL Prereqs Study Plan")

    # -----------------------
    # Load data
    # -----------------------
    df = get_tasks()

    if df.empty:
        st.warning("No tasks found.")
        st.stop()

    def week_number(topic):
        try:
            return int(topic.split()[0])
        except:
            return 0

    topics_sorted = sorted(df['topic'].dropna().unique(), key=week_number)
    topics_options = ["All"] + list(topics_sorted)
    topic_choice = st.selectbox("Filter by Week/Topic:", topics_options)

    display_df = df[df["topic"] == topic_choice] if topic_choice != "All" else df.copy()
    display_df = display_df.sort_values(by="target_date")

    # -----------------------
    # Color coding
    # -----------------------
    def color_row(row):
        if pd.isna(row["completed_date"]):
            return ["background-color: #2e2e2e; color: white"] * len(row)
        completed = row["completed_date"]
        target = row["target_date"]
        if completed == target:
            color = "lightblue"
        elif completed > target:
            color = "lightcoral"
        else:
            color = "lightgreen"
        return [f"background-color: {color}; color: black"] * len(row)

    styled = display_df.style.apply(color_row, axis=1)

    # -----------------------
    # Main page display
    # -----------------------
    st.subheader("Task Schedule")
    st.dataframe(styled, width="stretch", hide_index=True)


    # Filter to only incomplete tasks
    tasks_for_selection = display_df[display_df["completed_date"].isna()].copy()
    tasks_for_selection = tasks_for_selection.sort_values(by="target_date")

    # Build display column
    tasks_for_selection["display"] = (
        tasks_for_selection["topic"] + " — " + tasks_for_selection["description"]
    )

    task_choice = st.selectbox(
        "Select a task to mark complete:",
        ["None"] + tasks_for_selection["display"].tolist()
    )

    if task_choice != "None":
        selected_task_id = tasks_for_selection[
            tasks_for_selection["display"] == task_choice
        ]["id"].values[0]

        if st.button("✅ Mark Complete"):
            mark_complete(selected_task_id)

elif st.session_state.get('authentication_status') is False:
    st.error('Username/password is incorrect')
elif st.session_state.get('authentication_status') is None:
    st.warning('Please enter your username and password')
