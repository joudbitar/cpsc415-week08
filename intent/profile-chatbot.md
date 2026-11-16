# Intent: profile chatbot

## Goal
A chatbot on joudbitar.com that answers one question from a visitor: should we work together? It answers only from a profile I wrote. When the profile does not cover something, it says so and does not make an answer up.

## Who it is for
Recruiters, founders and possible clients who land on joudbitar.com. Today they read the project pages and guess the rest, or email me.

## Constraints
- It lives on the existing site: static HTML on Vercel, repository `joudbitar/portfolio`.
- The chatbot is a Python function on Vercel. The key lives in Vercel's secret store, never in the repository.
- Answers come only from `profile.json`. Shipped work and things I am still learning are kept apart, and the chatbot must say which is which.
- Default model `xiaomi/mimo-v2.6-flash`, compared against `anthropic/claude-sonnet-5.5` on my own adversarial test set.
- Final due Monday, December 14, 2026, 1:30 PM. Comprehension Defense December 17 to 23.

## Not in scope
- Answering general questions that are not about me or my work.
- Remembering visitors between visits.
- Booking calls or sending email for the visitor.
- A spoken interface. That comes with the Week 7 lab.
- Redesigning the rest of the site.

## Success looks like
- Asked about TradePulse, TrayPal or the doctor sites, it answers from the profile and names what I shipped.
- Asked about a skill that is not in the profile, it says the profile does not list it. Asked about one in "not yet", it says I have not prioritized it and why.
- Asked a leading question with a false premise ("since Joud worked at Google..."), it corrects the premise.
- At least ten adversarial questions are run and the results recorded, failures included.

## Open questions
- Which projects go in the profile beyond the three on the site today.
- The rest of the "not yet" inventory. It has one entry so far.
- The repository is private. The sheet asks for a public one.

**Approved by:** Joud Bitar, 2026-10-05
