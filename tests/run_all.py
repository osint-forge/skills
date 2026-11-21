#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["requests>=2.28", "beautifulsoup4>=4.11"]
# ///
"""Run the repository's offline test suites. Each skill owns its suites under
tests/<skill>/; repo-wide checks live in tests/test_skill_meta.py.

Run: python3 -B tests/run_all.py [--list] [--filter SUBSTRING]"""
import argparse
import glob
import os
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def suites():
    paths = glob.glob(os.path.join(ROOT, "tests", "**", "test_*.py"), recursive=True)
    paths += glob.glob(os.path.join(ROOT, "test_*.py"))
    return sorted(p for p in paths if os.path.isfile(p))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="list suites and exit")
    parser.add_argument("--filter", metavar="SUBSTRING", help="only run paths containing this text")
    a = parser.parse_args()
    chosen = [p for p in suites() if not a.filter or a.filter in os.path.relpath(p, ROOT)]
    if a.list:
        for path in chosen:
            print(os.path.relpath(path, ROOT))
        return 0 if chosen else 1
    if not chosen:
        print("no test suites found", file=sys.stderr)
        return 1

    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    failed = []
    for path in chosen:
        rel = os.path.relpath(path, ROOT)
        print(f"\n=== {rel} ===", flush=True)
        t0 = time.time()
        rc = subprocess.run([sys.executable, "-B", path], cwd=ROOT, env=env).returncode
        print(f"=== {rel}: {'ok' if rc == 0 else 'FAIL'} ({time.time() - t0:.1f}s) ===", flush=True)
        if rc != 0:
            failed.append(rel)

    print(f"\n{len(chosen) - len(failed)}/{len(chosen)} suites passed")
    if failed:
        print("failed: " + ", ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
