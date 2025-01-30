import streamlit as st
import gspread
import openai
import os
import datetime
import pandas as pd
import json 
from google.oauth2.service_account import Credentials

# Google Sheets API Setup
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Load credentials from GitHub Secrets
service_account_info = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])
credentials = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
client = gspread.authorize(credentials)

# Open Google Sheets
SHEET_ID = "1bbqswqlXR8KHkq0mRpsumSR4cw4QS16nd-o28J1OS_o"
micro_goals_sheet = client.open_by_key(SHEET_ID).worksheet("Micro Goals")
goals_sheet = client.open_by_key(SHEET_ID).worksheet("Goals")
journal_sheet = client.open_by_key(SHEET_ID).worksheet("Journal")  # New Journal Sheet

# Get today's date
today = datetime.datetime.now().strftime("%m/%d/%Y")

# Streamlit UI Setup
st.set_page_config(page_title="Goal Tracker", page_icon="📅", layout="wide")

# Sidebar Navigation
tab = st.sidebar.radio("Navigation", ["🏠 Main", "📊 Summary", "✏️ Edit/Add Goals", "📖 Journal", "💬 Chat with GPT"])

# Fetch all goals
goals_data = goals_sheet.get_all_values()
goals_df = pd.DataFrame(goals_data[1:], columns=goals_data[0]) if goals_data else pd.DataFrame()

# Fetch all micro-goals
micro_goals_data = micro_goals_sheet.get_all_values()
micro_goals_df = pd.DataFrame(micro_goals_data[1:], columns=micro_goals_data[0]) if micro_goals_data else pd.DataFrame()

# Fetch all journal entries
journal_data = journal_sheet.get_all_values()
journal_df = pd.DataFrame(journal_data[1:], columns=journal_data[0]) if journal_data else pd.DataFrame()

import streamlit as st
import gspread
import datetime
import pandas as pd
import streamlit.components.v1 as components
from google.oauth2.service_account import Credentials




# **🏠 Main Tab: Daily Micro-Goals**
if tab == "🏠 Main":
    st.title("📅 Daily Goal Tracker")
    st.subheader(f"Today: {today}")

    # Ensure "Due Date" is properly formatted as datetime
    if "Due Date" in micro_goals_df.columns and "Completion Status" in micro_goals_df.columns:
        micro_goals_df["Due Date"] = pd.to_datetime(micro_goals_df["Due Date"], errors="coerce")  # Convert date column

        # Filter for pending micro-goals due today or past due
        pending_micro_goals = micro_goals_df[
            (micro_goals_df["Due Date"].notna()) &  # Exclude NaT values
            (micro_goals_df["Due Date"] <= pd.to_datetime(today)) &
            (~micro_goals_df["Completion Status"].isin(["Yes", "No"]))
        ]

        # Track goals that were marked as completed
        if "completed_goals" not in st.session_state:
            st.session_state["completed_goals"] = {}

        if not pending_micro_goals.empty:
            for idx, goal in pending_micro_goals.iterrows():
                goal_key = f"{goal['Goal Name']} - {goal['Micro Goal Name']}"
                
                if goal_key in st.session_state["completed_goals"]:
                    # Show success message for completed goals
                    st.success(st.session_state["completed_goals"][goal_key])
                    continue  # Skip rendering this goal

                with st.container():  # Box for each goal
                    st.markdown(f"""
                        <div style="
                            padding: 10px;
                            border-radius: 10px;
                            background-color: #f9f9f9;
                            box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1);
                            margin-bottom: 10px;">
                        <h4>{goal['Goal Name']} {goal.get('Goal Emoji', '🏆')}</h4>
                        <p><strong>{goal['Micro Goal Name']}</strong> - {goal['Micro Goal Description']}</p>
                        <p><strong>Due:</strong> {goal['Due Date'].strftime('%m/%d/%Y')}</p>
                        </div>
                    """, unsafe_allow_html=True)

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"✅ Yes - {goal['Micro Goal Name']}", key=f"yes_{idx}"):
                            micro_goals_sheet.update_cell(idx + 2, 9, "Yes")
                            st.session_state["completed_goals"][goal_key] = f"Marked '{goal['Micro Goal Name']}' as ✅ Yes!"
                            st.rerun()  # Corrected function to refresh UI instantly

                    with col2:
                        if st.button(f"❌ No - {goal['Micro Goal Name']}", key=f"no_{idx}"):
                            micro_goals_sheet.update_cell(idx + 2, 9, "No")
                            st.session_state["completed_goals"][goal_key] = f"Marked '{goal['Micro Goal Name']}' as ❌ No!"
                            st.rerun()  # Corrected function to refresh UI instantly

        else:
            st.success("🎉 No pending micro-goals for today! Great job!")

    else:
        st.warning("Micro Goals data is missing necessary columns ('Due Date' and 'Completion Status').")




