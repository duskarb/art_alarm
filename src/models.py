from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Opportunity:
    id: str
    source: str
    title: str
    url: str
    posted_date: str = ""
    summary: str = ""
    body: str = ""
    category: str = ""
    relevance_score: float = 0.0
    relevance_reason: str = ""
    matched_keywords: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
