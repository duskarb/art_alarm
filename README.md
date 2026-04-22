# art_alarm

예술 공모·지원사업·전시 공고를 크롤링 → 키워드/규칙 필터 → Gemini 관련도 판정 → 이메일 알림.

## 구조

```
art_alarm/
├── .github/workflows/daily.yml   # 매일 KST 08:00 자동 실행
├── src/
│   ├── main.py                   # 오케스트레이터
│   ├── models.py                 # Opportunity 데이터클래스
│   ├── sources/                  # 사이트별 스크래퍼
│   │   └── kawf.py               # 한국예술인복지재단
│   ├── filter_rules.py           # 1차: 키워드/지역 규칙
│   ├── filter_gemini.py          # 2차: Gemini 관련도 판정
│   ├── notify_email.py           # Gmail SMTP
│   └── state.py                  # seen.json 중복 방지
├── config.yaml                   # 프로필·키워드·지역
├── requirements.txt
└── seen.json                     # 자동 생성/커밋
```

## 로컬 실행

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m src.main --dry-run   # 이메일 미전송 미리보기
```

실제 전송:

```bash
export GEMINI_API_KEY=...
export SMTP_USER=prism011312@gmail.com
export SMTP_PASS='gmail_app_password_16자리'
export NOTIFY_TO=prism011312@gmail.com
.venv/bin/python -m src.main
```

## GitHub 세팅

### 1. 리포지토리 푸시

```bash
cd art_alarm
git init
git add .
git commit -m "init: art_alarm"
git branch -M main
git remote add origin https://github.com/<USER>/<REPO>.git
git push -u origin main
```

### 2. Secrets 등록 (Settings → Secrets and variables → Actions)

| 이름             | 값                                                  |
| ---------------- | --------------------------------------------------- |
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey 에서 발급 (무료) |
| `SMTP_USER`      | Gmail 주소 (예: `prism011312@gmail.com`)            |
| `SMTP_PASS`      | Gmail **앱 비밀번호** 16자리 (아래 참고)            |
| `NOTIFY_TO`      | 수신 이메일 (보통 본인 Gmail)                       |

### 3. Gmail 앱 비밀번호 생성

1. Google 계정 → 보안 → **2단계 인증** 켜기
2. https://myaccount.google.com/apppasswords 접속
3. 앱 이름 `art_alarm` 입력 → 16자리 비밀번호 생성 → `SMTP_PASS` 에 그대로 넣기 (공백 제거)

### 4. 워크플로우 실행

- 자동: 매일 KST 08:00 실행
- 수동: Actions 탭 → `art_alarm daily` → Run workflow

## 대시보드

매 실행마다 `docs/index.html` + `docs/data.json` 이 자동 생성/커밋됨.
현재 지원 가능한 공고를 마감 임박 순으로 볼 수 있는 static 페이지.

### GitHub Pages 설정 (최초 1회)
1. 리포 Settings → **Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / Folder: `/docs` → Save
4. 1~2분 후 `https://<USER>.github.io/<REPO>/` 에서 접속 가능

### 아카이브 규칙
- Gemini 가 PASS 한 항목만 대시보드에 올라감
- 마감일이 있고 지난 항목 → 자동 제거
- 마감일 모름 → `first_seen` 기준 60일 뒤 자동 제거

## 동작 원리

1. **fetch**: `src/sources/*.py` 각 스크래퍼가 공고 리스트+본문 수집
2. **dedup**: `seen.json` 에 기록된 id 제외
3. **rule 1차 필터**: `config.yaml` 의 `include_keywords` 중 하나라도 매칭 + `exclude_keywords` 미매칭 + 지역 매칭
4. **Gemini 2차 판정**: 작가 프로필/작업과 공고 내용을 비교, `relevant=true` + `score≥0.55` 만 통과
5. **이메일 발송**: HTML 템플릿으로 통합 전송
6. **state 커밋**: seen.json 업데이트 후 리포에 커밋 백

## 새 소스 추가

`src/sources/` 에 `BaseSource` 를 상속해 `fetch_list` / `fetch_detail` 구현, `src/main.py:gather_sources()` 에 등록하면 끝.

## 현재 커버리지

- ✅ 한국예술인복지재단 (KAWF)
- ✅ 대전문화재단 (DCAF)
- ✅ 서울문화재단 (SFAC)
- ✅ 국립아시아문화전당 (ACC)
- ✅ 국립현대미술관 (MMCA) — 새소식
- ✅ MMCA 레지던시 — 연간 입주 작가 모집
- ✅ 아르코미술관 (ARKO Art Center)
- ✅ 인천문화재단 (IFAC)
- ✅ 파라다이스 문화재단 (PCF) — 파라다이스 아트랩 공모 포함
- ✅ **NCAS** — 17개 시도 문화재단 + ARKO 진행중 지원사업 통합 (마감일 직접 추출)
- ⚠️ 문화포털 — URL 패턴 추가 조사 필요
