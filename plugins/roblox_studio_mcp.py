"""
JARVIS Roblox Studio MCP Plugin

Connects JARVIS to the official Roblox Studio MCP server.

Windows:
    %LOCALAPPDATA%\\Roblox\\mcp.bat

Roblox Studio must have Studio MCP enabled.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import threading
import time
from typing import Any, Optional


# ============================================================
# JARVIS PLUGIN DEFINITION
# ============================================================

PLUGIN = {
    "name": "roblox_studio_mcp",

    "description": (
        "Connect to the official Roblox Studio MCP server. "
        "Use this when the user asks Buddy or JARVIS to inspect, "
        "read, search, edit, create, run, test, or interact with "
        "an open Roblox Studio project. "
        "Do not use browser tools for Roblox Studio actions."
    ),

    "parameters": {
        "type": "OBJECT",

        "properties": {

            "action": {
                "type": "STRING",
                "description": (
                    "Roblox Studio operation. Examples: "
                    "connect, list_studios, list_tools, "
                    "script_read, script_search, script_grep, "
                    "multi_edit, execute_luau, "
                    "get_studio_state, start_stop_play, "
                    "get_console_output, screen_capture, "
                    "call_tool, disconnect."
                ),
            },

            "tool": {
                "type": "STRING",
                "description": (
                    "Exact Roblox Studio MCP tool name."
                ),
            },

            "arguments": {
                "type": "OBJECT",
                "description": (
                    "Arguments to send to a Roblox Studio MCP tool."
                ),
            },

            "studio_id": {
                "type": "STRING",
                "description": (
                    "Roblox Studio instance ID."
                ),
            },

            "path": {
                "type": "STRING",
                "description": (
                    "Roblox Studio path, for example "
                    "game.ServerScriptService.MyScript."
                ),
            },

            "query": {
                "type": "STRING",
                "description": (
                    "Search query."
                ),
            },

            "pattern": {
                "type": "STRING",
                "description": (
                    "Text pattern to search for."
                ),
            },

            "code": {
                "type": "STRING",
                "description": (
                    "Luau code to execute."
                ),
            },

            "datamodel_type": {
                "type": "STRING",
                "description": (
                    "Roblox data model type, such as Edit."
                ),
            },

            "edits": {
                "type": "ARRAY",
                "description": (
                    "List of script edits."
                ),

                "items": {
                    "type": "OBJECT",

                    "properties": {

                        "old_text": {
                            "type": "STRING",
                            "description": (
                                "Text to replace."
                            ),
                        },

                        "new_text": {
                            "type": "STRING",
                            "description": (
                                "Replacement text."
                            ),
                        },

                    },

                    "required": [
                        "old_text",
                        "new_text",
                    ],
                },
            },

            "playing": {
                "type": "BOOLEAN",
                "description": (
                    "Whether Roblox Studio should be playing."
                ),
            },

        },

        "required": [
            "action",
        ],
    },
}


# ============================================================
# ERRORS
# ============================================================

class RobloxMCPError(Exception):
    pass


# ============================================================
# MCP CLIENT
# ============================================================

class RobloxMCPClient:

    def __init__(self):

        self.process: Optional[subprocess.Popen] = None

        self.lock = threading.Lock()

        self.next_id = 1

        self.responses: dict[int, dict[str, Any]] = {}

        self.reader_thread: Optional[threading.Thread] = None

        self.running = False


    # --------------------------------------------------------
    # Locate Roblox MCP
    # --------------------------------------------------------

    def get_command(self):

        system = platform.system()

        if system == "Windows":

            local_app_data = os.environ.get(
                "LOCALAPPDATA"
            )

            if not local_app_data:

                raise RobloxMCPError(
                    "LOCALAPPDATA is not available."
                )

            mcp_path = os.path.join(
                local_app_data,
                "Roblox",
                "mcp.bat",
            )

            if not os.path.isfile(mcp_path):

                raise RobloxMCPError(
                    "Roblox Studio MCP was not found at "
                    f"{mcp_path}. "
                    "Enable Studio MCP in Roblox Studio."
                )

            return [
                "cmd.exe",
                "/c",
                mcp_path,
            ]


        raise RobloxMCPError(
            f"Unsupported operating system: {system}"
        )


    # --------------------------------------------------------
    # Start
    # --------------------------------------------------------

    def start(self):

        with self.lock:

            if (
                self.process
                and self.process.poll() is None
            ):
                return

            command = self.get_command()

            try:

                self.process = subprocess.Popen(

                    command,

                    stdin=subprocess.PIPE,

                    stdout=subprocess.PIPE,

                    stderr=subprocess.PIPE,

                    text=True,

                    encoding="utf-8",

                    errors="replace",

                    bufsize=1,

                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if platform.system() == "Windows"
                        else 0
                    ),
                )

            except Exception as e:

                self.process = None

                raise RobloxMCPError(
                    f"Failed to start Roblox MCP: {e}"
                )


            self.running = True


            self.reader_thread = threading.Thread(
                target=self._reader,
                daemon=True,
                name="JARVIS-Roblox-MCP",
            )

            self.reader_thread.start()


        # Initialize MCP
        self._initialize()


    # --------------------------------------------------------
    # Reader
    # --------------------------------------------------------

    def _reader(self):

        process = self.process

        if not process:
            return

        if not process.stdout:
            return


        while self.running:

            try:

                line = process.stdout.readline()

            except Exception:

                break


            if not line:

                break


            line = line.strip()

            if not line:
                continue


            try:

                message = json.loads(line)

            except json.JSONDecodeError:

                continue


            if "id" not in message:
                continue


            try:

                request_id = int(
                    message["id"]
                )

            except Exception:

                continue


            self.responses[request_id] = message


    # --------------------------------------------------------
    # Send JSON-RPC
    # --------------------------------------------------------

    def _send(self, message):

        process = self.process

        if not process:

            raise RobloxMCPError(
                "Roblox MCP is not running."
            )


        if process.poll() is not None:

            raise RobloxMCPError(
                "Roblox MCP process has stopped."
            )


        if not process.stdin:

            raise RobloxMCPError(
                "Roblox MCP stdin is unavailable."
            )


        payload = json.dumps(
            message,
            separators=(",", ":"),
            ensure_ascii=False,
        )


        process.stdin.write(
            payload + "\n"
        )

        process.stdin.flush()


    # --------------------------------------------------------
    # Request
    # --------------------------------------------------------

    def request(
        self,
        method,
        params=None,
        timeout=30,
    ):

        self.start()


        request_id = self.next_id

        self.next_id += 1


        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }


        if params is not None:

            message["params"] = params


        self.responses.pop(
            request_id,
            None,
        )


        self._send(message)


        deadline = (
            time.monotonic()
            + timeout
        )


        while time.monotonic() < deadline:

            response = self.responses.pop(
                request_id,
                None,
            )


            if response:

                if "error" in response:

                    error = response["error"]

                    raise RobloxMCPError(
                        error.get(
                            "message",
                            "Unknown MCP error.",
                        )
                    )


                return response.get(
                    "result",
                    {},
                )


            if (
                self.process
                and self.process.poll()
                is not None
            ):

                raise RobloxMCPError(
                    "Roblox Studio MCP stopped."
                )


            time.sleep(0.01)


        raise RobloxMCPError(
            f"Timeout waiting for MCP '{method}'."
        )


    # --------------------------------------------------------
    # Initialize
    # --------------------------------------------------------

    def _initialize(self):

        result = self.request(

            "initialize",

            {
                "protocolVersion": "2025-06-18",

                "capabilities": {},

                "clientInfo": {
                    "name": "JARVIS",
                    "version": "1.0.0",
                },
            },

            timeout=20,
        )


        try:

            self._send({
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            })

        except Exception:

            pass


        return result


    # --------------------------------------------------------
    # MCP tools
    # --------------------------------------------------------

    def list_tools(self):

        return self.request(
            "tools/list",
            {},
            timeout=30,
        )


    def call_tool(
        self,
        name,
        arguments=None,
    ):

        return self.request(

            "tools/call",

            {
                "name": name,

                "arguments": (
                    arguments or {}
                ),
            },

            timeout=120,
        )


    # --------------------------------------------------------
    # Close
    # --------------------------------------------------------

    def close(self):

        self.running = False

        process = self.process

        self.process = None


        if not process:
            return


        try:

            process.terminate()

        except Exception:

            pass


        try:

            process.wait(
                timeout=3
            )

        except Exception:

            try:
                process.kill()

            except Exception:
                pass


# ============================================================
# GLOBAL CLIENT
# ============================================================

_client = RobloxMCPClient()

_cached_studio_id = None


# ============================================================
# RESULT HELPERS
# ============================================================

def extract_text(result):

    if result is None:
        return ""


    if isinstance(result, str):
        return result


    if isinstance(result, dict):

        content = result.get(
            "content"
        )


        if isinstance(
            content,
            list,
        ):

            output = []


            for item in content:

                if not isinstance(
                    item,
                    dict,
                ):
                    continue


                if item.get(
                    "type"
                ) == "text":

                    text = item.get(
                        "text",
                        "",
                    )


                    if text:
                        output.append(
                            str(text)
                        )


            if output:

                return "\n".join(
                    output
                )


        structured = result.get(
            "structuredContent"
        )


        if structured is not None:

            try:

                return json.dumps(
                    structured,
                    indent=2,
                    ensure_ascii=False,
                )

            except Exception:

                return str(
                    structured
                )


        try:

            return json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )

        except Exception:

            return str(result)


    try:

        return json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )

    except Exception:

        return str(result)


# ============================================================
# FIND STUDIO
# ============================================================

def find_studio_id(value):

    if isinstance(
        value,
        dict,
    ):

        for key in (
            "studio_id",
            "studioId",
        ):

            found = value.get(
                key
            )


            if (
                isinstance(
                    found,
                    str,
                )
                and found.strip()
            ):

                return found.strip()


        for child in value.values():

            result = find_studio_id(
                child
            )

            if result:
                return result


    elif isinstance(
        value,
        list,
    ):

        for child in value:

            result = find_studio_id(
                child
            )

            if result:
                return result


    return None


# ============================================================
# STUDIO ID
# ============================================================

def get_studio_id(parameters):

    global _cached_studio_id


    supplied = parameters.get(
        "studio_id"
    )


    if supplied:

        _cached_studio_id = str(
            supplied
        )

        return _cached_studio_id


    if _cached_studio_id:

        return _cached_studio_id


    result = _client.call_tool(
        "list_roblox_studios",
        {},
    )


    studio_id = find_studio_id(
        result
    )


    if studio_id:

        _cached_studio_id = studio_id

        return studio_id


    raise RobloxMCPError(
        "I could not find an open Roblox Studio "
        "instance. Make sure Roblox Studio is open "
        "and Studio MCP is enabled."
    )


# ============================================================
# CALL TOOL
# ============================================================

def call_tool(
    tool,
    parameters,
    arguments=None,
):

    if not tool:

        return (
            "Sir, no Roblox Studio MCP "
            "tool was specified."
        )


    args = dict(
        arguments or {}
    )


    # Most current Studio tools need the Studio ID.
    if (
        "studio_id"
        not in args
    ):

        try:

            args["studio_id"] = (
                get_studio_id(
                    parameters
                )
            )

        except RobloxMCPError:

            # Some tools may not require it.
            pass


    result = _client.call_tool(
        tool,
        args,
    )


    return extract_text(
        result
    )


# ============================================================
# MAIN PLUGIN ENTRY POINT
# ============================================================

def run(
    parameters: dict,
    player=None,
    session_memory=None,
) -> str:

    """
    JARVIS plugin entry point.

    IMPORTANT:
    The plugin loader requires this exact callable.
    """

    parameters = (
        parameters
        if isinstance(
            parameters,
            dict,
        )
        else {}
    )


    action = str(
        parameters.get(
            "action",
            "",
        )
    ).strip().lower()


    try:

        # ----------------------------------------------------
        # CONNECT
        # ----------------------------------------------------

        if action in (
            "connect",
            "connect_roblox",
            "connect_to_roblox",
        ):

            _client.start()

            result = _client.call_tool(
                "list_roblox_studios",
                {},
            )


            studio_id = find_studio_id(
                result
            )


            if studio_id:

                global _cached_studio_id

                _cached_studio_id = (
                    studio_id
                )


                result_text = (
                    "Connected to Roblox Studio. "
                    f"Studio ID: {studio_id}"
                )

            else:

                result_text = (
                    "Roblox Studio MCP is running, "
                    "but I could not find an open "
                    "Roblox Studio instance."
                )


        # ----------------------------------------------------
        # LIST STUDIOS
        # ----------------------------------------------------

        elif action in (
            "list_studios",
            "studios",
            "find_studios",
        ):

            result = _client.call_tool(
                "list_roblox_studios",
                {},
            )


            result_text = extract_text(
                result
            )


        # ----------------------------------------------------
        # LIST TOOLS
        # ----------------------------------------------------

        elif action in (
            "list_tools",
            "tools",
            "available_tools",
        ):

            result = _client.list_tools()

            tools = result.get(
                "tools",
                [],
            )


            names = []


            for tool in tools:

                if isinstance(
                    tool,
                    dict,
                ):

                    name = tool.get(
                        "name"
                    )

                    if name:

                        names.append(
                            str(name)
                        )


            if names:

                result_text = (
                    "Roblox Studio MCP tools:\n"
                    + "\n".join(
                        f"- {name}"
                        for name in names
                    )
                )

            else:

                result_text = (
                    "Roblox Studio MCP returned "
                    "no tools."
                )


        # ----------------------------------------------------
        # SCRIPT READ
        # ----------------------------------------------------

        elif action in (
            "script_read",
            "read_script",
        ):

            path = parameters.get(
                "path",
                "",
            )


            if not path:

                return (
                    "Sir, please provide "
                    "the script path."
                )


            result_text = call_tool(

                "script_read",

                parameters,

                {
                    "path": path,
                },

            )


        # ----------------------------------------------------
        # SCRIPT SEARCH
        # ----------------------------------------------------

        elif action in (
            "script_search",
            "search_scripts",
        ):

            query = parameters.get(
                "query",
                "",
            )


            if not query:

                return (
                    "Sir, please provide "
                    "a search query."
                )


            result_text = call_tool(

                "script_search",

                parameters,

                {
                    "query": query,
                },

            )


        # ----------------------------------------------------
        # SCRIPT GREP
        # ----------------------------------------------------

        elif action in (
            "script_grep",
            "grep",
            "search_code",
        ):

            pattern = parameters.get(
                "pattern",
                "",
            )


            if not pattern:

                return (
                    "Sir, please provide "
                    "a search pattern."
                )


            result_text = call_tool(

                "script_grep",

                parameters,

                {
                    "pattern": pattern,
                },

            )


        # ----------------------------------------------------
        # MULTI EDIT
        # ----------------------------------------------------

        elif action in (
            "multi_edit",
            "edit_script",
        ):

            path = parameters.get(
                "path",
                "",
            )


            edits = parameters.get(
                "edits",
                [],
            )


            if not path:

                return (
                    "Sir, please provide "
                    "the script path."
                )


            if not isinstance(
                edits,
                list,
            ):

                return (
                    "Sir, edits must be "
                    "an array."
                )


            result_text = call_tool(

                "multi_edit",

                parameters,

                {
                    "path": path,

                    "edits": edits,

                    "datamodel_type": (
                        parameters.get(
                            "datamodel_type",
                            "Edit",
                        )
                    ),
                },

            )


        # ----------------------------------------------------
        # EXECUTE LUAU
        # ----------------------------------------------------

        elif action in (
            "execute_luau",
            "run_luau",
            "execute",
        ):

            code = parameters.get(
                "code",
                "",
            )


            if not code:

                return (
                    "Sir, please provide "
                    "the Luau code."
                )


            result_text = call_tool(

                "execute_luau",

                parameters,

                {
                    "code": code,

                    "datamodel_type": (
                        parameters.get(
                            "datamodel_type",
                            "Edit",
                        )
                    ),
                },

            )


        # ----------------------------------------------------
        # STUDIO STATE
        # ----------------------------------------------------

        elif action in (
            "get_studio_state",
            "studio_state",
        ):

            result_text = call_tool(

                "get_studio_state",

                parameters,

                {},

            )


        # ----------------------------------------------------
        # PLAY MODE
        # ----------------------------------------------------

        elif action in (
            "start_stop_play",
            "play",
            "stop_play",
        ):

            playing = parameters.get(
                "playing"
            )


            args = {}


            if playing is not None:

                args["playing"] = (
                    bool(playing)
                )


            result_text = call_tool(

                "start_stop_play",

                parameters,

                args,

            )


        # ----------------------------------------------------
        # CONSOLE
        # ----------------------------------------------------

        elif action in (
            "get_console_output",
            "console",
        ):

            result_text = call_tool(

                "get_console_output",

                parameters,

                {},

            )


        # ----------------------------------------------------
        # SCREEN CAPTURE
        # ----------------------------------------------------

        elif action in (
            "screen_capture",
            "screenshot",
        ):

            result_text = call_tool(

                "screen_capture",

                parameters,

                {},

            )


        # ----------------------------------------------------
        # RAW TOOL
        # ----------------------------------------------------

        elif action in (
            "call_tool",
            "raw",
            "mcp",
            "tool",
        ):

            tool = parameters.get(
                "tool",
                "",
            )


            if not tool:

                return (
                    "Sir, please specify "
                    "the Roblox Studio MCP tool."
                )


            arguments = parameters.get(
                "arguments",
                {},
            )


            if not isinstance(
                arguments,
                dict,
            ):

                return (
                    "Sir, tool arguments "
                    "must be an object."
                )


            result_text = call_tool(

                tool,

                parameters,

                arguments,

            )


        # ----------------------------------------------------
        # DISCONNECT
        # ----------------------------------------------------

        elif action in (
            "disconnect",
            "disconnect_roblox",
        ):

            _client.close()

            result_text = (
                "Roblox Studio MCP disconnected."
            )


        # ----------------------------------------------------
        # UNKNOWN
        # ----------------------------------------------------

        else:

            result_text = (
                "Unknown Roblox Studio MCP action. "
                "Available actions include connect, "
                "list_studios, list_tools, "
                "script_read, script_search, "
                "script_grep, multi_edit, "
                "execute_luau, get_studio_state, "
                "start_stop_play, "
                "get_console_output, "
                "screen_capture, call_tool, "
                "and disconnect."
            )


    except RobloxMCPError as e:

        result_text = (
            "Sir, Roblox Studio MCP error: "
            f"{e}"
        )


    except Exception as e:

        result_text = (
            "Sir, Roblox Studio MCP failed: "
            f"{e}"
        )


    # --------------------------------------------------------
    # Log to JARVIS
    # --------------------------------------------------------

    if len(result_text) > 6000:

        result_text = (
            result_text[:6000]
            + "\n[Output truncated.]"
        )


    if player:

        try:

            player.write_log(
                "JARVIS: "
                + result_text[:1000]
            )

        except Exception:

            pass


    return result_text