"""The billed eval as tests. Skipped without OPENROUTER_API_KEY. About a cent.

    .venv/bin/pytest -m needs_key -s
"""
import os

import pytest

from tools.eval import CASES, MODELS, verdict

KEY = os.environ.get("OPENROUTER_API_KEY")
pytestmark = [pytest.mark.needs_key,
              pytest.mark.skipif(not KEY, reason="OPENROUTER_API_KEY not set: the billed eval is skipped")]


@pytest.fixture(scope="module")
def client():
    from openrouter import OpenRouter
    return OpenRouter(api_key=KEY)


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_case(client, model, case):
    import chatbot
    r = chatbot.answer(case[1], model=model, client=client)
    print(f"\n[{model}] {case[0]}: calls={r['calls']} cost=${r['cost']:.6f}\n  {r['answer']}")
    assert verdict(case, r) == []
