"""No-key tests for check_fit: matching is plain code, and the result reaches the model."""
import json

from tools import resume
from tools.loop import run
from tools.registry import TOOLS, run_tool
from tools.tests.test_tools import FakeClient, answer, tool_call


def entries(result):
    return [m["entry"] for m in result["matches"]]


def test_matching_task_returns_the_entry_and_its_bullet():
    r = resume.check_fit("We need an AI agent built with LangGraph that drafts contracts")
    assert entries(r)[0] == "TradePulse (Bitar LLC)"
    assert any("LangGraph copilot" in b for b in r["matches"][0]["evidence"])
    assert r["not_on_resume"] == []


def test_unknown_technology_matches_nothing_and_is_named():
    r = resume.check_fit("Set up Kubernetes on AWS for us")
    assert r["matches"] == [] and r["not_on_resume"] == ["kubernetes", "aws"]


def test_mixed_task_returns_both_halves():
    r = resume.check_fit("A Next.js intern who also knows Kubernetes")
    assert "TradePulse (Bitar LLC)" in entries(r) and "TrayPal" in entries(r)
    assert r["not_on_resume"] == ["kubernetes"]


def test_matching_is_whole_word():
    r = resume.check_fit("I want a good cookie recipe")              # "c" must not match inside a word
    assert r["matches"] == []
    assert "Pascal-variant compiler" not in entries(resume.check_fit("A C++ game engine"))
    assert resume.check_fit("A C++ game engine")["not_on_resume"] == ["c++"]


def test_too_short_task_is_an_error_result():
    assert "at least 3 characters" in run_tool("check_fit", '{"task": "AI"}')["error"]


def test_check_fit_is_in_the_schema_and_reaches_the_model():
    assert "check_fit" in [t["function"]["name"] for t in TOOLS]
    fake = FakeClient([tool_call("check_fit", '{"task": "a Next.js dashboard"}'),
                       answer("Yes, he built TrayPal in Next.js.")])
    r = run("Can Joud build a Next.js dashboard?", "system", "test/model", fake)
    result = json.loads(fake.sent[1]["messages"][-1]["content"])
    assert "TrayPal" in [m["entry"] for m in result["matches"]]
    assert r["calls"] == ["check_fit"] and r["stopped_by"] == "answer"
