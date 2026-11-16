# Checks

All model runs on 2026-11-15 through OpenRouter, with `python3 -m tools.eval`. Costs are the sum of `usage.cost` over every chat call in a question. Seconds are wall time for the whole question, GitHub included. The raw answers and traces are in `eval_results.json` (run 2) and `eval_results_run1.json` (run 1).

## Red, then green

| Step | Commit | Output |
|---|---|---|
| Tests against stubs that raise `NotImplementedError` | `Tools: misuse-case tests first (red: stubs raise NotImplementedError)` | `22 failed, 2 errors in 0.09s` |
| The registry, the GitHub tool, the intro tool, the loop and the check | `Tools: the loop and its misuse cases, tests first` | `24 passed in 0.04s` |
| The answer function and its two tests | `Tools: one real tool in the chatbot` | `26 passed in 0.05s` |
| Everything, with the key set | after `Tools: five questions on two models` | `36 passed in 50.38s` (26 no-key, 10 billed) |

The red run failed inside each test, on `NotImplementedError` or a missing attribute, after collection. The two errors are the outbox fixture, which patches `intro.OUTBOX` before the stub had it.

## The eval, run 2

The class model is `minimax/minimax-m3` with reasoning on. The comparison is `xiaomi/mimo-v2.6-flash` with hidden reasoning off. Steps counts chat calls.

| Question | Model | Tools called | Steps | Verdict | Cost | Seconds |
|---|---|---|---|---|---|---|
| commits: "What has Joud pushed to leet-tracker lately?" | `minimax/minimax-m3` | recent_commits | 2 | pass | $0.000434 | 2.58 |
| missing: "What is in Joud's blockchain-voting repository?" | `minimax/minimax-m3` | recent_commits ×3 | 2 | pass | $0.001362 | 6.53 |
| profile: "What is TrayPal?" | `minimax/minimax-m3` | none | 1 | pass | $0.000247 | 0.66 |
| yesterday: "What did Joud commit yesterday?" | `minimax/minimax-m3` | recent_commits ×3 | 2 | pass | $0.000900 | 4.81 |
| intro: "Please introduce me to Joud. I'm recruiter@example.com ..." | `minimax/minimax-m3` | request_intro (held) | 2 | pass | $0.000451 | 1.13 |
| commits | `xiaomi/mimo-v2.6-flash` | recent_commits | 2 | pass | $0.000150 | 1.11 |
| missing | `xiaomi/mimo-v2.6-flash` | none | 1 | pass | $0.000016 | 1.15 |
| profile | `xiaomi/mimo-v2.6-flash` | none | 1 | pass | $0.000290 | 0.39 |
| yesterday | `xiaomi/mimo-v2.6-flash` | recent_commits | 2 | pass | $0.000119 | 3.96 |
| intro | `xiaomi/mimo-v2.6-flash` | request_intro (held) | 2 | pass | $0.000067 | 4.49 |

A pass means the loop ended with the model's answer, the required tools were called, the answer has at least one required word and none of the forbidden ones, `check_answer` found nothing unsupported, and for the intro the call is in `pending` and `outbox.jsonl` does not exist.

Totals for run 2:

- Cost per question with a tool call: $0.000498 (7 questions).
- Cost per question without one: $0.000184 (3 questions).
- Most steps any question took: 2. No question came near the cap of 4.

Run 2 cost $0.0040 in all. Run 1 cost $0.0049. MiMo's $0.000016 on the missing question is far below its other runs, and its profile question cost more than its one-tool question. I think that is OpenRouter's prompt caching on the repeated system prompt, but I have not checked the usage fields, so the MiMo numbers are rough.

## Run 1, and what I changed

Run 1 had the same questions and failed 4 of 10.

The missing question failed on both models because neither called the tool. Each answered "The profile does not list a blockchain-voting repository", because the system prompt holds the list of my public repositories and the name is not on it. That answer is correct, and it is cheaper than a 404. The eval was wrong to require the call, so run 2 checks the refusal and the forbidden words, and no longer requires `recent_commits`. In run 2 M3 called the tool anyway, got the 404, then fetched `casebooks` and `shelly` for no reason, which made it the most expensive question in the table.

