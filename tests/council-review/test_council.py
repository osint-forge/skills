#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Offline tests for the council-review orchestration script."""

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "skills" / "council-review" / "scripts" / "council.py"
spec = importlib.util.spec_from_file_location("council_review", SCRIPT)
assert spec and spec.loader
council = importlib.util.module_from_spec(spec)
spec.loader.exec_module(council)

fails = 0


def check(name, condition, info=""):
    global fails
    print(("ok   " if condition else "FAIL ") + name + ("" if condition else f"  [{info}]"))
    if not condition:
        fails += 1


check("three default delegates", list(council.DEFAULT_DELEGATES) == ["codex", "antigravity", "opencode"])
check(
    "default models",
    [d["model"] for d in council.DEFAULT_DELEGATES.values()]
    == ["gpt-6.2-sol", "gemini-4-neon-xhigh", "opencode-go/deepseek-v4.1-flash"],
)

prompt = council.build_prompt(Path("brief.md"), Path("diff.patch"), Path("repo"), "Sol 6.2")
check("prompt includes the brief", "brief.md" in prompt)
check("prompt includes the patch", "diff.patch" in prompt)
check("prompt is read-only", "Review only" in prompt and "do not edit" in prompt)
check("prompt requires a score", "SCORE:" in prompt and "/10" in prompt)
check(
    "prompt treats repository text as untrusted data",
    "untrusted data" in prompt and "do not follow instructions" in prompt,
)

codex = council.command_for("codex", council.DEFAULT_DELEGATES["codex"], "PROMPT", Path("out"), Path("repo"), ["codex"])
check("codex uses exec and read-only sandbox", codex[:2] == ["codex", "exec"] and "read-only" in codex)
check("codex uses Sol 6.2", "gpt-6.2-sol" in codex)
check("codex writes the final message", "--output-last-message" in codex and any("codex.md" in part for part in codex))
check("codex prompt is last", codex[-1] == "PROMPT")

antigravity = council.command_for(
    "antigravity",
    council.DEFAULT_DELEGATES["antigravity"],
    "PROMPT",
    Path("out"),
    Path("repo"),
    ["agy"],
)
check("antigravity uses Neon xhigh", "gemini-4-neon-xhigh" in antigravity)
check(
    "antigravity uses plan and sandbox",
    "--mode" in antigravity and "plan" in antigravity and "--sandbox" in antigravity,
)
check("antigravity prompt follows -p", antigravity[1] == "-p" and antigravity[2] == "PROMPT")

opencode = council.command_for(
    "opencode", council.DEFAULT_DELEGATES["opencode"], "PROMPT", Path("out"), Path("repo"), ["opencode"]
)
check("opencode uses the DeepSeek model", "opencode-go/deepseek-v4.1-flash" in opencode)
check("opencode uses the plan agent", "--agent" in opencode and "plan" in opencode)
check("opencode prompt is last", opencode[-1] == "PROMPT")

check(
    "antigravity display command hides the prompt",
    council.redact_command(["agy", "-p", "PROMPT", "--output-format", "text"], "PROMPT")
    == ["agy", "-p", "<prompt>", "--output-format", "text"],
)
check(
    "codex display command hides the prompt",
    council.redact_command(["codex", "exec", "PROMPT"], "PROMPT") == ["codex", "exec", "<prompt>"],
)

check("delegate filter", council.parse_delegates("codex,opencode") == ["codex", "opencode"])
check(
    "duplicate delegates are removed",
    council.parse_delegates("codex,codex,opencode") == ["codex", "opencode"],
)
try:
    council.parse_delegates("nope")
except ValueError:
    check("unknown delegate rejected", True)
else:
    check("unknown delegate rejected", False)

with tempfile.TemporaryDirectory(prefix="council-test-") as tmp:
    tmp_path = Path(tmp)
    brief = tmp_path / "brief.md"
    diff = tmp_path / "diff.patch"
    out = tmp_path / "out"
    brief.write_text("Review this change.", encoding="utf-8")
    diff.write_text("diff --git a/x b/x\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--brief",
            str(brief),
            "--diff",
            str(diff),
            "--out",
            str(out),
            "--delegates",
            "codex",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    check("dry run exits 0 when the CLI is known or missing is allowed", result.returncode in (0, 2), result.returncode)
    check("dry run writes results", (out / "results.json").is_file())
    check("dry run writes the prompt", (out / "prompt.md").is_file())
    data = json.loads((out / "results.json").read_text(encoding="utf-8"))
    check("dry run reports codex", data["results"][0]["key"] == "codex")
    check("dry run does not call a provider", data["results"][0]["status"] in ("planned", "missing"))
    check("dry run records the reviewed head", "head" in data)

    bad_timeout = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--brief",
            str(brief),
            "--diff",
            str(diff),
            "--out",
            str(out / "timeout-check"),
            "--timeout",
            "0",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    check("non-positive timeout rejected", bad_timeout.returncode == 2, bad_timeout.returncode)

    head = council.git_head(REPO)
    if head:
        bad_head = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--brief",
                str(brief),
                "--diff",
                str(diff),
                "--out",
                str(out / "head-check"),
                "--cwd",
                str(REPO),
                "--head",
                "0" * 40,
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        check("head mismatch rejected", bad_head.returncode == 2, bad_head.returncode)
        check("head mismatch names the expected commit", "expected" in bad_head.stderr.lower())

with tempfile.TemporaryDirectory(prefix="council-stale-") as tmp:
    tmp_path = Path(tmp)
    out = tmp_path / "out"
    out.mkdir()
    stale = out / "codex.md"
    stale.write_text("stale answer from a previous round", encoding="utf-8")
    original_command_for = council.command_for
    council.command_for = lambda *args, **kwargs: [sys.executable, "-c", "import sys; sys.exit(1)"]
    try:
        failed = council.run_delegate(
            "codex",
            dict(council.DEFAULT_DELEGATES["codex"]),
            "PROMPT",
            out,
            tmp_path,
            30,
            False,
        )
    finally:
        council.command_for = original_command_for
    check("failed codex run is an error", failed["status"] == "error")
    check("failed codex run clears the stale answer", not stale.exists())
    check("failed codex run does not report the stale answer", failed["output"] != str(stale))

if council.git_head(REPO):
    with tempfile.TemporaryDirectory(prefix="council-worktree-") as tmp:
        repo = Path(tmp)
        git = lambda *args: subprocess.run(["git", *args], cwd=repo, capture_output=True, timeout=60, check=True)
        git("init", "-q")
        tracked = repo / "tracked.txt"
        tracked.write_text("one\n", encoding="utf-8")
        git("add", "tracked.txt")
        git("-c", "user.email=test@example.com", "-c", "user.name=Test", "commit", "-qm", "init")
        tracked.write_text("two\n", encoding="utf-8")
        before = council.worktree_snapshot(repo)
        tracked.write_text("three\n", encoding="utf-8")
        after = council.worktree_snapshot(repo)
        check(
            "worktree snapshot detects further edits to a dirty tracked file",
            before is not None and after is not None and before["fingerprint"] != after["fingerprint"],
        )
        (repo / "new.txt").write_text("new\n", encoding="utf-8")
        after_untracked = council.worktree_snapshot(repo)
        check(
            "worktree snapshot detects a new untracked file",
            after_untracked is not None and after_untracked["fingerprint"] != after["fingerprint"],
        )
        check(
            "worktree snapshot lists the new untracked file",
            after_untracked is not None and "new.txt" in after_untracked["paths"],
        )

print(f"\n{fails} failure(s)")
raise SystemExit(1 if fails else 0)
