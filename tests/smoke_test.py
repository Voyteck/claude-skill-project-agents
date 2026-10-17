"""End-to-end check of the templates and the guard, with no project around them.

Fills every `<<MARKER>>` in `assets/agents/` the way the skill tells Claude to (names
from a role map, the deep architect assembled from its head plus the architect's body),
then runs `scripts/check_agents.py` on the result and expects `OK`. It also expects the
guard to FAIL on the raw templates and on a filled set that has lost a property the
guard exists for, so a guard that stopped checking cannot pass here. A role map written
before the `explore` role existed must still pass.

    python3 tests/smoke_test.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills" / "project-agents"
TEMPLATES = SKILL / "assets" / "agents"
CHECKER = SKILL / "scripts" / "check_agents.py"
MARKER = re.compile(r"<<([A-Z_]+)>>")
RISK_MARKERS = ["src/auth/", "migrations/", ".github/"]

ROLES = {
    "implementer": "implementer",
    "implementer-simple": "implementer-simple",
    "reviewer-security": "reviewer-security",
    "reviewer-mechanical": "reviewer-mechanical",
    "reviewer-deploy": "reviewer-deploy",
    "architect": "architect",
    "architect-deep": "architect-deep",
    "ci-watcher": "ci-watcher",
    "explore": "Explore",
    "architecture_model": "fable",
}
VALUES = {
    "ARCHITECT_MODEL": "fable",
    "RISK_PATHS": "\n".join(f"- `{path}`" for path in RISK_MARKERS),
    "DEFAULT_BRANCH": "main",
    "FULL_CHECK": "make check",
    "TARGETED_CHECKS": "pytest tests/<area>",
}


def _fill(text: str) -> str:
    """Replaces every marker with a role name or a sample project fact."""

    def value(match: re.Match[str]) -> str:
        key = match.group(1)
        if key.startswith("NAME_"):
            return ROLES[key[len("NAME_") :].lower().replace("_", "-")]
        return VALUES.get(key, f"example {key.lower()}")

    return MARKER.sub(value, text)


def _body(text: str) -> str:
    """Returns a markdown file's text after its frontmatter."""
    return text.split("---\n", 2)[2]


def _write_filled(target: Path) -> None:
    """Writes the filled agent set and its role map into `target`, each file under its name."""
    for template in TEMPLATES.glob("*.md"):
        if template.name.endswith(".head.md"):
            continue
        (target / f"{ROLES[template.stem]}.md").write_text(_fill(template.read_text()))
    head = _fill((TEMPLATES / "architect-deep.head.md").read_text())
    (target / "architect-deep.md").write_text(head + _body((target / "architect.md").read_text()))
    (target / "roles.json").write_text(json.dumps(ROLES))


def _check(agents: Path) -> subprocess.CompletedProcess[str]:
    """Runs the guard the way the skill's README tells a project to."""
    command = [
        sys.executable,
        str(CHECKER),
        str(agents),
        "--roles",
        str(agents / "roles.json"),
    ]
    for marker in RISK_MARKERS:
        command += ["--risk-marker", marker]
    return subprocess.run(command, capture_output=True, text=True, check=False)


def main() -> int:
    """Runs the three cases.

    Returns:
        0 when every case behaves as expected, 1 otherwise.
    """
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        agents = Path(tmp)
        _write_filled(agents)
        filled = _check(agents)
        if filled.returncode != 0 or filled.stdout.strip() != "OK":
            failures.append(f"filled templates should pass:\n{filled.stdout}")

        # A reviewer that can write is exactly what the guard exists to refuse.
        reviewer = agents / "reviewer-security.md"
        original = reviewer.read_text()
        reviewer.write_text(
            re.sub(r"^tools: .*$", "tools: Read, Edit, Write", original, flags=re.M)
        )
        if _check(agents).returncode == 0:
            failures.append("a reviewer with Edit/Write should fail the guard")
        reviewer.write_text(original)

        # The locator must keep the built-in's name and its three read-only tools.
        explore = agents / "Explore.md"
        original = explore.read_text()
        explore.write_text(
            re.sub(r"^tools: .*$", "tools: Read, Glob, Grep, Bash", original, flags=re.M)
        )
        if _check(agents).returncode == 0:
            failures.append("an Explore with Bash should fail the guard")
        explore.write_text(original)
        renamed = agents / "explore-haiku.md"
        renamed.write_text(original.replace("name: Explore", "name: explore-haiku"))
        explore.unlink()
        (agents / "roles.json").write_text(json.dumps({**ROLES, "explore": "explore-haiku"}))
        if _check(agents).returncode == 0:
            failures.append("an explore role not named Explore should fail the guard")
        renamed.unlink()

        # A role map from before the explore role, with no Explore.md, still passes.
        (agents / "roles.json").write_text(
            json.dumps({k: v for k, v in ROLES.items() if k != "explore"})
        )
        before = _check(agents)
        if before.returncode != 0:
            failures.append(f"a role map without explore should still pass:\n{before.stdout}")

    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp)
        for template in TEMPLATES.glob("*.md"):
            (raw / template.name).write_text(template.read_text())
        (raw / "roles.json").write_text(json.dumps(ROLES))
        if _check(raw).returncode == 0:
            failures.append("raw templates (unfilled markers) should fail the guard")

    for failure in failures:
        print(f"FAIL: {failure}")
    if not failures:
        print(
            "smoke test OK: filled set and a pre-explore role map pass; raw templates, "
            "a writing reviewer and a renamed or shell-wielding Explore fail"
        )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
