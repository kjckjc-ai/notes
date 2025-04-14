
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

DB_PATH = "meeting_notes.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        date TEXT NOT NULL,
        participants TEXT,
        tags TEXT,
        body TEXT,
        actions TEXT,
        due_date TEXT
    )
    ''')
    conn.commit()
    conn.close()

def add_note(title, date, participants, tags, body, actions, due_date):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO notes (title, date, participants, tags, body, actions, due_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (title, date, participants, tags, body, actions, due_date))
    conn.commit()
    conn.close()

def get_notes(search_query=None, tag_filter=None, date_filter=None):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM notes WHERE 1=1"
    params = []

    if search_query:
        query += " AND (title LIKE ? OR body LIKE ? OR actions LIKE ?)"
        search_term = f"%{search_query}%"
        params.extend([search_term, search_term, search_term])

    if tag_filter:
        query += " AND tags LIKE ?"
        tag_term = f"%{tag_filter}%"
        params.append(tag_term)

    if date_filter:
        query += " AND date = ?"
        params.append(date_filter)

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def clear_all_actions():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE notes SET actions = NULL, due_date = NULL")
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Sidebar: Display open actions
st.sidebar.title("Pending Actions")
all_notes = get_notes()
actions_df = all_notes[all_notes["actions"].notnull() & (all_notes["actions"] != "")]
for idx, row in actions_df.iterrows():
    st.sidebar.markdown(f"**{row['title']} ({row['date']})**")
    st.sidebar.markdown(f"- {row['actions']}")
    if row['due_date']:
        due = datetime.strptime(row['due_date'], "%Y-%m-%d").date()
        days_left = (due - date.today()).days
        color = "red" if days_left < 0 else "orange" if days_left <= 2 else "green"
        st.sidebar.markdown(f"<span style='color:{color}'>Due: {row['due_date']}</span>", unsafe_allow_html=True)

if st.sidebar.button("Clear All Actions"):
    clear_all_actions()
    st.sidebar.success("All actions cleared.")

# Main UI
st.title("Meeting Notes")

with st.form("note_form"):
    st.subheader("Add a New Note")
    title = st.text_input("Title")
    date_val = st.date_input("Date", date.today())
    participants = st.text_input("Participants (comma-separated)")
    tags = st.text_input("Tags (comma-separated)")
    body = st.text_area("Notes", height=150)
    actions = st.text_area("Actions", help="Tasks or follow-ups from this meeting")
    due_date = st.date_input("Action Due Date", value=None)
    submitted = st.form_submit_button("Save Note")
    if submitted and title:
        due = due_date.strftime("%Y-%m-%d") if due_date else None
        add_note(title, date_val.strftime("%Y-%m-%d"), participants, tags, body, actions, due)
        st.success("Note saved.")

st.markdown("---")

# Filters and Export
st.subheader("Search & Filter Notes")
search = st.text_input("Keyword Search")
filter_tag = st.text_input("Filter by Tag")
filter_date = st.date_input("Filter by Date", value=None)

if st.button("Apply Filters"):
    df = get_notes(search_query=search, tag_filter=filter_tag, date_filter=filter_date.strftime("%Y-%m-%d") if filter_date else None)
else:
    df = get_notes()

if not df.empty:
    df_display = df[["date", "title", "participants", "tags", "body", "actions", "due_date"]]
    st.dataframe(df_display)

    # Export Options
    st.markdown("### Export")
    export_format = st.selectbox("Choose export format", ["CSV", "Markdown"])
    if st.button("Export Notes"):
        if export_format == "CSV":
            df_display.to_csv("filtered_meeting_notes.csv", index=False)
            with open("filtered_meeting_notes.csv", "rb") as f:
                st.download_button("Download CSV", f, file_name="filtered_meeting_notes.csv")
        elif export_format == "Markdown":
            md = ""
            for _, row in df_display.iterrows():
                md += f"### {row['title']} ({row['date']})\n"
                md += f"**Participants:** {row['participants']}\n"
                md += f"**Tags:** {row['tags']}\n"
                md += f"**Notes:**\n{row['body']}\n"
                if row['actions']:
                    md += f"**Actions:** {row['actions']}\n"
                if row['due_date']:
                    md += f"**Due Date:** {row['due_date']}\n"
                md += "\n---\n"
            st.download_button("Download Markdown", md, file_name="meeting_notes.md")
else:
    st.info("No notes found.")
