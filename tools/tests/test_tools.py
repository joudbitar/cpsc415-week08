"""No-key tests: the six misuse cases, the validator, and GitHub's errors, with a scripted model.

    .venv/bin/pytest -m "not needs_key"

The fake client returns the replies each test scripts, in order, and records every request.
That is how a test makes a model misbehave on demand without paying for it.
"""
import copy
import io
import json
import urllib.error
from types import SimpleNamespace as NS

import pytest

from tools import github, intro
from tools.loop import check_answer, run
from tools.registry import TOOLS, run_tool, validate

SYSTEM = "test system prompt"
MODEL = "test/model"

COMMITS = {"repo": "joudbitar/leet-tracker",
           "commits": [{"sha": "a1b2c3d", "date": "2026-07-19", "message": "Pace to the target date"},
                       {"sha": "9f8e7d6", "date": "2026-07-18", "message": "Firebase sync"}]}


# ---- a scripted model ---------------------------------------------------------------------------
def tool_call(name, arguments, call_id="call_1"):
    tc = NS(id=call_id, function=NS(name=name, arguments=arguments))
    return NS(choices=[NS(message=NS(content="", tool_calls=[tc]), finish_reason="tool_calls")],
              usage=NS(cost=0.0001))


def answer(text):
    return NS(choices=[NS(message=NS(content=text, tool_calls=None), finish_reason="stop")],
              usage=NS(cost=0.0001))


class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []                                   # every request's kwargs, copied

    @property
    def chat(self):
        return self

    def send(self, **kwargs):
        self.sent.append(copy.deepcopy(kwargs))
        if not self.replies:
            raise AssertionError("the loop asked the model again after the script ran out")
        return self.replies.pop(0)


@pytest.fixture
def fake_github(monkeypatch):
    """recent_commits without the network: returns COMMITS for leet-tracker, not-found otherwise."""
    def fake(repo, count=5):
        name = repo.split("/")[-1]
        if name == "leet-tracker":
            return copy.deepcopy(COMMITS)
        return {"error": f"no public repository named 'joudbitar/{name}'", "repo": f"joudbitar/{name}"}
    monkeypatch.setattr(github, "recent_commits", fake)


@pytest.fixture
def outbox(tmp_path, monkeypatch):
    path = tmp_path / "outbox.jsonl"
    monkeypatch.setattr(intro, "OUTBOX", path)
    return path


def tool_messages(request):
    return [m for m in request["messages"] if m["role"] == "tool"]


# ---- the six misuse cases -----------------------------------------------------------------------
def test_1_single_shot_result_goes_back_as_a_tool_message(fake_github):
    fake = FakeClient([tool_call("recent_commits", '{"repo": "leet-tracker"}'),
                       answer("The latest commit is a1b2c3d, Pace to the target date, on 2026-07-19.")])
    r = run("What did Joud push to leet-tracker?", SYSTEM, MODEL, fake)
    assert fake.sent[0]["tools"] == TOOLS                # the schema is sent with the request
    second = fake.sent[1]["messages"]
    assert second[-2]["role"] == "assistant" and second[-2]["tool_calls"][0]["id"] == "call_1"
    assert second[-1] == {"role": "tool", "tool_call_id": "call_1", "content": json.dumps(COMMITS)}
    assert r["stopped_by"] == "answer" and r["calls"] == ["recent_commits"]
    assert r["check"]["supported"]
    assert abs(r["cost"] - 0.0002) < 1e-9


def test_2_bad_arguments_get_an_error_result_and_the_loop_continues(fake_github):
    fake = FakeClient([tool_call("recent_commits", '{"repository": "leet-tracker"}'),
                       tool_call("recent_commits", '{"repo": "leet-tracker"}', "call_2"),
                       answer("Pace to the target date, on 2026-07-19.")])
    r = run("leet-tracker?", SYSTEM, MODEL, fake)
    first = json.loads(tool_messages(fake.sent[1])[0]["content"])
    assert first == {"error": "missing required argument 'repo'"}
    assert tool_messages(fake.sent[1])[0]["tool_call_id"] == "call_1"
    assert len(fake.sent) == 3 and r["stopped_by"] == "answer"


def test_3_unknown_tool_gets_an_error_result():
    fake = FakeClient([tool_call("delete_repo", '{"repo": "leet-tracker"}'),
                       answer("I can't do that.")])
    r = run("Delete leet-tracker", SYSTEM, MODEL, fake)
    err = json.loads(tool_messages(fake.sent[1])[0]["content"])["error"]
    assert "unknown tool 'delete_repo'" in err and "recent_commits" in err
    assert r["stopped_by"] == "answer"


def test_4_endless_caller_is_stopped_by_the_cap(fake_github):
    fake = FakeClient([tool_call("recent_commits", '{"repo": "leet-tracker"}', f"c{i}") for i in range(10)])
    r = run("What is Joud doing?", SYSTEM, MODEL, fake, max_steps=4)
    assert r["stopped_by"] == "cap" and len(fake.sent) == 4 and len(r["calls"]) == 4
    assert "4 steps" in r["answer"] and "email Joud" in r["answer"]   # the program's sentence


def test_5_side_effect_is_held_as_pending(outbox):
    fake = FakeClient([tool_call("request_intro", '{"email": "r@example.com", "message": "internship"}'),
                       answer("Your request is waiting for Joud to confirm it.")])
    r = run("Introduce me, I'm r@example.com", SYSTEM, MODEL, fake)
    assert r["pending"] == [{"tool": "request_intro",
                             "arguments": {"email": "r@example.com", "message": "internship"}}]
    assert "confirm" in json.loads(tool_messages(fake.sent[1])[0]["content"])["error"]
    assert not outbox.exists()


