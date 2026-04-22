"""현재 유효한(마감 전) Opportunity 아카이브 관리."""

import json
from dataclasses import fields
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, List

from .models import Opportunity


NO_DEADLINE_RETENTION_DAYS = 60  # 마감일 없는 항목은 first_seen 기준 60일 유지


def _parse_iso(s: str) -> date | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _opp_from_dict(d: dict) -> Opportunity:
    valid = {f.name for f in fields(Opportunity)}
    return Opportunity(**{k: v for k, v in d.items() if k in valid})


class ActiveStore:
    """active.json — 현재 유효한 opp 목록."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._opps: dict[str, Opportunity] = {}
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                for d in data.get("opportunities", []):
                    opp = _opp_from_dict(d)
                    self._opps[opp.id] = opp
            except Exception:
                self._opps = {}

    def add_or_update(self, opps: Iterable[Opportunity]) -> None:
        today_iso = date.today().isoformat()
        for o in opps:
            if not o.first_seen:
                prev = self._opps.get(o.id)
                o.first_seen = prev.first_seen if prev and prev.first_seen else today_iso
            self._opps[o.id] = o

    def prune_expired(self, today: date | None = None) -> int:
        today = today or date.today()
        cutoff_no_deadline = today - timedelta(days=NO_DEADLINE_RETENTION_DAYS)

        to_remove: list[str] = []
        for opp_id, o in self._opps.items():
            deadline = _parse_iso(o.deadline)
            if deadline:
                if deadline < today:
                    to_remove.append(opp_id)
                    continue
            else:
                first_seen = _parse_iso(o.first_seen)
                if first_seen and first_seen < cutoff_no_deadline:
                    to_remove.append(opp_id)
        for opp_id in to_remove:
            del self._opps[opp_id]
        return len(to_remove)

    def all_active(self) -> List[Opportunity]:
        def sort_key(o: Opportunity):
            d = _parse_iso(o.deadline)
            # 마감 임박 먼저, 마감 없는 건 뒤
            return (d is None, d or date.max, -o.relevance_score)

        return sorted(self._opps.values(), key=sort_key)

    def save(self) -> None:
        data = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "opportunities": [o.to_dict() for o in self.all_active()],
        }
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
