"""The profile chatbot's answer function. Every path calls answer(): the typed CLI today, the
site's api/chat.py and the voice route when they exist.

    .venv/bin/python chatbot.py "What has Joud pushed to leet-tracker lately?"
    .venv/bin/python chatbot.py "What is TrayPal?" --model xiaomi/mimo-v2.6-flash
"""
import argparse
import json
import os
import pathlib

from tools.loop import run

ROOT = pathlib.Path(__file__).resolve().parent
PROFILE = json.loads((ROOT / "profile.json").read_text())
DEFAULT_MODEL = os.environ.get("CHAT_MODEL", "minimax/minimax-m3")
MAX_STEPS = 4

SYSTEM = f"""You are the assistant on Joud Bitar's portfolio site. Answer only from the profile below
and from what the tools return. If neither covers the question, say the profile does not list it.
Never guess. Shipped work and things he is learning are different; say which.
For anything about what he has worked on lately, call recent_commits for one of the repositories
in "repos", and mention only commits, dates and repositories the tool returned. If the tool says a
repository does not exist, say so and describe nothing about it. If a visitor asks to be
If a visitor describes a job, a role or work they need done, call check_fit with the task. Say
Joud can do it only for the parts it matched, naming the resume entry for each, and say plainly
that his resume does not show anything listed in not_on_resume. If nothing matched, say the
resume does not show that kind of work, and do not guess. If a visitor asks to be
introduced, call request_intro; its result says whether anything was sent, and you must not say
it was sent unless it was. Answer in two or three plain sentences. Do not name the tools.

PROFILE:
{json.dumps(PROFILE, indent=1)}"""


def answer(question: str, model: str = DEFAULT_MODEL, client=None) -> dict:
    """Returns {answer, steps, stopped_by, cost, calls, pending, check}; steps is the trace."""
    q = (question or "").strip()
    if not q or len(q) > 500:
        return {"answer": "Please ask a question about Joud's work, in 500 characters or fewer.",
                "steps": [], "stopped_by": "rejected", "cost": 0.0, "calls": [], "pending": [],
                "check": {"supported": True, "unsupported": []}}
    if client is None:
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")
        from openrouter import OpenRouter
        client = OpenRouter(api_key=key)
    return run(q, SYSTEM, model, client, max_steps=MAX_STEPS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    a = ap.parse_args()
    r = answer(a.question, a.model)
    for s in r["steps"]:
        if "tool" in s:
            print(f"step {s['step']}  {s['tool']}({s['arguments']})  ->  {json.dumps(s['result'])[:160]}  [{s['seconds']}s]")
        else:
            print(f"step {s['step']}  answer  [{s['seconds']}s, finish={s['finish']}]")
    print(f"\n{r['answer']}\n")
    print(f"stopped_by={r['stopped_by']}  calls={r['calls']}  cost=${r['cost']:.6f}  "
          f"check={'ok' if r['check']['supported'] else r['check']['unsupported']}  [{a.model}]")
    if r["pending"]:
        print("pending (not run):", json.dumps(r["pending"]))


if __name__ == "__main__":
    main()
