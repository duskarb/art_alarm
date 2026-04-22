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

[판정 기준 — 순서대로 확인]
1. **제목에 문자 그대로** 다음 중 하나가 있으면 사후 공지로 간주하고 탈락(relevant=false, score<=0.1):
   "결과 발표", "선정 결과", "심의 결과", "최종 합격", "최종 선정", "합격자 안내",
   "선정자 안내", "당선작 발표", "선정 명단".
   ⚠️ 유사 표현·본문 내 언급·추론 금지. 반드시 **제목** 에 **그대로** 있을 때만 적용.
2. 이 공고가 **지원/신청 가능한 기회**인가? (채용공고, 정산 안내, 필수 교육 수강 안내, 대관료 변경 등은 제외)
3. 작가의 연령/자격/거주지역 조건에 해당하는가?
4. 작가의 작업과 어울리는 장르/형식인가? (미디어아트, 실험예술, 시각예술, 디자인, 오픈콜, 레지던시 계열이면 적합.
   순수 공연예술/국악/무용/연극/성악/아동 대상 프로그램은 부적합)
5. **마감일 추출**: 본문에서 "접수 마감", "신청 마감", "마감일", "~까지" 형태의 표현을 찾아 접수 마감 날짜를 추출.
   이미 지난 날짜면 relevant=false. 찾지 못하면 deadline=""(빈 문자열).
6. **공고 유형 분류** (`opportunity_type`): 다음 중 하나 —
   "오픈콜" / "레지던시" / "공모" / "지원사업" / "대관" / "전시" / "채용" / "기타"

다음 JSON 만 출력:
{{
  "relevant": true/false,
  "score": 0.0~1.0,
  "reason": "한 문장 이유 (한국어)",
  "deadline": "YYYY-MM-DD" 또는 "",
  "opportunity_type": "오픈콜/레지던시/공모/지원사업/대관/전시/채용/기타"
}}"""


class GeminiFilter:
    def __init__(
        self,
        api_key: str,
        profile: dict,
        work_summary: str,
        user_age: int,
        user_birth_year: int,
        model_name: str = "gemini-2.5-flash-lite",
        threshold: float = 0.55,
    ):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.profile = profile
        self.work_summary = work_summary
        self.user_age = user_age
        self.user_birth_year = user_birth_year
        self.threshold = threshold

    def judge(self, opp: Opportunity) -> dict:
        """Opportunity 하나에 대한 Gemini 판정. 반환값은 dict."""
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
            return {
                "relevant": bool(data.get("relevant", False)),
                "score": float(data.get("score", 0.0)),
                "reason": str(data.get("reason", "")),
                "deadline": str(data.get("deadline", "") or ""),
                "opportunity_type": str(data.get("opportunity_type", "") or ""),
                "error": None,
            }
        except Exception as e:
            return {
                "relevant": False,
                "score": 0.0,
                "reason": f"[gemini error] {e}",
                "deadline": "",
                "opportunity_type": "",
                "error": str(e),
            }

    def filter(self, opps: List[Opportunity], sleep_between: float = 0.5) -> List[Opportunity]:
        kept: List[Opportunity] = []
        for opp in opps:
            v = self.judge(opp)
            opp.relevance_score = v["score"]
            opp.relevance_reason = v["reason"]
            # 소스에서 미리 채워진 값(예: NCAS) 은 보존하고 빈 값만 채움
            if not opp.deadline:
                opp.deadline = v["deadline"]
            if not opp.opportunity_type:
                opp.opportunity_type = v["opportunity_type"]
            if v["relevant"] and v["score"] >= self.threshold:
                kept.append(opp)
            time.sleep(sleep_between)
        return kept
