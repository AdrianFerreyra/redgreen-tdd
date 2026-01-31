# redgreen-tdd

A session timer for Test-Driven Development that helps you stay disciplined with short, focused red-green-refactor cycles.

TDD practitioners need external structure to maintain discipline around timeboxed cycles. Generic timers lack context and create friction. redgreen-tdd lives in your terminal, is purpose-built for TDD cadence, and requires zero context-switching from your editor.

## Features (MVP)

### Start a Timed Session

```bash
redgreen start 10
# Session started: 10 minutes
```

Start a TDD session for a specified number of minutes (1-60). Only one session can be active at a time.

### Check Remaining Time

```bash
redgreen status
# 7:34 remaining
```

Displays remaining time in `MM:SS` format. Shows "(paused)" when applicable. Returns exit code 0 if a session is active, 1 if not.

### Pause and Resume

```bash
redgreen pause
# Session paused at 7:34 remaining

redgreen resume
# Session resumed: 7:34 remaining
```

Handle interruptions without abandoning your session. Multiple pauses are allowed within a single session.

### Restart the Timer

```bash
redgreen restart
# Session restarted: 10 minutes
```

Reset the clock to the original session duration. Works whether the session is running or paused.

## Installation

### Homebrew (macOS)

```bash
brew tap luisadrianferreyra/redgreen
brew install redgreen
```

### From Source

Requires Python 3.9 or later:

```bash
git clone https://github.com/luisadrianferreyra/redgreen-tdd.git
cd redgreen-tdd
pip install -e .
```

### Verify Installation

```bash
redgreen --version
```

## Target Users

**TDD practitioners** who start sessions with good intentions but lose track of time, spend 45 minutes on one test, or skip the refactor phase entirely because there's no external accountability. If you currently use kitchen timers, phone alarms, or Pomodoro apps for your TDD cycles, this tool is for you.

**Developers learning TDD** who need training wheels to internalize the rhythm of red-green-refactor cycles (typically 5-15 minutes each).

## Architecture

redgreen-tdd uses a layered architecture that separates the timer state machine from user interfaces. The `core` module provides pure Python timer logic with zero UI dependencies, allowing the same session management code to power both the CLI and the planned menu bar app. Each interface layer imports from `redgreen.core`, never the reverse.

```
+-------------------------------------+
|  Interface Layer (CLI / Menu Bar)   |   User-facing, replaceable
+-----------------+-------------------+
|  Session Manager                    |   Business logic orchestration
+-----------------+-------------------+
|  Timer Core                         |   Pure state machine
+-------------------------------------+
```

### Project Structure

```
redgreen-tdd/
├── src/
│   └── redgreen/
│       ├── core/            # Pure business logic, no UI dependencies
│       │   ├── timer.py     # State machine: IDLE -> RUNNING -> PAUSED -> EXPIRED
│       │   └── session.py   # Session manager, persistence, state file
│       ├── cli/             # CLI interface (Click)
│       │   └── main.py      # Commands: start, status, pause, resume, restart
│       └── menubar/         # Future: macOS menu bar app (rumps)
│           └── app.py
├── tests/
│   ├── test_timer.py
│   ├── test_session.py
│   └── test_cli.py
└── pyproject.toml
```

### Technical Decisions

- **Timer implementation**: Uses `time.monotonic()` elapsed-time calculation, not wall clock. Immune to system clock changes and sleep/wake cycles.
- **State persistence**: JSON file in `~/.config/redgreen/session.json` so `redgreen status` works across terminal sessions. File locking via `fcntl.flock` prevents race conditions.
- **Process model**: CLI is ephemeral (each command spawns, runs, exits). The future menu bar app will be long-running. Both read/write the same session state file.
- **CLI framework**: Click for its simplicity and wide adoption.
- **Future menu bar**: rumps (Ridiculously Uncomplicated macOS Python Statusbar apps), with PyObjC as an option if advanced features are needed later.

## Roadmap

### Current: CLI Tool (v0.1)

Four commands, no fluff. Validate whether TDD developers want a purpose-built timer.

### Next: Menu Bar App

- Persistent visual indicator in macOS menu bar (icon color changes with state)
- Dropdown controls (start/pause/restart without opening a terminal)
- Desktop notifications when sessions complete
- Session history tracking

### Later

- TDD phase labeling (red/green/refactor) to surface workflow patterns
- Editor integrations
- Session analytics

### Non-Goals for MVP

- No GUI or menu bar app (CLI only for now)
- No session history or analytics
- No integrations (Git hooks, editor plugins)
- No notifications or sounds
- No phase tracking within sessions
- No configuration file
- No cross-platform support (macOS only)

## Development

**Prerequisites:** macOS, Python 3.9+, Git

**Setup:**

```bash
git clone https://github.com/luisadrianferreyra/redgreen-tdd.git
cd redgreen-tdd
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**Development workflow:**

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov

# Lint and format
ruff check src tests
ruff format src tests

# Type check
mypy src

# Run all checks (what CI runs)
ruff check src tests && ruff format --check src tests && mypy src && pytest
```

**Making changes:**

1. Create a branch: `git checkout -b feature/your-feature-name`
2. Write tests first (this is a TDD tool, after all)
3. Make your changes
4. Ensure all checks pass
5. Commit using conventional messages (e.g., `feat: add pause command`)
6. Open a Pull Request

## Contributing

We welcome contributions. redgreen-tdd is open source and we appreciate bug reports, feature requests, and pull requests.

- Report bugs or request features via [GitHub Issues](https://github.com/luisadrianferreyra/redgreen-tdd/issues)
- Read our [Contributing Guidelines](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md)
- All contributions must pass linting, type checking, and tests before merging

## License

[MIT](LICENSE)
