
# streamlit_supabase_crm_full_ultimate.py
# Full-featured CRM: notes, contacts, actions, timelines, CSV export

import streamlit as st
from supabase import create_client, Client
from datetime import date, datetime
import pandas as pd
import uuid
import io
import zipfile

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()

st.set_page_config(page_title="CRM Ultimate", layout="wide")
st.title("Supabase CRM - Full Feature Suite")

# --- Data Access Functions ---
def fetch_contacts():
    return supabase.table("contacts").select("*").execute().data or []

def fetch_notes():
    return supabase.table("notes").select("*").order("date", desc=True).execute().data or []

def fetch_actions():
    return supabase.table("actions").select("*, notes(title, date)").execute().data or []

def fetch_note_contacts():
    return supabase.table("note_contacts").select("*").execute().data or []

def get_linked_contacts():
    contacts = {c["id"]: c["name"] for c in fetch_contacts()}
    links = fetch_note_contacts()
    mapping = {}
    for l in links:
        mapping.setdefault(l["note_id"], []).append(contacts.get(l["contact_id"], "Unknown"))
    return mapping

# --- Note Logic ---
def save_note(note_data, contact_ids, actions, note_id=None):
    if not note_id:
        note_id = str(uuid.uuid4())
        supabase.table("notes").insert({**note_data, "id": note_id}).execute()
    else:
        supabase.table("notes").update(note_data).eq("id", note_id).execute()
        supabase.table("note_contacts").delete().eq("note_id", note_id).execute()
        supabase.table("actions").delete().eq("note_id", note_id).execute()
    for cid in contact_ids:
        supabase.table("note_contacts").insert({"note_id": note_id, "contact_id": cid}).execute()
    for act in actions:
        if act["description"]:
            supabase.table("actions").insert({
                "note_id": note_id,
                "description": act["description"],
                "due_date": act["due_date"]
            }).execute()
    return note_id

def delete_note(note_id):
    supabase.table("actions").delete().eq("note_id", note_id).execute()
    supabase.table("note_contacts").delete().eq("note_id", note_id).execute()
    supabase.table("notes").delete().eq("id", note_id).execute()

def export_notes_csv(notes):
    df = pd.DataFrame(notes)
    return df.to_csv(index=False).encode("utf-8")

# --- Tabs ---
tabs = st.tabs(["Add/Edit Note", "Manage Contacts", "Notes Dashboard", "Actions", "Export Data", "Contact Timeline"])

# --- Add/Edit Note Tab ---
with tabs[0]:
    st.subheader("Add or Edit a Note")
    contacts = fetch_contacts()
    contact_map = {c["name"]: c["id"] for c in contacts}
    contact_names = list(contact_map.keys())

    note_list = fetch_notes()
    note_title_map = {n["title"]: n for n in note_list}
    selected_note_title = st.selectbox("Select existing note to edit (or leave blank)", [""] + list(note_title_map.keys()))
    editing_note = note_title_map[selected_note_title] if selected_note_title else None

    title = st.text_input("Title", value=editing_note["title"] if editing_note else "")
    date_val = st.date_input("Date", value=datetime.strptime(editing_note["date"], "%Y-%m-%d").date() if editing_note else date.today())
    participants = st.text_input("Participants", value=editing_note["participants"] if editing_note else "")
    tags = st.text_input("Tags", value=editing_note["tags"] if editing_note else "")
    body = st.text_area("Note Body", value=editing_note["body"] if editing_note else "", height=200)
    
    linked_contacts = get_linked_contacts()
    current_contact_ids = [contact_map.get(c) for c in linked_contacts.get(editing_note["id"], [])] if editing_note else []
    selected_contacts = st.multiselect("Link Contacts", contact_names, default=[name for name in contact_names if contact_map[name] in current_contact_ids])
    linked_ids = [contact_map[name] for name in selected_contacts]

    st.markdown("### Actions")
    actions = []
    for i in range(3):
        desc = st.text_input(f"Action {i+1}", key=f"desc{i}", value="")
        due = st.date_input(f"Due Date {i+1}", key=f"due{i}", value=None)
        actions.append({"description": desc, "due_date": due.strftime("%Y-%m-%d") if due else None})

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save Note"):
            note_data = {
                "title": title,
                "date": date_val.strftime("%Y-%m-%d"),
                "participants": participants,
                "tags": tags,
                "body": body
            }
            note_id = editing_note["id"] if editing_note else None
            save_note(note_data, linked_ids, actions, note_id)
            st.success("Note saved.")
            st.rerun()
    with col2:
        if editing_note and st.button("Delete Note"):
            delete_note(editing_note["id"])
            st.success("Note deleted.")
            st.rerun()

