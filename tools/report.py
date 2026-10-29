"""Console report that can also be saved as an evidence file."""

from datetime import datetime
from pathlib import Path

import tools_config as cfg


class Report:
    """Print every line to the console and keep it, so the file matches the console exactly.

    The first line is the date and time of the run, which dates the evidence file.
    """

    def __init__(self, title: str) -> None:
        """Start the report with its title and the current date and time."""
        self._lines: list[str] = []
        self.line(f"{title} - {datetime.now().strftime(cfg.TIMESTAMP_FORMAT)}")

    def line(self, text: str) -> None:
        """Print one line and keep it for the file."""
        print(text, flush=True)
        self._lines.append(text)

    def save(self, path: Path) -> None:
        """Write all lines to `path`, creating its folder if needed."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(self._lines) + "\n", encoding="utf-8")
        print(f"Report saved to {path}", flush=True)
