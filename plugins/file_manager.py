"""Safe local file manager plugin for JARVIS."""
from pathlib import Path

PLUGIN={"name":"file_manager","description":"List, search, inspect, create directories, rename, copy, and delete files when explicitly requested. Never silently delete files.","parameters":{"type":"OBJECT","properties":{"action":{"type":"STRING","description":"list, search, read, mkdir, rename, copy, delete"},"path":{"type":"STRING","description":"Path"},"destination":{"type":"STRING","description":"Destination for rename/copy"},"query":{"type":"STRING","description":"Search text or filename"}},"required":["action"]}}

def run(parameters,player=None,session_memory=None):
    p=parameters or {}; action=str(p.get("action","")).lower().strip(); path=Path(str(p.get("path",""))).expanduser()
    try:
        if action=="list":
            if not path.exists():return "FILE MANAGER: path does not exist."
            return "\n".join(("[DIR] " if x.is_dir() else "[FILE] ")+x.name for x in sorted(path.iterdir(),key=lambda x:(not x.is_dir(),x.name.lower())))
        if action=="search":
            q=str(p.get("query","")).lower(); root=path if path.is_dir() else path.parent
            hits=[]
            for x in root.rglob("*"):
                if len(hits)>=100:break
                if q in x.name.lower():hits.append(str(x))
            return "\n".join(hits) or "No matches."
        if action=="read": return path.read_text(encoding="utf-8",errors="replace") if path.is_file() else "FILE MANAGER: not a file."
        if action=="mkdir": path.mkdir(parents=True,exist_ok=True); return f"Created {path}"
        dest=Path(str(p.get("destination","")).strip()).expanduser()
        if action=="rename": path.rename(dest); return f"Renamed to {dest}"
        if action=="copy":
            import shutil; shutil.copy2(path,dest); return f"Copied to {dest}"
        if action=="delete":
            if not path.exists():return "FILE MANAGER: path does not exist."
            if path.is_dir(): return "Refusing to delete a directory through this plugin."
            path.unlink(); return f"Deleted {path}"
        return "FILE MANAGER: use list, search, read, mkdir, rename, copy, or delete."
    except Exception as e:return f"FILE MANAGER ERROR: {e}"
