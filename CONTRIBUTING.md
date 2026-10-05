# Contributing to JARVIS-PiPER

Thank you for your interest in contributing to **JARVIS-PiPER**! We welcome bug reports, feature requests, documentation improvements, and pull requests.

## Development Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/your-username/jarvis-piper.git
   cd jarvis-piper
   ```
2. Set up the development environment:
   ```bash
   ./scripts/setup.sh --mode mock
   pip install -e ".[dev]"
   ```
3. Run test suites before submitting PR:
   ```bash
   pytest tests/
   ```

## Code Standards
- **Formatting**: We use `ruff` and `black`.
- **Type Hints**: Please provide type hints for public functions and classes.
- **Testing**: Add unit tests for any new features or bug fixes in `tests/`.
- **Commits**: Follow conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`).

## Pull Request Process
1. Create a feature branch: `git checkout -b feat/my-new-feature`
2. Commit your changes: `git commit -am 'feat: add support for custom camera'`
3. Push to your branch: `git push origin feat/my-new-feature`
4. Submit a Pull Request targeting the `main` branch.
