"""request_intro: a visitor asks to be introduced. It writes to an outbox, so it is a side effect,
and the registry never runs it on the model's request alone."""
import json
import pathlib

OUTBOX = pathlib.Path(__file__).resolve().parents[1] / "outbox.jsonl"

SCHEMA = {"type": "function", "function": {
    "name": "request_intro",
    "description": "Ask Joud to get in touch with a visitor. Only when the visitor explicitly asks "
                   "to be introduced and gives an email address. Joud confirms before anything is sent.",
    "parameters": {"type": "object",
                   "properties": {"email": {"type": "string", "description": "The visitor's email address"},
                                  "message": {"type": "string", "description": "What the visitor wants"}},
                   "required": ["email", "message"]}}}


def request_intro(email: str, message: str) -> dict:
    with open(OUTBOX, "a") as f:
        f.write(json.dumps({"email": email, "message": message}) + "\n")
    return {"sent": True}
