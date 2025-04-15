
import streamlit as st
from supabase import create_client, Client
from datetime import date
import pandas as pd
import uuid

# Load Supabase credentials from Streamlit secrets
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()

st.title("Supabase CRM - Notes + Contacts + Actions")

# Fetch contacts
@st.cache_data
def fetch_contacts():
    return supabase.table("contacts").select("*").execute().data

# Save note and related actions + contact links
def save_note(title, date_val, participants, tags, body, contact_ids, actions):
    note_id = str(uuid.uuid4())
    supabase.table("notes").insert({
        "id": note_id,
        "title": title,
        "date": date_val,
        "participants": participants,
        "tags": tags,
        "body": body
    }).execute()

    for cid in contact_ids:
        supabase.table("note_contacts").insert({
            "note_id": note_id,
            "contact_id": cid
        }).execute()

    for act in actions:
        if act["description"]:
            supabase.table("actions").insert({
                "note_id": note_id,
                "description": act["description"],
                "due_date": act["due_date"]
            }).execute()

# UI for adding notes
contacts = fetch_contacts()
contact_name_map = {c["name"]: c["id"] for c in contacts}
contact_names = list(contact_name_map.keys())

st.subheader("Add New Meeting Note")
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
    actions.append({
        "description": desc,
        "due_date": due.strftime("%Y-%m-%d") if due else None
    })

if st.button("Save Note"):
    if title and linked_ids:
        save_note(title, date_val.strftime("%Y-%m-%d"), participants, tags, body, linked_ids, actions)
        st.success("Note saved to Supabase.")
    else:
        st.warning("Title and at least one contact are required.")
