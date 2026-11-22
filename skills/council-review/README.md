# council-review

A read-only, multi-model review of a pull request or local diff. The skill asks
Codex, Antigravity and OpenCode for independent reviews, then verifies the findings
and reports agreement, disagreement and scores.

## Members

| Member | CLI | Default model |
|---|---|---|
| Sol 6.2 | `codex` | `gpt-6.2-sol` |
| Neon | `agy` | `gemini-4-neon-xhigh` |
| DeepSeek v4.1 Flash | `opencode` | `opencode-go/deepseek-v4.1-flash` |

The defaults are configurable in the script. If a CLI or model is unavailable, the
council reports it; it does not substitute another model.

## Install

```bash
npx skills add osint-forge/skills --skill council-review
```

Or copy or symlink this directory into your agent's skills folder.

## Requirements

- Python 3.13+.
- [Codex CLI](https://github.com/openai/codex) signed in and able to run the
  `gpt-6.2-sol` model.
- [Antigravity CLI](https://antigravity.google/docs/getting-started/) as `agy`,
  signed in and able to run `gemini-4-neon-xhigh`. On Windows the official
  installer is:

  ```powershell
  irm https://antigravity.google/cli/install.ps1 | iex
  ```

- [OpenCode](https://opencode.ai) signed in and able to run
  `opencode-go/deepseek-v4.1-flash`.
- A Git checkout and network access for the model providers.

## Use

The skill runs a script that receives a review brief and a patch:

```bash
uv run scripts/council.py \
  --brief <out>/brief.md \
  --diff <out>/diff.patch \
  --out <out>/council
```

`<out>` is any folder outside this skill. The result folder contains:

- `prompt.md`: the common review prompt;
- `<member>.md`: the reviewer's final answer;
- `<member>.stdout` and `<member>.stderr`: raw process output;
- `results.json`: status, timing, missing CLIs, timeouts and worktree changes.

Useful flags:

```text
--delegates codex,antigravity,opencode
--codex-model gpt-6.2-sol
--antigravity-model gemini-4-neon-xhigh
--opencode-model opencode-go/deepseek-v4.1-flash
--timeout 900
--dry-run
```

## Read-only behavior

The script asks every delegate to review only and configures the closest read-only
mode each CLI offers:

- Codex: `--sandbox read-only`;
- Antigravity: `--mode plan --sandbox`;
- OpenCode: `--agent plan`.

The skill also tells the agent not to edit, commit, push or comment during a round,
and checks for tracked-file changes afterwards. A changed worktree is reported, not
reverted.

## Tests

The offline tests for this skill live in `tests/council-review/` and use the
repository runner:

```bash
uv run tests/run_all.py --filter council-review
```

They do not call the model providers.
