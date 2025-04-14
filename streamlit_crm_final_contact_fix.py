
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

DB_PATH = "meeting_notes.db"

# Initialize DB
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        company TEXT,
        tags TEXT,
        notes TEXT
    )
    """)
    cursor.execute("""
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
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id INTEGER,
        description TEXT,
        due_date TEXT,
        FOREIGN KEY (note_id) REFERENCES notes(id)
    )
    """)
    conn.commit()
    conn.close()

# DB functions
def get_contacts(filter_name=""):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM contacts"
    df = pd.read_sql_query(query, conn)
    if filter_name:
        df = df[df["name"].str.contains(filter_name, case=False, na=False)]
    conn.close()
    return df

def get_notes(search=None, tag=None, date_filter=None):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM notes WHERE 1=1"
    params = []
    if search:
        query += " AND (title LIKE ? OR body LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term])
    if tag:
        query += " AND tags LIKE ?"
        params.append(f"%{tag}%")
    if date_filter:
        query += " AND date = ?"
        params.append(date_filter)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_actions():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT actions.id, notes.title, notes.date, actions.description, actions.due_date FROM actions JOIN notes ON actions.note_id = notes.id", conn)
    conn.close()
    return df

def add_contact(name, email, phone, company, tags, notes):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO contacts (name, email, phone, company, tags, notes) VALUES (?, ?, ?, ?, ?, ?)", (name, email, phone, company, tags, notes))
    conn.commit()
    conn.close()

def update_contact(contact_id, name, email, phone, company, tags, notes):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE contacts SET name=?, email=?, phone=?, company=?, tags=?, notes=? WHERE id=?", (name, email, phone, company, tags, notes, contact_id))
    conn.commit()
    conn.close()

def delete_contact(contact_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contacts WHERE id=?", (contact_id,))
    conn.commit()
    conn.close()

def add_note(title, date, contact_id, participants, tags, body, actions):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO notes (title, date, contact_id, participants, tags, body) VALUES (?, ?, ?, ?, ?, ?)", (title, date, contact_id, participants, tags, body))
    note_id = cursor.lastrowid
    for action in actions:
        if action["description"]:
            cursor.execute("INSERT INTO actions (note_id, description, due_date) VALUES (?, ?, ?)", (note_id, action["description"], action["due_date"]))
    conn.commit()
    conn.close()

def delete_action(action_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM actions WHERE id=?", (action_id,))
    conn.commit()
    conn.close()

# Init DB
init_db()

st.title("Personal CRM with Meeting Notes and Actions")

tab1, tab2, tab3, tab4 = st.tabs(["Add Note", "Contacts", "Notes Dashboard", "Actions"])

# Add Note Tab
with tab1:
    st.subheader("New Meeting Note")
    contacts_df = get_contacts()
    contact_name_to_id = dict(zip(contacts_df['name'], contacts_df['id'])) if not contacts_df.empty else {}
    contact = st.selectbox("Select Contact", ["None"] + list(contact_name_to_id.keys()))
    contact_id = contact_name_to_id.get(contact) if contact != "None" else None
    title = st.text_input("Title")
    date_val = st.date_input("Date", date.today())
    participants = st.text_input("Participants")
    tags = st.text_input("Tags")
    body = st.text_area("Meeting Notes", height=150)
    st.markdown("#### Actions")
    actions = []
    for i in range(3):
        desc = st.text_input(f"Action {i+1}", key=f"act{i}")
        due = st.date_input(f"Due Date {i+1}", value=None, key=f"due{i}")
        actions.append({"description": desc, "due_date": due.strftime("%Y-%m-%d") if due else None})
    if st.button("Save Note"):
        if title:
            add_note(title, date_val.strftime("%Y-%m-%d"), contact_id, participants, tags, body, actions)
            st.success("Note saved.")
        else:
            st.warning("Title is required.")

# Contacts Tab
with tab2:
    st.subheader("Search Contacts")
    search_term = st.text_input("Search by name")
    contacts = get_contacts(search_term)
    if not contacts.empty:
        selected_contact = st.selectbox("Select contact to edit/delete", contacts["name"])
        row = contacts[contacts["name"] == selected_contact].iloc[0]
        new_name = st.text_input("Name", value=row["name"], key="edit_name")
        new_email = st.text_input("Email", value=row["email"], key="edit_email")
        new_phone = st.text_input("Phone", value=row["phone"], key="edit_phone")
        new_company = st.text_input("Company", value=row["company"], key="edit_company")
        new_tags = st.text_input("Tags", value=row["tags"], key="edit_tags")
        new_notes = st.text_area("Notes", value=row["notes"], height=100, key="edit_notes")
        if st.button("Update Contact"):
            update_contact(row["id"], new_name, new_email, new_phone, new_company, new_tags, new_notes)
            st.success("Contact updated.")
        if st.button("Delete Contact"):
            delete_contact(row["id"])
            st.success("Contact deleted.")
    else:
        st.info("No contacts found.")

    st.markdown("---")
    st.subheader("Add New Contact")
    name = st.text_input("New Name", key="new_name")
    email = st.text_input("New Email", key="new_email")
    phone = st.text_input("New Phone", key="new_phone")
    company = st.text_input("New Company", key="new_company")
    tags = st.text_input("New Tags", key="new_tags")
    notes = st.text_area("New Notes", height=100, key="new_notes")
    if st.button("Add Contact"):
        if name:
            add_contact(name, email, phone, company, tags, notes)
            st.success("Contact added.")
        else:
            st.warning("Name is required.")

# Notes Dashboard Tab
with tab3:
    st.subheader("Notes Dashboard")
    search = st.text_input("Keyword Search")
    tag = st.text_input("Tag Filter")
    date_filter = st.date_input("Date Filter", value=None)
    df = get_notes(search, tag, date_filter.strftime("%Y-%m-%d") if date_filter else None)
    if not df.empty:
        for _, row in df.iterrows():
            st.markdown(f"### {row['title']} ({row['date']})")
            st.markdown(f"**Participants:** {row['participants'] or 'N/A'}")
            st.markdown(f"**Tags:** {row['tags'] or 'None'}")
            st.markdown(f"**Body:** {row['body']}")
            st.markdown("---")
        if st.button("Download All as CSV"):
            df.to_csv("exported_notes.csv", index=False)
            with open("exported_notes.csv", "rb") as f:
                st.download_button("Download CSV", f, "meeting_notes.csv")
    else:
        st.info("No matching notes found.")

# Actions Tab
with tab4:
    st.subheader("Pending Actions")
    actions_df = get_actions()
    if not actions_df.empty:
        for _, row in actions_df.iterrows():
            st.markdown(f"**{row['title']} ({row['date']})**")
            st.markdown(f"- {row['description']}")
            if row['due_date']:
                due = datetime.strptime(row['due_date'], "%Y-%m-%d").date()
                days_left = (due - date.today()).days
                color = "red" if days_left < 0 else "orange" if days_left <= 2 else "green"
                st.markdown(f"<span style='color:{color}'>Due: {row['due_date']}</span>", unsafe_allow_html=True)
            if st.button("Delete Action", key=f"del_{row['id']}"):
                delete_action(row['id'])
                st.success("Action deleted.")
                st.rerun()
    else:
        st.info("No actions yet.")