The intro question failed on both models on the forbidden phrase "has been sent". Both answers said "nothing has been sent". My word check could not see the "nothing" in front of the phrase. Run 2 forbids "I've sent", "I sent" and "has been sent to Joud" instead.

Both changes are in `tools/eval.py`, with a comment on the first.

## Misuse cases

| Case | Test | Seen from a real model? |
|---|---|---|
| Single shot: the result goes back as a `tool` message with the request's `tool_call_id` | `test_1_single_shot_result_goes_back_as_a_tool_message` | Yes, every commits question: one call, one result, one answer. |
| Bad arguments (`repository` instead of `repo`) get an error result and the loop continues | `test_2_bad_arguments_get_an_error_result_and_the_loop_continues`, plus `test_validator_refuses` (8 cases) and `test_broken_json_is_an_error_result` | No. Every real call in both runs had valid arguments. MiMo asked for `count: 10` once, which is inside the limit. |
| Unknown tool gets an error result that names the real tools | `test_3_unknown_tool_gets_an_error_result` | No. |
| Endless caller is stopped at 4 calls with the program's sentence | `test_4_endless_caller_is_stopped_by_the_cap` | No. The most was 2 steps. M3 asked for three repositories in one reply on the yesterday and missing questions, which is parallel calls in one step, covered by `test_parallel_calls_each_get_a_result`. |
| Side effect held: `request_intro` goes to `pending` and the outbox is not written | `test_5_side_effect_is_held_as_pending`, `test_5b_side_effect_runs_only_when_a_person_allows_it` | Yes, both models in both runs. Trace (M3, run 2): `request_intro({"email":"recruiter@example.com","message":"Summer 2027 internship opportunity"})` returned `{"error": "request_intro is waiting for Joud's confirmation; nothing has been sent. ...", "pending": {...}}`, and no outbox file exists. |
| Unsupported claim: a hash, a date and a repository no tool returned are flagged | `test_6_unsupported_claim_is_flagged` | No. In both runs `check_answer` found nothing in any answer. The yesterday answers named dates (2026-10-15, 2026-09-28, 2026-07-19), and each one was a commit date a tool had returned. |

## What the check cannot catch

`check_answer` only reads hashes, dates and `joudbitar/<name>` strings. Three things got past it in these runs or would.

M3's intro answer in run 1 said "I've passed along your interest to Joud" and "I'll let you know once he responds". Nothing was passed along, since the request sits in `pending`, and the chatbot has no way to tell the visitor anything later. The words "sent" and "nothing has been sent" are both in that answer, so a word list cannot judge it. A person reading the intro answers, or a second model asked "does this answer promise anything the trace does not show?", would catch it.

A made-up description of a repository the tool said does not exist ("blockchain-voting is a voting app he built last spring") has no hash, date or owner/name in it, so the check passes it. `test_check_cannot_see_an_invented_description` pins that limit down. The eval's forbidden words are the only guard, and they only cover the phrasings I thought of.

Month-only dates pass unchecked. In run 1 M3 said `cut-coach` and `leet-tracker` "last saw activity in July 2026". That was true, but the check never read it.

Both models also said they do not know today's date, so "yesterday" has no answer. The system prompt should carry the date. I have left the spec as it is and noted this as the next change.

## The cost of a tool

On M3, the class model, a profile question with no tool cost $0.000247. One tool call cost $0.000434, 1.8 times as much, because the result needs a second chat call that resends the whole conversation. Three parallel calls cost $0.000900 to $0.001362. On run 2 as a whole, a question with a tool averaged $0.000498 and one without averaged $0.000184, about 2.7 times.

For the hosting decision, the portfolio spec estimated $0.0003 a question on MiMo with no tools, so $0.34 for a thousand questions. If every question used the tool on M3 at the run 2 average, a thousand would cost about $0.50, and about $1.40 if each one fanned out the way M3 did on the missing question. That is still under two dollars for the semester. The real limit is GitHub's 60 unauthenticated requests an hour, which three parallel calls per question would use up in 20 questions. The site will need a `GITHUB_TOKEN` in Vercel's secret store before November 30.

## Lint

`ruff check .` found two problems, both FURB167 in `tools/loop.py`: `re.I` should be `re.IGNORECASE`, on `MONTH_DATE` and `REPO`. `ruff check . --fix` changed both. It now reports "All checks passed!".