import matplotlib.pyplot as plt

# **📊 Summary Tab: Visualize Progress with Pie Charts**
if tab == "📊 Summary":
    st.title("📊 Goal Progress Summary")

    if not goals_df.empty and not micro_goals_df.empty:
        st.write("Each goal's progress is visualized as a pie chart.")

        grouped_goals = micro_goals_df.groupby("Goal Name")

        for goal_name, group in grouped_goals:
            completed = (group["Completion Status"] == "Yes").sum()
            missed = (group["Completion Status"] == "No").sum()
            remaining = len(group) - completed - missed

            if completed + missed + remaining == 0:
                continue

            st.subheader(f"📌 {goal_name}")

            # Create and close the pie chart properly
            fig, ax = plt.subplots(figsize=(5, 5))
            ax.pie([completed, missed, remaining], labels=["Completed", "Missed", "Remaining"], autopct='%1.1f%%',
                   colors=["#4CAF50", "#FF5252", "#FFC107"], startangle=90, wedgeprops={'edgecolor': 'black'})
            ax.set_title(f"Progress for {goal_name}")
            st.pyplot(fig)
            plt.close(fig)  # ✅ Close the figure after displaying it to free memory

    else:
        st.warning("No goals or micro-goals found.")


# **✏️ Edit/Add Goals Tab**
elif tab == "✏️ Edit/Add Goals":
    st.title("✏️ Edit or Add Goals")

    new_goal_name = st.text_input("Goal Name:")
    new_goal_desc = st.text_area("Goal Description:")
    new_goal_due = st.date_input("Goal Due Date:")
    new_goal_emoji = st.text_input("Emoji for Goal (Optional):", "🏆")

    if st.button("➕ Add Goal"):
        goals_sheet.append_row([new_goal_name, new_goal_desc, new_goal_due.strftime("%m/%d/%Y"), "", new_goal_emoji])
        st.success(f"Added goal: {new_goal_name} {new_goal_emoji}")

# **📖 Journal Entry Tab**
elif tab == "📖 Journal":
    st.title("📖 Daily Journal")

    journal_entry = st.text_area("Write your thoughts, reflections, and progress here:")
    if st.button("Save Journal Entry"):
        journal_sheet.append_row([today, journal_entry])
        st.success("Journal entry saved!")

    # Show past journal entries
    if not journal_df.empty:
        st.subheader("📜 Past Journal Entries")
        for _, row in journal_df.iterrows():
            st.write(f"**{row['Date']}** - {row['Entry']}")

