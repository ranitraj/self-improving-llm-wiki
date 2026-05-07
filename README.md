# agentic-python-template

A Python project template for development with AI agents (Claude Code).

Batteries included: UV + direnv per-service venvs, strict linting, TDD enforcement,
Document Driven Design, and a one-shot setup wizard.

> **Maintainer note:** After pushing, go to **Settings → General → check "Template repository"**
> so the green "Use this template" button appears for visitors.

---

## What's included

| Layer | Tool / Convention |
|---|---|
| Dependency management | [uv](https://docs.astral.sh/uv/) — fast, per-service virtualenvs |
| Venv auto-activation | [direnv](https://direnv.net/) — `cd` into a service, venv activates automatically |
| Linting & formatting | ruff (E, F, I, B, UP, RUF rules) |
| Type checking | mypy strict mode |
| Code quality | pylint (min score 10, McCabe complexity) |
| Pre-commit hooks | All of the above + TDD enforcement + branch protection |
| CI | GitHub Actions — quality gate + per-service test matrix |
| Design workflow | Document Driven Design (DDD) with design & solution doc templates |
| AI conventions | `CLAUDE.md` — NumPy docstrings, RED/GREEN TDD, SOLID, code review pace |
| Setup wizard | `init.py` — interactive, replaces all placeholders, self-deletes |

---

## Prerequisites

```bash
brew install uv direnv python@3.12
```

Add direnv to your shell (once, globally):

```bash
# bash
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc

# zsh
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc
```

---

## Using this template

### 1. Create your project from this template

1. Go to **[github.com/ranitraj/agentic-python-template](https://github.com/ranitraj/agentic-python-template)**
2. Click the green **"Use this template"** button → **"Create a new repository"**
3. Name your new repo, set visibility, click **"Create repository"**

This creates a clean copy in your own GitHub account with no git history carried over.

Clone your new repo:

```bash
git clone https://github.com/<you>/<your-project>.git
cd <your-project>
```

### 2. Run the setup wizard

```bash
python3 init.py
```

See the [full wizard walkthrough](#wizard-walkthrough) for an example of every prompt and what to enter.

The wizard asks five categories of questions, replaces all `{{placeholders}}` across every file, creates your first service, makes the initial git commit, and deletes itself.

### 3. Install dependencies and git hooks

```bash
make init          # installs root dev deps + all service deps + git hooks
direnv allow .     # approve the root .envrc (loads .env)
```

### 4. Set up your first service

```bash
cd services/<your-service>
direnv allow .     # approve service .envrc — venv is created and activated automatically
```

From now on, `cd`-ing into a service directory activates its venv. No manual `source .venv/bin/activate`.

---

## Wizard walkthrough

A complete example run of `python3 init.py` for a simple calculator project:

```
Agentic Python Project Initialiser
======================================
Defaults shown in [brackets] — press Enter to accept.

Project identity
  Project name (kebab-case) [my-project]: my-calculator
  One-line description [A Python project]: A calculator service with an AI-agent interface
  Available Python versions: 3.12, 3.11, 3.10
  Python version [3.12]:                          ← press Enter to accept 3.12

First service
  Service name (kebab-case) [api]: calculator     ← creates services/calculator/

Code quality  (press Enter to accept defaults)
  Strict mypy? [Y/n]:                             ← press Enter = yes
  Min pylint score [10]:                          ← press Enter = 10
  Line length [119]:                              ← press Enter = 119
  Max function args [5]:                          ← press Enter = 5

Workflow
  Enforce TDD? (pre-commit blocks commit if test file missing) [Y/n]:
  Use DDD design docs + solution docs? [Y/n]:
  Protect main branch? (blocks direct commits to main) [Y/n]:

CI/CD
  Add GitHub Actions? [Y/n]:

── Summary ──────────────────────────────────────────────
  project      : my-calculator
  description  : A calculator service with an AI-agent interface
  python       : 3.12
  service      : calculator  (module: calculator)
  strict mypy  : True
  pylint score : 10   line length: 119   max args: 5
  enforce TDD  : True
  DDD docs     : True
  protect main : True
  GitHub CI    : True

  Looks good? Proceed? [Y/n]:                     ← press Enter to apply

Initialising...

  my-calculator is ready.

  Next steps:
    cd services/calculator && uv sync --group dev
    make precommit-install
    direnv allow .
```

**Tips:**
- All questions default to the recommended value — press Enter to accept.
- For `Service name`, use kebab-case (`calculator`, `wiki-agent`, `gateway`). The wizard derives the Python module name automatically (`wiki-agent` → `wiki_agent`).
- `init.py` runs once and deletes itself. To start over, re-clone from the template.

---

## Project structure

```
your-project/
├── CLAUDE.md                        # AI agent conventions (auto-read by Claude Code)
├── STRATEGY.md                      # Product direction — fill this in first
├── pyproject.toml                   # Shared ruff / mypy / pylint config
├── Makefile                         # make init | lint | clean | hooks-update
├── .pre-commit-config.yaml          # ruff, mypy, pylint, TDD, branch protection
├── .github/workflows/ci.yml         # Quality gate + per-service test matrix
├── .envrc                           # Root direnv — loads .env
│
├── services/
│   └── <your-service>/              # Created by init.py from _service-template/
│       ├── .envrc                   # layout uv — auto-creates .venv on cd
│       ├── pyproject.toml           # Service dependencies
│       └── src/<module>/
│
└── .claude/
    ├── designs/_template.md         # Design doc template (fill before coding)
    └── solutions/_template.md       # Solution doc template (fill after shipping)
```

---

## Development workflow

This template enforces a specific workflow. `CLAUDE.md` is the full reference — summary below.

### Before you code: Document Driven Design

1. Copy `.claude/designs/_template.md` → `.claude/designs/<feature>.md`
2. Fill in: purpose, public API, data flow, test scenarios, error cases, out of scope
3. Get sign-off, then implement

### While you code: RED / GREEN TDD

```
Write failing test  →  commit test (RED)
Write implementation  →  commit impl (GREEN, pre-commit checks test file exists)
Refactor  →  keep tests green
```

The `enforce-tdd` pre-commit hook blocks committing a `src/` file if no matching `tests/test_<module>.py` exists.

### After you ship: Solution docs

You don't do anything. The moment Claude marks a design doc `status: done`, it automatically
creates `.claude/solutions/<topic>.md` — filling in what was built, decisions made, and what to
watch for next time. You review, it saves.

---

## Adding a new service

```bash
cp -r _service-template services/<new-service>
# rename src/service_module → src/<new_module>
# update services/<new-service>/pyproject.toml name + packages
# add "<new-service>" to the matrix in .github/workflows/ci.yml
cd services/<new-service> && direnv allow .
```

---

## Troubleshooting: Claude Code not following the plan

### Claude is ignoring CLAUDE.md conventions

`CLAUDE.md` is auto-read by Claude Code at the start of every session from the repo root.
If Claude isn't following it:

1. **Verify location** — `CLAUDE.md` must be at the repo root, not inside a subdirectory.
2. **Start a new session** — `CLAUDE.md` is only loaded at session start. Open a fresh Claude Code
   conversation so it reloads.
3. **Re-anchor mid-session** — If Claude drifts during a long session, say:
   *"Re-read CLAUDE.md and confirm the conventions before continuing."*

### Claude is not reading the design doc automatically

`CLAUDE.md` instructs Claude to proactively scan `.claude/designs/` before every implementation
task. If it skips this:

1. **Long session context** — On very long sessions Claude may lose track of earlier instructions.
   Start a new session with `/clear` to reload `CLAUDE.md` from scratch.
2. **Re-anchor** — Say: *"Check CLAUDE.md's DDD rules and follow them before continuing."*

### Claude starts implementing without the 3 rounds of questions

Say: *"Stop. We haven't done the 3 rounds of follow-up questions yet. Start from round 1."*

### Nothing works — Claude has lost context

`/clear` in the Claude Code chat resets the conversation and forces a clean re-read of `CLAUDE.md`.

---

## Useful commands

```bash
make init              # full bootstrap (install + git hooks)
make lint              # run all pre-commit hooks on every file
make hooks-update      # update pre-commit hooks to latest versions
make clean             # remove __pycache__, .mypy_cache, .ruff_cache, .pytest_cache
```
