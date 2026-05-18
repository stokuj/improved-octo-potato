from pathlib import Path


class WatcherState:
    def __init__(self, path: Path):
        self.path = path
        self.offset = self._load()

    def _load(self) -> int:
        if not self.path.exists():
            return 0
        try:
            return int(self.path.read_text().strip())
        except (ValueError, OSError):
            return 0

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(str(self.offset))
