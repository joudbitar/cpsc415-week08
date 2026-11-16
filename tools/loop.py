"""The tool loop and the claim check."""
CAP_ANSWER = ""


def run(question, system, model, client, max_steps=4, allow_side_effects=False):
    raise NotImplementedError


def check_answer(answer, steps, profile=None):
    raise NotImplementedError
