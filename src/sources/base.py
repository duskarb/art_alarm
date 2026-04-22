from abc import ABC, abstractmethod
from typing import List
import requests
import urllib3

from ..models import Opportunity

# 한국 정부/재단 사이트는 CA 체인이 기본 certifi에 없는 경우가 잦음.
# 공개 공고 데이터 스크래핑만 하므로 경고를 끄고 verify=False 를 허용한다.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BaseSource(ABC):
    name: str = "base"
    base_url: str = ""
    verify_ssl: bool = True  # 필요 시 각 소스에서 False 로 override

    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/124.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        })
        self.session.verify = self.verify_ssl

    def get(self, url: str) -> str:
        resp = self.session.get(url, timeout=self.timeout, verify=self.verify_ssl)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text

    @abstractmethod
    def fetch_list(self, max_items: int = 30) -> List[Opportunity]:
        """Return list of Opportunity with at least id/title/url/posted_date filled."""

    def fetch_detail(self, opp: Opportunity) -> None:
        """Optionally populate opp.body and opp.summary in-place."""
