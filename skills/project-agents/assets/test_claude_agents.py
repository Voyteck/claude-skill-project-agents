"""The project agents keep their pinned models, read-only reviewers, risk list and locator.

Runs `tools/claude/check_agents.py` (copied from the `project-agents` skill) over
`.claude/agents/`, finding each agent by its role through `.claude/agents/roles.json`, so
renaming an agent changes nothing about what is checked (the code locator alone keeps
its name, `Explore`, the built-in agent it replaces). Set `RISK_MARKERS` to 3-6
distinctive entries of the risk list in the simple implementer's file: if that agent stops
naming them, it could implement on a risk path without anyone noticing.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

#: Distinctive strings of the risk list that the simple implementer's file must contain
#: (directories or files, e.g. "src/auth/", "migrations/", ".github/").
RISK_MARKERS = ["<<RISK_MARKER>>"]


def _root() -> Path:
    """Find the repository root: the nearest parent holding `.claude/agents/`.

    Returns:
        The repository root.

    Raises:
        AssertionError: When no parent of this file holds `.claude/agents/`.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / ".claude" / "agents").is_dir():
            return parent
    raise AssertionError("no parent of this test holds `.claude/agents/`")


def _checker(root: Path) -> ModuleType:
    """Load the copied checker as a module.

    Args:
        root: The repository root.

    Returns:
        The `check_agents` module.
    """
    spec = importlib.util.spec_from_file_location(
        "check_agents", root / "tools" / "claude" / "check_agents.py"
    )
    assert spec is not None and spec.loader is not None, "tools/claude/check_agents.py is missing"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_risk_markers_are_real_strings():
    """An unfilled or empty marker list would make the risk-list check pass on nothing."""
    assert RISK_MARKERS, "RISK_MARKERS is empty"
    assert not [m for m in RISK_MARKERS if m.startswith("<<")], "fill RISK_MARKERS"


def test_the_project_agents_hold_their_invariants():
    """Every role's invariant holds on the agent file the role map names."""
    root = _root()
    problems = _checker(root).check(root / ".claude" / "agents", RISK_MARKERS)
    assert not problems, "\n".join(problems)
