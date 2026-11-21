"""Tool definitions (JSON schemas the model sees) + the dispatcher that runs them."""
from __future__ import annotations

from .config import LABELS
from .mailbox import Mailbox

TOOL_SCHEMAS = [
    {
        "name": "list_unread_emails",
        "description": "List unread emails in the inbox (id, sender, subject, date). Call this first.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "Max emails to return (default 20)"}},
        },
    },
    {
        "name": "read_email",
        "description": "Read the full body of one email by id. Always read before deciding a label.",
        "input_schema": {
            "type": "object",
            "properties": {"email_id": {"type": "string"}},
            "required": ["email_id"],
        },
    },
    {
        "name": "apply_label",
        "description": f"Apply exactly one category label to an email. Allowed labels: {', '.join(LABELS)}.",
        "input_schema": {
            "type": "object",
            "properties": {"email_id": {"type": "string"}, "label": {"type": "string", "enum": LABELS}},
            "required": ["email_id", "label"],
        },
    },
    {
        "name": "flag_urgent",
        "description": "Flag an email as urgent (time-sensitive, from a manager/client, deadlines within ~48h).",
        "input_schema": {
            "type": "object",
            "properties": {"email_id": {"type": "string"}, "reason": {"type": "string", "description": "One short sentence"}},
            "required": ["email_id", "reason"],
        },
    },
    {
        "name": "create_draft_reply",
        "description": "Save a draft reply for the user to review. It is NEVER sent automatically.",
        "input_schema": {
            "type": "object",
            "properties": {"email_id": {"type": "string"}, "body": {"type": "string", "description": "Reply text only, no subject line"}},
            "required": ["email_id", "body"],
        },
    },
]


def run_tool(mailbox: Mailbox, name: str, args: dict) -> tuple[str, bool]:
    """Execute a tool. Returns (result_text, is_error). Errors go back to the model so it can recover."""
    try:
        if name == "list_unread_emails":
            import json
            return json.dumps(mailbox.list_unread(int(args.get("limit", 20)))), False
        if name == "read_email":
            import json
            return json.dumps(mailbox.get_email(args["email_id"])), False
        if name == "apply_label":
            if args["label"] not in LABELS:
                return f"Invalid label '{args['label']}'. Allowed: {LABELS}", True
            return mailbox.add_label(args["email_id"], args["label"]), False
        if name == "flag_urgent":
            return mailbox.flag(args["email_id"], args["reason"]), False
        if name == "create_draft_reply":
            if not args["body"].strip():
                return "Draft body is empty.", True
            return mailbox.save_draft(args["email_id"], args["body"]), False
        return f"Unknown tool '{name}'", True
    except KeyError as e:
        return f"Error: {e}", True
    except Exception as e:  # keep the agent alive on unexpected failures
        return f"Unexpected error in {name}: {e}", True
