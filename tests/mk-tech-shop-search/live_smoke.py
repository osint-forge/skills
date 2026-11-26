#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = ["requests>=2.28", "beautifulsoup4>=4.11"]
# ///
"""Live smoke check: search every shop once and fail when a shop stops answering or
its records lose their core fields. It calls the real shops, so it is not a test_*.py
file and tests/run_all.py never runs it; the scheduled live-smoke workflow does.

Run: uv run tests/mk-tech-shop-search/live_smoke.py [--query logitech]"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MKSHOP = os.path.join(ROOT, "skills", "mk-tech-shop-search", "scripts", "mkshop.py")
# Share of records that must carry each field; a shop far below it has probably changed
# its API or page structure. Price is looser: some shops list "ask for price" items.
CORE = {"title": 0.95, "url": 0.95, "price_mkd": 0.5}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default="logitech", help="a brand every shop carries")
    ap.add_argument("--min-filled", type=float, help="override every field's required share (0-1)")
    a = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "smoke.json")
        proc = subprocess.run(
            [sys.executable, MKSHOP, "search", a.query, "--no-table", "--json", out],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        )
        if not os.path.exists(out):
            print(proc.stdout)
            print(f"FAIL mkshop.py exited {proc.returncode} without writing results")
            return 1
        with open(out, encoding="utf-8") as f:
            env = json.load(f)

    failures = []
    for key, st in env["stores"].items():
        recs = [r for r in env["results"] if r.get("store") == key]
        problems = []
        if st["status"] != "ok":
            problems.append(f"status {st['status']}: {st.get('message')}")
        elif not recs:
            problems.append(f"no results for {a.query!r}")
        for field, share in CORE.items():
            filled = sum(1 for r in recs if r.get(field) not in (None, ""))
            if recs and filled / len(recs) < (share if a.min_filled is None else a.min_filled):
                problems.append(f"{field} filled in {filled}/{len(recs)}")
        line = "; ".join(problems) or f"{len(recs)} results"
        print(("FAIL " if problems else "ok   ") + f"{key:<12} {line}")
        if problems:
            failures.append(key)

    print(f"\n{len(failures)} shop(s) failing" + (f": {', '.join(failures)}" if failures else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