# **💬 Chat with GPT Tab - Now Efficient & Cost-Saving**
if tab == "💬 Chat with GPT":
    st.title("💬 Chat with GPT About Your Goals & Journal")

    openai_api_key = os.getenv("OPENAI_API_KEY")

    # **🔹 Summarize Main Goals for GPT (Only Key Details)**
    if not goals_df.empty:
        goal_summary = "\n".join([
            f"- {row['Goal Name']} (Due: {row['Goal End Date']})"
            for _, row in goals_df.iterrows()
        ])
    else:
        goal_summary = "No goals currently tracked."

    # **🔹 Summarize Micro-Goals (Only Pending & Recent)**
    if not micro_goals_df.empty:
        recent_micro_goals = micro_goals_df.sort_values("Due Date", ascending=False).head(5)  # Only last 5 goals
        micro_goal_summary = "\n".join([
            f"- {row['Micro Goal Name']} (Due: {row['Due Date']}, Status: {row['Completion Status']})"
            for _, row in recent_micro_goals.iterrows()
        ])
    else:
        micro_goal_summary = "No active micro-goals."

    # **🔹 Summarize Recent Journal Entries (Last 5 Entries Only)**
    if not journal_df.empty:
        recent_journal_entries = journal_df.tail(5)  # Keep only the last 5 journal entries
        journal_summary = "\n".join([
            f"{row['Date']}: {row['Entry']}"
            for _, row in recent_journal_entries.iterrows()
        ])
    else:
        journal_summary = "No journal entries recorded yet."

  # **💬 Chat with GPT Tab - Now Includes Current Date Context**
if tab == "💬 Chat with GPT":
    st.title("💬 Chat with GPT About Your Goals & Journal")

    openai_api_key = os.getenv("OPENAI_API_KEY")

    # **🔹 Fetch Current Date from Column H (Micro Goals Sheet)**
    if "Current Date" in micro_goals_df.columns:
        current_date = micro_goals_df["Current Date"].iloc[-1]  # Last recorded date in Column H
    else:
        current_date = today  # Default to system date if missing

    # **🔹 Summarize Main Goals for GPT (Only Key Details)**
    if not goals_df.empty:
        goal_summary = "\n".join([
            f"- {row['Goal Name']} (Due: {row['Goal End Date']})"
            for _, row in goals_df.iterrows()
        ])
    else:
        goal_summary = "No goals currently tracked."

    # **🔹 Summarize Micro-Goals (Only Pending & Recent)**
    if not micro_goals_df.empty:
        micro_goals_df["Due Date"] = pd.to_datetime(micro_goals_df["Due Date"], errors="coerce")
        recent_micro_goals = micro_goals_df[
            (micro_goals_df["Due Date"] <= pd.to_datetime(current_date))  # Compare with Column H date
        ].sort_values("Due Date", ascending=False).head(5)  # Keep only last 5 due goals

        micro_goal_summary = "\n".join([
            f"- {row['Micro Goal Name']} (Due: {row['Due Date']}, Status: {row['Completion Status']})"
            for _, row in recent_micro_goals.iterrows()
        ])
    else:
        micro_goal_summary = "No active micro-goals."

    # **🔹 Summarize Recent Journal Entries (Last 5 Entries Only)**
    if not journal_df.empty:
        recent_journal_entries = journal_df.tail(5)  # Keep only the last 5 journal entries
        journal_summary = "\n".join([
            f"{row['Date']}: {row['Entry']}"
            for _, row in recent_journal_entries.iterrows()
        ])
    else:
        journal_summary = "No journal entries recorded yet."

 # **💬 Chat with GPT - Now Fully Aware of Your Spreadsheet Data**
