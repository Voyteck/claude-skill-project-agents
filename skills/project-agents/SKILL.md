---
name: project-agents
description: Sets up a tiered team of Claude Code subagents in a project's `.claude/agents/` - an Opus implementer for risky paths, a Sonnet implementer bound to an explicit path list, read-only security, mechanical and deploy reviewers, an architect on the strongest reasoning model, a Haiku CI watcher and a Haiku code locator that replaces the built-in `Explore` - each pinning its model and effort, fitted to the project's real commands, risk paths and deploy path, plus the matching "Working with Claude Code" rules in CLAUDE.md and a guard script that keeps the agent files honest. Use it whenever someone starts or onboards a repository for Claude Code, asks for agents, subagents, reviewers, a model-per-task split or lower token cost, notices subagents running on the wrong model, or wants an existing `.claude/agents/` set audited or brought in line - even if they never say "skill". Polish triggers too - "skonfiguruj agentów", "dodaj agentów do projektu", "podział modeli na zadania".
---

# Project agents

This skill installs a tested set of project subagents into a repository. Two facts shaped
it: subagents without a pinned model inherit the caller's model, so routine work silently
runs on the most expensive tier; and reviews that can edit, or that redo what CI already
decided, cost a lot and catch little. Every choice below answers one of those two. Keep
that in mind when you adapt it - the goal is cheap work on the cheap tier, careful work on
the careful tier, and reviewers that cannot touch what they review.

## The roles

| role (default name) | model / effort | tools | job |
|---|---|---|---|
| `implementer` | opus / high | read + write | implements a decided change on a RISK path, opens a PR; never merges or deploys |
| `implementer-simple` | sonnet / medium | read + write | implements a SIMPLE change from an explicit path list; refuses the risk list |
| `reviewer-security` | opus / high | read-only | pre-merge review of risk-path PRs; confirms findings by probing production entry points |
| `reviewer-mechanical` | sonnet / low | read-only | takes CI's verdict, runs only what CI lacks, audits skips/docs/counters; the one review of a no-code PR |
| `reviewer-deploy` | opus / high | read-only | pre-deploy review of the deploy path and cross-PR interactions only |
| `architect` | strongest reasoning model / high | read-only | design options and trade-offs; recommends, never implements |
| `architect-deep` | same model as `architect` / xhigh | read-only | OPTIONAL: the architect at more effort, for GO/NO-GO reviews around irreversible steps |
| `ci-watcher` | haiku / low | Bash only | waits on one CI run and reports the failed steps |
| `explore` (always `Explore`) | haiku / low | Read, Glob, Grep | code search: returns `path:line-range` locations, not files; replaces the built-in `Explore` |

"Strongest reasoning model" means the strongest one the user's plan offers (e.g. `opus`,
or a newer top model alias). Templates live in `assets/agents/`, one per role.

Drop an agent the project cannot use rather than filling it with fiction: no deploy path
-> no `reviewer-deploy`; no GitHub Actions -> adapt `ci-watcher` to the CI the project
has, or drop it. Say what you dropped and why.

**`Explore` overrides a built-in on purpose.** Claude Code's built-in `Explore` inherits a
model unless the caller passes one, so code search - a large share of all subagent calls -
runs on whatever the session runs on. A project agent with the built-in's exact name
replaces it: every `Explore` call, the default ones included, then runs on Haiku and
returns locations instead of file contents. That is why this role is the one name the
role map cannot change, and why its file is `Explore.md` (the name must equal the file's
stem). Its answer is a locator, not proof: a reviewer that must prove a safety claim reads
the code itself.

## Names: one role -> name map

The default names are the roles themselves, in English. The user may want their own (for
example, one owner names them in Polish: `programista`, `programista-prosty`,
`przeglad-bezpieczenstwa`, `przeglad-mechaniczny`, `przeglad-wdrozenia`, `architekt`,
`architekt-przeglad`, `obserwator-ci`). The `explore` role is the exception: it is always
`Explore`, the built-in's name, or it stops replacing the built-in.

- **Ask once**, in the same message as the risk and simple lists (step 2): "The agents get
  English role names by default (`implementer`, `reviewer-security`, ...). Keep them, or
  give your own?" If `.claude/agents/` already holds agents that fill these roles, propose
  their names instead.
- **Keep the map** in `.claude/agents/roles.json` (start from `assets/roles.json`): every
  role -> its agent name, `null` for a role dropped on purpose, and `architecture_model`
  (see "Adapting the models").
- **Apply it everywhere**, consistently: the file names (`.claude/agents/<name>.md`), the
  `name:` fields, every `<<NAME_...>>` marker (the templates cross-reference each other),
  the `Agent: <name>` trailers, the CLAUDE.md section and the CONTRIBUTING table
  (`Explore` stays `Explore`). The guard reads `roles.json`, so it checks roles whatever
  they are called; a rename is a change of the file name and of `roles.json` together.

## Workflow

### 1. Look before you write

If `.claude/agents/` already exists, read every file there, and `roles.json` if present.
Never overwrite an agent silently: for an existing agent with the same name, show the user
what would change and ask. Keep agents that are not part of this set untouched (the guard
checks them only for a pinned model and effort).

