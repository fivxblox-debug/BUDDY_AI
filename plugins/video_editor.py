"""
JARVIS Video Editor Plugin
Remotion + OpenChatCut MCP

Capabilities:
- Detect Remotion projects
- Inspect project files
- Create/edit Remotion React/TypeScript files
- Create Remotion compositions
- Open Remotion Studio
- Render Remotion compositions
- Run npm/npx project commands
- Connect to OpenChatCut Streamable HTTP MCP
- Maintain MCP sessions correctly
- List OpenChatCut tools
- Call OpenChatCut tools
- Automatically recover stale MCP sessions

Environment:
    OPENCHATCUT_MCP_URL=http://127.0.0.1:5199/api/external-mcp/mcp
    OPENCHATCUT_MCP_TOKEN=your_token_here
"""

from __future__ import annotations

import json
import os
import platform
import shlex
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


# =========================================================
# Optional .env support
# =========================================================

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


# =========================================================
# PLUGIN DEFINITION
# =========================================================

PLUGIN = {
    "name": "video_editor",
    "description": (
        "Advanced video editing plugin for JARVIS. "
        "Supports Remotion coding, motion graphics, animations, "
        "text, images, video, audio, transitions, rendering and "
        "OpenChatCut through its Streamable HTTP MCP interface. "
        "Use this plugin when the user wants JARVIS to create, "
        "inspect, edit, preview or render video projects."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": (
                    "Action: status, detect_project, list_files, "
                    "read_file, write_file, create_file, "
                    "create_composition, open_studio, render, run, "
                    "openchatcut_status, openchatcut_tools, "
                    "openchatcut_call."
                ),
            },
            "project": {
                "type": "STRING",
                "description": "Video or Remotion project directory.",
            },
            "file": {
                "type": "STRING",
                "description": "File path relative to the project.",
            },
            "content": {
                "type": "STRING",
                "description": "Complete file content.",
            },
            "composition": {
                "type": "STRING",
                "description": "Remotion composition ID.",
            },
            "output": {
                "type": "STRING",
                "description": "Rendered video output path.",
            },
            "command": {
                "type": "STRING",
                "description": "npm/npx project command.",
            },
            "editor": {
                "type": "STRING",
                "description": "Video editor name.",
            },
            "tool": {
                "type": "STRING",
                "description": "OpenChatCut MCP tool name.",
            },
            "arguments": {
                "type": "OBJECT",
                "description": "Arguments for the OpenChatCut MCP tool.",
            },
        },
        "required": ["action"],
    },
}


# =========================================================
# LOGGING
# =========================================================

def _log(player, message: str):
    if player:
        try:
            player.write_log(f"JARVIS: {message}")
        except Exception:
            pass


def _result(message: str, player=None) -> str:
    _log(player, message)
    return message


# =========================================================
# PROJECT HELPERS
# =========================================================

def _find_project(project: str | None) -> Path:

    if project:
        path = Path(project).expanduser().resolve()
    else:
        path = Path.cwd().resolve()

    if not path.exists():
        raise RuntimeError(
            f"Project does not exist: {path}"
        )

    if not path.is_dir():
        raise RuntimeError(
            f"Project path is not a directory: {path}"
        )

    return path


def _package_json(project: Path) -> dict[str, Any]:

    package_file = project / "package.json"

    if not package_file.exists():
        return {}

    try:
        return json.loads(
            package_file.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return {}


def _is_remotion_project(project: Path) -> bool:

    data = _package_json(project)

    dependencies: dict[str, Any] = {}

    dependencies.update(
        data.get("dependencies", {})
    )

    dependencies.update(
        data.get("devDependencies", {})
    )

    dependencies.update(
        data.get("peerDependencies", {})
    )

    return any(
        "remotion" in str(name).lower()
        for name in dependencies
    )


# =========================================================
# COMMAND EXECUTION
# =========================================================

def _npm_command(args: list[str]) -> list[str]:

    if platform.system() == "Windows":
        return ["npm.cmd", *args]

    return ["npm", *args]


def _run(
    command: list[str],
    cwd: Path,
    timeout: int = 900,
) -> tuple[int, str]:

    process = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        shell=False,
    )

    output = process.stdout or ""

    if process.stderr:
        output += "\n" + process.stderr

    return (
        process.returncode,
        output.strip(),
    )


