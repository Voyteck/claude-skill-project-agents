# Text to add to the project

Fill the markers the same way as in the agent files, names included. Drop a rule whose
subject the project lacks (no deploy -> drop the deploy half of rule 3 and rule 4's
"dispatches deploys"); drop the line of an agent that was not written.

## A. The CLAUDE.md section

Append to the project's root `CLAUDE.md` (create it if missing).

```markdown
## Working with Claude Code - sessions, agents, reviews

1. **Context budget.** After closing a task (merge, deploy, report) a session runs
   `/compact` or starts fresh; a main session stays under ~250k tokens of context. Heavy
   reading goes to subagents and only conclusions come back (findings, not file dumps).
   Code search - locating files, symbols, call sites - goes to `Explore` (Haiku,
   `path:line-range` back) instead of files read into the caller's context, for main
   sessions and implementing agents alike; an implementing agent has no `Agent` tool, so
   its coordinator runs `Explore` before the brief and puts the locations in its "Scope",
   and inside the run the agent greps and reads line ranges, not whole files. `Explore`
   locates; it proves nothing - a review reads the code itself.
   The prompt cache lives about an hour: before a wait of over ~50 min (CI, a review) a
   session above ~150k runs `/compact` or hands the wait to `<<NAME_CI_WATCHER>>`, and a
   session whose task is closed ends instead of idling.
2. **Model per task.** Opus (`<<NAME_IMPLEMENTER>>`): implementation touching the risk
   list - <<RISK_SUMMARY>>. Sonnet (`<<NAME_IMPLEMENTER_SIMPLE>>`): simple implementation
   from its path list in `.claude/agents/<<NAME_IMPLEMENTER_SIMPLE>>.md` - the list
   decides, not a judgement call; plus lint/format runs, docs-vs-code checks and test runs
   (`<<NAME_REVIEWER_MECHANICAL>>`). Haiku: code search (`Explore`) and watching one CI run (`<<NAME_CI_WATCHER>>`).
   `<<ARCHITECT_MODEL>>`: architectural analysis (`<<NAME_ARCHITECT>>`), never
   implementation. The coordinating session runs on Opus. When unsure, the risk list
   decides: one path on it -> Opus. Before briefing `<<NAME_IMPLEMENTER>>`, check the
   change's paths against `<<NAME_IMPLEMENTER_SIMPLE>>`'s list. An `Agent` call that names
   no project agent passes `model: sonnet` unless the brief says which risk path needs
   Opus. `Explore` is a project agent on Haiku (`.claude/agents/Explore.md`) that replaces
   the built-in of that name, so an `Explore` call needs no `model`; a built-in agent with
   no project file of its name (e.g. `Plan`) still gets `model: sonnet`. An implementing agent signs each commit and PR with `Agent: <name>`; re-check the
   Sonnet tier after its first ten PRs (rework and review findings vs
   `<<NAME_IMPLEMENTER>>`).
3. **Review levels.** ONE full review per PR, before merge, scoped by risk: a risk-path PR
   gets `<<NAME_REVIEWER_SECURITY>>` (probes, not just reading); a PR with no code gets
   `<<NAME_REVIEWER_MECHANICAL>>`. Before a deploy, when every PR in the range was
   reviewed at merge, ONE `<<NAME_REVIEWER_DEPLOY>>` reviews only the deploy path and the
   interactions between the PRs. A re-verification after fixes checks only the findings,
   by probes.
4. **One gate to `<<DEFAULT_BRANCH>>`.** Worker sessions and agents open PRs; only the
   coordinating session (or the owner) merges and dispatches deploys, after review.
5. **Safety claims through the production entry.** A change on a risk path is tested
   through <<PROBE_ENTRY>>; a test of an internal function alone is not proof.
6. **Tool hygiene.** Multi-step shell logic goes into a script in the scratchpad, not one
   long command. Wait with background tasks, never a foreground `sleep`. Cut tool output
   at the source (`tail`, `-q`, `Read` with a limit). One full `<<FULL_CHECK>>` per PR,
   before the final push; while iterating, only what the change touches; never two full
   runs on one machine at once (the coordinator serialises them). Never merge
   `<<DEFAULT_BRANCH>>` into a branch just to keep it fresh: each merge re-runs full CI.
7. **Measure the rules.** Weekly, and after every change to an agent file, compare cost
   per merged PR, the share of main-session calls above 250k context, subagent calls by
   model, and review findings per tier; a rule the numbers no longer support is proposed
   for change, not kept by habit.

The agents are found by role through `.claude/agents/roles.json`; rename an agent there
and in its file together, and the guard keeps checking it.
```

## B. For CONTRIBUTING.md (optional, for humans)

```markdown
## Claude Code agents

The project agents in `.claude/agents/` pin their model; pick one by its description.
The rules for using them: `CLAUDE.md` -> "Working with Claude Code".

| agent | model / effort | when |
|---|---|---|
| `<<NAME_IMPLEMENTER>>` | opus / high | implements a scoped change on a risk path; opens a PR, never merges or deploys |
| `<<NAME_IMPLEMENTER_SIMPLE>>` | sonnet / medium | implements a simple change from its path list; refuses the risk list |
| `<<NAME_REVIEWER_SECURITY>>` | opus / high | pre-merge review of risk-path PRs, by probes (read-only) |
| `<<NAME_REVIEWER_MECHANICAL>>` | sonnet / low | takes CI's verdict, runs only the missing gates; the one review of a no-code PR (read-only) |
| `<<NAME_REVIEWER_DEPLOY>>` | opus / high | pre-deploy review of the deploy path and cross-PR interactions (read-only) |
| `<<NAME_ARCHITECT>>` | <<ARCHITECT_MODEL>> / high | design options and trade-offs; recommends, never implements (read-only) |
| `<<NAME_CI_WATCHER>>` | haiku / low | waits for one CI run and reports failed steps |
| `Explore` | haiku / low | code search: returns `path:line-range` locations with one-line notes instead of files; replaces the built-in `Explore`, so a default call runs on Haiku too; a locator, not proof (read-only) |

### A subagent brief

A brief is the subagent's whole context. Five parts, in this order, short:

    Task: <one sentence - the outcome, not the method>
    Scope: <the paths it may change or must read; "nothing else">
    Rules: <the scoped docs that apply; the issue or PR number>
    Done when: <the check that proves it - a test, a gate, a PR with green CI>
    Report: <what comes back and how long - e.g. "PR number, head SHA, CI conclusion, <=10 lines">

Give an implementing agent the attribution lines to end its commits with; it adds its own
`Agent:` trailer. Paste no file contents the agent can read itself - name the path.
```

Keep the table in sync with the agents actually written (drop rows for dropped agents,
add `<<NAME_ARCHITECT_DEEP>>` at `<<ARCHITECT_MODEL>>` / xhigh if written).
