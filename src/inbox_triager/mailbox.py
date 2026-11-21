"""Mailbox backends.

Both backends expose the same 5 methods so the agent never cares which one it uses:
  list_unread, get_email, add_label, flag, save_draft

SAFETY: there is intentionally NO send method. The agent can only create drafts.
"""
from __future__ import annotations

import imaplib
import json
import time
from abc import ABC, abstractmethod
from email import message_from_bytes, policy
from email.message import EmailMessage
from pathlib import Path


class Mailbox(ABC):
    @abstractmethod
    def list_unread(self, limit: int = 20) -> list[dict]: ...

    @abstractmethod
    def get_email(self, email_id: str) -> dict: ...

    @abstractmethod
    def add_label(self, email_id: str, label: str) -> str: ...

    @abstractmethod
    def flag(self, email_id: str, reason: str) -> str: ...

    @abstractmethod
    def save_draft(self, email_id: str, body: str) -> str: ...


class DemoMailbox(Mailbox):
    """In-memory mailbox loaded from a JSON file. Great for demos and tests."""

    def __init__(self, path: str = "data/sample_emails.json"):
        self.emails = {e["id"]: e for e in json.loads(Path(path).read_text())}
        self.labels: dict[str, list[str]] = {}
        self.flags: dict[str, str] = {}
        self.drafts: dict[str, str] = {}

    def _get(self, email_id: str) -> dict:
        if email_id not in self.emails:
            raise KeyError(f"No email with id '{email_id}'")
        return self.emails[email_id]

    def list_unread(self, limit: int = 20) -> list[dict]:
        out = []
        for e in list(self.emails.values())[:limit]:
            out.append({"id": e["id"], "from": e["from"], "subject": e["subject"], "date": e["date"]})
        return out

    def get_email(self, email_id: str) -> dict:
        return dict(self._get(email_id))

    def add_label(self, email_id: str, label: str) -> str:
        self._get(email_id)
        self.labels.setdefault(email_id, [])
        if label not in self.labels[email_id]:
            self.labels[email_id].append(label)
        return f"Label '{label}' applied to email {email_id}"

    def flag(self, email_id: str, reason: str) -> str:
        self._get(email_id)
        self.flags[email_id] = reason
        return f"Email {email_id} flagged as urgent: {reason}"

    def save_draft(self, email_id: str, body: str) -> str:
        self._get(email_id)
        self.drafts[email_id] = body
        return f"Draft reply saved for email {email_id} (NOT sent)"

    def report(self) -> list[dict]:
        rows = []
        for eid, e in self.emails.items():
            rows.append({
                "id": eid, "from": e["from"], "subject": e["subject"],
                "labels": self.labels.get(eid, []),
                "urgent_reason": self.flags.get(eid),
                "draft": self.drafts.get(eid),
            })
        return rows


class ImapMailbox(Mailbox):
    """Real mailbox over IMAP (tested design for Gmail with an App Password)."""

    def __init__(self, host: str, user: str, password: str, is_gmail: bool, drafts_folder: str):
        self.user = user
        self.is_gmail = is_gmail
        self.drafts_folder = drafts_folder
        self.conn = imaplib.IMAP4_SSL(host)
        self.conn.login(user, password)
        self.conn.select("INBOX")
        self._last: dict[str, dict] = {}
        self.actions: list[dict] = []

    @staticmethod
    def _parse(raw: bytes) -> dict:
        msg = message_from_bytes(raw, policy=policy.default)
        body_part = msg.get_body(preferencelist=("plain", "html"))
        body = body_part.get_content() if body_part else ""
        return {
            "from": str(msg.get("From", "")),
            "reply_to": str(msg.get("Reply-To", "") or msg.get("From", "")),
            "subject": str(msg.get("Subject", "")),
            "date": str(msg.get("Date", "")),
            "message_id": str(msg.get("Message-ID", "")),
            "body": body[:3000],  # cap size to control token usage
        }

    def _fetch(self, uid: str) -> dict:
        status, data = self.conn.uid("fetch", uid, "(BODY.PEEK[])")  # PEEK keeps email unread
        if status != "OK" or not data or not data[0]:
            raise KeyError(f"Could not fetch email uid {uid}")
        parsed = self._parse(data[0][1])
        parsed["id"] = uid
        self._last[uid] = parsed
        return parsed

    def list_unread(self, limit: int = 20) -> list[dict]:
        self.conn.select("INBOX")
        _, data = self.conn.uid("search", None, "UNSEEN")
        uids = data[0].split()[-limit:]
        out = []
        for u in reversed(uids):
            m = self._fetch(u.decode())
            out.append({k: m[k] for k in ("id", "from", "subject", "date")})
        return out

    def get_email(self, email_id: str) -> dict:
        return self._last.get(email_id) or self._fetch(email_id)

    def add_label(self, email_id: str, label: str) -> str:
        if not self.is_gmail:
            self.actions.append({"id": email_id, "label": label, "note": "non-Gmail: not applied"})
            return f"Labeling is Gmail-only; recorded '{label}' for {email_id} locally"
        self.conn.uid("store", email_id, "+X-GM-LABELS", f'("{label}")')
        self.actions.append({"id": email_id, "label": label})
        return f"Label '{label}' applied to email {email_id}"

    def flag(self, email_id: str, reason: str) -> str:
        self.conn.uid("store", email_id, "+FLAGS", r"(\Flagged)")
        self.actions.append({"id": email_id, "flagged": reason})
        return f"Email {email_id} starred/flagged as urgent: {reason}"

    def save_draft(self, email_id: str, body: str) -> str:
        orig = self.get_email(email_id)
        draft = EmailMessage()
        draft["From"] = self.user
        draft["To"] = orig["reply_to"]
        subject = orig["subject"]
        draft["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
        if orig.get("message_id"):
            draft["In-Reply-To"] = orig["message_id"]
            draft["References"] = orig["message_id"]
        draft.set_content(body)
        self.conn.append(self.drafts_folder, r"\Draft", imaplib.Time2Internaldate(time.time()), draft.as_bytes())
        self.actions.append({"id": email_id, "draft": body})
        return f"Draft reply saved in '{self.drafts_folder}' for email {email_id} (NOT sent)"

    def report(self) -> list[dict]:
        return self.actions

    def close(self) -> None:
        try:
            self.conn.logout()
        except Exception:
            pass
