"""The schemas the model sees and the code that decides whether to run a call."""
TOOLS: list = []
SIDE_EFFECTS: set = set()


def validate(name, args):
    raise NotImplementedError


def run_tool(name, arguments, allow_side_effects=False):
    raise NotImplementedError
