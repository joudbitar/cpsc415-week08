"""No-key tests for the chatbot's answer function: the tool goes through it, the trace comes back."""
import json

import chatbot
from tools.registry import TOOLS
from tools.tests.test_tools import COMMITS, FakeClient, answer, fake_github, tool_call  # noqa: F401


def test_answer_sends_the_schema_and_returns_the_trace(fake_github):  # noqa: F811
    fake = FakeClient([tool_call("recent_commits", '{"repo": "leet-tracker"}'),
                       answer("His latest leet-tracker commit is a1b2c3d, on 2026-07-19.")])
    r = chatbot.answer("What has Joud pushed to leet-tracker?", client=fake)
    assert fake.sent[0]["tools"] == TOOLS
    assert "leet-tracker" in fake.sent[0]["messages"][0]["content"]        # the profile is in the prompt
    assert r["steps"][0]["tool"] == "recent_commits" and r["steps"][0]["result"] == COMMITS
    assert r["check"]["supported"] and json.loads(fake.sent[1]["messages"][-1]["content"]) == COMMITS


def test_empty_or_long_question_makes_no_call():
    fake = FakeClient([])
    assert chatbot.answer("   ", client=fake)["stopped_by"] == "rejected"
    assert chatbot.answer("x" * 501, client=fake)["stopped_by"] == "rejected"
    assert fake.sent == []
