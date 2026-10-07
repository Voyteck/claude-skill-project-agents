#!/usr/bin/env python3
"""Check a `.claude/agents/` directory against the tiered-agent invariants, by role.

The agents are found by ROLE, not by name: `roles.json` next to the agent files maps each
role (`implementer`, `reviewer-security`, ...) to the agent name the project chose, so a
project may call its agents anything and still be checked. Without `roles.json` the
default English names apply (each role is named after itself).

Each check answers a failure seen in practice:

* every agent pins `model` and `effort` - a subagent without a pinned model inherits the
  caller's model, usually the most expensive one;
* a read-only role lists its tools and none of them writes - a review that can edit the
  tree it reviews is no longer a review, and an empty list means ALL tools;
* an implementer role does not run on the architecture model, and requires the
  `Agent: <name>` trailer - without it nobody can tell which tier wrote a commit;
* the simple implementer names every risk marker - a cheap-tier writer that stops naming
  the risk list can implement on a risk path unnoticed;
* the deep architect variant keeps its base's tools, model and body - it differs only in
  effort and an opening paragraph;
* no `<<MARKER>>` from the templates is left unfilled.

`roles.json` format (every key optional; `null` marks a role dropped on purpose)::

    {
      "implementer": "implementer",
      "implementer-simple": "implementer-simple",
      "reviewer-security": "reviewer-security",
      "reviewer-mechanical": "reviewer-mechanical",
      "reviewer-deploy": null,
      "architect": "architect",
      "architect-deep": null,
      "ci-watcher": "ci-watcher",
      "architecture_model": null
    }

`architecture_model` names the model the architect roles use that implementers must not;
leave it `null` when the architect runs on the same model as the implementer (then the
read-only tool list is what keeps the architect from implementing).

Usage:
    python check_agents.py [AGENTS_DIR] [--roles ROLES_JSON] [--risk-marker TEXT ...]

Exit status 0 and `OK` when every check passes; 1 and one line per problem otherwise.
Standard library only, so it can be copied into any project (e.g. `tools/claude/`).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

#: Every role this checker knows, in the order the skill presents them.
ROLES = (
    "implementer",
    "implementer-simple",
    "reviewer-security",
    "reviewer-mechanical",
    "reviewer-deploy",
    "architect",
    "architect-deep",
    "ci-watcher",
)
#: Roles that may never write to the tree.
READ_ONLY_ROLES = (
    "reviewer-security",
    "reviewer-mechanical",
    "reviewer-deploy",
    "architect",
    "architect-deep",
    "ci-watcher",
)
#: Roles that implement: signed commits, never on the architecture model.
IMPLEMENTER_ROLES = ("implementer", "implementer-simple")
#: The role that must name the risk list it hands back.
SIMPLE_IMPLEMENTER_ROLE = "implementer-simple"
#: Effort variant role -> its base role; the variant differs by effort and an opening
#: paragraph only.
EFFORT_VARIANTS = {"architect-deep": "architect"}
#: Roles whose file may be absent when `roles.json` does not name them explicitly.
OPTIONAL_ROLES = ("architect-deep",)
#: The `roles.json` key that is a setting, not a role.
ARCHITECTURE_MODEL_KEY = "architecture_model"
ROLES_FILE = "roles.json"

EFFORTS = ("low", "medium", "high", "xhigh", "max")
WRITING_TOOLS = frozenset({"Edit", "Write", "NotebookEdit"})
MARKER = re.compile(r"<<[A-Z_]+>>")


def frontmatter(path: Path) -> dict[str, str]:
    """Read the `key: value` lines of the file's leading `---` block.

    Args:
        path: An agent definition.

    Returns:
        The keys mapped to raw values; empty when there is no closed frontmatter block.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    return {}


