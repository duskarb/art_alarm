import re
from typing import List
from bs4 import BeautifulSoup

from .base import BaseSource
from ..models import Opportunity


class AccSource(BaseSource):
    """국립아시아문화전당 (Asia Culture Center) 공지사항."""

    name = "국립아시아문화전당 (ACC)"
    base_url = "https://www.acc.go.kr"
    list_url = "https://www.acc.go.kr/main/board/board.do?PID=0701&boardID=NOTICE"
    verify_ssl = False

    def fetch_list(self, max_items: int = 30) -> List[Opportunity]:
        html = self.get(self.list_url)
        soup = BeautifulSoup(html, "lxml")

        items: List[Opportunity] = []
        for tr in soup.select("div.boardList tbody tr"):
            subject_td = tr.select_one("td.subject")
            date_td = tr.select_one("td.date")
            if not subject_td:
                continue
            a = subject_td.select_one("a")
            if not a:
                continue
            href = a.get("href", "")
            m = re.search(r"idx=(\d+)", href)
            if not m:
                continue
            idx = m.group(1)
            title = a.get_text(" ", strip=True)
            if not title:
                continue

            category_span = subject_td.select_one("span")
            category = category_span.get_text(strip=True) if category_span else ""
            posted = date_td.get_text(strip=True) if date_td else ""

            full_url = f"https://www.acc.go.kr{href}" if href.startswith("/") else href

            items.append(Opportunity(
                id=f"acc:{idx}",
                source=self.name,
                title=title,
                url=full_url,
                posted_date=posted,
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
        view = (
            soup.select_one(".boardView .viewContents")
            or soup.select_one(".boardView")
            or soup.select_one(".view_cont")
            or soup.select_one("#contents")
        )
        if view:
            text = view.get_text("\n", strip=True)
            opp.body = text
            opp.summary = text[:400]
