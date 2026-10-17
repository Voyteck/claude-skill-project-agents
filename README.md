# project-agents

A Claude Code skill that gives a repository a small, tiered team of subagents: each one
pins its model and effort, each one is fitted to the project's real commands and paths,
and a guard script keeps them that way.

## What it does, and why

Claude Code subagents are cheap to create and easy to get wrong. Two mistakes are common
and expensive:

- **An agent file without `model:` inherits the caller's model.** A main session on the
  top model hands mechanical work (lint runs, CI watching, docs edits) to subagents, and
  every one of them runs on the top model too.
- **Reviews that can edit, or that redo CI.** A reviewer with Edit/Write is no longer a
  review. A reviewer that re-runs the linters CI already ran pays for the same verdict
  twice.

Run the skill in a repository and it:

1. reads the project (CI, test commands, deploy path, architecture docs);
2. drafts a **risk list** (paths only the careful tier may change) and a **simple list**
   (paths the cheap tier may change), and asks you once to correct them and to choose the
   agents' names;
3. writes the agents to `.claude/agents/`, filled with the project's real facts, plus
   `.claude/agents/roles.json` (role -> agent name);
4. appends a "Working with Claude Code" section to `CLAUDE.md`, so the main session knows
   which agent to call for what;
5. installs a guard (`tools/claude/check_agents.py`, and a pytest test if the project uses
   pytest) and runs it.

## The roles

| role (default name) | model / effort | tools | job |
|---|---|---|---|
| `implementer` | opus / high | read + write | implements a decided change on a risk path, opens a PR; never merges or deploys |
| `implementer-simple` | sonnet / medium | read + write | implements a simple change from an explicit path list; hands back anything on the risk list |
| `reviewer-security` | opus / high | read-only | pre-merge review of risk-path PRs; confirms every finding by probing a production entry point |
| `reviewer-mechanical` | sonnet / low | read-only | takes CI's verdict, runs only what CI lacks, audits skips, docs and counters |
| `reviewer-deploy` | opus / high | read-only | before a deploy: the deploy path and the interactions between PRs, not the code again |
| `architect` | the strongest reasoning model your plan offers / high | read-only | design options and trade-offs; recommends, never implements |
| `architect-deep` | same as `architect` / xhigh | read-only | optional: GO/NO-GO reviews around irreversible steps |
| `ci-watcher` | haiku / low | Bash only | waits for one CI run and reports the failed steps |
| `explore` (always `Explore`) | haiku / low | Read, Glob, Grep | code search: returns `path:line-range` locations with one-line notes, not files; replaces the built-in `Explore` |

Agents the project cannot use are dropped, not filled with fiction (no deploy path -> no
`reviewer-deploy`).

### `Explore` replaces the built-in

Claude Code's built-in `Explore` runs on a model the caller does not pin, so code search -
a large share of all subagent calls - runs on whatever the session runs on, and tends to
bring whole files back into the caller's context. A project agent with the built-in's
exact name replaces it. This one is pinned to Haiku at low effort, may only use Read, Glob
and Grep, reads line ranges instead of whole files, skips vendored, built and duplicated
trees, and returns only `path:line-range` locations, at most five relationship bullets and
open questions. Every `Explore` call, the default ones included, then runs on Haiku. Its
result is a locator, not proof: a review that must prove a safety claim reads the code
itself. Without Haiku on the plan, it runs on `sonnet` at the same effort.

### Your own names

The default names are the roles, in English. Prefer other names? Say so when the skill
asks: it keeps one role -> name map in `.claude/agents/roles.json` and applies it to the
files, the cross-references between agents, the `Agent:` commit trailers, the `CLAUDE.md`
section and the guard. For example:

```json
{
  "implementer": "programista",
  "implementer-simple": "programista-prosty",
  "reviewer-security": "przeglad-bezpieczenstwa",
  "reviewer-mechanical": "przeglad-mechaniczny",
  "reviewer-deploy": "przeglad-wdrozenia",
  "architect": "architekt",
  "architect-deep": "architekt-przeglad",
  "ci-watcher": "obserwator-ci",
  "explore": "Explore",
  "architecture_model": null
}
```

`null` marks a role dropped on purpose. `explore` is the one role whose name is fixed:
it must be `Explore` (or `null`), or it no longer replaces the built-in. `architecture_model` names a model reserved for
the architects (set it when the architect runs on a model above the implementers', and
the guard fails if an implementer is moved onto it).

## Install

**As a Claude Code plugin** (updates with the repository):

```text
/plugin marketplace add Voyteck/claude-skill-project-agents
/plugin install project-agents@voyteck-project-agents
```

**As a plain skill**: copy `skills/project-agents/` into your personal skills or one project's:

```bash
git clone https://github.com/Voyteck/claude-skill-project-agents
cp -r claude-skill-project-agents/skills/project-agents ~/.claude/skills/                # every project on this machine
cp -r claude-skill-project-agents/skills/project-agents /path/to/repo/.claude/skills/    # one project, shared with its team
```

**On claude.ai** (Settings → Capabilities → Skills): upload a zip with the skill folder at
its root:

```bash
cd claude-skill-project-agents/skills && zip -r ../project-agents.zip project-agents
```

Claude Code picks the skill up at the next session start.

## An example run

