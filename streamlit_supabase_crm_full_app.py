
import streamlit as st
from supabase import create_client, Client
from datetime import date, datetime
import pandas as pd
import uuid

# Load Supabase credentials
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()

st.title("KJC Supabase CRM")

# Fetch all contacts
def fetch_contacts():
    response = supabase.table("contacts").select("*").order("name").execute()
    return response.data if response.data else []

# Save a new contact
def save_contact(data):
    supabase.table("contacts").insert(data).execute()

# Save a new note with multi-contacts and actions
def save_note(note_data, contact_ids, actions):
    note_id = str(uuid.uuid4())
    supabase.table("notes").insert({**note_data, "id": note_id}).execute()
    for cid in contact_ids:
        supabase.table("note_contacts").insert({"note_id": note_id, "contact_id": cid}).execute()
    for act in actions:
        if act["description"]:
            supabase.table("actions").insert({
                "note_id": note_id,
                "description": act["description"],
                "due_date": act["due_date"]
            }).execute()

# Fetch joined notes with contact names
def get_notes():
    notes = supabase.table("notes").select("*").order("date", desc=True).execute().data
    links = supabase.table("note_contacts").select("*").execute().data
    contacts = {c["id"]: c["name"] for c in fetch_contacts()}
    by_note = {}
    for l in links:
        by_note.setdefault(l["note_id"], []).append(contacts.get(l["contact_id"], "Unknown"))
    for note in notes:
        note["contacts"] = ", ".join(by_note.get(note["id"], []))
    return notes

# Get all actions
def get_actions():
    actions = supabase.table("actions").select("id, note_id, description, due_date, notes(title, date)").execute()
    return actions.data if actions.data else []

# Delete action by ID
def delete_action(action_id):
    supabase.table("actions").delete().eq("id", action_id).execute()

# Tabs
tabs = st.tabs(["Add Note", "Contacts", "Notes Dashboard", "Actions"])

# --- Add Note ---
with tabs[0]:
    st.subheader("New Meeting Note")
    contacts = fetch_contacts()
    contact_name_map = {c["name"]: c["id"] for c in contacts}
    contact_names = list(contact_name_map.keys())

    title = st.text_input("Title")
    date_val = st.date_input("Date", date.today())
    participants = st.text_input("Participants")
    tags = st.text_input("Tags")
    body = st.text_area("Notes", height=150)
    selected_contacts = st.multiselect("Link Contacts", contact_names)
    linked_ids = [contact_name_map[name] for name in selected_contacts]

    st.markdown("### Actions")
    actions = []
    for i in range(3):
        desc = st.text_input(f"Action {i+1}", key=f"desc_{i}")
        due = st.date_input(f"Due Date {i+1}", value=None, key=f"due_{i}")
        actions.append({"description": desc, "due_date": due.strftime("%Y-%m-%d") if due else None})

    if st.button("Save Note"):
        if title and linked_ids:
            note_data = {
                "title": title,
                "date": date_val.strftime("%Y-%m-%d"),
                "participants": participants,
                "tags": tags,
                "body": body
            }
            save_note(note_data, linked_ids, actions)
            st.success("Note saved to Supabase.")
        else:
            st.warning("Title and at least one contact are required.")

# --- Contacts ---
with tabs[1]:
    st.subheader("Add or Search Contacts")
    new_name = st.text_input("Name", key="contact_name")
    new_email = st.text_input("Email", key="contact_email")
    new_phone = st.text_input("Phone", key="contact_phone")
    new_company = st.text_input("Company", key="contact_company")
    new_tags = st.text_input("Tags", key="contact_tags")
    new_notes = st.text_area("Notes", key="contact_notes")
    if st.button("Add Contact"):
        if new_name:
            save_contact({
                "id": str(uuid.uuid4()),
                "name": new_name,
                "email": new_email,
                "phone": new_phone,
                "company": new_company,
                "tags": new_tags,
                "notes": new_notes
            })
            st.success("Contact added.")
        else:
            st.warning("Name is required.")

    st.markdown("### All Contacts")
    contact_search = st.text_input("Search contacts by name or company")
    contact_list = pd.DataFrame(fetch_contacts())
    if not contact_list.empty:
        if contact_search:
            contact_list = contact_list[
                contact_list["name"].str.contains(contact_search, case=False, na=False) |
                contact_list["company"].str.contains(contact_search, case=False, na=False)
            ]
        st.dataframe(contact_list[["name", "email", "company", "tags"]])
    else:
        st.info("No contacts found.")

# --- Notes Dashboard ---
with tabs[2]:
    st.subheader("Search Notes")
    search = st.text_input("Search text")
    tag_filter = st.text_input("Tag filter")
    date_filter = st.date_input("Filter by date", value=None)

    notes_df = pd.DataFrame(get_notes())
    if not notes_df.empty:
        if search:
            notes_df = notes_df[notes_df["title"].str.contains(search, case=False, na=False) | notes_df["body"].str.contains(search, case=False, na=False)]
        if tag_filter:
            notes_df = notes_df[notes_df["tags"].str.contains(tag_filter, case=False, na=False)]
        if date_filter:
            notes_df = notes_df[notes_df["date"] == date_filter.strftime("%Y-%m-%d")]
        for _, row in notes_df.iterrows():
            st.markdown(f"### {row['title']} ({row['date']})")
            st.markdown(f"**Contacts:** {row['contacts']}")
            st.markdown(f"**Participants:** {row['participants']}")
            st.markdown(f"**Tags:** {row['tags']}")
            st.markdown(f"{row['body']}")
            st.markdown("---")
    else:
        st.info("No notes found.")

# --- Actions ---
with tabs[3]:
    st.subheader("All Actions")
    actions = get_actions()
    if actions:
        for row in actions:
            st.markdown(f"**{row['notes']['title']} ({row['notes']['date']})**")
            st.markdown(f"- {row['description']}")
            if row['due_date']:
                due = datetime.strptime(row['due_date'], "%Y-%m-%d").date()
                days_left = (due - date.today()).days
                color = "red" if days_left < 0 else "orange" if days_left <= 2 else "green"
                st.markdown(f"<span style='color:{color}'>Due: {row['due_date']}</span>", unsafe_allow_html=True)
            if st.button("Delete", key=row["id"]):
                delete_action(row["id"])
                st.success("Deleted")
                st.rerun()
    else:
        st.info("No actions found.")