if tab == "💬 Chat with GPT":
    st.title("💬 Chat with GPT About Your Goals & Journal")

    openai_api_key = os.getenv("OPENAI_API_KEY")

    # **🔹 Fetch Current Date from Column H (Micro Goals Sheet)**
    if "Current Date" in micro_goals_df.columns:
        current_date = micro_goals_df["Current Date"].iloc[-1]  # Last recorded date in Column H
    else:
        current_date = today  # Default to system date if missing

    # **🔹 Summarize Main Goals for GPT**
    if not goals_df.empty:
        goal_summary = "\n".join([
            f"- {row['Goal Name']} (Due: {row['Goal End Date']})"
            for _, row in goals_df.iterrows()
        ])
    else:
        goal_summary = "No goals currently tracked."

    # **🔹 Summarize Micro-Goals (Categorized by Due Date)**
    if not micro_goals_df.empty:
        micro_goals_df["Due Date"] = pd.to_datetime(micro_goals_df["Due Date"], errors="coerce")

        # Filter by different timeframes
        due_today = micro_goals_df[micro_goals_df["Due Date"] == pd.to_datetime(current_date)]
        due_tomorrow = micro_goals_df[micro_goals_df["Due Date"] == pd.to_datetime(current_date) + pd.Timedelta(days=1)]
        due_this_week = micro_goals_df[
            (micro_goals_df["Due Date"] >= pd.to_datetime(current_date)) &
            (micro_goals_df["Due Date"] <= pd.to_datetime(current_date) + pd.Timedelta(days=7))
        ]

        micro_goal_summary_today = "\n".join([
            f"- {row['Micro Goal Name']} (Status: {row['Completion Status']})"
            for _, row in due_today.iterrows()
        ]) if not due_today.empty else "No goals due today."

        micro_goal_summary_tomorrow = "\n".join([
            f"- {row['Micro Goal Name']} (Status: {row['Completion Status']})"
            for _, row in due_tomorrow.iterrows()
        ]) if not due_tomorrow.empty else "No goals due tomorrow."

        micro_goal_summary_week = "\n".join([
            f"- {row['Micro Goal Name']} (Due: {row['Due Date'].strftime('%m/%d/%Y')}, Status: {row['Completion Status']})"
            for _, row in due_this_week.iterrows()
        ]) if not due_this_week.empty else "No goals due this week."

    else:
        micro_goal_summary_today = "No goals currently tracked."
        micro_goal_summary_tomorrow = "No goals currently tracked."
        micro_goal_summary_week = "No goals currently tracked."

    # **🔹 Summarize Recent Journal Entries**
    if not journal_df.empty:
        recent_journal_entries = journal_df.tail(5)  # Keep only the last 5 journal entries
        journal_summary = "\n".join([
            f"{row['Date']}: {row['Entry']}"
            for _, row in recent_journal_entries.iterrows()
        ])
    else:
        journal_summary = "No journal entries recorded yet."

    # **🔹 GPT System Message (Comprehensive Context)**
    gpt_context_message = {
        "role": "system",
        "content": f"""
        You are an AI assistant helping the user with goal tracking. Today's date is **{current_date}**.
        
        📌 **Main Goals**:
        {goal_summary}

        🎯 **Micro Goals Due Today**:
        {micro_goal_summary_today}

        ⏳ **Micro Goals Due Tomorrow**:
        {micro_goal_summary_tomorrow}

        📆 **Micro Goals Due This Week**:
        {micro_goal_summary_week}

        📖 **Recent Journal Entries**:
        {journal_summary}

        **Use this information to answer questions about upcoming deadlines, where the user should refocus, and how they are progressing toward their goals.**
        """
    }

    # **🔹 Keep Chat History, But Now With Full Context**
    if "messages" not in st.session_state:
        st.session_state["messages"] = [gpt_context_message]  # Start with context message

    # **Display chat history**
    for msg in st.session_state["messages"]:
        with st.chat_message("assistant" if msg["role"] == "assistant" else "user"):
            st.markdown(msg["content"])

    # **Chat Input at the Bottom**
    user_input = st.chat_input("Ask GPT about your goals, deadlines, or progress...")
    if user_input:
        st.session_state["messages"].append({"role": "user", "content": user_input})

        client = openai.OpenAI(api_key=openai_api_key)

        response = client.chat.completions.create(
            model="gpt-4",
            messages=st.session_state["messages"]  # No limit, full memory
        )

        reply = response.choices[0].message.content
        st.session_state["messages"].append({"role": "assistant", "content": reply})

        # **Display new message immediately**
        with st.chat_message("assistant"):
            st.markdown(reply)