```text
you:    Set up subagents for this repo.
claude: (reads CI, Makefile, src/, deploy/)
        Proposed lists - please correct:
          risk:   src/auth/, src/billing/, migrations/, deploy/, .github/
          simple: web/landing/, web/styles/, UI copy in web/components/ (no stores, no API calls)
        Names: keep the English role names (implementer, reviewer-security, ...) or use your own?
you:    Fine, keep them; drop the deep architect.
claude: Wrote 8 agents and roles.json, appended "Working with Claude Code" to CLAUDE.md,
        added tools/claude/check_agents.py and tests/test_claude_agents.py.
        Checker: OK. Restart the session (or open /agents) to see them.
```

## The guard

`skills/project-agents/scripts/check_agents.py` is standard-library Python, copied into the project as
`tools/claude/check_agents.py`:

```bash
python tools/claude/check_agents.py .claude/agents --risk-marker src/auth/ --risk-marker migrations/ --risk-marker .github/
```

It finds agents by role through `roles.json` (default: the English names), so renaming
an agent never silences a check. It fails when:

- an agent does not pin `model` and `effort`, or its `name:` differs from its file;
- a read-only role lists no tools (= all tools) or lists Edit/Write/NotebookEdit;
- the `explore` role is not named `Explore`, or lists a tool beyond Read, Glob and Grep
  (a role map written before 1.1.0, without `explore`, still passes);
- an implementer runs on the `architecture_model`, or does not require its `Agent: <name>`
  commit trailer (the trailer is how rework is counted per tier);
- the simple implementer stops naming any of the risk markers;
- the deep architect's tools, model or body drift from the architect's;
- a role's file is missing, or a `<<MARKER>>` from the templates is left unfilled.

`skills/project-agents/assets/test_claude_agents.py` wraps the same check as a pytest test.

## Why these rules - measurements

The rules come from measuring Claude Code usage on one multi-application repository
worked by several parallel sessions, in September and October 2026. Cost is in weighted
tokens (input x1, cache write x2, cache read x0.1, output x5), compared within one model.

**Before the rules (one weekend):**

- 97 % of all tokens were cache reads, so cost was context size x number of calls. Every
  rule below shrinks the context, cuts calls, or moves calls to a cheaper model.
- Main sessions were 55 % of the cost, at a mean context per call between ~390k and
  ~720k tokens.
- 100 % of subagent calls ran on Opus. The cheaper model was used once, in a weekend of
  mostly mechanical subagent work: no agent pinned a model.
- About 270 tool calls were refused, each a full-context turn; 224 of them were a
  worktree guard refusing compound shell commands, 14 a foreground `sleep`.
- A batch of 15 PRs reached production before review, and the same range was then
  reviewed in full again, by four agents, before deploy.

**After the first rules (the next few days):**

- Main sessions fell from 55 % to 32 % of the cost, and mean context per call to
  ~210k-380k - but 60-90 % of the calls in every main session were still above 250k,
  because nobody saw the context grow. Hence a visible context budget.
- Subagent calls that named no project agent (a generic agent inheriting Opus) were 31 %
  of all spend. Hence: such calls pass a cheap model explicitly.
- The cheap implementer ran once among ~234 subagent runs, the Opus implementer 73 times.
  Hence: check the simple path list before choosing the tier.
- Two full test runs in one PR, plus another session's run, exhausted a 3 GiB sandbox and
  killed two sessions. Hence: one full run per PR, never two at once.
- Cache writes averaged ~7.4k tokens per call, mostly large tool outputs that every later
  call reads again. Hence: cut output at the source.
- In long-lived cloud sessions, turns that re-wrote 250k+ tokens of context into the
  cache after an idle hour were ~59 % of those sessions' cost. Hence: compact before a
  long wait, end a session whose task is closed.
- A top reasoning model as coordinator cost ~1.8x Opus per weighted token and found 4.5
  of 5 seeded bugs, against Opus's 5 of 5 with ~56 % of the tokens. Hence: the
  coordinator runs on the strong implementation model; the top model is for architecture.
- A safety fix took four review rounds: its test called an internal function, and the
  measurement covered a sibling configuration, not the one the bug hit. Hence: safety
  claims are tested through the production entry point.
- Merging the main branch into a branch to keep it fresh re-runs full CI each time.
  Hence: merge only on a real conflict.

**A week later:**

- Main sessions: aggregate mean context ~190k, p90 ~350k; 27 % of calls above 250k (from
  60-90 % per session).
- Refused tool calls: 24 in four days (from ~270 in a weekend), none from the worktree
  guard.
- Subagent calls: Opus 83 %, Sonnet 16 %, Haiku under 1 %. Pinning works; the cheap tier
  is still under-used - which is what the weekly re-measurement and the "re-check the
  cheap tier after ten PRs" rule are for.

## Layout

```text
skills/project-agents/
  SKILL.md                          the instructions Claude follows
  references/discovery.md           where each template fact comes from
  references/claude-md-section.md   the CLAUDE.md section and the CONTRIBUTING table
  assets/agents/*.md                one template per role
  assets/roles.json                 the default role -> name map
  assets/test_claude_agents.py      the guard as a pytest test
  scripts/check_agents.py           the guard
```

## License

MIT - see [LICENSE](LICENSE). Plugin name `project-agents`, skill name `project-agents`.
