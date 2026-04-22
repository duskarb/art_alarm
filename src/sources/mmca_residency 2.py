import re
from typing import List

from bs4 import BeautifulSoup

from .base import BaseSource
from ..models import Opportunity


class MmcaResidencySource(BaseSource):
    """국립현대미술관 레지던시 — 연간 입주 작가 모집 공고."""

    name = "MMCA 레지던시"
    base_url = "https://www.mmca.go.kr"
    ajax_url = "https://www.mmca.go.kr/artStudio/AjaxReviewList.do"
    detail_fmt = "https://www.mmca.go.kr/artStudio/reviewDetail.do?oppId={opp_id}"
    verify_ssl = False

    LOCATION_MAP = {"A1": "창동레지던시", "A2": "고양레지던시"}

    def fetch_list(self, max_items: int = 20) -> List[Opportunity]:
        resp = self.session.post(
            self.ajax_url,
            data={
                "searchText": "",
                "pageIndex": "1",
                "searchCcdId": "",
                "oppTargetSite": "01",
                "oppGrpCd": "31",
                "sort": "",
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.mmca.go.kr/artStudio/reviewList.do",
            },
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        data = resp.json()

        items: List[Opportunity] = []
        for row in (data.get("newsList") or []):
            opp_id = str(row.get("oppId", "")).strip()
            title = (row.get("oppTitle") or "").strip()
            if not opp_id or not title:
                continue
            year = str(row.get("oppYear") or "").strip()
            location = self.LOCATION_MAP.get(row.get("oppLocation") or "", "")
            body_html = row.get("oppContents") or ""
            body = BeautifulSoup(body_html, "lxml").get_text("\n", strip=True) if body_html else ""

            # oppYear 는 작성 연도 추정 — posted_date 정식 필드에 그대로
            posted = f"{year}" if year else ""

            items.append(Opportunity(
                id=f"mmca_res:{opp_id}",
                source=self.name,
                title=title,
                url=self.detail_fmt.format(opp_id=opp_id),
                posted_date=posted,
                category=location or "레지던시",
                body=body,
                summary=body[:400],
            ))
            if len(items) >= max_items:
                break
        return items

    def fetch_detail(self, opp: Opportunity) -> None:
        if opp.body:
            return
