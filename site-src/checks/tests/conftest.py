import os
import subprocess
import sys
from pathlib import Path

import pytest

CHECKS = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def run_site():
    def run(name, tree=None, unset=False):
        env = {k: v for k, v in os.environ.items() if k != "RIG_SITE_TREE"}
        if not unset:
            env["RIG_SITE_TREE"] = str(tree or FIXTURES / "site" / name)
        return subprocess.run(
            [sys.executable, str(CHECKS / "check_site.py")],
            env=env, capture_output=True, text=True,
        )
    return run


@pytest.fixture
def run_actions():
    def run(name):
        return subprocess.run(
            [sys.executable, str(CHECKS / "check_actions_pinned.py")],
            cwd=FIXTURES / "workflows" / name, capture_output=True, text=True,
        )
    return run
