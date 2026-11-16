"""check_fit: which resume entries show Joud has done the work a visitor describes.

Matching is plain code. Each entry in resume.json has tags; a tag matches when it appears in
the task as a whole word. The program decides what counts as evidence; the model only writes
the sentence.
"""
import json
import pathlib
import re

RESUME = json.loads((pathlib.Path(__file__).resolve().parents[1] / "resume.json").read_text())

SCHEMA = {"type": "function", "function": {
    "name": "check_fit",
    "description": "When a visitor describes a job, a role, or work they need done, call this with the "
                   "task in their words. It returns the resume entries that show Joud has done that kind "
                   "of work, and the technologies in the task his resume does not show. Say he can do "
                   "only the parts it matched, and name the entry.",
    "parameters": {"type": "object",
                   "properties": {"task": {"type": "string", "minLength": 3, "maxLength": 300,
                                           "description": "The job or task, in the visitor's words"}},
                   "required": ["task"]}}}


def _has(term: str, text: str) -> bool:
    """Whole-word match that treats + and # as part of a word, so 'c' does not match 'c++'."""
    return re.search(rf"(?<![\w+#]){re.escape(term)}(?![\w+#])", text) is not None


def check_fit(task: str) -> dict:
    low = task.lower()
    matches, all_tags = [], set()
    for e in RESUME["entries"]:
        all_tags |= set(e["tags"])
        hit = [t for t in e["tags"] if _has(t, low)]
        if hit:
            evidence = [b for b in e["bullets"] if any(_has(t, b.lower()) for t in hit)] or e["bullets"][:1]
            matches.append({"entry": e["entry"], "role": e["role"], "dates": e["dates"],
                            "matched": hit, "evidence": evidence})
    matches.sort(key=lambda m: -len(m["matched"]))
    missing = [t for t in RESUME["not_on_resume_vocabulary"] if t not in all_tags and _has(t, low)]
    missing.sort(key=low.find)
    result = {"task": task, "matches": matches, "not_on_resume": missing}
    if not matches:
        result["note"] = "Nothing on the resume matches this task."
    return result
