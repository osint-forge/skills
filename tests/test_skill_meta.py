#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# ///
"""Repository-wide checks for every skill under skills/: portable frontmatter, naming,
documentation limits, local links, a catalogue row in the root README, and hidden text.
Run: python3 -B tests/test_skill_meta.py"""
import glob
import os
import re
import sys
import unicodedata

sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
FAILS = 0


def check(name, cond, info=""):
    global FAILS
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  [{info}]"))
    if not cond:
        FAILS += 1


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def local_paths(text, folder):
    pattern = r"(?<![\w/<>])(" + re.escape(folder) + r"/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\.[A-Za-z0-9]+)"
    return sorted(set(re.findall(pattern, text)))


def main():
    readme = read(os.path.join(ROOT, "README.md"))
    names = sorted(
        d for d in os.listdir(SKILLS) if os.path.isdir(os.path.join(SKILLS, d))
    )
    check("skills/ contains at least one skill", bool(names), names)

    for name in names:
        skill_dir = os.path.join(SKILLS, name)
        skill_md_path = os.path.join(skill_dir, "SKILL.md")
        if not os.path.isfile(skill_md_path):
            check(f"{name}: SKILL.md exists", False)
            continue
        skill_md = read(skill_md_path)
        fm = re.match(r"---\r?\n(.*?)\r?\n---\r?\n", skill_md, re.S)
        check(f"{name}: SKILL.md starts with a frontmatter block", fm is not None)
        fields = dict(re.findall(r"^([a-z][a-z-]*): ?(.*)$", fm.group(1), re.M)) if fm else {}
        check(
            f"{name}: frontmatter keys are portable",
            set(fields) <= {"name", "description", "license", "compatibility", "metadata", "allowed-tools"},
            set(fields),
        )
        fm_name = fields.get("name", "")
        desc = fields.get("description", "")
        check(f"{name}: name matches the directory", fm_name == name, fm_name)
        check(
            f"{name}: name is 1-64 lowercase letters, digits and single hyphens",
            re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", fm_name) is not None and len(fm_name) <= 64,
            fm_name,
        )
        check(f"{name}: description is 1-1024 characters", 0 < len(desc) <= 1024, len(desc))
        check(
            f"{name}: description has no angle brackets and no unquoted ': '",
            not re.search(r"[<>]", desc) and (": " not in desc or desc[:1] in "\"'"),
            desc[:80],
        )
        check(f"{name}: SKILL.md stays under 500 lines", skill_md.count("\n") < 500, skill_md.count("\n"))
        check(
            f"{name}: compatibility, when present, is 1-500 characters",
            "compatibility" not in fields or 0 < len(fields["compatibility"]) <= 500,
            len(fields.get("compatibility", "")),
        )
        if "license" in fields:
            lic = os.path.join(ROOT, "LICENSE")
            check(
                f"{name}: frontmatter license matches the repo LICENSE",
                os.path.exists(lic) and read(lic).split()[0] == fields["license"],
                fields["license"],
            )
        catalog_row = re.search(
            r"^\s*\|\s*\[`?" + re.escape(name) + r"`?\]\(skills/" + re.escape(name) + r"/?\)",
            readme,
            re.M,
        )
        check(f"{name}: root README has a catalogue row", catalog_row is not None, name)

        docs = [skill_md]
        skill_readme = os.path.join(skill_dir, "README.md")
        if os.path.isfile(skill_readme):
            docs.append(read(skill_readme))
        for doc in docs:
            for folder in ("references", "assets", "scripts"):
                for rel in local_paths(doc, folder):
                    check(
                        f"{name}: {rel} exists",
                        os.path.exists(os.path.join(skill_dir, rel)),
                        rel,
                    )

    tests_dir = os.path.join(ROOT, "tests")
    test_skills = sorted(
        d
        for d in os.listdir(tests_dir)
        if os.path.isdir(os.path.join(tests_dir, d)) and d != "__pycache__"
    )
    for name in test_skills:
        check(f"tests/{name} has a matching skill", name in names, name)
    check(
        "tests/ contains no SKILL.md",
        not glob.glob(os.path.join(tests_dir, "**", "SKILL.md"), recursive=True),
    )

    # Hidden text: instructions, code and tests, but not fixture data.
    srcs = []
    for root, _, files in os.walk(SKILLS):
        for f in files:
            if f.endswith((".md", ".py", ".html", ".js", ".ts", ".css")):
                srcs.append(os.path.join(root, f))
    for pattern in ("tests/**/*.py", "tests/**/*.md"):
        srcs += glob.glob(os.path.join(ROOT, pattern), recursive=True)
    srcs += [os.path.join(ROOT, "README.md"), os.path.join(ROOT, "CONTRIBUTING.md")]
    hidden = []
    for path in sorted(set(srcs)):
        if not os.path.isfile(path):
            continue
        for line_no, line in enumerate(read(path).splitlines(), 1):
            if any(
                unicodedata.category(c) == "Cf"
                or 0xFE00 <= ord(c) <= 0xFE0F
                or 0xE0100 <= ord(c) <= 0xE01EF
                for c in line
            ):
                hidden.append(f"{os.path.relpath(path, ROOT)}:{line_no}")
    check("no invisible or bidi characters in skills, docs or tests", not hidden, hidden[:10])

    print(f"\n{FAILS} failure(s)")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
