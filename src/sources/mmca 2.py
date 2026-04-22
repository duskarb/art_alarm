import json
import re
from typing import List

from bs4 import BeautifulSoup

from .base import BaseSource
from ..models import Opportunity


class MmcaSource(BaseSource):
    """국립현대미술관 (MMCA) 새소식 — AJAX JSON 엔드포인트 사용."""

    name = "국립현대미술관 (MMCA)"
    base_url = "https://www.mmca.go.kr"
    ajax_url = "https://www.mmca.go.kr/pr/AjaxNewsList.do"
    detail_fmt = "https://www.mmca.go.kr/pr/newsDetail.do?bdCId={bdc_id}"
    verify_ssl = False

    def fetch_list(self, max_items: int = 30) -> List[Opportunity]:
        resp = self.session.post(
            self.ajax_url,
            data={
                "searchType": "all",
                "searchCcdId": "",
                "searchBdCTp": "",
                "searchText": "",
                "pageIndex": "1",
                "searchFrom": "",
                "searchTo": "",
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.mmca.go.kr/pr/newsList.do",
            },
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        data = resp.json()

        items: List[Opportunity] = []
        for row in (data.get("newsList") or []):
            bdc_id = str(row.get("bdCId", "")).strip()
            title = (row.get("bdCTitle") or "").strip()
            if not bdc_id or not title:
                continue
            posted = (row.get("bdCNoticeStDt") or "").strip()
            category = (row.get("bdPlaNm") or "").strip()
            body_html = row.get("bdCContents") or ""
            body = BeautifulSoup(body_html, "lxml").get_text("\n", strip=True) if body_html else ""

            items.append(Opportunity(
                id=f"mmca:{bdc_id}",
                source=self.name,
                title=title,
                url=self.detail_fmt.format(bdc_id=bdc_id),
                posted_date=posted,
                category=category,
                body=body,
                summary=body[:400],
            ))
            if len(items) >= max_items:
                break
        return items

    def fetch_detail(self, opp: Opportunity) -> None:
        # fetch_list 에서 body 이미 채워졌으면 추가 호출 불필요
        if opp.body:
            return
        m = re.search(r"bdCId=(\d+)", opp.url)
        if not m:
            return
        try:
            resp = self.session.post(
                "https://www.mmca.go.kr/pr/newsDetail.do",
                data={"bdCId": m.group(1)},
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
        except Exception as e:
            opp.body = f"[fetch_detail error: {e}]"
            return
        soup = BeautifulSoup(resp.text, "lxml")
        view = soup.select_one(".viewBody") or soup.select_one("#content")
        if view:
            opp.body = view.get_text("\n", strip=True)
            opp.summary = opp.body[:400]