### 2. Gather the project facts, then ask once

The templates hold `<<PLACEHOLDER>>` markers. Each must become a real fact about THIS
project - a command that runs, a path that exists. Read `references/discovery.md` for
where to find each one and what to do in a brand-new, nearly empty repository.

The two lists that matter most are the **risk list** (paths only the Opus implementer may
change) and the **simple list** (paths the Sonnet implementer may change). They are the
cheap tier's whole scope, so they decide both cost and safety. Draft them from the code,
then show them to the user in ONE short message together with the naming question, and
let them correct before you write files. This is the one step where the owner's judgement
is worth a question; everything else, decide yourself and report.

### 3. Fill the templates and write the files

Copy each template from `assets/agents/` to `.claude/agents/<name>.md` and replace the
markers. Write in the project's technical language (English unless the project says
otherwise). Keep the stance lines verbatim - "You never edit files, commit, push, merge or
deploy", the `Agent: <name>` trailer, "never merge the default branch to keep it fresh",
"one full check per PR" - they are the part that was learned the hard way.

If the project has its own scoped docs (subdirectory `CLAUDE.md` files, a CONTRIBUTING, a
deploy doc), point the agents at them by path instead of copying their content in; an
agent reads files itself, and a copy drifts.

The optional `architect-deep` is assembled, not filled: take
`assets/agents/architect-deep.head.md` (frontmatter + opening paragraph), fill it, then
append the finished architect body verbatim. Same model as the architect. Write it only
when the user plans irreversible steps worth a GO/NO-GO review; otherwise its role is
`null` in `roles.json`.

Write `.claude/agents/roles.json` last, from the names actually used.

### 4. Wire up the rules (default: all of it; skip a part only if the user says so)

- **CLAUDE.md section** - append the section from `references/claude-md-section.md` (fill
  its markers). Without it the main session does not know when to call which agent, and
  the tiers are never used. If CLAUDE.md already has an equivalent section, merge rather
  than duplicate.
- **CONTRIBUTING / README table** - optional: the agent table and the brief template from
  the same reference file, for humans.
- **Guard** - copy `scripts/check_agents.py` to `tools/claude/check_agents.py` and, if the
  project uses pytest, `assets/test_claude_agents.py` to its tests directory, with
  `RISK_MARKERS` set to 3-6 distinctive strings that literally appear in the simple
  implementer's file. For non-Python projects, add
  `python tools/claude/check_agents.py --risk-marker ...` to CI or the local check script
  instead. Check that the full check or CI really runs the new test (e.g. pytest collects
  that directory): a guard nobody runs guards nothing.

### 5. Verify

Run the checker on the result, with the same risk markers as the guard:

```bash
python <this-skill>/scripts/check_agents.py <repo>/.claude/agents --risk-marker <m1> --risk-marker <m2> ...
```

It reads `<repo>/.claude/agents/roles.json` (or `--roles <file>`), and fails when:

- an agent does not pin `model` and `effort`, or its `name:` differs from its file name;
- a read-only role (reviewers, architects, CI watcher, `Explore`) lists no tools or lists
  Edit/Write/NotebookEdit;
- the `explore` role is not named `Explore`, or lists a tool beyond Read, Glob and Grep;
- an implementer role runs on the `architecture_model` or does not require its
  `Agent: <name>` trailer;
- the simple implementer does not contain each risk marker;
- the deep variant's tools, model or body drift from the architect's, or its effort does
  not exceed the architect's;
- a role's file is missing (set the role to `null` if it was dropped), or roles.json names
  an unknown role or one name twice;
- any `<<...>>` marker is left.

Fix and re-run until it prints `OK`. Then re-read each written file once as the agent
would: does every command exist, every path resolve? A placeholder filled with a guess is
worse than a dropped agent.

### 6. Report

Tell the user, briefly: which agents were written under which names (and which dropped
and why), the risk and simple lists as finally chosen, what was added to CLAUDE.md /
CONTRIBUTING / tests, and the checker result. Mention that Claude Code loads project
agents at session start - a running session sees them after a restart (or via `/agents`).
Do not commit unless asked; if asked, stage explicit paths only.

## Adapting the models

The tiers are a policy, not a law. Use model aliases the user's plan offers and substitute
when one is missing (no Haiku -> `sonnet` for the CI watcher and for `Explore`, at the
same `low` effort), saying so in the report.

- **The architect** runs on the strongest reasoning model available. If that is a model
  above the implementers' (a newer top alias), set `architecture_model` in `roles.json` to
  it: the guard then fails if an implementer is ever moved onto it, because that model is
  for analysis, not for writing code. If the architect runs on `opus` like the
  implementer, leave `architecture_model` `null`; the architect's read-only tool list is
  what keeps it from implementing.
- **The coordinating session** (the one that briefs agents and merges) belongs on the
  strong implementation model, not the top reasoning model: it reads a lot and decides
  little.

Keep the invariants: every agent pins `model` and `effort`; implementers never run on the
architecture model; read-only roles list their tools and none of them writes.
