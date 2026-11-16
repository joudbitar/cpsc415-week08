# Spec

## Intent
Implements `intent/profile-chatbot.md` (the chatbot, specified in full in `joudbitar/portfolio`'s `spec.md`) and `intent/tools.md` (this week's tool).

## The chatbot, as far as this repository builds it
- `profile.json` holds what the chatbot may say about me: a summary, projects, skills with a shipped project as evidence, things I am learning, a "not yet" list, and the names of my public repositories.
- `chatbot.py` has `answer(question)`, the one function every path calls. Today the only path is the typed one (`python3 chatbot.py "..."`). The site's `api/chat.py` and the Week 7 voice route will call the same function when they exist.
- A question that is empty or longer than 500 characters is rejected with a message and no model call.

## Week 8: one tool

### Component: tools/
- **What it does:** gives the chatbot one live tool, `recent_commits`, and runs the loop in which the model asks for tools and the program decides. It also holds `request_intro`, a side-effect tool that is never run on the model's request.
- **Language:** Python 3.13, same as the chatbot. **Why:** the loop is a dozen lines around a chat call the chatbot already makes, and GitHub's REST API needs only `urllib` from the standard library. Java was the alternative; it would mean a second runtime on Vercel for one function.
- **Model:** `minimax/minimax-m3`, the class model, with reasoning left on. **Comparison:** `xiaomi/mimo-v2.6-flash`, the default in the portfolio spec, with hidden reasoning off (it returns nothing otherwise, from Week 5). Both are in OpenRouter's list of models that support `tools`.
- **Interfaces:** `tools.loop.run(question, system, model, client, max_steps=4)` returns `{answer, steps, stopped_by, cost, calls, pending, check}`. `chatbot.answer(question)` returns the same dictionary with the trace in `steps`.
- **Data:** `resume.json`, my resume without phone, email or GPA, with tags on each entry.
- **Dependencies:** `openrouter` (the SDK used since Week 2, for the chat call with `tools`), `pytest` and `ruff` for development. GitHub is called with `urllib`, no library.

### Behaviors
1. **The schema.** Every chat request carries `tools`, a list of two schemas. `recent_commits`: description "The most recent commits in one of Joud's public GitHub repositories. Call this before saying anything about what he has worked on lately, and use only the commits it returns." Arguments: `repo` (string, required, the repository name, for example `leet-tracker`, or `joudbitar/leet-tracker`), `count` (integer, optional, 1 to 10, default 5). `request_intro`: arguments `email` (string, required) and `message` (string, required).
2. **Arguments are parsed and validated in code.** `arguments` arrives as a JSON string. Code parses it and checks it against the schema: required keys present, no unexpected keys, strings are strings, integers are integers (a boolean is not an integer) and within their minimum and maximum. A repository owned by anyone but `joudbitar` is refused. Any failure goes back to the model as `{"error": "..."}` in a `tool` message with the request's `tool_call_id`, and the loop continues so the model can correct the call.
3. **An unknown tool** gets `{"error": "unknown tool 'x'; the tools are [...]"}` as its result. Nothing runs.
4. **GitHub failures are results.** A repository that does not exist (404) returns `{"error": "no public repository named ...", "repo": ...}`. The rate limit (403) and a network failure return an error that says what happened. None of them raise.
5. **The step cap.** The loop makes at most four chat calls. If the model is still asking for tools after the fourth, the loop stops and the answer is the program's sentence: "I couldn't finish answering that in 4 steps. Ask me something narrower, or email Joud." The model's text is discarded.
6. **Side effects wait for a person.** `request_intro` is in `SIDE_EFFECTS`. When the model asks for it, the program does not run it. The result tells the model the request is waiting for Joud's confirmation, and the call is listed in `pending`. It runs only when the caller passes `allow_side_effects=True`, which nothing on the site does.
7. **The claim check.** After the answer, plain code reads it. A commit hash in the answer must match a hash a tool returned. A date in the answer (`2026-11-14`, `Nov 14`, `November 14`) must match a commit date a tool returned or appear in the profile. A `joudbitar/<name>` repository in the answer must be in the profile or in a tool call. Anything else is listed in `check.unsupported`. The check does not change the answer; it is recorded in the trace and in the eval.
8. **Cost per question.** Every tool request costs one more chat call to send the result back. The loop adds up `usage.cost` from every call, and the eval records the cost, steps and seconds of each question.

### Addendum, 2026-11-16: `check_fit`
9. **The schema.** `check_fit`: description "When a visitor describes a job, a role, or work they need done, call this with the task in their words. It returns the resume entries that show Joud has done that kind of work, and the technologies in the task his resume does not show. Say he can do only the parts it matched, and name the entry." Arguments: `task` (string, required, 3 to 300 characters).
10. **Matching is plain code.** `resume.json` gives every entry a list of tags. A tag matches when it appears in the task as a whole word, ignoring case. The result is `{"task", "matches": [{"entry", "role", "dates", "evidence"}], "not_on_resume": [...]}`, where `evidence` is the bullets of that entry that contain a matched tag (or the first bullet if none does), and `not_on_resume` is every term from a fixed list of common technologies that appears in the task and in no entry's tags. With no match, `matches` is empty and the result says so.
11. **The answer names its evidence.** The system prompt tells the model to say Joud can do the work only for matched parts, to name the entry for each, and to name everything in `not_on_resume` as not shown on his resume.
12. **What code cannot check.** Whether the answer's "yes, he can" is a fair reading of the matched bullets is a judgement. The claim check does not attempt it. The eval's must-say and must-not-say words are the guard, and `CHECKS.md` records the limit.

### Failure handling
- Missing key: `answer()` raises before any call, naming `OPENROUTER_API_KEY`.
- Model error: the exception reaches the caller; the site's function will show "the assistant is unavailable, email me", as the portfolio spec says.

### Out of scope
Private repositories, writing to GitHub, a confirmation screen for intros, the voice path (see the intent).
