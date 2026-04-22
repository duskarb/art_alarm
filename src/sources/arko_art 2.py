import re
from typing import List
from bs4 import BeautifulSoup

from .base import BaseSource
from ..models import Opportunity


class ArkoArtCenterSource(BaseSource):
    """아르코미술관 공지사항."""

    name = "아르코미술관 (ARKO Art Center)"
    base_url = "https://www.arko.or.kr"
    list_url = "https://www.arko.or.kr/artcenter/board/list/503"
    verify_ssl = False

    def fetch_list(self, max_items: int = 30) -> List[Opportunity]:
        html = self.get(self.list_url)
        soup = BeautifulSoup(html, "lxml")

        items: List[Opportunity] = []
        for tr in soup.select("tr"):
            subject_td = tr.select_one("td.subject")
            if not subject_td:
                continue
            a = subject_td.select_one("a")
            if not a:
                continue
            href = a.get("href", "")
            m = re.search(r"cid=(\d+)", href)
            if not m:
                continue
            cid = m.group(1)
            title = a.get_text(" ", strip=True)
            if not title:
                continue

            tds = tr.find_all("td")
            date_text = ""
            if tds:
                last_td_text = tds[-1].get_text(strip=True)
                if re.match(r"^20\d{2}\.\d{2}\.\d{2}$", last_td_text):
                    date_text = last_td_text.replace(".", "-")

            full_url = f"https://www.arko.or.kr{href}" if href.startswith("/") else href

            items.append(Opportunity(
                id=f"arko_art:{cid}",
                source=self.name,
                title=title,
                url=full_url,
                posted_date=date_text,
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
            soup.select_one(".boardView")
            or soup.select_one(".board-view")
            or soup.select_one(".viewContent")
            or soup.select_one("#content")
        )
        if view:
            opp.body = view.get_text("\n", strip=True)
            opp.summary = opp.body[:400]
