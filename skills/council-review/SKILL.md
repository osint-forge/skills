---
name: council-review
description: Run a read-only council review of a pull request or local change through several independent agent CLIs (Claude Code, Codex, Antigravity, OpenCode), then verify and reconcile their findings, disagreements and scores. Use when the user says council, council review, multi-model review, second opinions, or asks several models to review a PR or diff.
license: MIT
compatibility: Python 3.13+ and git; gh for pull requests; at least one authenticated member CLI (claude, codex, agy, opencode). Sends the change to each member's model provider.
---

# Council review

Independent reviewers from different model providers read the same change in a
throwaway worktree. You scope the change, verify what they report, fix what holds up,
and report scores without inventing any. `scripts/council.py` (next to this file) does
the mechanical work. Run it with `uv run` when available, otherwise `python3`.

## 0. Before you start

- Address known issues, outstanding PR comments and failing checks first, so the
  council reviews the real candidate. Skip fixes to code the user plans to discard.
- Pick the members. Default: every member in `references/members.toml` except your
  own provider (`--exclude-provider anthropic` when you are Claude, `openai` when you
  are Codex, `google` when you are Antigravity/Gemini). You review independently anyway.
- If the user names members or models, use `--members` and `--member key=model`. If a
  named member is unavailable, report it. Never substitute another model.
- Reasoning effort is one setting for all members: `--effort` (default `high`). Use
  `xhigh` or `max` only when the user asks or the change is high-risk (security,
  concurrency, data migrations); it roughly doubles time and cost. `low` and `medium`
  suit a quick sanity pass.

## 1. Prepare

```bash
python3 <skill>/scripts/council.py prepare --pr 123          # a GitHub PR (needs gh)
python3 <skill>/scripts/council.py prepare --base origin/main # local branch + uncommitted work
```

`--pr` reviews the PR's head commit and GitHub diff. `--base` defaults to `HEAD`
(uncommitted changes only) and includes staged, unstaged and untracked files. Both
create a throwaway worktree of the changed code and print the output folder (`<out>`,
under the system temp folder unless you pass `--out`; never the repository itself).
`<out>` contains `context.md` (generated facts), `diff.patch`, `ledger.md` and a
`brief.md` template. `prepare --in-place` reviews the checkout directly instead; use it
only when the worktree cannot be built.

Fill every `TODO(agent):` in `<out>/brief.md`: intent, scope, out of scope, checks run
with results, known risks. `run` refuses a brief with markers left. Use `--blind` on
`run` to hide the brief when you want reviewers unanchored by the author's framing.

## 2. Run a round

```bash
python3 <skill>/scripts/council.py run --out <out> --exclude-provider <yours>
```

Members run in parallel with each CLI's read-only settings and a stdin or file prompt.
`run --dry-run` checks every member's CLI and prints its command without running it.
A round can take up to `--timeout` seconds (default 900) per member, so start it as a
background job if your harness limits foreground commands, and wait for it to exit.
Each line `done <member> ...` is printed as a member finishes: read that answer
(`<out>/round-N/<key>.md`) and verify it while the others run. Members read the
throwaway worktree, so you may start fixes in the user's checkout meanwhile; after
`prepare --in-place`, do not edit anything until the round ends. `run` refuses to start
when the reviewed checkout changed since `prepare`; run `prepare` again.

Exit codes: 0 at least one usable review, 2 none, 3 a member changed the reviewed
checkout (listed in `worktree_changed`; it is a throwaway worktree unless you used
`--in-place`, so your work is safe, but treat that member's review with suspicion).

`round-N/results.json` has, per member: `status` (`ok`, `unparsed`, `error`,
`timeout`, `missing`), `verdict`, `score`, and parsed `findings` (severity, file, line,
claim, fix). `<out>/scores.md` is the score table across rounds, one row per member, model
and effort. Use it as-is: a
member without a parsed score is `no score`. Never invent or adjust a score.

## 3. Verify and reconcile

Check every finding against the code. Reviewers repeat the brief, misread guards, and
flag pre-existing code. Sort the surviving findings into:

- agreed by several members and reproduced by you;
- disagreements, with the evidence for each side and your call;
- single-member findings that survive verification;
- nits and out-of-scope items (list them, do not act on them).

Record every finding's decision in `<out>/ledger.md` (fixed, disputed, declined,
duplicate, out-of-scope).

## 4. Fix and re-review

Fix only findings you agree with, with the smallest change, in the user's checkout.
Re-run the covering checks. Start a new round only when a blocker or should was fixed:
run `prepare` again (it refreshes the worktree and patch, keeps the brief and ledger;
for a PR with unpushed fixes use `--base <PR base>` and the same `--out`), update the
brief's checks, then `run`. Default to two rounds. Stop when a round returns only nits.
Resist scope creep: new ideas outside the change go in the report, not the code.

## 5. Report and clean up

Write `<out>/council-report.md` and give the user the same summary:

- head commit reviewed and members excluded or unavailable;
- the score table from `scores.md`, unchanged;
- recommendation, verified blockers and shoulds, disagreements and how you resolved
  them, fixes made, declined findings;
- checks run and their results.

Do not post a PR comment or review, or edit the PR description, unless the user asks.
If they ask to record it on the PR, add a "Council review" section to the description
with the rounds and score table. Finally run `council.py cleanup --out <out>` to remove
the worktree (`--all` also deletes `<out>`).

Members run tools inside the reviewed code. For a PR from an untrusted author, note
that a CLI may load project config or plugins from that checkout (see
`references/cli-models.md`); exclude such members or review it in a sandboxed machine.

Member commands, read-only modes, install and auth notes: `references/cli-models.md`.
Add or change members in `references/members.toml` or pass `--config <file>`.
