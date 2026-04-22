"""static 대시보드 HTML 생성."""

import json
from datetime import datetime
from pathlib import Path
from typing import List

from .models import Opportunity


HTML_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>art_alarm — 지금 지원 가능한 공고</title>
<style>
  :root {{
    --bg: #fafafa;
    --card: #fff;
    --text: #111;
    --muted: #888;
    --accent: #2d6cdf;
    --danger: #d93025;
    --border: #e5e5e5;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Segoe UI", sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
  }}
  .container {{ max-width: 920px; margin: 0 auto; padding: 24px 16px 64px; }}
  header {{ margin-bottom: 24px; }}
  h1 {{ font-size: 22px; margin: 0 0 6px; }}
  .sub {{ color: var(--muted); font-size: 13px; }}
  .controls {{
    display: flex; flex-wrap: wrap; gap: 8px;
    margin: 20px 0 16px;
    padding: 12px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
  }}
  .controls input, .controls select {{
    padding: 6px 10px; font-size: 13px;
    border: 1px solid var(--border); border-radius: 6px;
    background: #fff;
  }}
  .controls input[type="search"] {{ flex: 1; min-width: 180px; }}
  .count {{ color: var(--muted); font-size: 13px; padding: 6px 0; }}
  .opp {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 12px;
  }}
  .opp-head {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; font-size: 12px; color: var(--muted); margin-bottom: 6px; }}
  .badge {{ padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 500; }}
  .badge-src {{ background: #eef1f6; color: #444; }}
  .badge-type {{ background: #e7f0ff; color: #1d4ed8; }}
  .badge-dday {{ background: #fff1e0; color: #b4531a; }}
  .badge-dday.urgent {{ background: #ffe0e0; color: var(--danger); font-weight: 600; }}
  .badge-score {{ background: #eef6e5; color: #3b6a14; }}
  .opp h2 {{ font-size: 15px; margin: 4px 0 8px; line-height: 1.35; }}
  .opp h2 a {{ color: var(--text); text-decoration: none; }}
  .opp h2 a:hover {{ color: var(--accent); text-decoration: underline; }}
  .opp .meta {{ font-size: 12px; color: var(--muted); margin-top: 8px; }}
  .opp .reason {{ font-size: 13px; color: #333; background: #f7f7f7; padding: 8px 10px; border-radius: 6px; margin-top: 8px; }}
  .opp .summary {{ font-size: 13px; color: #555; margin-top: 8px; }}
  footer {{ margin-top: 40px; text-align: center; color: var(--muted); font-size: 11px; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg: #111; --card: #1c1c1c; --text: #f3f3f3; --muted: #888; --border: #2a2a2a; }}
    .controls input, .controls select {{ background: #1c1c1c; color: var(--text); }}
    .opp .reason {{ background: #222; }}
    .badge-src {{ background: #2a2a2a; color: #ccc; }}
    .badge-type {{ background: #13264d; color: #79a8ff; }}
    .badge-dday {{ background: #3a2812; color: #e0a872; }}
    .badge-dday.urgent {{ background: #3d1818; color: #ff8d8d; }}
    .badge-score {{ background: #1f3312; color: #a5d17c; }}
  }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>지금 지원 가능한 공고</h1>
    <div class="sub">마지막 갱신: {generated_at} · 총 <span id="totalCount">{total}</span>건</div>
  </header>

  <div class="controls">
    <input id="q" type="search" placeholder="제목·내용 검색">
    <select id="source"><option value="">전체 소스</option></select>
    <select id="type"><option value="">전체 유형</option></select>
    <select id="sort">
      <option value="deadline">마감 임박 순</option>
      <option value="score">관련도 높은 순</option>
      <option value="first_seen">최근 감지 순</option>
    </select>
  </div>

  <div class="count" id="filteredCount"></div>

  <div id="list"></div>

  <footer>
    art_alarm · <a href="https://github.com/duskarb/art_alarm" style="color:inherit;">github</a>
  </footer>
</div>

<script id="data" type="application/json">
{data_json}
</script>
<script>
  const data = JSON.parse(document.getElementById("data").textContent);
  const opps = data.opportunities || [];

  const qEl = document.getElementById("q");
  const sourceEl = document.getElementById("source");
  const typeEl = document.getElementById("type");
  const sortEl = document.getElementById("sort");
  const listEl = document.getElementById("list");
  const fcEl = document.getElementById("filteredCount");

  const uniq = (arr) => [...new Set(arr.filter(Boolean))].sort();
  for (const s of uniq(opps.map(o => o.source))) {{
    const o = document.createElement("option"); o.value = s; o.textContent = s;
    sourceEl.appendChild(o);
  }}
  for (const t of uniq(opps.map(o => o.opportunity_type))) {{
    const o = document.createElement("option"); o.value = t; o.textContent = t;
    typeEl.appendChild(o);
  }}

  function ddays(deadline) {{
    if (!deadline) return null;
    const d = new Date(deadline + "T23:59:59");
    if (isNaN(d)) return null;
    const diff = Math.ceil((d - new Date()) / (1000 * 60 * 60 * 24));
    return diff;
  }}

  function esc(s) {{ return (s||"").replace(/[&<>"']/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}}[c])); }}

  function render() {{
    const q = qEl.value.trim().toLowerCase();
    const srcF = sourceEl.value;
    const typeF = typeEl.value;
    const sortK = sortEl.value;

    let arr = opps.filter(o => {{
      if (srcF && o.source !== srcF) return false;
      if (typeF && o.opportunity_type !== typeF) return false;
      if (q) {{
        const hay = ((o.title||"") + " " + (o.summary||"") + " " + (o.relevance_reason||"")).toLowerCase();
        if (!hay.includes(q)) return false;
      }}
      return true;
    }});

    arr.sort((a, b) => {{
      if (sortK === "score") return (b.relevance_score||0) - (a.relevance_score||0);
      if (sortK === "first_seen") return (b.first_seen||"").localeCompare(a.first_seen||"");
      // deadline default: 임박 먼저, 없는 건 뒤로
      const da = ddays(a.deadline), db = ddays(b.deadline);
      if (da === null && db === null) return (b.relevance_score||0) - (a.relevance_score||0);
      if (da === null) return 1;
      if (db === null) return -1;
      return da - db;
    }});

    fcEl.textContent = `${{arr.length}}건 표시 중`;

    listEl.innerHTML = arr.map(o => {{
      const dd = ddays(o.deadline);
      let ddBadge = "";
      if (dd !== null) {{
        const urgent = dd <= 7;
        const label = dd === 0 ? "오늘 마감" : dd < 0 ? `마감 ${{Math.abs(dd)}}일 지남` : `D-${{dd}}`;
        ddBadge = `<span class="badge badge-dday ${{urgent ? "urgent" : ""}}">${{esc(label)}}${{o.deadline ? " · " + esc(o.deadline) : ""}}</span>`;
      }} else if (o.deadline) {{
        ddBadge = `<span class="badge badge-dday">${{esc(o.deadline)}}</span>`;
      }}
      const typeBadge = o.opportunity_type ? `<span class="badge badge-type">${{esc(o.opportunity_type)}}</span>` : "";
      const scoreBadge = o.relevance_score ? `<span class="badge badge-score">관련도 ${{(+o.relevance_score).toFixed(2)}}</span>` : "";
      const summary = o.summary ? `<div class="summary">${{esc(o.summary.slice(0, 200))}}${{o.summary.length > 200 ? "…" : ""}}</div>` : "";
      return `
        <article class="opp">
          <div class="opp-head">
            <span class="badge badge-src">${{esc(o.source)}}</span>
            ${{typeBadge}}
            ${{ddBadge}}
            ${{scoreBadge}}
          </div>
          <h2><a href="${{esc(o.url)}}" target="_blank" rel="noopener">${{esc(o.title)}}</a></h2>
          ${{summary}}
          ${{o.relevance_reason ? `<div class="reason">${{esc(o.relevance_reason)}}</div>` : ""}}
          <div class="meta">게시일 ${{esc(o.posted_date || "-")}} · 최초 감지 ${{esc(o.first_seen || "-")}}</div>
        </article>`;
    }}).join("");
  }}

  [qEl, sourceEl, typeEl, sortEl].forEach(el => el.addEventListener("input", render));
  render();
</script>
</body>
</html>
"""


def render_dashboard(
    active_opps: List[Opportunity],
    out_dir: Path,
    repo_url: str = "",
) -> None:
    """docs/index.html + docs/data.json 생성."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "opportunities": [o.to_dict() for o in active_opps],
    }
    data_json = json.dumps(data, ensure_ascii=False, indent=0)

    html = HTML_TEMPLATE.format(
        generated_at=data["generated_at"],
        total=len(active_opps),
        data_json=data_json.replace("</script>", "<\\/script>"),
    )

    (out_dir / "index.html").write_text(html, encoding="utf-8")
    (out_dir / "data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
