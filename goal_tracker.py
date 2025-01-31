import streamlit as st
import gspread
import openai
import os
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from openai import OpenAI
from google.oauth2.service_account import Credentials

# Set page config (must be first)
st.set_page_config(page_title="Goal Tracker", page_icon="📅", layout="wide")

# Load credentials securely from Streamlit Secrets
if "GOOGLE_SHEETS_CREDENTIALS" in st.secrets:
    try:
        service_account_info = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]
        credentials = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        client = gspread.authorize(credentials)
    except Exception as e:
        st.error(f"❌ Error loading Google credentials: {e}")
        client = None
else:
    st.error("❌ Google Credentials not found. Please add them in Streamlit Secrets.")
    client = None

if client is None:
    st.stop()

# Google Sheets Setup
SHEET_ID = "1bbqswqlXR8KHkq0mRpsumSR4cw4QS16nd-o28J1OS_o"

# Function to fetch and cache data
@st.cache_data(ttl=600)  # Cache for 10 minutes
def fetch_google_sheet(sheet_name):
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet(sheet_name)
        data = sheet.get_all_values()
        return pd.DataFrame(data[1:], columns=data[0]) if data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching {sheet_name}: {e}")
        return pd.DataFrame()

# Fetch data once and cache
goals_df = fetch_google_sheet("Goals")
micro_goals_df = fetch_google_sheet("Micro Goals")
journal_df = fetch_google_sheet("Journal")

# Get today's date
today = datetime.datetime.now().strftime("%m/%d/%Y")

# Sidebar Navigation
tab = st.sidebar.radio("Navigation", ["🏠 Main", "📊 Summary", "✏️ Edit/Add Goals", "📖 Journal", "💬 Chat with GPT"])

# Ensure "Due Date" is properly formatted
if "Due Date" in micro_goals_df.columns:
    micro_goals_df["Due Date"] = pd.to_datetime(micro_goals_df["Due Date"], errors="coerce")

# **🏠 Main Tab: Daily Micro-Goals**
if tab == "🏠 Main":
    st.title("📅 Daily Goal Tracker")
    st.subheader(f"Today: {today}")

    if "Due Date" in micro_goals_df.columns and "Completion Status" in micro_goals_df.columns:
        pending_micro_goals = micro_goals_df[
            (micro_goals_df["Due Date"].notna()) &
            (micro_goals_df["Due Date"] <= pd.to_datetime(today)) &
            (~micro_goals_df["Completion Status"].isin(["Yes", "No"]))
        ]

        if "completed_goals" not in st.session_state:
            st.session_state["completed_goals"] = {}

        if not pending_micro_goals.empty:
            for idx, goal in pending_micro_goals.iterrows():
                goal_key = f"{goal['Goal Name']} - {goal['Micro Goal Name']}"

                if goal_key in st.session_state["completed_goals"]:
                    st.success(st.session_state["completed_goals"][goal_key])
                    continue

                with st.container():
                    st.markdown(f"""
                        <div style="padding: 10px; border-radius: 10px; background-color: #f9f9f9; 
                        box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1); margin-bottom: 10px;">
                        <h4>{goal['Goal Name']} {goal.get('Goal Emoji', '🏆')}</h4>
                        <p><strong>{goal['Micro Goal Name']}</strong> - {goal['Micro Goal Description']}</p>
                        <p><strong>Due:</strong> {goal['Due Date'].strftime('%m/%d/%Y')}</p>
                        </div>
                    """, unsafe_allow_html=True)

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"✅ Yes - {goal['Micro Goal Name']}", key=f"yes_{idx}"):
                            st.session_state["completed_goals"][goal_key] = f"Marked '{goal['Micro Goal Name']}' as ✅ Yes!"
                            pending_micro_goals.at[idx, "Completion Status"] = "Yes"
                            st.rerun()

                    with col2:
                        if st.button(f"❌ No - {goal['Micro Goal Name']}", key=f"no_{idx}"):
                            st.session_state["completed_goals"][goal_key] = f"Marked '{goal['Micro Goal Name']}' as ❌ No!"
                            pending_micro_goals.at[idx, "Completion Status"] = "No"
                            st.rerun()

        else:
            st.success("🎉 No pending micro-goals for today! Great job!")