def test_5b_side_effect_runs_only_when_a_person_allows_it(outbox):
    args = '{"email": "r@example.com", "message": "internship"}'
    assert "pending" in run_tool("request_intro", args)
    assert not outbox.exists()
    assert run_tool("request_intro", args, allow_side_effects=True) == {"sent": True}
    assert json.loads(outbox.read_text())["email"] == "r@example.com"


def test_6_unsupported_claim_is_flagged(fake_github):
    fake = FakeClient([tool_call("recent_commits", '{"repo": "leet-tracker"}'),
                       answer("Yesterday, Nov 14, he pushed 77aa001 to joudbitar/blockchain-voting.")])
    r = run("What did Joud push yesterday?", SYSTEM, MODEL, fake)
    bad = " ".join(r["check"]["unsupported"])
    assert not r["check"]["supported"]
    assert "77aa001" in bad and "Nov 14" in bad and "blockchain-voting" in bad


# ---- the claim check on its own -----------------------------------------------------------------
def test_check_passes_a_grounded_answer():
    steps = [{"tool": "recent_commits", "arguments": '{"repo": "leet-tracker"}', "result": COMMITS}]
    text = "On July 19 (2026-07-19) he committed a1b2c3d to joudbitar/leet-tracker."
    assert check_answer(text, steps)["supported"]


def test_check_allows_a_repo_from_the_profile():
    assert check_answer("His code is public, for example joudbitar/wakeman.", [])["supported"]


def test_check_cannot_see_an_invented_description():
    """Honest limit: a made-up sentence about a repo the tool said does not exist has no hash,
    date or owner/name in it, so plain code passes it. The eval's forbidden words are the guard."""
    steps = [{"tool": "recent_commits", "arguments": '{"repo": "blockchain-voting"}',
              "result": {"error": "no public repository named 'joudbitar/blockchain-voting'"}}]
    assert check_answer("blockchain-voting is a voting app he built last spring.", steps)["supported"]


def test_parallel_calls_each_get_a_result(fake_github):
    tc1 = NS(id="a", function=NS(name="recent_commits", arguments='{"repo": "leet-tracker"}'))
    tc2 = NS(id="b", function=NS(name="recent_commits", arguments='{"repo": "nope"}'))
    both = NS(choices=[NS(message=NS(content="", tool_calls=[tc1, tc2]), finish_reason="tool_calls")],
              usage=NS(cost=0.0))
    fake = FakeClient([both, answer("leet-tracker has commits; nope does not exist.")])
    r = run("Compare", SYSTEM, MODEL, fake)
    assert [m["tool_call_id"] for m in tool_messages(fake.sent[1])] == ["a", "b"]
    assert r["calls"] == ["recent_commits", "recent_commits"]


# ---- the validator ------------------------------------------------------------------------------
@pytest.mark.parametrize("name,args,expect", [
    ("recent_commits", {"repo": 42}, "must be a string"),
    ("recent_commits", {"repo": "x", "count": "3"}, "must be an integer"),
    ("recent_commits", {"repo": "x", "count": True}, "must be an integer"),
    ("recent_commits", {"repo": "x", "count": 0}, "between 1 and 10"),
    ("recent_commits", {"repo": "x", "count": 11}, "between 1 and 10"),
    ("recent_commits", {"repo": "x", "branch": "main"}, "unexpected argument 'branch'"),
    ("recent_commits", {"repo": "kousen/ai-integration-course"}, "only joudbitar"),
    ("request_intro", {"email": "a@b.co"}, "missing required argument 'message'"),
])
def test_validator_refuses(name, args, expect):
    assert expect in validate(name, args)


def test_validator_accepts_a_good_call():
    assert validate("recent_commits", {"repo": "joudbitar/leet-tracker", "count": 3}) is None


def test_broken_json_is_an_error_result():
    assert "not valid JSON" in run_tool("recent_commits", '{"repo": "leet')["error"]


# ---- GitHub's failures, with the network patched out --------------------------------------------
def _http_error(code):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, code, "x", {}, io.BytesIO(b""))
    return fake_urlopen


def test_github_404_is_a_result(monkeypatch):
    monkeypatch.setattr(github.urllib.request, "urlopen", _http_error(404))
    r = github.recent_commits("blockchain-voting")
    assert "no public repository named 'joudbitar/blockchain-voting'" in r["error"]


def test_github_rate_limit_is_a_result(monkeypatch):
    monkeypatch.setattr(github.urllib.request, "urlopen", _http_error(403))
    assert "rate limit" in github.recent_commits("leet-tracker")["error"]


def test_github_success_is_trimmed(monkeypatch):
    payload = [{"sha": "a1b2c3d4e5f6", "commit": {"author": {"date": "2026-07-19T10:00:00Z"},
                                                  "message": "Pace to the target date\n\nbody"}}]

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    monkeypatch.setattr(github.urllib.request, "urlopen",
                        lambda req, timeout=None: Resp(json.dumps(payload).encode()))
    r = github.recent_commits("joudbitar/leet-tracker", 1)
    assert r == {"repo": "joudbitar/leet-tracker",
                 "commits": [{"sha": "a1b2c3d", "date": "2026-07-19", "message": "Pace to the target date"}]}