def _run_remotion(
    project: Path,
    args: list[str],
    timeout: int = 1800,
):

    return _run(
        _npm_command(
            [
                "exec",
                "remotion",
                "--",
                *args,
            ]
        ),
        project,
        timeout,
    )


# =========================================================
# SAFE PROJECT FILES
# =========================================================

def _safe_project_file(
    project: Path,
    filename: str,
) -> Path:

    target = (
        project / filename
    ).resolve()

    try:
        target.relative_to(project)
    except ValueError:
        raise RuntimeError(
            "The file must stay inside the selected project."
        )

    return target


# =========================================================
# OPENCHATCUT MCP STATE
# =========================================================

_MCP_SESSION_ID: str | None = None
_MCP_REQUEST_ID = 0


def _mcp_url() -> str:

    return os.getenv(
        "OPENCHATCUT_MCP_URL",
        "http://127.0.0.1:5199/api/external-mcp/mcp",
    ).strip()


def _mcp_token() -> str:

    return (
        os.getenv(
            "OPENCHATCUT_MCP_TOKEN",
            "",
        )
        .strip()
        .strip("'")
        .strip('"')
    )


def _next_request_id() -> int:

    global _MCP_REQUEST_ID

    _MCP_REQUEST_ID += 1

    return _MCP_REQUEST_ID


def _reset_mcp_session():

    global _MCP_SESSION_ID

    _MCP_SESSION_ID = None


# =========================================================
# MCP RESPONSE PARSER
# =========================================================

def _parse_mcp_response(
    raw: str,
    content_type: str,
):

    raw = raw.strip()

    if not raw:
        return {}

    # Normal JSON
    if (
        "application/json"
        in content_type.lower()
    ):

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

    # Streamable HTTP / SSE
    results = []

    for line in raw.splitlines():

        line = line.strip()

        if not line.startswith("data:"):
            continue

        data = line[
            len("data:"):
        ].strip()

        if not data:
            continue

        if data == "[DONE]":
            continue

        try:
            results.append(
                json.loads(data)
            )
        except json.JSONDecodeError:
            continue

    if len(results) == 1:
        return results[0]

    if results:
        return results

    # Last attempt
    try:
        return json.loads(raw)
    except Exception:
        return {
            "raw": raw
        }


# =========================================================
# MCP HTTP REQUEST
# =========================================================

def _mcp_request(
    payload: dict[str, Any],
    timeout: int = 60,
):

    global _MCP_SESSION_ID

    token = _mcp_token()

    if not token:
        raise RuntimeError(
            "OPENCHATCUT_MCP_TOKEN is not configured."
        )

    headers = {
        "Content-Type": "application/json",
        "Accept": (
            "application/json, "
            "text/event-stream"
        ),
        "Authorization": (
            f"Bearer {token}"
        ),

        # MCP protocol version
        "MCP-Protocol-Version": "2025-03-26",
    }

    # IMPORTANT:
    # Every request after initialize must use
    # the session returned by the server.
    if _MCP_SESSION_ID:
        headers["Mcp-Session-Id"] = (
            _MCP_SESSION_ID
        )

    request = urllib.request.Request(
        _mcp_url(),
        data=json.dumps(
            payload
        ).encode("utf-8"),
        method="POST",
        headers=headers,
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:

            # OpenChatCut returns the session here.
            session_id = (
                response.headers.get(
                    "Mcp-Session-Id"
                )
            )

            if session_id:
                _MCP_SESSION_ID = (
                    session_id
                )

            raw = (
                response.read()
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )

            return _parse_mcp_response(
                raw,
                response.headers.get(
                    "Content-Type",
                    "",
                ),
            )

    except urllib.error.HTTPError as e:

        body = (
            e.read()
            .decode(
                "utf-8",
                errors="replace",
            )
        )

        raise RuntimeError(
            f"OpenChatCut MCP HTTP {e.code}: "
            f"{body[:5000]}"
        )

    except urllib.error.URLError as e:

        raise RuntimeError(
            "Could not connect to OpenChatCut MCP: "
            f"{e}"
        )


# =========================================================
# MCP INITIALIZATION
# =========================================================

def _mcp_initialize():

    global _MCP_SESSION_ID

    # Always begin a fresh session.
    _MCP_SESSION_ID = None

    result = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": _next_request_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {
                    "name": "JARVIS",
                    "version": "1.0",
                },
            },
        }
    )

    # MCP requires this notification after
    # successful initialization.
    try:

        _mcp_request(
            {
                "jsonrpc": "2.0",
                "method": (
                    "notifications/initialized"
                ),
                "params": {},
            }
        )

    except Exception:
        # Some MCP implementations return no body
        # for notifications. That is okay.
        pass

    return result


