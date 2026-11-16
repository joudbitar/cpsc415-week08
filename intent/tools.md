# Intent: one tool for the profile chatbot

## Goal
The profile chatbot (`intent/profile-chatbot.md`) can only repeat what I wrote in `profile.json`. A visitor who asks what I am working on this month gets an answer that is as old as the file. The chatbot gets one tool, `recent_commits(repo)`, that reads the latest commits of one of my public GitHub repositories, so it can answer that question with live data.

## Who it is for
The same visitors as the chatbot: recruiters, founders and possible clients. The question this tool answers is "is he still building, and what?"

## How it works
The model never runs anything. It asks for the tool by name with JSON arguments. Our code parses the arguments, checks them against the schema, runs the function or refuses, and sends every result back to the model as a message, errors included. The loop stops after four steps. If it stops there, the visitor reads a sentence written by the program, not by the model.

The tool only reads repositories owned by `joudbitar`. A request for anybody else's repository is refused in code.

A second tool, `request_intro(email, message)`, exists to test the permission rule. It would write the visitor's request to an outbox. It has a side effect, so the program records it as pending and does not run it unless a person confirms. Nothing on the site confirms it yet.

## Constraints
- Python, the OpenRouter SDK, and GitHub's public REST API with no token (60 requests an hour).
- The chatbot must not claim anything the tool did not return. A commit, a date or a repository in the answer has to come from a tool result or the profile, and code checks the ones it can.
- Every misuse case gets a test that runs without a key, written before the code.
- Due Monday, November 16, 2026, 1:30 PM.

## Not in scope
- Writing to GitHub, or reading private repositories.
- A confirmation screen for `request_intro`. The pending request is shown in the trace and goes no further.
- The voice path. The Week 7 voice route was not built, so the typed path is the only one that goes through the answer function for now.

## Success looks like
- Asked what I pushed lately to one of my repositories, it lists real commits from the tool and nothing else.
- Asked about a repository I do not have, it says GitHub has no such repository.
- Asked about TrayPal, it answers from the profile and does not need the tool.
- Asked to introduce a visitor, it says the request is waiting for me and does not say it was sent.
- Five questions on two models, with the cost of each, recorded in `tools/CHECKS.md`.

## Open questions
- Whether a visitor ever asks about commits, or whether this tool mostly costs a second call for nothing. The eval measures the cost; only the site's logs can answer the first half.

**Approved by:** Joud Bitar, 2026-11-15

## Addendum, 2026-11-16: a second tool, `check_fit(task)`

I rarely push to public repositories. Most of my work is client code or private, so `recent_commits` mostly finds nothing new. The question visitors bring is different: "we need someone to build X, can Joud do it?"

`check_fit(task)` takes the job or task the visitor described and returns the entries on my resume that match it: the role or project, the dates, and the bullet that shows the work. It also names any technology in the task that my resume does not show. The chatbot can then say "yes, he has done this, at TradePulse" for the parts that matched, and must say plainly which parts the resume does not cover. It never says I can do something with no matching entry behind it.

The resume lives in `resume.json`, copied from my resume without my phone number, email or GPA, because this repository is public. Matching is plain code (keyword tags on each entry), so the program decides what counts as evidence and the model only writes the sentence.

Not in scope: judging seniority, quoting prices or availability, and anything the resume does not say.

**Approved by:** 
