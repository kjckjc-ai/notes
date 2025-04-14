
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = "meeting_notes.db"

# Database Setup
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Contacts table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        company TEXT,
        tags TEXT,
        notes TEXT
    )
    ''')
    # Notes table with contact_id
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        date TEXT NOT NULL,
        contact_id INTEGER,
        participants TEXT,
        tags TEXT,
        body TEXT,
        FOREIGN KEY (contact_id) REFERENCES contacts(id)
    )
    ''')
    conn.commit()
    conn.close()

# Save new contact
def add_contact(name, email, phone, company, tags, notes):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO contacts (name, email, phone, company, tags, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, email, phone, company, tags, notes))
    conn.commit()
    conn.close()

# Save new note
def add_note(title, date, contact_id, participants, tags, body):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO notes (title, date, contact_id, participants, tags, body)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (title, date, contact_id, participants, tags, body))
    conn.commit()
    conn.close()

# Fetch contacts and notes
def get_contacts():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM contacts", conn)
    conn.close()
    return df

def get_notes(contact_id=None):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM notes"
    if contact_id is not None:
        query += " WHERE contact_id = ?"
        df = pd.read_sql_query(query, conn, params=(contact_id,))
    else:
        df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Initialize DB
init_db()

st.title("Personal CRM - Meeting Notes + Contacts")

tab1, tab2, tab3 = st.tabs(["Add Note", "Manage Contacts", "CRM Dashboard"])

with tab1:
    st.subheader("Add a New Meeting Note")
    title = st.text_input("Meeting Title")
    date_val = st.date_input("Date", datetime.today())
    contacts_df = get_contacts()
    contact_name_to_id = dict(zip(contacts_df['name'], contacts_df['id'])) if not contacts_df.empty else {}
    contact_selection = st.selectbox("Select Contact", ["None"] + list(contact_name_to_id.keys()))
    contact_id = contact_name_to_id.get(contact_selection) if contact_selection != "None" else None
    participants = st.text_input("Other Participants")
    tags = st.text_input("Tags (comma-separated)")
    body = st.text_area("Meeting Notes", height=200)
    if st.button("Save Note"):
        if title:
            add_note(title, date_val.strftime("%Y-%m-%d"), contact_id, participants, tags, body)
            st.success("Note saved.")
        else:
            st.warning("Meeting title is required.")

with tab2:
    st.subheader("Add New Contact")
    name = st.text_input("Full Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone")
    company = st.text_input("Company")
    tags = st.text_input("Tags (comma-separated)")
    notes = st.text_area("Notes", height=100)
    if st.button("Save Contact"):
        if name:
            add_contact(name, email, phone, company, tags, notes)
            st.success("Contact added.")
        else:
            st.warning("Name is required.")
    st.subheader("All Contacts")
    contact_list = get_contacts()
    if not contact_list.empty:
        st.dataframe(contact_list)
    else:
        st.info("No contacts found.")

with tab3:
    st.subheader("CRM Dashboard")
    contact_list = get_contacts()
    for _, contact in contact_list.iterrows():
        st.markdown(f"### {contact['name']} - {contact['company'] or ''}")
        st.markdown(f"**Email:** {contact['email']} | **Phone:** {contact['phone']}")
        st.markdown(f"**Tags:** {contact['tags']}")

        contact_notes = get_notes(contact_id=contact['id'])
        if not contact_notes.empty:
            last_note = contact_notes.sort_values("date", ascending=False).iloc[0]
            st.markdown(f"**Last Contacted:** {last_note['date']}")
            st.markdown(f"**Most Recent Note:** {last_note['body'][:150]}...")
        else:
            st.markdown("*No interactions logged yet.*")
        st.markdown("---")
