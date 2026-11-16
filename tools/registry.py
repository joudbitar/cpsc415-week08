"""The schemas the model sees, and the code that decides whether to run a call.

The model never runs anything. It writes a request; run_tool parses it, validates it against
the schema in plain code, refuses what it must, and returns every problem as a result.
"""
import json

from tools import github, intro

TOOLS = [github.SCHEMA, intro.SCHEMA]
SIDE_EFFECTS = {"request_intro"}          # never run on the model's request alone
MODULES = {"recent_commits": github, "request_intro": intro}


def validate(name: str, args) -> str | None:
    """Return an error message, or None if the call is well formed."""
    schema = next((t["function"]["parameters"] for t in TOOLS if t["function"]["name"] == name), None)
    if schema is None:
        return f"unknown tool {name!r}; the tools are {sorted(MODULES)}"
    if not isinstance(args, dict):
        return "arguments must be a JSON object"
    for req in schema.get("required", []):
        if req not in args:
            return f"missing required argument {req!r}"
    for key, val in args.items():
        spec = schema["properties"].get(key)
        if spec is None:
            return f"unexpected argument {key!r}"
        if spec["type"] == "string" and not isinstance(val, str):
            return f"argument {key!r} must be a string, got {type(val).__name__}"
        if spec["type"] == "integer":
            if not isinstance(val, int) or isinstance(val, bool):
                return f"argument {key!r} must be an integer, got {type(val).__name__}"
            if not spec.get("minimum", val) <= val <= spec.get("maximum", val):
                return f"argument {key!r} must be between {spec['minimum']} and {spec['maximum']}"
    if name == "recent_commits" and "/" in args["repo"]:
        owner = args["repo"].split("/")[0]
        if owner != github.OWNER:
            return f"only joudbitar's repositories can be read, not {owner!r}'s"
    return None


def run_tool(name: str, arguments: str | dict, allow_side_effects: bool = False) -> dict:
    """Never raises on a bad request: the error goes back to the model as the tool's result."""
    if isinstance(arguments, str):
        try:
            args = json.loads(arguments or "{}")
        except json.JSONDecodeError as e:
            return {"error": f"arguments were not valid JSON: {e.msg}"}
    else:
        args = arguments
    problem = validate(name, args)
    if problem:
        return {"error": problem}
    if name in SIDE_EFFECTS and not allow_side_effects:
        return {"error": f"{name} is waiting for Joud's confirmation; nothing has been sent. "
                         "Tell the visitor that.",
                "pending": {"tool": name, "arguments": args}}
    return getattr(MODULES[name], name)(**args)
