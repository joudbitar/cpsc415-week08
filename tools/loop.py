"""The tool loop: the model asks, the program decides, the model answers from what came back.

One run is one question. Each trip through the loop is one billed chat call, so a tool request
costs a second call to deliver the result. The loop stops when the model answers without asking
for a tool, or after max_steps calls; then the answer is the program's sentence.
"""
import json
import pathlib
import re
import time

from tools.registry import TOOLS, run_tool

ROOT = pathlib.Path(__file__).resolve().parents[1]
# MiMo thinks for the whole budget and returns nothing unless hidden reasoning is off (Week 5).
REASONING = {"xiaomi/mimo-v2.6-flash": {"enabled": False}}
CAP_ANSWER = "I couldn't finish answering that in {n} steps. Ask me something narrower, or email Joud."


def _call(client, model, messages):
    kwargs = {"model": model, "messages": messages, "tools": TOOLS, "max_tokens": 1500}
    if model in REASONING:
        kwargs["reasoning"] = REASONING[model]
    return client.chat.send(**kwargs)


def run(question, system, model, client, max_steps=4, allow_side_effects=False) -> dict:
    """Returns {answer, steps, stopped_by, cost, calls, pending, check}. steps is the trace."""
    messages = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    steps, cost, pending = [], 0.0, []
    for step in range(1, max_steps + 1):
        t0 = time.time()
        c = _call(client, model, messages)
        cost += getattr(c.usage, "cost", None) or 0.0
        msg = c.choices[0].message
        calls = msg.tool_calls or []
        if not calls:
            text = (msg.content or "").strip()
            steps.append({"step": step, "answer": text, "seconds": round(time.time() - t0, 2),
                          "finish": c.choices[0].finish_reason})
            return _result(text, steps, "answer", cost, pending)
        messages.append({"role": "assistant", "content": msg.content or "",
                         "tool_calls": [{"id": tc.id, "type": "function",
                                         "function": {"name": tc.function.name,
                                                      "arguments": tc.function.arguments}}
                                        for tc in calls]})
        for tc in calls:
            result = run_tool(tc.function.name, tc.function.arguments, allow_side_effects)
            if "pending" in result:
                pending.append(result["pending"])
            steps.append({"step": step, "tool": tc.function.name, "arguments": tc.function.arguments,
                          "result": result, "seconds": round(time.time() - t0, 2)})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})
    return _result(CAP_ANSWER.format(n=max_steps), steps, "cap", cost, pending)


def _result(answer, steps, stopped_by, cost, pending):
    return {"answer": answer, "steps": steps, "stopped_by": stopped_by, "cost": round(cost, 6),
            "calls": [s["tool"] for s in steps if "tool" in s], "pending": pending,
            "check": check_answer(answer, steps)}


MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun",
                                      "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
MONTH_DATE = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? (\d{1,2})\b", re.IGNORECASE)
ISO_DATE = re.compile(r"\b\d{4}-(\d{2})-(\d{2})\b")
HASH = re.compile(r"\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b")
REPO = re.compile(r"\bjoudbitar/([\w.-]+)", re.IGNORECASE)


def _load_profile():
    return json.loads((ROOT / "profile.json").read_text())


def check_answer(answer: str, steps: list, profile: dict | None = None) -> dict:
    """Plain code looking for claims no tool and no profile entry supports: a commit hash, a date,
    or a joudbitar/<name> repository. It does not read meaning, so an invented sentence with none
    of those in it passes; CHECKS.md says so."""
    profile = profile or _load_profile()
    shas, dates, repos = set(), set(), {r.lower() for r in profile.get("repos", [])}
    for s in steps:
        if "tool" not in s:
            continue
        try:
            args = json.loads(s.get("arguments") or "{}")
        except (json.JSONDecodeError, TypeError):
            args = {}
        if isinstance(args, dict) and isinstance(args.get("repo"), str):
            repos.add(args["repo"].split("/")[-1].lower())
        for c in s["result"].get("commits", []):
            shas.add(c["sha"].lower())
            dates.add(c["date"][5:])                              # "MM-DD"
    profile_text = json.dumps(profile).lower()
    dates |= {f"{int(m):02d}-{int(d):02d}" for m, d in ISO_DATE.findall(profile_text)}
    unsupported = []
    for h in HASH.findall(answer.lower()):
        if not any(h.startswith(s) or s.startswith(h) for s in shas):
            unsupported.append(f"commit {h} is not in any tool result")
    for m in MONTH_DATE.finditer(answer):
        if f"{MONTHS[m.group(1).lower()[:3]]:02d}-{int(m.group(2)):02d}" not in dates:
            unsupported.append(f"date {m.group(0)!r} is not in any tool result")
    for mm, dd in ISO_DATE.findall(answer):
        if f"{mm}-{dd}" not in dates:
            unsupported.append(f"date {mm}-{dd} is not in any tool result")
    for name in REPO.findall(answer):
        name = name.rstrip(".").lower()
        if name not in repos:
            unsupported.append(f"repository joudbitar/{name} is not in the profile or any tool call")
    return {"supported": not unsupported, "unsupported": unsupported}
