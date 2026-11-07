# Finding the project facts

Fill every `<<MARKER>>` from evidence in the repository. Read the files named below; do
not run the full test suite just to discover the command (look at CI and the manifests).
If a fact does not exist, choose: drop the agent, or write the honest generic text the
row allows. Never invent a command or path.

## The names and the models

| marker | what it is | where it comes from |
|---|---|---|
| `<<NAME_IMPLEMENTER>>`, `<<NAME_IMPLEMENTER_SIMPLE>>`, `<<NAME_REVIEWER_SECURITY>>`, `<<NAME_REVIEWER_MECHANICAL>>`, `<<NAME_REVIEWER_DEPLOY>>`, `<<NAME_ARCHITECT>>`, `<<NAME_ARCHITECT_DEEP>>`, `<<NAME_CI_WATCHER>>`, `<<NAME_OPERATOR>>` | the agent name chosen for each role | the role -> name map you wrote to `.claude/agents/roles.json` (default: the role itself, e.g. `implementer`). The templates cross-reference each other, so a marker for a role you dropped may still appear in another agent's body: replace it with the name of the agent that takes that work, or rephrase the sentence. The `explore` role has no marker: its name is always `Explore` |
| `<<ARCHITECT_MODEL>>` | the architect's model | the strongest reasoning model the user's plan offers (e.g. `opus`, or a newer top model alias). Ask only if unsure which aliases the plan has; `opus` is always a safe answer |

## The project facts

