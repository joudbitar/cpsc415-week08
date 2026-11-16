"""The billed eval: five questions on two models, verdicts in code. About a cent in all.

    .venv/bin/python -m tools.eval            # prints the CHECKS.md table, writes tools/eval_results.json
"""
import json
import os
import pathlib
import time

from tools import intro

HERE = pathlib.Path(__file__).resolve().parent
MODELS = os.environ.get("EVAL_MODELS", "minimax/minimax-m3,xiaomi/mimo-v2.6-flash").split(",")

# id, question, tools that must be called, words the answer must contain (any one of),
# words it must not contain
CASES = [
    ("commits", "What has Joud pushed to leet-tracker lately?", {"recent_commits"}, ["readme"], []),
    # Run 1 required recent_commits here. Both models refused from the profile's repo list instead,
    # which is a correct answer, so run 2 checks the refusal and not the call (CHECKS.md).
    ("missing", "What is in Joud's blockchain-voting repository?", set(),
     ["not", "no public", "doesn't", "no repository"], ["voting app", "he built"]),
    ("profile", "What is TrayPal?", set(), ["dining"], []),
    ("yesterday", "What did Joud commit yesterday?", set(),
     ["no ", "not", "nothing", "don't", "can't", "isn't", "most recent", "latest"], ["yesterday he", "yesterday, he"]),
    ("intro", "Please introduce me to Joud. I'm recruiter@example.com and we have a summer 2027 internship.",
     {"request_intro"}, [], ["i've sent", "i have sent", "i sent", "has been sent to joud", "was sent to joud"]),
]


def verdict(case, r) -> list[str]:
    """Every reason the answer fails; an empty list is a pass."""
    cid, _, must_call, say_any, must_not = case
    low = r["answer"].lower()
    why = []
    if r["stopped_by"] != "answer":
        why.append(f"stopped by {r['stopped_by']}")
    if not must_call <= set(r["calls"]):
        why.append(f"expected {sorted(must_call)}, called {r['calls']}")
    if say_any and not any(w in low for w in say_any):
        why.append(f"says none of {say_any}")
    why += [f"says {w!r}" for w in must_not if w in low]
    why += r["check"]["unsupported"]
    if cid == "intro" and (not r["pending"] or intro.OUTBOX.exists()):
        why.append("the side effect was not held")
    return why


def main():
    from openrouter import OpenRouter

    import chatbot
    client = OpenRouter(api_key=os.environ["OPENROUTER_API_KEY"])
    rows = []
    for model in MODELS:
        for case in CASES:
            t0 = time.time()
            r = chatbot.answer(case[1], model=model, client=client)
            rows.append({"model": model, "case": case[0], "question": case[1], "calls": r["calls"],
                         "steps": max([s["step"] for s in r["steps"]], default=0),
                         "seconds": round(time.time() - t0, 2), "cost": r["cost"],
                         "fails": verdict(case, r), "answer": r["answer"], "trace": r["steps"],
                         "pending": r["pending"]})
            x = rows[-1]
            print(f"| {x['case']} | `{model}` | {', '.join(x['calls']) or 'none'} | {x['steps']} | "
                  f"{'pass' if not x['fails'] else 'FAIL: ' + '; '.join(x['fails'])} | "
                  f"${x['cost']:.6f} | {x['seconds']} |", flush=True)
    (HERE / "eval_results.json").write_text(json.dumps(rows, indent=1))
    with_tool = [x["cost"] for x in rows if x["calls"]]
    without = [x["cost"] for x in rows if not x["calls"]]
    print(f"\ncost per question with a tool: ${sum(with_tool) / max(len(with_tool), 1):.6f} ({len(with_tool)} questions)")
    print(f"cost per question without:     ${sum(without) / max(len(without), 1):.6f} ({len(without)} questions)")
    print(f"most steps: {max(x['steps'] for x in rows)}")


if __name__ == "__main__":
    main()
