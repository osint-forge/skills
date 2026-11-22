# Macedonian skills

A collection of agent skills for North Macedonia, built for the Macedonian developer
community: developer tooling, local services, and shopping. Each skill is self-contained
under `skills/<name>/` and follows the [Agent Skills](https://agentskills.io/specification)
format, so it works in any agent that supports skills.

## Skills

| Skill | What it does |
|---|---|
| [`mk-tech-shop-search`](skills/mk-tech-shop-search/) | Search, compare and price-check products across 11 Macedonian online shops: Setec, Neptun, Tehnomarket, Anhoch, Neksio, DDStore, Hivetec, Gjirafa50, ZirafaMall, Setra and the Ananas marketplace. |

More developer-tooling skills are planned. The repository layout and test tooling are
ready for them; see [CONTRIBUTING.md](CONTRIBUTING.md).

## Install

List the skills in this repository:

```bash
npx skills add osint-forge/skills --list
```

Install one skill:

```bash
npx skills add osint-forge/skills --skill mk-tech-shop-search
```

Install everything:

```bash
npx skills add osint-forge/skills --all
```

Or copy or symlink `skills/<name>/` into your agent's skills folder, for example
`~/.claude/skills/<name>`.

Each skill lists its own requirements, network hosts and files in its README.

## Repository layout

```text
skills/<name>/SKILL.md          agent-facing instructions and triggers
skills/<name>/README.md         human-facing install, requirements and notes
skills/<name>/references/       per-topic details loaded on demand
skills/<name>/scripts/          optional tools the skill runs
skills/<name>/assets/           optional templates and fixtures
tests/test_skill_meta.py        repo-wide checks for every skill
tests/run_all.py                discovers and runs every suite
tests/<name>/                   offline tests owned by one skill
```

## Development

Run the whole offline suite:

```bash
uv run tests/run_all.py
```

List or filter suites:

```bash
uv run tests/run_all.py --list
uv run tests/run_all.py --filter mk-tech-shop-search
```

Lint the repository:

```bash
uvx ruff@latest check .
npx --yes markdownlint-cli2@latest "**/*.md"
npx --yes html-validate@latest "**/*.html"
docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:latest
```

CI runs the suite on Ubuntu and Windows with Python 3.13,
plus Ruff, markdownlint, html-validate and actionlint. No test needs network access;
live shop checks are manual.

See [CONTRIBUTING.md](CONTRIBUTING.md) before adding a skill.

## License

MIT, see [LICENSE](LICENSE).
