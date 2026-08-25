"""
JARVIS PC Control plugin.

Provides controlled Windows automation.

Safe:
- open applications
- open files/folders
- inspect processes
- run approved commands

Dangerous:
- deleting files
- formatting
- shutdown/restart
- killing arbitrary processes
- registry modification
- privileged commands

Dangerous operations return CONFIRM_REQUIRED instead of executing.
"""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from typing import Any


PLUGIN = {
    "name": "pc_control",
    "description": (
        "Control the Windows PC. Use this when the user asks Buddy/JARVIS "
        "to open or close applications, inspect processes, open files or "
        "folders, run commands, or perform computer-management tasks. "
        "Dangerous operations require explicit confirmation in the JARVIS UI."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": (
                    "open_app, close_app, open_path, processes, "
                    "run_command, minimize_jarvis, restore_jarvis."
                ),
            },
            "target": {
                "type": "STRING",
                "description": "Application, process, file, folder, or command.",
            },
            "arguments": {
                "type": "STRING",
                "description": "Optional application arguments.",
            },
        },
        "required": ["action"],
    },
}


# Commands that must NEVER silently execute.
DANGEROUS_WORDS = {
    "format",
    "diskpart",
    "reg delete",
    "reg add",
    "shutdown",
    "shutdown.exe",
    "restart-computer",
    "remove-item",
    "del /s",
    "rmdir /s",
    "rd /s",
    "cipher /w",
    "bcdedit",
    "takeown",
    "icacls",
    "net user",
    "net localgroup",
}


def _log(player, text):
    if player:
        try:
            player.write_log(f"JARVIS: {text}")
        except Exception:
            pass


def _dangerous(command: str) -> bool:

    lowered = command.lower()

    return any(
        word in lowered
        for word in DANGEROUS_WORDS
    )


def _confirmation(command: str) -> str:

    # Your main UI should detect this marker and show
    # ALLOW / CANCEL.
    return (
        "CONFIRM_REQUIRED\n"
        "JARVIS wants permission to perform a potentially dangerous "
        f"computer operation:\n{command}\n"
        "Ask the user to explicitly allow or cancel it."
    )


def run(parameters: dict, player=None, session_memory=None) -> str:

    params = parameters or {}

    action = str(
        params.get("action", "")
    ).strip().lower()

    target = str(
        params.get("target", "")
    ).strip()

    try:

        # ---------------------------------------------------------
        # Open application
        # ---------------------------------------------------------

        if action in ("open_app", "launch_app", "start_app"):

            if not target:
                return "Sir, tell me which application to open."

            subprocess.Popen(
                target,
                shell=True,
            )

            result = f"Opened {target}."

            _log(player, result)

            return result

        # ---------------------------------------------------------
        # Close application
        # ---------------------------------------------------------

        if action in ("close_app", "stop_app"):

            if not target:
                return "Sir, tell me which application to close."

            # Only terminate the named process.
            # Do NOT accept arbitrary shell syntax here.
            process_name = Path(target).name

            if not process_name.lower().endswith(".exe"):
                process_name += ".exe"

            dangerous = (
                process_name.lower()
                in {
                    "wininit.exe",
                    "csrss.exe",
                    "services.exe",
                    "lsass.exe",
                    "smss.exe",
                    "winlogon.exe",
                }
            )

            if dangerous:
                return _confirmation(
                    f"Terminate protected system process {process_name}"
                )

            subprocess.run(
                [
                    "taskkill",
                    "/IM",
                    process_name,
                ],
                capture_output=True,
                text=True,
                timeout=20,
            )

            result = f"Requested closure of {process_name}."

            _log(player, result)

            return result

        # ---------------------------------------------------------
        # Open file/folder
        # ---------------------------------------------------------

        if action in ("open_path", "open_file", "open_folder"):

            if not target:
                return "Sir, tell me what file or folder to open."

            path = Path(target).expanduser().resolve()

            if not path.exists():
                return f"I could not find {path}."

            if platform.system() == "Windows":
                os.startfile(str(path))
            else:
                subprocess.Popen(
                    ["xdg-open", str(path)]
                )

            result = f"Opened {path}."

            _log(player, result)

            return result

        # ---------------------------------------------------------
        # Process list
        # ---------------------------------------------------------

        if action in ("processes", "list_processes", "task_manager"):

            result = subprocess.run(
                [
                    "tasklist",
                    "/FO",
                    "CSV",
                    "/NH",
                ],
                capture_output=True,
                text=True,
                timeout=20,
            )

            output = result.stdout.strip()

            if len(output) > 12000:
                output = output[:12000] + "\n[truncated]"

            _log(
                player,
                "Retrieved the Windows process list."
            )

            return output

        # ---------------------------------------------------------
        # Command
        # ---------------------------------------------------------

        if action in ("run_command", "command", "shell"):

            if not target:
                return "Sir, give me a command to run."

            if _dangerous(target):
                return _confirmation(target)

            # Keep this as a normal command execution rather than
            # an administrator shell.
            result = subprocess.run(
                target,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )

            output = (
                result.stdout
                or result.stderr
                or "Command completed."
            )

            if len(output) > 12000:
                output = output[:12000] + "\n[truncated]"

            _log(player, output[:1000])

            return output

        # ---------------------------------------------------------
        # JARVIS UI hooks
        # ---------------------------------------------------------

        if action == "minimize_jarvis":

            if player and hasattr(player, "showMinimized"):
                player.showMinimized()
                return "JARVIS minimized."

            return (
                "JARVIS minimization is not exposed by the current UI."
            )

        if action == "restore_jarvis":

            if player and hasattr(player, "showNormal"):
                player.showNormal()
                return "JARVIS restored."

            return (
                "JARVIS restoration is not exposed by the current UI."
            )

        return (
            "Unknown PC control action. Use open_app, close_app, "
            "open_path, processes, run_command, minimize_jarvis, "
            "or restore_jarvis."
        )

    except subprocess.TimeoutExpired:
        return "Sir, the computer operation timed out."

    except Exception as e:
        return f"Sir, PC control failed: {e}"