def _ensure_mcp_session():

    if not _MCP_SESSION_ID:
        _mcp_initialize()


# =========================================================
# MCP TOOLS
# =========================================================

def _mcp_tools_list():

    _ensure_mcp_session()

    try:

        return _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": _next_request_id(),
                "method": "tools/list",
                "params": {},
            }
        )

    except RuntimeError as e:

        # Recover from a stale session.
        if (
            "not initialized"
            in str(e).lower()
            or "session"
            in str(e).lower()
        ):

            _mcp_initialize()

            return _mcp_request(
                {
                    "jsonrpc": "2.0",
                    "id": _next_request_id(),
                    "method": "tools/list",
                    "params": {},
                }
            )

        raise


def _mcp_tool_call(
    tool_name: str,
    arguments: dict[str, Any],
):

    _ensure_mcp_session()

    payload = {
        "jsonrpc": "2.0",
        "id": _next_request_id(),
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments or {},
        },
    }

    try:

        return _mcp_request(
            payload,
            timeout=300,
        )

    except RuntimeError as e:

        # OpenChatCut can invalidate a session.
        # Automatically reconnect once.
        if (
            "not initialized"
            in str(e).lower()
            or "session"
            in str(e).lower()
        ):

            _mcp_initialize()

            payload["id"] = (
                _next_request_id()
            )

            return _mcp_request(
                payload,
                timeout=300,
            )

        raise


# =========================================================
# PLUGIN ENTRY POINT
# =========================================================

