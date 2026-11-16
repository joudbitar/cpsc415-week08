"""request_intro: a side effect, never run on the model's request alone."""


def request_intro(email: str, message: str) -> dict:
    raise NotImplementedError
