# CLI and model reference

The council uses one strong model from each CLI. Prefer the IDs below unless the
user names another model. `council.py` accepts per-member model overrides.

## Codex: Sol 6.2

- CLI: `codex`
- Model: `gpt-6.2-sol`
- Read-only: `--sandbox read-only`
- Check availability: `codex --version`, then sign in with `codex login` if needed.
- List models or configuration: `codex --help`; the local model is
  `model = "gpt-6.2-sol"` in `~/.codex/config.toml`.

Command shape:

```bash
codex exec \
  --model gpt-6.2-sol \
  --sandbox read-only \
  --ephemeral \
  --color never \
  --output-last-message <out>/codex.md \
  --cd <repo> \
  "<prompt>"
```

`codex review` is not used because it selects the configured review model
(`gpt-6.2-astra` in the local configuration), not Sol.

## Antigravity: Neon

- CLI: `agy`
- Model: `gemini-4-neon-xhigh` (Gemini 4 Neon, Extra reasoning)
- Read-only: `--mode plan --sandbox`
- Install on Windows:

  ```powershell
  irm https://antigravity.google/cli/install.ps1 | iex
  ```

- Install elsewhere: `curl -fsSL https://antigravity.google/cli/install.sh | bash`
- Default binary: `~/.local/bin/agy` or `%LOCALAPPDATA%\agy\bin\agy.exe`.
- List models: `agy models`.
- Authenticate by launching `agy` once or following the Antigravity authentication
  guide.

Command shape:

```bash
agy -p "<prompt>" \
  --model gemini-4-neon-xhigh \
  --mode plan \
  --sandbox \
  --output-format text
```

The Antigravity CLI is not installed on every machine. If `agy` is missing, the
council reports `missing`; install it and retry rather than substituting a model.

## OpenCode: DeepSeek v4.1 Flash

- CLI: `opencode`
- Model: `opencode-go/deepseek-v4.1-flash`
- Read-only: `--agent plan`
- Check availability: `opencode models` and `opencode auth login`.
- The model is also listed as `nearai/deepseek/deepseek-v4.1-flash-1017` and
  `nearai/deepseek-ai/DeepSeek-V4.1-Flash-1017` on some accounts; the council
  defaults to the `opencode-go` provider.

Command shape:

```bash
opencode run \
  --model opencode-go/deepseek-v4.1-flash \
  --agent plan \
  --format default \
  "<prompt>"
```

On Windows, `opencode` may be installed as a `.cmd` or `.ps1` shim. `council.py`
resolves those through `shutil.which` and runs `.ps1` files through PowerShell.

## Availability and failure handling

`council.py` checks `shutil.which` before starting. A missing CLI is reported as
`missing`; a non-zero exit is `error`; a timeout is `timeout`. The council does not
fall back to another provider because that would make the score and coverage
misleading.

The prompt is always read-only:

```text
Review only. Do not edit, commit, push, comment or start subagents.
Score this review out of 10 and list findings with file:line and a fix.
```

If a delegate changes a tracked file anyway, `results.json` records
`worktree_changed`. Stop, inspect the change, and do not discard the user's work.
