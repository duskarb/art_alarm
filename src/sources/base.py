from abc import ABC, abstractmethod
from typing import List
import requests

from ..models import Opportunity


class BaseSource(ABC):
    name: str = "base"
    base_url: str = ""

    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/124.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        })

    def get(self, url: str) -> str:
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text

    @abstractmethod
    def fetch_list(self, max_items: int = 30) -> List[Opportunity]:
        """Return list of Opportunity with at least id/title/url/posted_date filled."""

    def fetch_detail(self, opp: Opportunity) -> None:
        """Optionally populate opp.body and opp.summary in-place."""
