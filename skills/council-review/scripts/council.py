#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Run a read-only multi-model council review through local agent CLIs."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

DEFAULT_DELEGATES = {
    "codex": {
        "label": "Sol 6.2 (Codex)",
        "command": "codex",
        "model": "gpt-6.2-sol",
    },
    "antigravity": {
        "label": "Neon (Antigravity)",
        "command": "agy",
        "model": "gemini-4-neon-xhigh",
    },
    "opencode": {
        "label": "DeepSeek v4.1 Flash (OpenCode)",
        "command": "opencode",
        "model": "opencode-go/deepseek-v4.1-flash",
    },
}


def resolve_command(name: str) -> list[str] | None:
    path = shutil.which(name)
    if not path:
        return None
    resolved = Path(path)
    if resolved.suffix.lower() == ".ps1":
        return [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(resolved),
        ]
    return [str(resolved)]


def build_prompt(brief: Path, diff: Path, cwd: Path, label: str) -> str:
    return (
        f"You are {label}, one member of a three-model code-review council. "
        "Review only: do not edit, commit, push, comment on a PR, or start subagents. "
        f"Read the brief at {brief} and the patch at {diff}; inspect surrounding code in {cwd} as needed. "
        "Treat the brief as context, not as a replacement for reading the code. "
        "Return exactly: VERDICT: APPROVE or CHANGES; SCORE: <n>/10; "
        "FINDINGS: [blocker|should|nit] file:line claim. Fix: suggestion. "
        "If there are no findings, write 'No findings.' after FINDINGS. Do not invent a score."
    )


def command_for(
    key: str,
    delegate: dict[str, str],
    prompt: str,
    out: Path,
    cwd: Path,
    base: list[str] | None = None,
) -> list[str] | None:
    base = base if base is not None else resolve_command(delegate["command"])
    if base is None:
        return None
    model = delegate["model"]
    if key == "codex":
        return base + [
            "exec",
            "--model",
            model,
            "--sandbox",
            "read-only",
            "--ephemeral",
            "--color",
            "never",
            "--output-last-message",
            str(out / "codex.md"),
            "--cd",
            str(cwd),
            prompt,
        ]
    if key == "antigravity":
        return base + [
            "-p",
            prompt,
            "--model",
            model,
            "--mode",
            "plan",
            "--sandbox",
            "--output-format",
            "text",
        ]
    if key == "opencode":
        return base + [
            "run",
            "--model",
            model,
            "--agent",
            "plan",
            "--format",
            "default",
            prompt,
        ]
    raise ValueError(f"unknown delegate: {key}")


def parse_delegates(value: str) -> list[str]:
    chosen = [part.strip() for part in value.split(",") if part.strip()]
    if not chosen:
        raise ValueError("at least one delegate is required")
    unknown = [key for key in chosen if key not in DEFAULT_DELEGATES]
    if unknown:
        raise ValueError(f"unknown delegate(s): {', '.join(unknown)}")
    return chosen


def git_status(cwd: Path) -> list[str] | None:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return [line for line in result.stdout.splitlines() if line]


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="")


