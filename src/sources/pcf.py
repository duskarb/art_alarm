import re
from typing import List
from bs4 import BeautifulSoup

from .base import BaseSource
from ..models import Opportunity


class PcfSource(BaseSource):
    """파라다이스 문화재단 (Paradise Cultural Foundation) — 공지사항.

    파라다이스 아트랩 공모, 신청 소식 포함.
    """

    name = "파라다이스 문화재단 (PCF)"
    base_url = "https://www.pcf.or.kr"
    list_url = "https://www.pcf.or.kr/board/notice"

    def fetch_list(self, max_items: int = 30) -> List[Opportunity]:
        html = self.get(self.list_url)
        soup = BeautifulSoup(html, "lxml")

        items: List[Opportunity] = []
        for tr in soup.select("tbody tr"):
            title_td = tr.select_one("td.title a")
            if not title_td:
                continue
            href = title_td.get("href", "")
            m = re.search(r"/notice_view/(\d+)", href)
            if not m:
                continue
            idx = m.group(1)
            title = title_td.get_text(" ", strip=True)
            if not title:
                continue

            date_td = tr.select_one("td.table_date")
            posted = ""
            if date_td:
                raw = date_td.get_text(strip=True)
                if re.match(r"^20\d{2}\.\d{2}\.\d{2}$", raw):
                    posted = raw.replace(".", "-")

            full_url = f"https://www.pcf.or.kr{href}" if href.startswith("/") else href

            items.append(Opportunity(
                id=f"pcf:{idx}",
                source=self.name,
                title=title,
                url=full_url,
                posted_date=posted,
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
            soup.select_one(".board_view_content")
            or soup.select_one(".view_content")
            or soup.select_one(".content")
            or soup.select_one("#contents")
        )
        if view:
            opp.body = view.get_text("\n", strip=True)
            opp.summary = opp.body[:400]
