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
   본문에 "결과 안내: 2026.05.20" 같은 스케줄 문구가 있어도 이건 향후 결과 안내일 뿐, 사후 공지가 아님.
   제목에 "공모", "모집", "신청", "접수", "오픈콜", "지원사업", "대관" 같은 기회를 암시하는 단어가 있고
   동시에 위 사후 공지 표현이 **제목에 없다면** 기회로 간주하고 다음 단계로 진행.
2. 이 공고가 **지원/신청 가능한 기회**인가? (채용공고, 정산 안내, 필수 교육 수강 안내, 대관료 변경 등은 제외)
3. 작가의 연령/자격/거주지역 조건에 해당하는가? (모집 대상이 2003년생 만 22세에게 열려 있는가)
4. 작가의 작업과 어울리는 장르/형식인가? (미디어아트, 실험예술, 시각예술, 디자인, 오픈콜, 레지던시 계열이면 적합.
   순수 공연예술/국악/무용/연극/성악/아동 대상 프로그램은 부적합)
5. 접수 마감일이 이미 지났다면 탈락.

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
