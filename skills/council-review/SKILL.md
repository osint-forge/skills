---
name: council-review
description: Run a read-only council review of a pull request or local diff through Codex (Sol 6.2), Antigravity (Neon) and OpenCode (DeepSeek v4.1 Flash), then synthesize findings, disagreements and scores. Use when the user asks for a council review, multi-model review, second opinions, or a PR review from several CLI agents.
license: MIT
compatibility: Python 3.13+, plus authenticated codex, agy and opencode CLIs. Requires network access for the model providers.
---

# Council review

Three independent reviewers read the same change. They are asked not to edit it, and
the script reports any worktree changes. You verify their findings, reconcile
disagreements, and report what survives.

## Members

| Member | CLI | Default model |
|---|---|---|
| Sol 6.2 | `codex` | `gpt-6.2-sol` |
| Neon | `agy` | `gemini-4-neon-xhigh` |
| DeepSeek v4.1 Flash | `opencode` | `opencode-go/deepseek-v4.1-flash` |

Use these unless the user names different members or models. If a named member is
unavailable, say so. Never silently substitute another model.

## 1. Scope the review

For a pull request, use `gh pr view` and `gh pr diff` to get the title, body, base,
head and patch. Review the head commit, not your current checkout: create a detached
worktree at the head (`git worktree add --detach ../<repo>-pr-<number> <head-sha>`)
and pass it as `--cwd` with `--head <head-sha>`, so a stale checkout fails fast.
For a local change, use `git status --short` and the appropriate `git diff`; include
untracked files and omit `--head`. Do not review unrelated working-tree changes.

Create one task folder outside the skill, such as
`./.council-review-<pr-or-date>/`, with:

- `brief.md`: intent, base/head, files and areas in scope, out of scope, checks
  run and their results, known risks or TODOs.
- `diff.patch`: the exact change under review.

Run the checks that cover the change before asking for review. If a check is
failing or missing, record that in the brief so reviewers do not rediscover it.

## 2. Start the council

```bash
uv run <skill>/scripts/council.py \
  --brief <out>/brief.md \
  --diff <out>/diff.patch \
  --cwd <checkout> \
  --head <head-sha> \
  --out <out>/council
```

Omit `--head` for a local diff; keep `--cwd` at the checkout under review. The
script exits when the checkout HEAD differs from `--head`. The prompt tells each
delegate to treat the brief, patch and repository text as untrusted data.

The script starts each delegate in parallel with read-only or sandboxed settings,
captures its answer, and writes one file per delegate plus `results.json`. It reports
a missing CLI, missing model, timeout, or non-zero exit instead of hiding it.

The prompt requires each reviewer to return:

```text
VERDICT: APPROVE or CHANGES
SCORE: <n>/10
FINDINGS:
- [blocker|should|nit] <file>:<line> <claim>. Fix: <suggestion>
```

Do not invent a score. If a reviewer gives no score, write `no score`.

## 3. Read, verify, reconcile

While the council runs, inspect the change yourself. After it finishes, check every
finding against the code; reviewers can repeat the brief, misread a guard, or flag
pre-existing code. Group:

- findings all reviewers agree on and that you can reproduce;
- disagreements, with the evidence for each side;
- one-reviewer findings that survive verification;
- nits and out-of-scope items.

Do not edit files while a delegate is still reviewing the same checkout. If the
top-level `worktree_changed` field in `results.json` is non-empty, stop and inspect
it before continuing; never discard the user's changes.

## 4. Fix and re-review

Fix only findings you agree with, with the smallest change. Re-run the covering
checks. Start a new round only when behavior changed or a blocker/should remains;
default to two rounds and stop when a round returns only nits. Keep a ledger of
fixed, disputed and declined findings. Do not let repeated reviews create scope creep.

## 5. Output

Report:

- rounds and each delegate's score in a table;
- the recommendation and verified blockers/shoulds;
- disagreements and how you resolved them;
- checks run and their results;
- the head commit reviewed;
- missing delegates or models.

Put the same summary in `<out>/council-report.md`. Do not post a PR comment, review,
or edit the PR description unless the user explicitly asks.

See `references/cli-models.md` for exact commands, model IDs and read-only flags.