# **📊 Summary Tab: Visualize Progress**
elif tab == "📊 Summary":
    st.title("📊 Goal Progress Summary")

    if not goals_df.empty and not micro_goals_df.empty:
        grouped_goals = micro_goals_df.groupby("Goal Name")

        for goal_name, group in grouped_goals:
            completed = (group["Completion Status"] == "Yes").sum()
            missed = (group["Completion Status"] == "No").sum()
            remaining = len(group) - completed - missed

            if completed + missed + remaining == 0:
                continue

            st.subheader(f"📌 {goal_name}")

            fig, ax = plt.subplots(figsize=(5, 5))
            ax.pie([completed, missed, remaining], labels=["Completed", "Missed", "Remaining"],
                   autopct='%1.1f%%', colors=["#4CAF50", "#FF5252", "#FFC107"], startangle=90)
            ax.set_title(f"Progress for {goal_name}")
            st.pyplot(fig)
            plt.close(fig)

# **✏️ Edit/Add Goals Tab**
elif tab == "✏️ Edit/Add Goals":
    st.title("✏️ Edit or Add Goals")

    new_goal_name = st.text_input("Goal Name:")
    new_goal_desc = st.text_area("Goal Description:")
    new_goal_due = st.date_input("Goal Due Date:")
    new_goal_emoji = st.text_input("Emoji for Goal (Optional):", "🏆")

    if st.button("➕ Add Goal"):
        goals_df = pd.concat([goals_df, pd.DataFrame([[new_goal_name, new_goal_desc, new_goal_due.strftime("%m/%d/%Y"), "", new_goal_emoji]],
                                                     columns=goals_df.columns)])
        st.success(f"Added goal: {new_goal_name} {new_goal_emoji}")

# **📖 Journal Entry Tab**
elif tab == "📖 Journal":
    st.title("📖 Daily Journal")
    journal_entry = st.text_area("Write your thoughts, reflections, and progress here:")

    if st.button("Save Journal Entry"):
        journal_df = pd.concat([journal_df, pd.DataFrame([[today, journal_entry]], columns=journal_df.columns)])
        st.success("Journal entry saved!")

    if not journal_df.empty:
        st.subheader("📜 Past Journal Entries")
        for _, row in journal_df.tail(5).iterrows():
            st.write(f"**{row['Date']}** - {row['Entry']}")

# **💬 Chat with GPT**
elif tab == "💬 Chat with GPT":
    st.title("💬 Chat with GPT About Your Goals & Journal")

    st.write(
        "This chatbot uses OpenAI's GPT-4 model to generate responses. "
        "To use this app, you need to provide an OpenAI API key, which you can get [here](https://platform.openai.com/account/api-keys)."
    )

    # Ask user for their OpenAI API key via text input.
    openai_api_key = st.text_input("🔑 Enter your OpenAI API Key", type="password")

    if not openai_api_key:
        st.info("Please enter your OpenAI API key to continue.", icon="🗝️")
        st.stop()  # Stop execution until the API key is provided

    # Initialize OpenAI client with the provided API key.
    client = OpenAI(api_key=openai_api_key)

    # **Maintain chat history in session state**
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # **Display existing chat messages**
    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # **Chat input field**
    if user_input := st.chat_input("Ask GPT about your goals, deadlines, or progress..."):

        # **Store and display user message**
        st.session_state["messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # **Generate AI response**
        stream = client.chat.completions.create(
            model="gpt-4",
            messages=st.session_state["messages"],  # Full conversation history
            stream=True
        )

        # **Stream and store response**
        with st.chat_message("assistant"):
            response = st.write_stream(stream)

        st.session_state["messages"].append({"role": "assistant", "content": response})