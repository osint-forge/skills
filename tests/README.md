# Tests

Tests are development-only and are not installed with a skill. They live outside
`skills/` so `npx skills add` copies only the runtime files for a skill.

- Per-skill tests go in `tests/<skill>/`, named after the skill directory.
- Repository-wide checks live in `tests/test_skill_meta.py`.
- Test files are named `test_*.py`; `tests/run_all.py` discovers them.
- Do not add a `SKILL.md` under `tests/`; `npx skills` discovers skills by that file.

Run everything:

```bash
uv run tests/run_all.py
```

Run one skill:

```bash
uv run tests/run_all.py --filter mk-tech-shop-search
```

The CI test workflow runs the same command on Ubuntu and Windows. Linting is a
separate workflow. To check that the repository still exposes its skills to the CLI:

```bash
npx --yes skills@latest add . --list --yes
```

That should list each skill and must not list anything under `tests/`.
