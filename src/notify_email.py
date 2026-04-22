import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from html import escape
from typing import List

from .models import Opportunity


def render_html(opps: List[Opportunity]) -> str:
    if not opps:
        return "<p>오늘 새로 매칭된 공고가 없습니다.</p>"

    rows = []
    for opp in opps:
        matched = ", ".join(opp.matched_keywords[:6])
        reason = escape(opp.relevance_reason or "")
        summary = escape((opp.summary or opp.body or "")[:260])
        rows.append(f"""
        <div style="border-left:4px solid #2d6cdf;padding:12px 16px;margin-bottom:16px;background:#f7f9fc;border-radius:4px;">
          <div style="font-size:12px;color:#666;margin-bottom:4px;">
            [{escape(opp.source)}] · {escape(opp.posted_date)} · 관련도 {opp.relevance_score:.2f}
          </div>
          <div style="font-size:16px;font-weight:600;margin-bottom:6px;">
            <a href="{escape(opp.url)}" style="color:#111;text-decoration:none;">{escape(opp.title)}</a>
          </div>
          <div style="font-size:13px;color:#333;margin-bottom:6px;">{summary}…</div>
          <div style="font-size:12px;color:#555;"><b>판정:</b> {reason}</div>
          <div style="font-size:11px;color:#888;margin-top:4px;">매칭 키워드: {escape(matched)}</div>
          <div style="font-size:12px;margin-top:8px;">
            <a href="{escape(opp.url)}" style="color:#2d6cdf;">공고 바로가기 →</a>
          </div>
        </div>
        """)
    return f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo',sans-serif;max-width:680px;margin:0 auto;">
      <h2 style="font-size:18px;border-bottom:2px solid #111;padding-bottom:8px;">오늘의 예술 공모 알림 · {len(opps)}건</h2>
      {''.join(rows)}
      <p style="font-size:11px;color:#999;margin-top:24px;">art_alarm · 자동 생성</p>
    </div>"""


def send(
    *,
    smtp_host: str,
    smtp_port: int,
    username: str,
    password: str,
    from_addr: str,
    to_addr: str,
    subject: str,
    html_body: str,
    text_fallback: str = "",
) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Date"] = formatdate(localtime=True)
    msg.attach(MIMEText(text_fallback or "HTML 메일 클라이언트에서 확인해주세요.", "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # Gmail 앱 비번 복사시 섞이는 non-breaking space/공백 제거
    clean_user = username.strip().replace("\xa0", "")
    clean_pass = "".join(password.split()).replace("\xa0", "")

    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
        server.login(clean_user, clean_pass)
        server.sendmail(clean_user, [to_addr], msg.as_string())
