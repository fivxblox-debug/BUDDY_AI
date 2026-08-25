"""Lightweight persistent calendar plugin using iCalendar-compatible events."""
from pathlib import Path
from datetime import datetime
import json

PLUGIN={"name":"calendar","description":"Create, list, and remove local calendar events for JARVIS.","parameters":{"type":"OBJECT","properties":{"action":{"type":"STRING","description":"add, list, or remove"},"title":{"type":"STRING","description":"Event title"},"when":{"type":"STRING","description":"Date/time text or ISO timestamp"},"event_id":{"type":"STRING","description":"Event ID"}},"required":["action"]}}
DB=Path.home()/"JarvisProjects"/"calendar.json"

def _load():
    try:return json.loads(DB.read_text(encoding="utf-8"))
    except:return []
def _save(x):DB.parent.mkdir(parents=True,exist_ok=True);DB.write_text(json.dumps(x,indent=2),encoding="utf-8")
def run(parameters,player=None,session_memory=None):
    p=parameters or {}; action=str(p.get("action","")).lower().strip(); events=_load()
    if action=="add":
        title=str(p.get("title","")).strip(); when=str(p.get("when","")).strip()
        if not title or not when:return "CALENDAR: title and when are required."
        e={"id":datetime.now().strftime("%Y%m%d%H%M%S%f"),"title":title,"when":when};events.append(e);_save(events);return f"Added '{title}' on {when}. ID: {e['id']}"
    if action=="list":
        return "\n".join(f"{e['id']} | {e['when']} | {e['title']}" for e in events) or "Calendar is empty."
    if action=="remove":
        i=str(p.get("event_id",""));new=[e for e in events if e["id"]!=i]
        if len(new)==len(events):return "CALENDAR: event not found."
        _save(new);return "Calendar event removed."
    return "CALENDAR: use add, list, or remove."
