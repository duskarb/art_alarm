import re
from typing import List
from bs4 import BeautifulSoup

from .base import BaseSource
from ..models import Opportunity


class IfacSource(BaseSource):
    """인천문화재단 지원사업 공고."""

    name = "인천문화재단 (IFAC)"
    base_url = "https://www.ifac.or.kr"
    list_url = "https://www.ifac.or.kr/artsSupProjects/supProjects/list.do?key=m2501143953255"
    detail_fmt = "https://www.ifac.or.kr/artsSupProjects/supProjects/view.do?key=m2501143953255&bbsSn={bbs_sn}"
    verify_ssl = False

    def fetch_list(self, max_items: int = 30) -> List[Opportunity]:
        html = self.get(self.list_url)
        soup = BeautifulSoup(html, "lxml")

        items: List[Opportunity] = []
        pattern = re.compile(r"goView\('(\d+)'")

        for li in soup.select("div.boardList ul > li"):
            a = li.select_one("a")
            if not a:
                continue
            onclick = a.get("onclick", "")
            m = pattern.search(onclick)
            if not m:
                continue
            bbs_sn = m.group(1)

            title_dd = li.select_one("dl.title dd")
            date_dd = li.select_one("dl.date dd")
            team_dd = li.select_one("dl.team dd")
            if not title_dd:
                continue
            title = " ".join(title_dd.get_text(" ", strip=True).split())
            # notice 배지 텍스트 제거
            title = re.sub(r"\s*공지\s*$", "", title).strip()
            if not title:
                continue

            posted = date_dd.get_text(strip=True) if date_dd else ""
            category = team_dd.get_text(strip=True) if team_dd else ""

            items.append(Opportunity(
                id=f"ifac:{bbs_sn}",
                source=self.name,
                title=title,
                url=self.detail_fmt.format(bbs_sn=bbs_sn),
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
            soup.select_one(".boardView")
            or soup.select_one(".view-content")
            or soup.select_one(".contentsBody")
            or soup.select_one("#contents")
        )
        if view:
            opp.body = view.get_text("\n", strip=True)
            opp.summary = opp.body[:400]