# --- Manage Contacts ---
with tabs[1]:
    st.subheader("Contacts")
    contacts_df = pd.DataFrame(contacts)
    if not contacts_df.empty:
        selected = st.selectbox("Select contact to edit", contacts_df["name"])
        row = contacts_df[contacts_df["name"] == selected].iloc[0]
        new_name = st.text_input("Name", value=row["name"], key="edit_name")
        new_email = st.text_input("Email", value=row["email"], key="edit_email")
        new_phone = st.text_input("Phone", value=row["phone"], key="edit_phone")
        new_company = st.text_input("Company", value=row["company"], key="edit_company")
        new_tags = st.text_input("Tags", value=row["tags"], key="edit_tags")
        new_notes = st.text_area("Notes", value=row["notes"], key="edit_notes")

        if st.button("Update Contact"):
            supabase.table("contacts").update({
                "name": new_name,
                "email": new_email,
                "phone": new_phone,
                "company": new_company,
                "tags": new_tags,
                "notes": new_notes
            }).eq("id", row["id"]).execute()
            st.success("Contact updated.")
            st.rerun()

        if st.button("Delete Contact"):
            supabase.table("contacts").delete().eq("id", row["id"]).execute()
            st.success("Contact deleted.")
            st.rerun()

# --- Notes Dashboard ---
with tabs[2]:
    st.subheader("All Notes")
    notes = fetch_notes()
    link_map = get_linked_contacts()
    for note in notes:
        st.markdown(f"### {note['title']} ({note['date']})")
        st.markdown(f"**Participants:** {note['participants']}") 
st.markdown(f"**Tags:** {note['tags']}")  
st.markdown(f"**Contacts:** {', '.join(link_map.get(note['id'], []))}")
        st.markdown(note['body'])
        st.download_button("Download Note", data=note['body'], file_name=f"{note['title']}.txt")
        st.markdown("---")

# --- Actions Tab ---
with tabs[3]:
    st.subheader("All Actions")
    for row in fetch_actions():
        st.markdown(f"**{row['notes']['title']} ({row['notes']['date']})**")
        st.markdown(f"- {row['description']}")
        if row['due_date']:
            due = datetime.strptime(row['due_date'], "%Y-%m-%d").date()
            days = (due - date.today()).days
            color = "red" if days < 0 else "orange" if days <= 2 else "green"
            st.markdown(f"<span style='color:{color}'>Due: {row['due_date']}</span>", unsafe_allow_html=True)
        if st.button("Delete Action", key=row["id"]):
            supabase.table("actions").delete().eq("id", row["id"]).execute()
            st.rerun()

# --- Export Tab ---
with tabs[4]:
    st.subheader("Export All Data")
    notes_df = pd.DataFrame(fetch_notes())
    contacts_df = pd.DataFrame(fetch_contacts())
    actions_df = pd.DataFrame(fetch_actions())

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zipf:
        if not notes_df.empty:
            zipf.writestr("notes.csv", notes_df.to_csv(index=False))
        if not contacts_df.empty:
            zipf.writestr("contacts.csv", contacts_df.to_csv(index=False))
        if not actions_df.empty:
            zipf.writestr("actions.csv", actions_df.to_csv(index=False))

    st.download_button("Download Backup (ZIP)", data=buffer.getvalue(), file_name="crm_backup.zip")

# --- Contact Timeline ---
with tabs[5]:
    st.subheader("Contact Timeline")
    contact_options = fetch_contacts()
    contact_map = {c["name"]: c["id"] for c in contact_options}
    contact_choice = st.selectbox("Choose a contact", list(contact_map.keys()))
    contact_id = contact_map[contact_choice]

    links = fetch_note_contacts()
    notes = {n["id"]: n for n in fetch_notes()}
    note_ids = [l["note_id"] for l in links if l["contact_id"] == contact_id]
    timeline = sorted([notes[nid] for nid in note_ids if nid in notes], key=lambda x: x["date"], reverse=True)

    for note in timeline:
        st.markdown(f"### {note['title']} ({note['date']})")
        st.markdown(f"{note['body']}")
        st.markdown("---")
