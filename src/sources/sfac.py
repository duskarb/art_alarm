import re
from typing import List
from bs4 import BeautifulSoup

from .base import BaseSource
from ..models import Opportunity


class SfacSource(BaseSource):
    """Seoul Foundation for Arts and Culture — 공모소식.

    The list is populated via POST to /site/SFAC_KOR/ex/bbs/ListSfac.do with cbIdx=992.
    Each item carries onclick="doView('992', bcIdx, '/business/artsupport/notice_gather.do')".
    """

    name = "서울문화재단"
    base_url = "https://www.sfac.or.kr"
    ajax_url = "https://www.sfac.or.kr/site/SFAC_KOR/ex/bbs/ListSfac.do"
    detail_path = "/business/artsupport/notice_gather.do"
    cb_idx = "992"
    verify_ssl = False

    def _fetch_list_html(self) -> str:
        data = {
            "cbIdx": self.cb_idx,
            "pageIndex": "1",
            "searchKey": "",
            "tgtTypeCd": "",
            "cateTypeCd": "",
            "viewUrl": "/opensquare/notice/support_list.do",
            "listUrl": "/opensquare/notice/support_list.do",
            "registUrl": "",
            "type": "",
        }
        resp = self.session.post(
            self.ajax_url,
            data=data,
            headers={"Referer": "https://www.sfac.or.kr/opensquare/notice/support_list.do"},
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text

    def fetch_list(self, max_items: int = 30) -> List[Opportunity]:
        html = self._fetch_list_html()
        soup = BeautifulSoup(html, "lxml")

        items: List[Opportunity] = []
        pattern = re.compile(r"doView\('(\d+)','(\d+)','([^']+)'\)")

        for li in soup.select("ul.board-list--wrap > li"):
            a = li.select_one("a")
            if not a:
                continue
            onclick = a.get("onclick", "")
            m = pattern.search(onclick)
            if not m:
                continue
            cb_idx, bc_idx, view_path = m.groups()

            subject = li.select_one("dl.subject dd p")
            date = li.select_one("dl.date dd")
            if not subject:
                continue
            title = subject.get_text(strip=True)
            if not title:
                continue
            posted = date.get_text(strip=True) if date else ""

            detail_url = f"https://www.sfac.or.kr{view_path}?cbIdx={cb_idx}&bcIdx={bc_idx}"

            items.append(Opportunity(
                id=f"sfac:{bc_idx}",
                source=self.name,
                title=title,
                url=detail_url,
                posted_date=self._normalize_date(posted),
            ))
            if len(items) >= max_items:
                break
        return items

    def fetch_detail(self, opp: Opportunity) -> None:
        # opp.url 에서 bcIdx 추출해 AJAX endpoint 호출
        m = re.search(r"bcIdx=(\d+)", opp.url)
        if not m:
            return
        bc_idx = m.group(1)
        try:
            resp = self.session.post(
                "https://www.sfac.or.kr/site/SFAC_KOR/ex/bbs/ViewSfac.do",
                data={
                    "cbIdx": self.cb_idx,
                    "bcIdx": bc_idx,
                    "viewUrl": "/opensquare/notice/support_list.do",
                    "listUrl": "/opensquare/notice/support_list.do",
                    "registUrl": "",
                    "type": "",
                },
                headers={"Referer": opp.url},
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            html = resp.text
        except Exception as e:
            opp.body = f"[fetch_detail error: {e}]"
            return
        soup = BeautifulSoup(html, "lxml")
        body = soup.select_one(".board-view--body")
        if body:
            text = body.get_text("\n", strip=True)
            opp.body = text
            opp.summary = text[:400]

    @staticmethod
    def _normalize_date(s: str) -> str:
        s = s.strip()
        if re.match(r"^\d{4}\.\d{2}\.\d{2}$", s):
            return s.replace(".", "-")
        return s