def body(path: Path) -> str:
    """Return the text after the frontmatter block, stripped.

    Args:
        path: An agent definition.

    Returns:
        Everything after the closing `---`; the whole text when there is no frontmatter.
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return text.strip()
    return text[3:].partition("\n---")[2].strip()


def tools(path: Path) -> set[str]:
    """Return the agent's tool list.

    Args:
        path: An agent definition.

    Returns:
        The tool names; empty when none is given, which Claude Code reads as ALL tools.
    """
    raw = frontmatter(path).get("tools", "")
    return {t.strip() for t in raw.split(",") if t.strip()}


def load_roles(path: Path) -> tuple[dict[str, str | None], set[str], str | None, list[str]]:
    """Read the role -> agent name map, falling back to the default English names.

    Args:
        path: The `roles.json` file; it need not exist.

    Returns:
        A tuple of: every role mapped to its agent name (`None` = dropped on purpose); the
        roles the file names explicitly; the architecture model (`None` = not set); and
        the problems found in the file itself.
    """
    names: dict[str, str | None] = {role: role for role in ROLES}
    if not path.is_file():
        return names, set(), None, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return names, set(), None, [f"{path.name}: not valid JSON ({exc})"]
    if not isinstance(data, dict):
        return names, set(), None, [f"{path.name}: must be a JSON object of role -> name"]

    problems: list[str] = []
    explicit: set[str] = set()
    architecture_model = data.pop(ARCHITECTURE_MODEL_KEY, None)
    if architecture_model is not None and (
        not isinstance(architecture_model, str) or not architecture_model.strip()
    ):
        problems.append(f"{path.name}: `{ARCHITECTURE_MODEL_KEY}` must be a model name or null")
        architecture_model = None
    for role, name in data.items():
        if role not in ROLES:
            problems.append(f"{path.name}: unknown role `{role}` (known: {', '.join(ROLES)})")
            continue
        if name is not None and (not isinstance(name, str) or not name.strip()):
            problems.append(f"{path.name}: role `{role}` must map to an agent name or null")
            continue
        names[role] = name.strip() if isinstance(name, str) else None
        explicit.add(role)
    taken: dict[str, str] = {}
    for role, name in names.items():
        if name is None:
            continue
        if name in taken:
            problems.append(
                f"{path.name}: roles `{taken[name]}` and `{role}` share the name `{name}`"
            )
        taken.setdefault(name, role)
    return names, explicit, architecture_model, problems


def _check_every_agent(path: Path) -> list[str]:
    """Check what holds for any agent file, whatever its role.

    Args:
        path: An agent definition.

    Returns:
        The problems of this file.
    """
    name, fields = path.name, frontmatter(path)
    problems: list[str] = []
    leftovers = sorted(set(MARKER.findall(path.read_text(encoding="utf-8"))))
    if leftovers:
        problems.append(f"{name}: unfilled template markers {leftovers}")
    missing = [k for k in ("name", "description", "model", "effort") if not fields.get(k)]
    if missing:
        problems.append(f"{name}: frontmatter lacks {missing}")
        return problems
    if fields["name"] != path.stem:
        problems.append(f"{name}: `name: {fields['name']}` differs from the file name")
    if fields["effort"] not in EFFORTS:
        problems.append(f"{name}: effort `{fields['effort']}` not in {list(EFFORTS)}")
    return problems


def _check_role(
    role: str,
    path: Path,
    risk_markers: list[str],
    architecture_model: str | None,
) -> list[str]:
    """Check the invariants of one role on the file that fills it.

    Args:
        role: The role, one of `ROLES`.
        path: The agent file named for that role.
        risk_markers: Strings the simple implementer must contain.
        architecture_model: The model implementers must not use; `None` skips that check.

    Returns:
        The problems of this role.
    """
    label = f"{path.name} ({role})"
    text = path.read_text(encoding="utf-8")
    tool_set = tools(path)
    problems: list[str] = []

    if role in READ_ONLY_ROLES:
        if not tool_set:
            problems.append(f"{label}: a read-only role must list its tools (none = ALL tools)")
        elif tool_set & WRITING_TOOLS:
            problems.append(f"{label}: a read-only role lists {sorted(tool_set & WRITING_TOOLS)}")

    if role in IMPLEMENTER_ROLES:
        model = frontmatter(path).get("model")
        if architecture_model and model == architecture_model:
            problems.append(
                f"{label}: an implementer must not run on the architecture model `{architecture_model}`"
            )
        if f"`Agent: {path.stem}`" not in text:
            problems.append(f"{label}: the `Agent: {path.stem}` trailer is not required")

    if role == SIMPLE_IMPLEMENTER_ROLE:
        if not risk_markers:
            problems.append(f"{label}: pass --risk-marker to check that it names the risk list")
        else:
            absent = [m for m in risk_markers if m not in text]
            if absent:
                problems.append(f"{label}: must name {absent} as off limits (the risk list)")
    return problems


def _check_variant(variant: Path, base: Path) -> list[str]:
    """Check that an effort variant differs from its base by effort and preamble only.

    Args:
        variant: The variant's agent file.
        base: The base agent's file.

    Returns:
        The problems of the pair.
    """
    problems: list[str] = []
    vf, bf = frontmatter(variant), frontmatter(base)
    if tools(variant) != tools(base):
        problems.append(f"{variant.name}: tools differ from {base.name}")
    if vf.get("model") != bf.get("model"):
        problems.append(f"{variant.name}: model differs from {base.name}")
    if (
        vf.get("effort") in EFFORTS
        and bf.get("effort") in EFFORTS
        and (EFFORTS.index(vf["effort"]) <= EFFORTS.index(bf["effort"]))
    ):
        problems.append(f"{variant.name}: effort does not exceed {base.name}'s")
    if body(base) not in body(variant):
        problems.append(f"{variant.name}: must carry {base.name}'s body verbatim")
    return problems


def check(
    agents_dir: Path,
    risk_markers: list[str] | None = None,
    roles_path: Path | None = None,
) -> list[str]:
    """Return every invariant the agents in `agents_dir` break.

    Args:
        agents_dir: The `.claude/agents` directory.
        risk_markers: Distinctive entries of the risk list that the simple implementer
            must contain.
        roles_path: The role -> name map; defaults to `agents_dir / "roles.json"`.

    Returns:
        Human-readable problems, one per broken invariant; empty when all hold.
    """
    risk_markers = risk_markers or []
    names, explicit, architecture_model, problems = load_roles(
        roles_path or agents_dir / ROLES_FILE
    )
    agents = sorted(agents_dir.glob("*.md"))
    if not agents:
        return [*problems, f"{agents_dir}: no *.md agent files"]

    for path in agents:
        problems.extend(_check_every_agent(path))

    files: dict[str, Path] = {}
    for role, name in names.items():
        if name is None:
            continue
        path = agents_dir / f"{name}.md"
        if path.is_file():
            files[role] = path
        elif role not in OPTIONAL_ROLES or role in explicit:
            problems.append(
                f"role `{role}`: {path.name} is missing (set the role to null in "
                f"{ROLES_FILE} if it was dropped on purpose)"
            )
    if not files:
        problems.append("no role maps to an existing agent file: the role checks judged nothing")

    for role, path in files.items():
        problems.extend(_check_role(role, path, risk_markers, architecture_model))

    for variant_role, base_role in EFFORT_VARIANTS.items():
        if variant_role not in files:
            continue
        if base_role not in files:
            problems.append(f"{files[variant_role].name}: its base role `{base_role}` has no file")
            continue
        problems.extend(_check_variant(files[variant_role], files[base_role]))
    return problems


def main() -> int:
    """Run the checks from the command line.

    Returns:
        The exit status: 0 when every check passes, 1 otherwise.
    """
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("agents_dir", nargs="?", default=".claude/agents", type=Path)
    parser.add_argument("--roles", type=Path, default=None, help="role -> name map (JSON)")
    parser.add_argument("--risk-marker", action="append", default=[])
    args = parser.parse_args()
    problems = check(args.agents_dir, args.risk_marker, args.roles)
    for problem in problems:
        print(problem)
    if not problems:
        print("OK")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
