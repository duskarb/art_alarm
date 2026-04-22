from typing import List
from bs4 import BeautifulSoup

from .base import BaseSource
from ..models import Opportunity


class KawfSource(BaseSource):
    name = "한국예술인복지재단"
    base_url = "https://www.kawf.kr"
    list_url = "https://www.kawf.kr/notice/sub01.do"
    detail_url_fmt = "https://www.kawf.kr/notice/sub01View.do?selIdx={idx}"

    def fetch_list(self, max_items: int = 30) -> List[Opportunity]:
        html = self.get(self.list_url)
        soup = BeautifulSoup(html, "lxml")

        board = soup.select_one(".board-list")
        if not board:
            return []

        items: List[Opportunity] = []
        for li in board.select("li"):
            title_p = li.select_one("p.title")
            date_p = li.select_one("p.date")
            if not title_p or not date_p:
                continue
            idx = title_p.get("data-pidx") or title_p.get("data-pIdx")
            if not idx:
                continue
            anchor = title_p.select_one("a")
            title = anchor.get_text(strip=True) if anchor else title_p.get_text(strip=True)
            if not title:
                continue
            date = date_p.get_text(strip=True)
            category_span = li.select_one("p.number span.ctgr")
            category = category_span.get_text(strip=True) if category_span else ""

            items.append(Opportunity(
                id=f"kawf:{idx}",
                source=self.name,
                title=title,
                url=self.detail_url_fmt.format(idx=idx),
                posted_date=self._normalize_date(date),
                category=category,
            ))
            if len(items) >= max_items:
                break
        return items

    def fetch_detail(self, opp: Opportunity) -> None:
        try:
            html = self.get(opp.url)
        except Exception as e:
            opp.body = f"[fetch_detail error: {e}]"
            return
        soup = BeautifulSoup(html, "lxml")
        view_con = soup.select_one(".view-con")
        if view_con:
            text = view_con.get_text("\n", strip=True)
            opp.body = text
            opp.summary = text[:400]

    @staticmethod
    def _normalize_date(date_str: str) -> str:
        s = date_str.strip()
        if len(s) == 8 and s[2] == "." and s[5] == ".":
            return f"20{s[:2]}-{s[3:5]}-{s[6:8]}"
        return s
