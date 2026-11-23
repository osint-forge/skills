# Member CLIs

The exact command for each member is in `members.toml`. This file covers install,
authentication, read-only behavior and caveats. Check every member at once with
`council.py run --out <out> --dry-run`: it resolves each CLI and prints its command
without starting a round.

A CLI that is not on `PATH` is reported as `missing`. The council never falls back to
another model, because that would make scores and coverage misleading.

## Reasoning effort

`run --effort low|medium|high|xhigh|max` (default `high`) sets every member's reasoning.
Each member's `effort` table in `members.toml` turns the level into that CLI's syntax.
When a CLI lacks a level, the table names the nearest one it has:

| Level | Claude | Codex | Antigravity model | OpenCode variant |
|---|---|---|---|---|
| low | `--effort low` | `model_reasoning_effort=low` | `gemini-4-neon-low` | `#low` |
| medium | `--effort medium` | `model_reasoning_effort=medium` | `gemini-4-neon-medium` | `#low` |
| high | `--effort high` | `model_reasoning_effort=high` | `gemini-4-neon-high` | `#high` |
| xhigh | `--effort xhigh` | `model_reasoning_effort=xhigh` | `gemini-4-neon-xhigh` | `#max` |
| max | `--effort max` | `model_reasoning_effort=max` | `gemini-4-neon-xhigh` | `#max` |

`high` is the default because deeper reasoning finds more subtle bugs in review, and
`xhigh`/`max` roughly double time and cost. In one measured round, Antigravity at
xhigh took 488 s against Codex's 178 s at high. Raise it for high-risk changes.

The levels were checked against each CLI: Codex and Claude accept all five, Antigravity
lists `-low` to `-xhigh` model IDs, and DeepSeek v4.1 Flash on OpenCode has the `low`,
`high` and `max` variants.

## Claude Code: Claude Opus

- CLI: `claude`; model alias `opus` (`--member claude=<model-id>` to pin one).
- Prompt on stdin with `-p`; reasoning with `--effort`.
- Read-only: `--tools Read,Grep,Glob` makes only read tools exist, and
  `--permission-mode dontAsk` denies anything not pre-approved. `--add-dir` grants read
  access to the inputs folder. `--setting-sources user` ignores the reviewed repo's
  `.claude/` settings and hooks.
- Install: see the Claude Code docs; authenticate by running `claude` once.
- Exclude it with `--exclude-provider anthropic` when Claude is the host agent.

## Codex: Sol 6.2

- CLI: `codex`; model `gpt-6.2-sol`; reasoning with `-c model_reasoning_effort=<level>`,
  which overrides your `~/.codex/config.toml`.
- Prompt on stdin (`codex exec ... -`); the final answer is written with
  `--output-last-message`.
- Read-only: `--sandbox read-only`; `--ephemeral` keeps the session out of history.
- Authenticate with `codex login`. Codex applies a project's `.codex/` config only to
  trusted projects, and the throwaway worktree is not trusted.
- `codex review` is not used because it selects the configured review model, not the
  member's model.

## Antigravity: Gemini 4 Neon

- CLI: `agy`; model `gemini-4-neon`. The reasoning level is part of the model ID, so the
  script appends `-<level>` (`gemini-4-neon-high`). Override with a base ID and no
  suffix: `--member antigravity=gemini-4-argon`. List models with `agy models`.
- `agy -p` takes the prompt as its value and does not read stdin, so the member gets a
  one-line instruction to read the prompt file (`-p=<launcher>`).
- Read-only: none in print mode. `--sandbox` restricts the terminal, and `--mode plan`
  waits for approval, so it cannot run non-interactively. The throwaway worktree and the
  change check are the guard.
- `--add-dir` adds the inputs folder to the workspace.
- Install on Windows: `irm https://antigravity.google/cli/install.ps1 | iex`; elsewhere:
  `curl -fsSL https://antigravity.google/cli/install.sh | bash`. The default binary is
  `%LOCALAPPDATA%\agy\bin\agy.exe` or `~/.local/bin/agy`. Authenticate by running `agy`
  once.

## OpenCode: DeepSeek v4.1 Flash

- CLI: `opencode`; model `opencode-go/deepseek-v4.1-flash`. List models with
  `opencode models`. The script appends the reasoning variant (`#high`), so override
  with a model ID and no variant, such as
  `--member opencode=opencode-go/deepseek-v4-pro` for the larger previous-generation
  model. Check the variants a model has before switching; an unknown one fails.
- Gets the one-line launcher as its message.
- Read-only: `--agent plan` denies edits. Reading files outside the project needs
  approval in OpenCode, which is why the inputs live inside the worktree. With
  `--in-place`, OpenCode may be unable to read them.
- Authenticate with `opencode auth login`.
- OpenCode loads project config and plugins (`opencode.json`, `.opencode/`) from the
  reviewed checkout at startup, and plugins run as code with your permissions. There is
  no flag to disable that, so exclude this member (`--exclude-provider deepseek`) for
  PRs from untrusted authors.
- On Windows npm installs `opencode.cmd`, which runs through `cmd.exe`. The script
  refuses arguments containing `% ^ & | < > !` or quotes for `.cmd`/`.bat` shims; keep
  the output folder path free of those characters.

## Adding a member

Add a `[members.<key>]` table to `members.toml` (or a copy passed with `--config`):

```toml
[members.example]
label = "Example (Example CLI)"
provider = "example"
command = "example"
model = "example-large"
default = false          # run only with --members example
prompt = "stdin"         # or "launcher" with {launcher} in args
output = "stdout"        # or "file" with {final} in args
args = ["review", "--model", "{model}", "--reasoning", "{effort}", "--read-only"]
# Map every level; omit the table and {effort} if the CLI has no reasoning setting.
effort = { low = "low", medium = "medium", high = "high", xhigh = "high", max = "high" }
```

Pick the CLI's strongest read-only mode, keep the prompt off the command line where
the CLI allows it, and add a test for the command shape in
`tests/council-review/test_council.py`.
