
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

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
        body TEXT
    )
    ''')
    conn.commit()
    conn.close()

def add_note(title, date, participants, tags, body):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO notes (title, date, participants, tags, body)
        VALUES (?, ?, ?, ?, ?)
    ''', (title, date, participants, tags, body))
    conn.commit()
    conn.close()

def get_notes(search_query=None, tag_filter=None, date_filter=None):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM notes WHERE 1=1"
    params = []

    if search_query:
        query += " AND (title LIKE ? OR body LIKE ?)"
        search_term = f"%{search_query}%"
        params.extend([search_term, search_term])

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

# Initialize database
init_db()

# App layout
st.title("Meeting Notes")

with st.form("note_form"):
    st.subheader("Add a New Note")
    title = st.text_input("Title")
    date = st.date_input("Date", datetime.today())
    participants = st.text_input("Participants (comma-separated)")
    tags = st.text_input("Tags (comma-separated)")
    body = st.text_area("Notes", height=200)
    submitted = st.form_submit_button("Save Note")
    if submitted and title:
        add_note(title, date.strftime("%Y-%m-%d"), participants, tags, body)
        st.success("Note saved.")

st.markdown("---")

# Filters
st.subheader("Search & Filter Notes")
search = st.text_input("Keyword Search")
filter_tag = st.text_input("Filter by Tag")
filter_date = st.date_input("Filter by Date", value=None)

if st.button("Apply Filters"):
    df = get_notes(search_query=search, tag_filter=filter_tag, date_filter=filter_date.strftime("%Y-%m-%d") if filter_date else None)
else:
    df = get_notes()

if not df.empty:
    df_display = df[["date", "title", "participants", "tags", "body"]]
    st.dataframe(df_display)
else:
    st.info("No notes found.")
