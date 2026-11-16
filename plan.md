# Plan

## Week 8

Implements the "Week 8: one tool" section of `spec.md`.

### Files
- `tools/github.py`: the `recent_commits` schema and function (behaviors 1, 4).
- `tools/intro.py`: the `request_intro` schema and function, which appends to `outbox.jsonl` (behavior 6).
- `tools/registry.py`: `TOOLS`, `SIDE_EFFECTS`, `validate()` and `run_tool()` (behaviors 2, 3, 6).
- `tools/loop.py`: `run()` with the cap, and `check_answer()` (behaviors 5, 7, 8).
- `tools/tests/test_tools.py`: the no-key tests, with a scripted fake client.
- `tools/tests/test_eval.py` and `tools/eval.py`: the billed eval.
- `profile.json` and `chatbot.py`: the answer function that calls `run()`.
- `tools/CHECKS.md`: the eval table, totals, findings, lint.

### Order of work
1. Tests for the six misuse cases and the validator, against stubs that raise `NotImplementedError`. Run them red. Commit.
2. `github.py`, `intro.py`, `registry.py`, `loop.py`. Run green. Commit.
3. `profile.json`, `chatbot.py`, and a no-key test that the answer function sends the schema and returns the trace. Commit.
4. The eval: five questions on both models. Write the table. Commit.
5. Findings and lint in `CHECKS.md`. Tag `week08-submitted`.

### Risks
- MiMo with reasoning on returns an empty answer. The per-model `REASONING` setting turns it off.
- GitHub's limit is 60 requests an hour without a token. The eval makes about 12. A 403 is a result the model reads, so the eval still runs, but the question fails.
- A model that never calls the tool. The description is written as an instruction ("call this before saying anything about what he has worked on lately").
- My public repositories have not had a push since October 26. "What did you push yesterday" has a true answer of nothing, which is what question 4 needs.

### Questions asked about this plan
- *If the model asks for the tool with the wrong argument name, what goes back, and what does the test assert?* `run_tool` returns `{"error": "missing required argument 'repo'"}` (or `unexpected argument 'repository'`, whichever the validator meets first, required keys first). It goes back as a `tool` message with the same `tool_call_id`. The test scripts a bad call, then a good one, then an answer, and asserts the first `tool` message holds that error, that a second call happened, and that the loop stopped by `answer`.
- *What stops a model that asks for the same tool ten times, and what does the visitor see?* The `for` loop runs at most `max_steps` (4) chat calls. The test scripts ten tool requests and asserts exactly four calls were made, `stopped_by == "cap"`, and the answer is the program's sentence with "4 steps" in it.
- *If the model answers about a repository the tool said does not exist, which line notices?* For a made-up commit hash or date, `check_answer` does, because neither came back from a tool. For a sentence like "blockchain-voting is a voting app", nothing in code notices: the repository name was in the tool call, so it passes. That limit is recorded in `CHECKS.md`, and the eval's must-not-say words are the only guard.

### Proof
**No-key tests** (`pytest -m "not needs_key"`, free, under a second). A scripted `FakeClient` returns replies in order and records every request.
1. Single shot: a `recent_commits` call, then an answer. The second request carries the assistant's `tool_calls` and a `tool` message with the right `tool_call_id` and the result. Proves the result is delivered the way the API expects.
2. Bad arguments: wrong argument name, then a correct call. Proves an error is a result and the loop continues.
3. Unknown tool: proves nothing runs and the model reads the list of real tools.
4. Endless caller: ten scripted requests, cap 4. Proves the cap and that the program writes the capped answer.
5. Side effect held: a `request_intro` call. Proves `pending` is filled and `outbox.jsonl` is not written; a second test with `allow_side_effects=True` proves the write happens only then.
6. Unsupported claim: an answer with a hash and a date no tool returned. Proves `check_answer` flags them, and a grounded answer passes.
Plus validator unit tests (wrong type, out of range, a boolean count, another owner, broken JSON) and GitHub errors with `urlopen` patched (404, 403). No network.

**Billed eval** (`python3 -m tools.eval`, skipped without a key, about one cent). Five questions on each model: latest commits of a real repository; a repository I do not have; a profile question that needs no tool; "what did Joud push yesterday"; an introduction request. Each records the tools called, steps, seconds, cost, and a verdict from code: the required tool was called, required words present, forbidden words absent, the claim check passed, and for the intro, nothing in the outbox. Proves the real models use the schema. It does not prove they always will, because each question runs once.

**Approved by:** Joud Bitar, 2026-11-15

## Week 8 addendum: `check_fit`

Implements spec behaviors 9 to 12.

### Files
- `resume.json`: experience, projects, volunteering and skills from my resume, each entry with `tags`.
- `tools/resume.py`: the `check_fit` schema and function.
- `tools/registry.py`: add the schema and the module. `validate()` gains string `minLength` and `maxLength`.
- `chatbot.py`: one paragraph in the system prompt (behavior 11).
- `tools/eval.py`: three more questions.

### Order of work
1. Tests first against a stub that raises `NotImplementedError`: a matching task returns the TradePulse entry with its LangGraph bullet; a task with only unknown technology returns no matches and lists it in `not_on_resume`; a mixed task returns both; matching is whole-word ("go" does not match "good"); a too-short task is an error result; through the loop, the result reaches the model as a `tool` message. Run red. Commit.
2. `tools/resume.py`, the registry change, the prompt. Run green. Commit.
3. The eval with eight questions on both models. Update `CHECKS.md`. Commit.

### Risks
- Keyword tags miss a task phrased in other words ("an app that reads PDFs" matches nothing unless a tag says `pdf`). The test set and the eval show which phrasings work. More tags fix it one phrasing at a time.
- A model that reads one matched tag as "yes to everything". Question 7 asks for Next.js and Kubernetes together to catch it.

### Proof
No-key tests for the six cases in step 1, free. The billed eval adds three questions per model, about a third of a cent: a contract-drafting AI agent (must call `check_fit` and name TradePulse or LangGraph), a Kubernetes-on-AWS job (must call it and say the resume does not show it), and an internship asking for Next.js and Kubernetes (must name a Next.js entry and say Kubernetes is not shown).

**Approved by:** Joud Bitar, 2026-11-16
