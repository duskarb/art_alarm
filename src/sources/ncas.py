import hashlib
import json
import re
from typing import List

from bs4 import BeautifulSoup

from .base import BaseSource
from ..models import Opportunity


class NcasSource(BaseSource):
    """국가문화예술지원시스템 (NCAS) 홈페이지 진행중 지원사업 통합 리스트.

    홈페이지 메인 표 자체가 17개 시도 문화재단 + ARKO 진행중 공모 통합 뷰.
    각 행에서 사업명, 마감일, 신청대상, 분야, 외부 상세 URL 을 직접 추출.
    """

    name = "NCAS"
    base_url = "https://www.ncas.or.kr"
    list_url = "https://www.ncas.or.kr/"
    verify_ssl = False

    DEADLINE_RE = re.compile(r"(\d{4})\.(\d{2})\.(\d{2})")
    URL_RE = re.compile(r"window\.open\(\s*['\"]([^'\"]+)['\"]")

    def fetch_list(self, max_items: int = 80) -> List[Opportunity]:
        html = self.get(self.list_url)
        soup = BeautifulSoup(html, "lxml")

        items: List[Opportunity] = []
        for tr in soup.select("tr[data-item]"):
            data_attr = tr.get("data-item", "")
            try:
                meta = json.loads(data_attr)
            except Exception:
                meta = {}
            if meta.get("prgsStatus") != "진행중":
                continue

            tds = tr.find_all("td")
            if len(tds) < 7:
                continue

            inst = tds[0].get_text(" ", strip=True)
            program = tds[1].get_text(" ", strip=True)
            start = tds[2].get_text(" ", strip=True)
            deadline_text = tds[3].get_text(" ", strip=True)
            target = tds[4].get_text(" ", strip=True)
            field = tds[5].get_text(" ", strip=True)

            if not program:
                continue

            btn = tds[6].select_one("button[onclick]")
            url = ""
            if btn:
                m = self.URL_RE.search(btn.get("onclick", ""))
                if m:
                    url = m.group(1)
            if not url:
                continue

            # ISO 마감일 추출
            deadline_iso = ""
            m = self.DEADLINE_RE.search(deadline_text)
            if m:
                deadline_iso = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

            posted_iso = ""
            m = self.DEADLINE_RE.search(start)
            if m:
                posted_iso = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

            opp_id = f"ncas:{hashlib.md5(url.encode('utf-8')).hexdigest()[:12]}"
            summary = f"[{inst}] 분야: {field} · 신청대상: {target} · 마감 {deadline_iso or '미정'}"

            items.append(Opportunity(
                id=opp_id,
                source=f"NCAS · {inst}",
                title=program,
                url=url,
                posted_date=posted_iso,
                deadline=deadline_iso,
                category=field,
                opportunity_type="지원사업",
                summary=summary,
                body=summary,  # Gemini 가 판정용으로 쓸 본문
            ))
            if len(items) >= max_items:
                break
        return items

    def fetch_detail(self, opp: Opportunity) -> None:
        # NCAS 행 자체에 모든 메타데이터가 있으므로 별도 호출 불필요
        return
