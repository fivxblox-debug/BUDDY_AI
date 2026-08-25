"""
JARVIS Conversation Saver Plugin

Saves and loads complete JARVIS conversations locally.
"""

from pathlib import Path
from datetime import datetime


PLUGIN = {
    "name": "conversation_saver",
    "description": (
        "Save and load complete JARVIS conversations. "
        "When saving, always provide the actual conversation text. "
        "Never use the literal placeholder CURRENT_CONVERSATION. "
        "When loading, return the complete conversation contents "
        "so JARVIS can use them as context."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "save or load",
            },
            "conversation": {
                "type": "STRING",
                "description": (
                    "The complete actual conversation text. "
                    "Do not pass CURRENT_CONVERSATION."
                ),
            },
        },
        "required": ["action"],
    },
}


SAVE_DIR = (
    Path.home()
    / "JarvisProjects"
    / "conversations"
)


def _log(player, message):
    if player:
        try:
            player.write_log(f"JARVIS: {message}")
        except Exception:
            pass


def _result(message, player=None):
    _log(player, message)
    return message


def _latest_file():

    if not SAVE_DIR.exists():
        return None

    files = list(
        SAVE_DIR.glob("conversation_*.txt")
    )

    if not files:
        return None

    return max(
        files,
        key=lambda file: file.stat().st_mtime,
    )


def run(
    parameters: dict,
    player=None,
    session_memory=None,
) -> str:

    try:

        parameters = parameters or {}

        action = str(
            parameters.get(
                "action",
                "",
            )
        ).strip().lower()

        SAVE_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        # =====================================================
        # SAVE
        # =====================================================

        if action == "save":

            conversation = parameters.get(
                "conversation"
            )

            if conversation is None:
                return _result(
                    "SAVE FAILED: No conversation was supplied.",
                    player,
                )

            conversation = str(
                conversation
            ).strip()

            # Prevent useless placeholder files.
            if not conversation:
                return _result(
                    "SAVE FAILED: Conversation is empty.",
                    player,
                )

            if conversation.upper() in (
                "CURRENT_CONVERSATION",
                "{{CURRENT_CONVERSATION}}",
                "[CURRENT_CONVERSATION]",
            ):
                return _result(
                    "SAVE FAILED: JARVIS supplied the "
                    "CURRENT_CONVERSATION placeholder instead "
                    "of the actual conversation text. "
                    "The conversation was NOT saved.",
                    player,
                )

            now = datetime.now()

            filename = (
                "conversation_"
                + now.strftime(
                    "%Y-%m-%d_%H-%M-%S"
                )
                + ".txt"
            )

            save_path = SAVE_DIR / filename

            header = (
                "JARVIS Conversation\n"
                "===================\n"
                f"Saved: "
                f"{now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            )

            save_path.write_text(
                header + conversation,
                encoding="utf-8",
            )

            return _result(
                "Conversation saved successfully.\n"
                f"File: {save_path}\n"
                f"Characters: {len(conversation)}",
                player,
            )

        # =====================================================
        # LOAD
        # =====================================================

        if action == "load":

            latest = _latest_file()

            if latest is None:
                return _result(
                    "No saved conversations were found.",
                    player,
                )

            conversation = latest.read_text(
                encoding="utf-8",
                errors="replace",
            )

            if not conversation.strip():
                return _result(
                    "The latest conversation file is empty.",
                    player,
                )

            return _result(
                "LOADED CONVERSATION CONTEXT\n"
                "============================\n"
                f"Source: {latest}\n\n"
                f"{conversation}",
                player,
            )

        # =====================================================
        # UNKNOWN ACTION
        # =====================================================

        return _result(
            f"Unknown conversation action: {action}. "
            "Use save or load.",
            player,
        )

    except Exception as e:

        return _result(
            f"Conversation saver failed: {e}",
            player,
        )