def run(
    parameters: dict,
    player=None,
    session_memory=None,
) -> str:

    params = parameters or {}

    action = str(
        params.get(
            "action",
            "",
        )
    ).strip().lower()

    try:

        # =================================================
        # STATUS
        # =================================================

        if action in (
            "status",
            "detect_project",
        ):

            project = _find_project(
                params.get("project")
            )

            package = _package_json(
                project
            )

            if _is_remotion_project(
                project
            ):

                return _result(
                    "Remotion project detected.\n"
                    f"Project: {project}\n"
                    f"Name: "
                    f"{package.get('name', 'unknown')}",
                    player,
                )

            return _result(
                f"No Remotion project detected at "
                f"{project}.",
                player,
            )

        # =================================================
        # LIST FILES
        # =================================================

        if action in (
            "list_files",
            "files",
        ):

            project = _find_project(
                params.get("project")
            )

            ignored = {
                "node_modules",
                ".git",
                "out",
                "dist",
                ".next",
                "__pycache__",
            }

            files = []

            for item in project.rglob("*"):

                if not item.is_file():
                    continue

                if any(
                    part in ignored
                    for part in item.parts
                ):
                    continue

                files.append(
                    str(
                        item.relative_to(
                            project
                        )
                    )
                )

                if len(files) >= 500:
                    break

            return _result(
                "Project files:\n"
                + "\n".join(
                    f"- {file}"
                    for file in files
                ),
                player,
            )

        # =================================================
        # READ FILE
        # =================================================

        if action in (
            "read_file",
            "inspect_file",
        ):

            project = _find_project(
                params.get("project")
            )

            filename = params.get(
                "file"
            )

            if not filename:
                return _result(
                    "I need a file path.",
                    player,
                )

            target = _safe_project_file(
                project,
                filename,
            )

            if not target.exists():
                return _result(
                    f"File not found: {filename}",
                    player,
                )

            content = target.read_text(
                encoding="utf-8",
                errors="replace",
            )

            if len(content) > 50000:
                content = (
                    content[:50000]
                    + "\n\n[truncated]"
                )

            return _result(
                content,
                player,
            )

        # =================================================
        # WRITE FILE
        # =================================================

        if action in (
            "write_file",
            "create_file",
            "edit_file",
        ):

            project = _find_project(
                params.get("project")
            )

            filename = params.get(
                "file"
            )

            content = params.get(
                "content"
            )

            if not filename:
                return _result(
                    "I need a file path.",
                    player,
                )

            if content is None:
                return _result(
                    "I need the file content.",
                    player,
                )

            target = _safe_project_file(
                project,
                filename,
            )

            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            target.write_text(
                str(content),
                encoding="utf-8",
            )

            return _result(
                f"Updated {filename}.",
                player,
            )

        # =================================================
        # CREATE REMOTION COMPOSITION
        # =================================================

        if action == "create_composition":

            project = _find_project(
                params.get("project")
            )

            if not _is_remotion_project(
                project
            ):
                return _result(
                    "That folder is not detected "
                    "as a Remotion project.",
                    player,
                )

            composition = (
                params.get("composition")
                or "MyVideo"
            )

            filename = (
                params.get("file")
                or f"src/{composition}.tsx"
            )

            content = params.get(
                "content"
            )

            if not content:

                content = f'''import React from "react";
import {{
    AbsoluteFill,
    Easing,
    interpolate,
    useCurrentFrame,
    useVideoConfig,
}} from "remotion";

export const {composition}: React.FC = () => {{
    const frame = useCurrentFrame();
    const {{fps}} = useVideoConfig();

    const opacity = interpolate(
        frame,
        [0, fps],
        [0, 1],
        {{
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(
                0.16,
                1,
                0.3,
                1
            ),
        }}
    );

    const scale = interpolate(
        frame,
        [0, fps],
        [0.8, 1],
        {{
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
        }}
    );

    return (
        <AbsoluteFill
            style={{
                backgroundColor: "#111",
                justifyContent: "center",
                alignItems: "center",
            }}
        >
            <div
                style={{
                    opacity,
                    transform: `scale(${{scale}})`,
                    color: "white",
                    fontSize: 96,
                    fontWeight: 700,
                    fontFamily: "Arial",
                }}
            >
                {composition}
            </div>
        </AbsoluteFill>
    );
}};
'''

            target = _safe_project_file(
                project,
                filename,
            )

            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            target.write_text(
                content,
                encoding="utf-8",
            )

            return _result(
                f"Created Remotion composition "
                f"{composition} in {filename}.",
                player,
            )

        # =================================================
        # OPEN REMOTION STUDIO
        # =================================================

        if action in (
            "open_studio",
            "studio",
            "preview",
        ):

            project = _find_project(
                params.get("project")
            )

            if not _is_remotion_project(
                project
            ):
                return _result(
                    "That folder is not detected "
                    "as a Remotion project.",
                    player,
                )

            process = subprocess.Popen(
                _npm_command(
                    [
                        "exec",
                        "remotion",
                        "--",
                        "studio",
                        "--no-open",
                    ]
                ),
                cwd=str(project),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                shell=False,
            )

            return _result(
                f"Remotion Studio started. "
                f"PID: {process.pid}",
                player,
            )

        # =================================================
        # RENDER
        # =================================================

        if action in (
            "render",
            "render_video",
        ):

            project = _find_project(
                params.get("project")
            )

            composition = params.get(
                "composition"
            )

            output = (
                params.get("output")
                or "out/video.mp4"
            )

            if not composition:
                return _result(
                    "I need the composition ID.",
                    player,
                )

            code, output_text = (
                _run_remotion(
                    project,
                    [
                        "render",
                        composition,
                        output,
                    ],
                    timeout=1800,
                )
            )

            if code != 0:

                return _result(
                    "Render failed:\n"
                    + output_text[-8000:],
                    player,
                )

            return _result(
                "Render completed:\n"
                + output_text[-5000:],
                player,
            )

        # =================================================
        # RUN NPM / NPX
        # =================================================

        if action in (
            "run",
            "command",
        ):

            project = _find_project(
                params.get("project")
            )

            command_text = str(
                params.get(
                    "command",
                    "",
                )
            ).strip()

            if not command_text:
                return _result(
                    "I need a command.",
                    player,
                )

            parts = shlex.split(
                command_text,
                posix=False,
            )

            if not parts:
                return _result(
                    "Empty command.",
                    player,
                )

            executable = (
                parts[0]
                .lower()
                .replace(
                    ".cmd",
                    "",
                )
            )

            if executable not in (
                "npm",
                "npx",
            ):
                return _result(
                    "Only npm/npx project commands "
                    "are allowed here.",
                    player,
                )

            code, output_text = _run(
                parts,
                project,
                timeout=1800,
            )

            if code != 0:

                return _result(
                    "Command failed:\n"
                    + output_text[-8000:],
                    player,
                )

            return _result(
                output_text[-8000:]
                or "Command completed.",
                player,
            )

        # =================================================
        # OPENCHATCUT STATUS
        # =================================================

        if action == "openchatcut_status":

            url = _mcp_url()

            if not _mcp_token():

                return _result(
                    "OpenChatCut is not configured. "
                    "OPENCHATCUT_MCP_TOKEN is missing.",
                    player,
                )

            try:

                result = _mcp_initialize()

                return _result(
                    "OpenChatCut MCP connected.\n"
                    f"Endpoint: {url}\n"
                    f"Session: "
                    f"{_MCP_SESSION_ID}\n"
                    f"Server: "
                    f"{json.dumps(result)[:4000]}",
                    player,
                )

            except Exception as e:

                return _result(
                    "OpenChatCut MCP connection failed:\n"
                    f"{e}",
                    player,
                )

        # =================================================
        # OPENCHATCUT TOOLS
        # =================================================

        if action in (
            "openchatcut_tools",
            "mcp_tools",
        ):

            result = _mcp_tools_list()

            return _result(
                json.dumps(
                    result,
                    indent=2,
                )[:20000],
                player,
            )

        # =================================================
        # OPENCHATCUT TOOL CALL
        # =================================================

        if action in (
            "openchatcut_call",
            "mcp_call",
        ):

            tool_name = str(
                params.get(
                    "tool",
                    "",
                )
            ).strip()

            arguments = (
                params.get(
                    "arguments"
                )
                or {}
            )

            if not tool_name:
                return _result(
                    "I need the OpenChatCut "
                    "tool name.",
                    player,
                )

            result = _mcp_tool_call(
                tool_name,
                arguments,
            )

            return _result(
                json.dumps(
                    result,
                    indent=2,
                )[:30000],
                player,
            )

        # =================================================
        # UNKNOWN ACTION
        # =================================================

        return _result(
            "Unknown video action. Available actions: "
            "status, detect_project, list_files, "
            "read_file, write_file, create_file, "
            "create_composition, open_studio, render, "
            "run, openchatcut_status, "
            "openchatcut_tools, openchatcut_call.",
            player,
        )

    # =====================================================
    # ERRORS
    # =====================================================

    except subprocess.TimeoutExpired:

        return _result(
            "The video operation timed out.",
            player,
        )

    except Exception as e:

        return _result(
            f"Video plugin failed: {e}",
            player,
        )