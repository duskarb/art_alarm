import json
from pathlib import Path
from typing import Iterable


class SeenStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._ids: set[str] = set()
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self._ids = set(data.get("seen", []))
            except Exception:
                self._ids = set()

    def is_seen(self, opp_id: str) -> bool:
        return opp_id in self._ids

    def mark(self, opp_ids: Iterable[str]) -> None:
        for i in opp_ids:
            self._ids.add(i)

    def save(self) -> None:
        ids = sorted(self._ids)
        if len(ids) > 5000:
            ids = ids[-5000:]
        self.path.write_text(
            json.dumps({"seen": ids}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
