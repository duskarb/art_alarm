import json
import time
from typing import List

from google import genai
from google.genai import types

from .models import Opportunity


PROMPT_TEMPLATE = """너는 한국의 예술 공모/지원사업/전시 공고를 읽고 특정 작가에게 적합한지 판정하는 도우미야.

[작가 프로필]
- 이름: {name}
- 출생년도: {birth_year} (현재 만 {age}세)
- 소속: {affiliation}
- 활동 지역: {regions}
- 작업 요약: {work_summary}

[작가의 관심 분야]
미디어아트, AI/LLM 기반 예술, 인터랙티브, 개념미술, critical system, 펜 플로터 등 물리적 매체를 이용한 설치/퍼포먼스, 시각예술, 디자인 기반 실험작업.

[공고 내용]
제목: {title}
게시일: {posted_date}
본문:
{body}

[판정 기준]
1. 이 공고가 **지원/신청 가능한 기회**인가? (결과 발표, 채용공고, 정산 안내, 교육 수강 안내 등은 제외)
2. 작가의 연령/자격/거주지역 조건에 해당하는가? (모집 대상이 2003년생 만 22세에게 열려 있는가)
3. 작가의 작업과 어울리는 장르/형식인가? (미디어아트, 실험예술, 시각예술, 디자인 계열이면 적합. 순수 공연예술/국악/무용/연극/성악은 부적합)
4. 공고가 이미 마감되었거나 선정 결과/후속 안내 성격이면 제외.

다음 JSON만 출력:
{{
  "relevant": true/false,
  "score": 0.0~1.0,
  "reason": "한 문장 이유 (한국어)"
}}"""


class GeminiFilter:
    def __init__(
        self,
        api_key: str,
        profile: dict,
        work_summary: str,
        user_age: int,
        user_birth_year: int,
        model_name: str = "gemini-2.0-flash",
        threshold: float = 0.55,
    ):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.profile = profile
        self.work_summary = work_summary
        self.user_age = user_age
        self.user_birth_year = user_birth_year
        self.threshold = threshold

    def judge(self, opp: Opportunity) -> tuple[bool, float, str]:
        body = (opp.body or opp.summary or "")[:3500]
        prompt = PROMPT_TEMPLATE.format(
            name=self.profile.get("name", ""),
            birth_year=self.user_birth_year,
            age=self.user_age,
            affiliation=self.profile.get("affiliation", ""),
            regions=", ".join(self.profile.get("regions", [])),
            work_summary=self.work_summary.strip(),
            title=opp.title,
            posted_date=opp.posted_date,
            body=body,
        )
        try:
            resp = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            data = json.loads(resp.text)
            score = float(data.get("score", 0.0))
            reason = str(data.get("reason", ""))
            relevant = bool(data.get("relevant", False)) and score >= self.threshold
            return relevant, score, reason
        except Exception as e:
            return False, 0.0, f"[gemini error] {e}"

    def filter(self, opps: List[Opportunity], sleep_between: float = 0.5) -> List[Opportunity]:
        kept: List[Opportunity] = []
        for opp in opps:
            relevant, score, reason = self.judge(opp)
            opp.relevance_score = score
            opp.relevance_reason = reason
            if relevant:
                kept.append(opp)
            time.sleep(sleep_between)
        return kept
