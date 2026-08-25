"""Coding workspace utilities: inspect project structure, search code, and collect focused context."""
from pathlib import Path

PLUGIN={"name":"coding_workspace","description":"Help JARVIS work like a coding agent: inspect project trees, search source files, read focused files, and summarize relevant code context before edits.","parameters":{"type":"OBJECT","properties":{"action":{"type":"STRING","description":"tree, search, read"},"path":{"type":"STRING","description":"Project or file path"},"query":{"type":"STRING","description":"Text or symbol to search"},"max_results":{"type":"INTEGER","description":"Maximum results"}},"required":["action"]}}
SKIP={'.git','__pycache__','.venv','venv','node_modules','.mypy_cache','.pytest_cache'}

def run(parameters,player=None,session_memory=None):
    p=parameters or {}; action=str(p.get("action","")).lower(); root=Path(str(p.get("path","."))).expanduser(); limit=min(max(int(p.get("max_results",50)),1),200)
    try:
        if action=="tree":
            out=[]
            for x in root.rglob("*"):
                if any(part in SKIP for part in x.parts):continue
                out.append(str(x.relative_to(root)))
                if len(out)>=limit:break
            return "\n".join(out) or "Empty project."
        if action=="search":
            q=str(p.get("query","")).lower();out=[]
            for x in root.rglob("*"):
                if len(out)>=limit or not x.is_file() or any(part in SKIP for part in x.parts):continue
                if x.suffix.lower() not in {'.py','.js','.ts','.tsx','.jsx','.json','.md','.txt','.yaml','.yml','.toml'}:continue
                try:
                    for n,line in enumerate(x.read_text(encoding='utf-8',errors='ignore').splitlines(),1):
                        if q in line.lower():out.append(f"{x}:{n}: {line.strip()}");break
                except:pass
            return "\n".join(out) or "No matches."
        if action=="read":
            if not root.is_file():return "CODING WORKSPACE: not a file."
            text=root.read_text(encoding='utf-8',errors='replace');return text[:120000]
        return "CODING WORKSPACE: use tree, search, or read."
    except Exception as e:return f"CODING WORKSPACE ERROR: {e}"
