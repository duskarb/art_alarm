from typing import List, Tuple

from .models import Opportunity


class RuleFilter:
    """First-pass filter: include/exclude keywords + region.

    Only prunes obvious non-matches. Age and detailed fit are judged by Gemini later.
    """

    def __init__(
        self,
        include_keywords: List[str],
        exclude_keywords: List[str],
        regions_of_interest: List[str],
    ):
        self.include = [k.lower() for k in include_keywords]
        self.exclude = [k.lower() for k in exclude_keywords]
        self.regions = [r.lower() for r in regions_of_interest]

    def passes(self, opp: Opportunity) -> Tuple[bool, List[str]]:
        text = f"{opp.title}\n{opp.body}".lower()

        for kw in self.exclude:
            if kw in text:
                return False, []

        matched = [kw for kw in self.include if kw in text]
        if not matched:
            return False, []

        has_any_region_mention = any(
            r in text for r in ["서울", "부산", "인천", "대구", "광주", "대전", "울산",
                                "세종", "경기", "강원", "충북", "충남", "전북", "전남",
                                "경북", "경남", "제주", "전국", "온라인"]
        )
        if has_any_region_mention:
            if not any(r in text for r in self.regions):
                return False, []

        return True, matched

    def filter(self, opps: List[Opportunity]) -> List[Opportunity]:
        kept: List[Opportunity] = []
        for opp in opps:
            ok, matched = self.passes(opp)
            if ok:
                opp.matched_keywords = matched
                kept.append(opp)
        return kept
