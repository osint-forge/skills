# council-review

A read-only, multi-model review of a pull request or local change. Independent agent
CLIs from different model providers review the same change in a throwaway worktree;
your agent verifies their findings and reports agreement, disagreement and scores.
It works from any agent harness that can run a shell command.

## Members

| Key | Member | CLI | Default model | Provider |
|---|---|---|---|---|
| `claude` | Claude Opus | `claude` | `opus` | anthropic |
| `codex` | Sol 6.2 | `codex` | `gpt-6.2-sol` | openai |
| `antigravity` | Gemini 4 Neon | `agy` | `gemini-4-neon` (+ `-<effort>`) | google |
| `opencode` | DeepSeek v4.1 Flash | `opencode` | `opencode-go/deepseek-v4.1-flash` | deepseek |

Every member runs at the same reasoning effort, `high` by default (`--effort`). The
agent excludes its own provider, so a Claude Code host runs the other three.
Members are defined in [`references/members.toml`](references/members.toml); add one
there or pass `--config <file>`. A missing CLI or model is reported, never substituted.

## Install

```bash
npx skills add osint-forge/skills --skill council-review
```

Or copy or symlink this directory into your agent's skills folder.

## Requirements

- Python 3.13+ and git. `gh` for `--pr`.
- At least one member CLI, signed in. Install and auth notes are in
  [`references/cli-models.md`](references/cli-models.md).
- The context, brief and patch are sent to each member's provider. Do not review
  changes containing secrets or data you cannot share with them.

## Use

```bash
# 1. Scope the change: a PR, or the local branch plus uncommitted work.
python3 scripts/council.py prepare --pr 123
python3 scripts/council.py prepare --base origin/main

# 2. Fill <out>/brief.md, then run a round.
python3 scripts/council.py run --out <out> --exclude-provider anthropic

# 3. After fixes, prepare again with the same --out and run the next round.
# 4. Remove the worktree (and with --all, the output folder).
python3 scripts/council.py cleanup --out <out>
```

`prepare` flags:

```text
--pr 123                      a GitHub PR (needs gh); fetches pull/123/head if missing
--base origin/main            local mode base (default HEAD: uncommitted work only)
--repo <path>                 repository (default: current directory)
--out <folder>                output folder (never the repository itself)
--remote origin               remote to fetch the PR head from
--in-place                    review the checkout itself instead of a worktree
```

`run` flags:

```text
--members claude,codex        subset of members (default: every default member)
--member codex=gpt-6.2-sol    override a member's model (repeatable)
--effort high                 low, medium, high, xhigh or max for every member
--exclude-provider anthropic  skip a provider or member key (repeatable)
--config members.toml         alternative members file
--timeout 900                 seconds per member
--blind                       hide the author's brief from reviewers
--round N                     re-run a specific round
--allow-incomplete-brief      run with TODO(agent) markers left in the brief
--dry-run                     print each member's command; no round, no scores
```

Exit codes: 0 at least one usable review, 1 usage error, 2 no usable review,
3 a member changed the reviewed checkout.

## Output

`<out>` defaults to `<temp>/council-review/<repo>-<pr-N|local-branch>`:

- `session.json`, `context.md`, `diff.patch`, `brief.md`, `ledger.md`;
- `checkout/`: the throwaway worktree, with the inputs copied to a fresh
  `checkout/.council-inputs-<random>/` folder;
- `round-N/`: per member `prompt-<key>.md`, `<key>.md` (answer), `<key>.stdout`,
  `<key>.stderr`, plus `results.json` with status, verdict, score and parsed findings;
- `scores.md`: the score table across rounds;
- `council-report.md`: written by the agent.

## Read-only behavior

Each member runs with its CLI's read-only settings: Claude with read-only tools,
Codex with `--sandbox read-only`, OpenCode with `--agent plan`. Antigravity has no
read-only print mode and runs with `--sandbox`. Every member reviews a throwaway
worktree, not your checkout. The script hashes HEAD plus every dirty and untracked file
before and after the round and reports any change; it does not see writes to ignored
files. `run` refuses to start when the checkout changed since `prepare`. On timeout,
the whole process tree is killed.

Read-only modes limit what a model does, not what the CLI loads. A CLI may load
project configuration or plugins from the reviewed checkout before the model runs; the
Claude member skips project settings with `--setting-sources user`, and the others are
described in [`references/cli-models.md`](references/cli-models.md). Review PRs from
untrusted authors only with members you have checked, or on an isolated machine.

## Tests

```bash
uv run tests/run_all.py --filter council-review
```

The tests use fake member CLIs and temporary git repositories; they do not call any
model provider.