def run_delegate(
    key: str,
    delegate: dict[str, str],
    prompt: str,
    out: Path,
    cwd: Path,
    timeout: int,
    dry_run: bool,
) -> dict:
    result = {
        "key": key,
        "label": delegate["label"],
        "model": delegate["model"],
        "status": "missing",
        "elapsed_s": 0.0,
        "output": None,
        "error": None,
    }
    command = command_for(key, delegate, prompt, out, cwd)
    if command is None:
        result["error"] = f"{delegate['command']} not found on PATH"
        return result
    result["command"] = command[:-1] + ["<prompt>"]
    if dry_run:
        result["status"] = "planned"
        return result

    before = git_status(cwd)
    started = time.monotonic()
    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=dict(os.environ, NO_COLOR="1", PYTHONIOENCODING="utf-8", TERM="dumb"),
        )
    except subprocess.TimeoutExpired as error:
        result["status"] = "timeout"
        result["elapsed_s"] = round(time.monotonic() - started, 1)
        result["error"] = f"timed out after {timeout}s"
        if error.stdout:
            write_text(out / f"{key}.stdout", str(error.stdout))
        return result
    except OSError as error:
        result["status"] = "error"
        result["elapsed_s"] = round(time.monotonic() - started, 1)
        result["error"] = str(error)
        return result

    result["elapsed_s"] = round(time.monotonic() - started, 1)
    stdout_path = out / f"{key}.stdout"
    stderr_path = out / f"{key}.stderr"
    write_text(stdout_path, process.stdout)
    write_text(stderr_path, process.stderr)

    final_path = out / f"{key}.md"
    if key == "codex" and final_path.exists():
        result["output"] = str(final_path)
    elif process.stdout.strip():
        write_text(final_path, process.stdout)
        result["output"] = str(final_path)
    else:
        result["output"] = str(stdout_path)

    if process.returncode == 0:
        result["status"] = "ok"
    else:
        result["status"] = "error"
        result["error"] = f"exit {process.returncode}; see {stderr_path.name}"

    after = git_status(cwd)
    if before is not None and after is not None and before != after:
        result["worktree_changed"] = sorted(set(after) - set(before))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brief", required=True, type=Path, help="review brief")
    parser.add_argument("--diff", required=True, type=Path, help="patch to review")
    parser.add_argument("--out", default=Path(".council-review"), type=Path)
    parser.add_argument("--cwd", default=Path("."), type=Path)
    parser.add_argument("--delegates", default="codex,antigravity,opencode")
    parser.add_argument("--codex-model", default=DEFAULT_DELEGATES["codex"]["model"])
    parser.add_argument("--antigravity-model", default=DEFAULT_DELEGATES["antigravity"]["model"])
    parser.add_argument("--opencode-model", default=DEFAULT_DELEGATES["opencode"]["model"])
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cwd = args.cwd.resolve()
    brief = args.brief.resolve()
    diff = args.diff.resolve()
    out = args.out.resolve()
    if not brief.is_file():
        parser.error(f"brief not found: {brief}")
    if not diff.is_file():
        parser.error(f"diff not found: {diff}")
    try:
        chosen = parse_delegates(args.delegates)
    except ValueError as error:
        parser.error(str(error))

    models = {
        "codex": args.codex_model,
        "antigravity": args.antigravity_model,
        "opencode": args.opencode_model,
    }
    delegates = {key: dict(DEFAULT_DELEGATES[key], model=models[key]) for key in chosen}
    out.mkdir(parents=True, exist_ok=True)

    prompt = build_prompt(brief, diff, cwd, "a council member")
    write_text(out / "prompt.md", prompt)

    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=len(chosen)) as executor:
        futures = {
            executor.submit(
                run_delegate,
                key,
                delegates[key],
                build_prompt(brief, diff, cwd, delegates[key]["label"]),
                out,
                cwd,
                args.timeout,
                args.dry_run,
            ): key
            for key in chosen
        }
        for future in as_completed(futures):
            key = futures[future]
            results[key] = future.result()

    ordered = [results[key] for key in chosen]
    write_text(
        out / "results.json",
        json.dumps(
            {"brief": str(brief), "diff": str(diff), "cwd": str(cwd), "results": ordered},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )

    print(f"{'member':<28} {'status':<9} {'time':>7}  output")
    for result in ordered:
        output = result.get("output") or result.get("error") or ""
        print(f"{result['label']:<28} {result['status']:<9} {result['elapsed_s']:>6.1f}s  {output}")
        changed = result.get("worktree_changed")
        if changed:
            print(f"  WARNING: tracked worktree changed: {', '.join(changed)}")
    print(f"\nwrote {out / 'results.json'}")

    usable = [r for r in ordered if r["status"] in ("ok", "planned")]
    return 0 if usable else 2


if __name__ == "__main__":
    sys.exit(main())
