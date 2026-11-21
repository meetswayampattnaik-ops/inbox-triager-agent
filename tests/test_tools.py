import json

import pytest

from inbox_triager.mailbox import DemoMailbox
from inbox_triager.tools import run_tool


@pytest.fixture
def mb():
    return DemoMailbox("data/sample_emails.json")


def test_list_and_read(mb):
    out, err = run_tool(mb, "list_unread_emails", {})
    assert not err and len(json.loads(out)) == 8
    out, err = run_tool(mb, "read_email", {"email_id": "1"})
    assert not err and "demo" in json.loads(out)["body"]


def test_label_valid_and_invalid(mb):
    _, err = run_tool(mb, "apply_label", {"email_id": "2", "label": "Newsletter"})
    assert not err and mb.labels["2"] == ["Newsletter"]
    _, err = run_tool(mb, "apply_label", {"email_id": "2", "label": "MadeUp"})
    assert err


def test_unknown_email_returns_error_not_crash(mb):
    out, err = run_tool(mb, "read_email", {"email_id": "999"})
    assert err and "999" in out


def test_flag_and_draft(mb):
    _, err = run_tool(mb, "flag_urgent", {"email_id": "1", "reason": "Client demo today"})
    assert not err and "1" in mb.flags
    _, err = run_tool(mb, "create_draft_reply", {"email_id": "1", "body": "Yes, I can present."})
    assert not err and mb.drafts["1"].startswith("Yes")
    _, err = run_tool(mb, "create_draft_reply", {"email_id": "1", "body": "  "})
    assert err


def test_no_send_capability(mb):
    _, err = run_tool(mb, "send_email", {"email_id": "1", "body": "x"})
    assert err
    assert not hasattr(mb, "send")
