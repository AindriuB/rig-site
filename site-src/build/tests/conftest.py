import subprocess
import sys
from pathlib import Path

import pytest

BUILD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BUILD))

FIXTURES = Path(__file__).parent / "fixtures" / "core"
ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": "/dev/null"}


def pytest_configure(config):
    config.addinivalue_line("markers", "docker: test needs Docker")


def _git(repo: Path, *args: str) -> None:
    import os
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                   env={**os.environ, **ENV})


def _write(repo: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        p = repo / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)


def build_fixture_rig(path: Path) -> Path:
    """A rig-like repo: v0.1.0, v0.3.0, v0.3.1, v0.4.0-rc.1 and a `main` with planning pages."""
    path.mkdir(parents=True)
    _git(path, "init", "-q", "-b", "main")

    def commit(msg: str, tag: str | None = None) -> None:
        _git(path, "add", "-A")
        _git(path, "commit", "-q", "-m", msg)
        if tag:
            _git(path, "tag", tag)

    _write(path, {
        "README.md": "# rig 0.1\n\nSee [design](docs/design.md) and [licence](LICENSE).\n",
        "docs/design.md": "# Design\n\nBack to the [readme](../README.md).\n",
    })
    commit("0.1", "v0.1.0")
    _write(path, {
        "README.md": "# rig\n\nRead [workflows](docs/workflows.md), [design](docs/design.md#goals),\n"
                     "[phase 2](docs/phase-2.md) and the [licence](LICENSE).\n",
        "docs/design.md": "# Design\n\n## Goals\n\nSee [phase 2](phase-2.md#scope).\n",
        "docs/workflows.md": "# The `workflow` file\n\nBody.\n",
        "docs/phase-2.md": "# Phase 2\n\n## Scope\n",
        "LICENSE": "MIT\n",
    })
    commit("0.3.0", "v0.3.0")
    _write(path, {"docs/release.md": "# Release *notes*\n\nPatch.\n"})
    commit("0.3.1", "v0.3.1")
    _write(path, {"docs/zeta.md": "# Zeta\n"})
    commit("rc", "v0.4.0-rc.1")
    _write(path, {
        "docs/plan/PLAN.md": "# Plan\n",
        "docs/plan/tasks/one.md": "# One\n",
        "docs/sub/deep.md": "# Deep\n",
        "docs/alpha.md": "# Alpha\n\nSee [plan](plan/PLAN.md) and [deep](sub/deep.md).\n",
    })
    commit("main")
    return path


@pytest.fixture
def make_rig_repo(tmp_path):
    """Return a builder: `make_rig_repo()` creates a fresh fixture rig repo."""
    count = [0]

    def make() -> Path:
        count[0] += 1
        return build_fixture_rig(tmp_path / f"rig{count[0]}")
    return make


@pytest.fixture(scope="session")
def core_fixtures() -> Path:
    return FIXTURES
