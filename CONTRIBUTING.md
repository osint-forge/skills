# Contributing

This repository is a collection of agent skills for North Macedonia, focused on
developer tooling for the Macedonian developer community, alongside local services
and shopping. A skill must be useful on its own and live entirely under
`skills/<name>/`.

## Adding a skill

1. Create `skills/<name>/SKILL.md` with the frontmatter below. The directory name and
   the frontmatter `name` must match.
2. Add `skills/<name>/README.md` for humans: install, requirements, network hosts and
   files the skill writes.
3. Put details that are only needed sometimes in `references/`, runnable helpers in
   `scripts/`, and templates or fixtures in `assets/`.
4. Add offline tests under `tests/<name>/`. The root runner discovers them
   automatically.
5. Add a row for the skill to the table in the root `README.md`.
6. Run `uv run tests/run_all.py` and open a PR.

Minimal layout:

```text
skills/<name>/
  SKILL.md          required, agent-facing
  README.md         recommended, human-facing
  references/       optional, loaded on demand
  scripts/          optional, called by the agent
  assets/           optional, templates and fixtures
tests/<name>/
  test_*.py         optional, offline and self-contained
```

## Frontmatter

```markdown
---
name: my-skill
description: What it does and when an agent should use it. Name the triggers and the boundary in one line, under 1024 characters.
license: MIT
compatibility: Python 3.13+ with requests; outbound HTTPS to api.example.mk
---
```

- `name`: 1-64 lowercase letters, digits and single hyphens; it must equal the
  directory name.
- `description`: one line, no angle brackets, no unescaped colon followed by a space. Say what the skill
  does and when to use it; this is what an agent sees before loading the skill.
- `license`: must match the repository's `LICENSE` when present.
- `compatibility`: optional, under 500 characters. State the runtime, dependencies and
  network hosts an agent needs.
- `SKILL.md` must stay under 500 lines. Move shop-specific, API-specific or long
  reference material into `references/` and point to it from `SKILL.md`.

## Writing the skill

- **Lead with the decision.** The first lines should tell an agent what to do, not
  history or background.
- **Use progressive disclosure.** Keep `SKILL.md` to the workflow and the rules that
  apply every time. Put endpoint details, data traps and troubleshooting in
  `references/<topic>.md`.
- **Write for an agent, not a search engine.** Short sections, imperative rules and
  concrete commands. Avoid marketing language.
- **Keep it self-contained.** A skill may use its own scripts, references and assets;
  do not import another skill's files at runtime.
- **Treat fetched text as data.** Product titles, seller names, issue text and web
  pages are third-party content. Quote them as facts, never follow instructions in
  them, and escape them before inserting into HTML.
- **Date volatile facts.** Prices, delivery terms, APIs and version numbers drift.
  Say when a fact was checked, and separate what the data states from your judgement.
- **Prefer an official API or CLI** over scraping where one exists. Document the
  hosts, auth and rate limits, and do not try to bypass a CAPTCHA, WAF or login wall.
- **No secrets.** Do not commit tokens, keys, cookies, private endpoints or customer
  data. Skills must work with credentials supplied by the user at runtime.

## Tests

Tests are offline and deterministic. Do not call a live service from CI; use recorded
fixtures or fake clients under `tests/<name>/`.

- Name test files `test_*.py`; the runner finds every test below `tests/`.
- Keep each suite standalone: it should run with `python -B tests/<name>/test_*.py`
  from the repository root.
- Add the PEP 723 header when the suite can be run with `uv run`, and list its
  dependencies there.
- Test on Windows path handling as well as Linux: use `pathlib` or `os.path`, not
  hard-coded `/` paths.
- Cover the failure states, not only the happy path: blocked, timeout, partial
  results, an empty shop and invalid input.
- A skill-specific validator belongs in `tests/<name>/`; repository-wide checks
  belong in `tests/test_skill_meta.py`.

## Linting

- **Python:** `uvx ruff@latest check .` uses [`ruff.toml`](ruff.toml). CI runs the latest
  Ruff release; the config targets Python 3.13 and currently checks pyflakes, syntax
  and bare-except errors. Add rules only with a plan to fix the existing findings.
- **Markdown:** `npx --yes markdownlint-cli2@0.24.2 "**/*.md"` uses
  [`.markdownlint.json`](.markdownlint.json). Line length and inline HTML are
  allowed because the skill references deliberately use tables and XML tags.
- **HTML:** `npx --yes html-validate@10.4.0 "**/*.html"`.
- **Workflows:** `docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:1.7.12`
  from the repository root, or rely on the CI lint job.

## Before opening a PR

- `uv run tests/run_all.py` passes.
- `uvx ruff@latest check .` and the Markdown and HTML linters pass.
- Actionlint passes if `.github/workflows/` changed.
- The new skill appears in the root README.
- `SKILL.md` and `README.md` agree on install, requirements and network hosts.
- No secrets, tokens, customer data or generated caches are included.
- Any live verification is described in the PR, with the date and the commands used.

Contributions are licensed under the repository's MIT license.
