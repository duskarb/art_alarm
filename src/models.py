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

    # Gemini 가 추출하는 필드
    deadline: str = ""          # ISO "YYYY-MM-DD" 또는 빈 문자열
    opportunity_type: str = ""  # 오픈콜/레지던시/공모/지원사업/대관/기타

    # 대시보드 아카이브용
    first_seen: str = ""        # 최초 감지 ISO 날짜

    def to_dict(self) -> dict:
        d = asdict(self)
        # 대시보드 HTML 에 body 전체 넣을 필요 없음 — 용량 절약
        d.pop("body", None)
        return d