| marker | what it is | where to look |
|---|---|---|
| `<<PROJECT>>` | the project's name as people say it | README title, package name, repo name |
| `<<DEFAULT_BRANCH>>` | the integration branch | `git symbolic-ref refs/remotes/origin/HEAD`; with no remote yet, `git branch --show-current`, else `main` (the templates' `origin/<branch>` starts working once a remote exists) |
| `<<FULL_CHECK>>` | ONE command a contributor runs before pushing, covering lint + tests | a `check` script, `Makefile`/`justfile` targets, `package.json` scripts, `tox.ini`/`noxfile.py`, what CI runs. If there is none, combine the CI steps into one line (`ruff check . && pytest -q`), or suggest adding a script and say so in the report |
| `<<TARGETED_CHECKS>>` | how to run only what a change touches | per-package test commands, `pytest <path>`, `npm test -w <pkg>`, `go test ./pkg/...` |
| `<<CI_WORKFLOW>>` | the workflow file that runs the tests on push | `.github/workflows/*.yml` with the test job |
| `<<EXTRA_GATES>>` | gates CI or the full check does NOT run but a diff may need | language linters missing from the check (e.g. eslint with `--max-warnings 0`, shellcheck, actionlint); "nothing else" if none |
| `<<RISK_PATHS>>` | markdown bullets `- \`path/\` (reason);`, each ending in `;`: project-specific paths only the implementer may change | see "The risk list" below |
| `<<RISK_SUMMARY>>` | 4-8 words for descriptions | condensed from the risk list ("auth, payments, personal data, migrations, workflows") |
| `<<SIMPLE_PATHS>>` | markdown bullets ending in `;`: paths the simple implementer may change, each with what is in and out; leave out docs/READMEs/fixtures, which the template already allows | see "The simple list" below |
| `<<SIMPLE_SUMMARY>>` | short phrase for the description | "landing pages, styles and UI copy" |
| `<<STAKES>>` | one or two sentences: the worst realistic outcome of a bad change on a risk path | the product's purpose; e.g. "a user's data readable by another tenant, or a payment captured twice." Ask the user if the product's purpose is unclear |
| `<<SEARCH_SKIP>>` | the `Explore` locator's skip list beyond the generic one: the project's own duplicate or generated trees, as a short list of paths with what each is | session worktrees kept inside the checkout (`.claude/worktrees/`), built documentation sites, vendored copies of the project's own code, virtualenvs, caches, archived code nothing runs ("search it only when asked to"); `git ls-files`/`.gitignore` and a `Glob` for duplicated file names show them. With none, write "none beyond the list above" |
| `<<STAKES_SHORT>>` | the same in a few words | "a permission, a payment, a data mask" |
| `<<PROBE_ENTRY>>` | where a safety claim is tested from outside | the HTTP API (route + how to start the app locally), the CLI, the public function the request handler calls |
| `<<DEPLOY_SUMMARY>>` | short phrase for the description | "workflows, infra scripts, compose, env/secrets, migrations" |
| `<<DEPLOY_SCOPE>>` | markdown bullets: the paths that change what runs in production | deploy workflows, `infra/`, `deploy/`, `k8s/`, `terraform/`, Dockerfiles, compose, migration runner |
| `<<DEPLOY_DOCS>>` | the docs on deploying, as backticked paths | `DEPLOY.md`, `docs/deploy*`, runbooks; "the deploy workflow itself" when there is no doc |
| `<<COMPONENTS>>` | the applications/services/packages, by name | top-level dirs, workspace members, compose services |
| `<<BOUNDARY_RULES>>` | the architecture rules as one sentence each, separated by semicolons | CLAUDE.md, ARCHITECTURE.md, ADRs, READMEs; if none are written, state the ones the code plainly follows (which component calls which, what is shared) and list them in the report for the owner to confirm |
| `<<CONTRACTS>>` | where the interfaces between components are defined | OpenAPI/proto files, a shared types module, HTTP clients |
| `<<IRREVERSIBLE_STEPS>>` | (deep variant only) examples of steps the owner cannot take back | splitting a repository, a data migration, a public API version; only if the user wants the variant |
| `<<RISK_MARKER>>` | (guard test only) 3-6 quoted, distinctive strings of the risk list | pick entries of `<<RISK_PATHS>>` and the template's tail (e.g. `".github/"`) that literally appear in the simple implementer's file |
| `<<LOG_SOURCES>>` | (operator) a few words for the description: where its logs come from | "`journalctl`, `docker compose logs`", "Vercel logs", "the hosting panel's CLI"; "no server logs" when there are none |
| `<<DEPLOY_TARGETS>>` | (operator) one bullet per target: name, workflow file, how a run starts (push to which branch, and/or the exact `gh workflow run ...` dispatch line with its inputs), the site it deploys to, its jobs in order, and which target is production (needs the owner's go) | see "The ops facts" below |
| `<<HEALTH_CHECKS>>` | (operator) the URLs or commands that say a deploy is alive, with the expected answer | see "The ops facts" below |
| `<<OPS_HOSTS>>` | (operator) one bullet per server: its ssh alias (or hosting CLI), what runs there, and the read-only log commands for its units/containers/services | see "The ops facts" below; "none - logs only through <the hosting CLI>" or "none" when nothing is reached by shell |
| `<<OPS_NEVER>>` | (operator) the project's own don'ts beyond the template's | other dispatchable workflows it must not start (data syncs, cron jobs), legacy deploy scripts nothing uses, commands that once broke a host (e.g. a firewall reload); "nothing beyond the rules below" if none |

## The risk list

A path belongs on it when a mistake there is expensive or silent: security and
authentication, sessions/tokens/keys/crypto, personal data, payments and billing, the
product's core decision logic (whatever the stakes sentence is about), database
migrations and schema, CI workflows and deploy/infra scripts, CSP and other security
headers, legal pages, and wire strings other components depend on. The template already
adds the generic tail (CI, infra, compose, Docker, `.env*`, migrations, `CLAUDE.md`,
`.claude/`, wire strings); `<<RISK_PATHS>>` carries only the project-specific paths the
tail does not already cover (name the concrete directory, e.g. `deploy/`, only when the
tail's generic word would not obviously match it), concrete enough to match with
`git diff --name-only` - directories and files, not adjectives.

## The simple list

Paths where a mistake is visible and cheap: marketing/landing pages, styles, presentational
UI components and copy, documentation sites, examples. Name what is OUT inside an allowed
directory when it matters (stores, API calls, auth code inside a UI package).

## The ops facts (the operator)

Read them from the repository, never from a server: the operator's template is filled
before anyone has run it.

- **Deploy path.** `.github/workflows/*.yml` with `on: workflow_dispatch`, an
  `environment:` (`production`, `staging`), or a deploy step (`ssh`, `rsync`, `scp`,
  `docker push`, `kubectl`, `helm`, `terraform apply`, a hosting action such as
  Vercel/Netlify/Fly/Cloudflare). The dispatch line is `gh workflow run <file> --ref
  <default branch>` plus every required `inputs:` key as `-f key=value` (a confirmation
  input, e.g. `confirm=deploy-production`, goes in verbatim). A target that runs by
  itself on push is "follow", not "dispatch". Also `DEPLOY.md`, `docs/deploy*`, runbooks,
  `Makefile`/`justfile` deploy targets - but a script no workflow calls is legacy: list it
  under `<<OPS_NEVER>>`, not as a target.
- **Health checks.** The workflow's own smoke or post-deploy steps (`curl` of a URL,
  Playwright base URLs), `HEALTHCHECK` in a Dockerfile, `healthcheck:` in compose, a
  `/health`, `/healthz` or `/status` route in the code, the site URL in the README or the
  `environment: url:`. Note anything that answers plain `curl` differently from a browser
  (a CDN or WAF that returns 403 to unknown user agents): the check then sends a browser
  user agent, and a 403 is reported as inconclusive, not as an outage.
- **Servers and logs.** ssh host aliases the workflows and docs use (`ssh <alias>`,
  `secrets.SSH_HOST` names the role, not the alias - ask the owner for the alias the
  operator's machine has); systemd units in `deploy/*.service` or the docs
  (`journalctl -u <unit>`); compose services and their directory on the host
  (`docker compose logs <service>`); container names; for managed hosting, its CLI's log
  command without follow (check its `--help`: `fly logs --no-tail`, `heroku logs -n 200`,
  `gcloud logging read ... --limit 200`). Never read `~/.ssh` key files, `.env*` or
  secrets to find any of this.
- **Drop rule.** No deploy path and no servers or hosting logs -> no operator (role
  `null`). A deploy with nothing to log into keeps the operator for following runs and
  health checks (`<<OPS_HOSTS>>` "none"); servers with no deploy workflow keep it for log
  reads (`<<DEPLOY_TARGETS>>` "none - deploys are manual; never deploy"). Without GitHub
  Actions, adapt the run commands to the CI the project has, as for the CI watcher.

## A brand-new repository

With almost no code, write the lists from the planned layout the user describes, or use
the generic categories above as directory guesses the user confirms. Keep `<<FULL_CHECK>>`
honest: if nothing exists yet, write the command the project will use (e.g. `npm test`)
and flag it in the report as "to be created". Drop the deploy reviewer and the operator
until there is a deploy path or a server (set their roles to `null` in `roles.json`); they
can be added later by running this skill again.
