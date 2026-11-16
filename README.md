# cpsc415-week08

The Week 8 lab for CPSC 415. My portfolio chatbot gets one real tool, `recent_commits`, which reads the latest commits of one of my public GitHub repositories. The chatbot's intent and spec live in my private portfolio repository. Its answer function and the tool are here, public, until they move to the site.

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install openrouter pytest ruff
.venv/bin/pytest -m "not needs_key"                                     # 26 tests, no key, under a second
export OPENROUTER_API_KEY=...
.venv/bin/python chatbot.py "What has Joud pushed to leet-tracker lately?"
.venv/bin/python -m tools.eval                                          # five questions, two models, about half a cent
```

## Where things are

`chatbot.py` has the answer function every path calls. `tools/registry.py` has the schemas and the code that validates and runs (or refuses) every call. `tools/loop.py` has the loop with its four-step cap and the claim check. `tools/CHECKS.md` has the eval, the misuse cases, and what the check misses. The intent, spec and plan are in `intent/tools.md`, `spec.md` and `plan.md`.
