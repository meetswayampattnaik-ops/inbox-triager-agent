"""Runs the full agent loop with a FAKE model, so no API key or internet is needed."""
import json
from types import SimpleNamespace as NS

from inbox_triager import agent
from inbox_triager.config import Settings
from inbox_triager.mailbox import DemoMailbox


def _tc(i, name, args):
    return NS(id=f"call_{i}", function=NS(name=name, arguments=json.dumps(args)))


def _resp(content=None, tool_calls=None):
    return NS(choices=[NS(message=NS(content=content, tool_calls=tool_calls))])


class FakeClient:
    def __init__(self, script):
        self.script = list(script)
        self.chat = NS(completions=NS(create=lambda **kw: self.script.pop(0)))


def test_full_loop_with_fake_model(monkeypatch):
    script = [
        _resp(tool_calls=[_tc(1, "list_unread_emails", {"limit": 10})]),
        _resp(tool_calls=[_tc(2, "read_email", {"email_id": "1"})]),
        _resp(tool_calls=[_tc(3, "apply_label", {"email_id": "1", "label": "Urgent"}),
                          _tc(4, "flag_urgent", {"email_id": "1", "reason": "Demo at 3pm"})]),
        _resp(tool_calls=[_tc(5, "create_draft_reply", {"email_id": "1", "body": "Yes, I can present. - Me"})]),
        _resp(content="Done: 1 urgent, 1 draft."),
    ]
    monkeypatch.setattr(agent, "_make_client", lambda s: FakeClient(script))
    mb = DemoMailbox("data/sample_emails.json")
    s = Settings(provider="groq", groq_api_key="x")
    out = agent.run_agent(mb, s, verbose=False)
    assert out.startswith("Done")
    assert mb.labels["1"] == ["Urgent"] and "1" in mb.flags and "1" in mb.drafts
