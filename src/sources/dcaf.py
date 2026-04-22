import re
from typing import List
from bs4 import BeautifulSoup

from .base import BaseSource
from ..models import Opportunity


class DcafSource(BaseSource):
    name = "대전문화재단"
    base_url = "https://dcaf.or.kr"
    list_url = "https://dcaf.or.kr/web/board.do?menuIdx=375"
    verify_ssl = False  # DCAF CA 체인이 기본 certifi 에 없음

    def fetch_list(self, max_items: int = 30) -> List[Opportunity]:
        html = self.get(self.list_url)
        soup = BeautifulSoup(html, "lxml")

        items: List[Opportunity] = []
        for tr in soup.select("tr"):
            title_td = tr.select_one("td.ms-bbs-title a")
            if not title_td:
                continue
            href = title_td.get("href", "")
            m = re.search(r"bbsIdx=(\d+)", href)
            if not m:
                continue
            idx = m.group(1)
            title = title_td.get_text(strip=True)
            if not title:
                continue

            start_td = tr.select_one("td.ms-bbs-startline")
            end_td = tr.select_one("td.ms-bbs-deadline")
            cate_td = tr.select_one("td.ms-bbs-cate")
            sort_td = tr.select_one("td.ms-bbs-sort")

            posted = start_td.get_text(strip=True) if start_td else ""
            deadline = end_td.get_text(strip=True) if end_td else ""
            category = cate_td.get_text(strip=True) if cate_td else ""
            sort = sort_td.get_text(strip=True) if sort_td else ""

            summary_bits = []
            if sort:
                summary_bits.append(f"[{sort}]")
            if category:
                summary_bits.append(category)
            if deadline:
                summary_bits.append(f"마감 {deadline}")
            summary = " · ".join(summary_bits)

            items.append(Opportunity(
                id=f"dcaf:{idx}",
                source=self.name,
                title=title,
                url=f"https://dcaf.or.kr/web/board.do?menuIdx=375&bbsIdx={idx}",
                posted_date=posted,
                summary=summary,
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
            soup.select_one(".ms-bbs-view-content")
            or soup.select_one(".board-view")
            or soup.select_one("#contents")
        )
        if view:
            text = view.get_text("\n", strip=True)
            opp.body = (opp.summary + "\n\n" + text) if opp.summary else text
