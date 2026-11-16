# Project conventions

## What this repository is
The Week 8 lab for CPSC 415: the profile chatbot from `joudbitar/portfolio` (intent in `intent/profile-chatbot.md`), with one real tool. The portfolio repository is private and the chatbot was not built there yet, so the answer function and the tool live here, public, until they move to the site before November 30. See [`spec.md`](spec.md).

## Commands
```
.venv/bin/pytest -m "not needs_key"                 # no-key tests
.venv/bin/pytest                                    # all tests (eval needs OPENROUTER_API_KEY)
.venv/bin/python chatbot.py "What has Joud pushed to leet-tracker lately?"
.venv/bin/python -m tools.eval                      # the billed eval, about a cent
.venv/bin/ruff check .
```

## Working rules
- Write or update `intent/` and `spec.md` before code. Get `plan.md` approved before implementing.
- Never commit `.env` or `.claude/settings.local.json`. No API key in the repository.
- Week 8: the chatbot's tools live in tools/. Stages assigned: intent, spec,
  plan, tests. Commit to main.
- The model never runs anything. Every tool request is validated and run (or
  refused) by our code; every problem goes back to the model as a result, not
  an exception. Tools with side effects are never run on the model's request
  alone. The loop has a step cap.
- No model call inside a test that runs without a key; the billed eval is
  separate and skipped when OPENROUTER_API_KEY is unset.

## Common mistakes
Add to this list as they happen.
- A forbidden phrase in the eval ("has been sent") matched an answer that said "nothing has been sent". Forbidden phrases name the claim with its subject ("I sent", "has been sent to Joud").
