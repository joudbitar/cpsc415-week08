"""recent_commits: the latest commits of one of Joud's public GitHub repositories.

GitHub's REST API, no token (60 requests an hour per address; GITHUB_TOKEN raises it).
Everything that can go wrong comes back as a result the model can read, never an exception.

    .venv/bin/python -m tools.github leet-tracker
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

OWNER = "joudbitar"

SCHEMA = {"type": "function", "function": {
    "name": "recent_commits",
    "description": "The most recent commits in one of Joud's public GitHub repositories. Call this "
                   "before saying anything about what he has worked on lately, and use only the "
                   "commits it returns.",
    "parameters": {"type": "object",
                   "properties": {"repo": {"type": "string",
                                           "description": "The repository name, for example leet-tracker, "
                                                          "or joudbitar/leet-tracker"},
                                  "count": {"type": "integer", "description": "How many commits, 1 to 10",
                                            "minimum": 1, "maximum": 10}},
                   "required": ["repo"]}}}


def full_name(repo: str) -> str:
    return repo if "/" in repo else f"{OWNER}/{repo}"


def recent_commits(repo: str, count: int = 5) -> dict:
    repo = full_name(repo.strip())
    if not re.fullmatch(rf"{OWNER}/[\w.-]+", repo):
        return {"error": f"repo must be a repository name like leet-tracker, got {repo!r}"}
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/commits?per_page={count}",
                                 headers={"Accept": "application/vnd.github+json",
                                          "User-Agent": "cpsc415-week08"})
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"error": f"no public repository named {repo!r}", "repo": repo}
        if e.code == 403:
            return {"error": "GitHub rate limit reached; say you cannot check right now"}
        return {"error": f"GitHub answered {e.code}"}
    except (urllib.error.URLError, TimeoutError) as e:
        return {"error": f"could not reach GitHub: {e}"}
    return {"repo": repo, "commits": [{"sha": c["sha"][:7], "date": c["commit"]["author"]["date"][:10],
                                      "message": c["commit"]["message"].splitlines()[0][:100]}
                                     for c in data[:count]]}


if __name__ == "__main__":
    print(json.dumps(recent_commits(sys.argv[1] if len(sys.argv) > 1 else "leet-tracker"), indent=1))
