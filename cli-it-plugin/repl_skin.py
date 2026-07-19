"""Shared REPL skin for CLI-It harnesses.

Every harness copies this file verbatim into ``cli_it/<software>/utils/`` so
all CLI-It REPLs look and behave the same. ``prompt_toolkit`` is a soft
dependency — when absent the skin falls back to plain ``input()``.
"""

from __future__ import annotations

from pathlib import Path


class ReplSkin:
    """Consistent banner, prompt, and message styling for harness REPLs."""

    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version

    # --- skill discovery -----------------------------------------------------

    def skill_path(self) -> Path | None:
        """Prefer the repo-root canonical skill; fall back to the packaged copy."""
        module_dir = Path(__file__).resolve().parent.parent  # cli_it/<software>/
        for parent in module_dir.parents:
            candidate = parent / "skills" / f"cli-it-{self.name}" / "SKILL.md"
            if candidate.is_file():
                return candidate
        packaged = module_dir / "skills" / "SKILL.md"
        return packaged if packaged.is_file() else None

    # --- banner / prompt -----------------------------------------------------

    def print_banner(self) -> None:
        title = f"CLI-It · {self.name} v{self.version}"
        bar = "─" * max(len(title) + 2, 40)
        print(f"┌{bar}┐")
        print(f"│ {title.ljust(len(bar) - 2)} │")
        print(f"└{bar}┘")
        skill = self.skill_path()
        if skill is not None:
            print(f"  agents: read {skill}")
        print("  type 'help' for commands, 'exit' to quit\n")

    def create_prompt_session(self):
        """Return a callable prompt(text) -> str, nicest available."""
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.history import InMemoryHistory

            session = PromptSession(history=InMemoryHistory())
            return lambda text: session.prompt(text)
        except ImportError:
            return input

    # --- message styling ------------------------------------------------------

    def success(self, message: str) -> None:
        print(f"✓ {message}")

    def error(self, message: str) -> None:
        print(f"✗ {message}")

    def warning(self, message: str) -> None:
        print(f"! {message}")

    def info(self, message: str) -> None:
        print(f"· {message}")

    def status(self, key: str, value: str) -> None:
        print(f"  {key:<16} {value}")

    def table(self, headers: list[str], rows: list[list[str]]) -> None:
        widths = [
            max(len(str(headers[i])), *(len(str(r[i])) for r in rows), 1)
            if rows
            else len(str(headers[i]))
            for i in range(len(headers))
        ]
        line = "  ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers))
        print(line)
        print("  ".join("-" * w for w in widths))
        for row in rows:
            print("  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))

    def help(self, commands: dict[str, str]) -> None:
        self.table(["command", "description"], [[c, d] for c, d in commands.items()])

    def progress(self, message: str, done: int, total: int) -> None:
        total = max(total, 1)
        filled = int(20 * done / total)
        bar = "█" * filled + "░" * (20 - filled)
        print(f"  [{bar}] {done}/{total} {message}")

    def print_goodbye(self) -> None:
        print(f"\nbye — {self.name} session ended.")
