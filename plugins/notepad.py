"""Persistent local notepad plugin."""
from pathlib import Path
from datetime import datetime

PLUGIN={"name":"notepad","description":"Create, append, read, list, and clear persistent JARVIS notes stored locally.","parameters":{"type":"OBJECT","properties":{"action":{"type":"STRING","description":"write, append, read, list, or clear"},"name":{"type":"STRING","description":"Note name"},"text":{"type":"STRING","description":"Text to write or append"}},"required":["action"]}}
ROOT=Path.home()/"JarvisProjects"/"notes"

def run(parameters,player=None,session_memory=None):
    p=parameters or {}; action=str(p.get("action","")).lower().strip(); ROOT.mkdir(parents=True,exist_ok=True)
    name=str(p.get("name","default")).strip() or "default"
    path=ROOT/(name.replace("..","_").replace("/","_").replace("\\","_")+".txt")
    try:
        if action in ("write","append"):
            text=str(p.get("text","")).strip()
            if not text:return "NOTEPAD: no text supplied."
            with path.open("a" if action=="append" else "w",encoding="utf-8") as f:
                if action=="append": f.write("\n")
                f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {text}\n")
            return f"Note '{name}' saved."
        if action=="read": return path.read_text(encoding="utf-8") if path.exists() else f"Note '{name}' does not exist."
        if action=="list": return "\n".join(x.stem for x in sorted(ROOT.glob("*.txt"))) or "No notes yet."
        if action=="clear": path.unlink(missing_ok=True); return f"Note '{name}' cleared."
        return "NOTEPAD: use write, append, read, list, or clear."
    except Exception as e:return f"NOTEPAD ERROR: {e}"
