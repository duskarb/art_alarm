import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml

from .active_store import ActiveStore
from .dashboard import render_dashboard
from .filter_gemini import GeminiFilter
from .filter_rules import RuleFilter
from .models import Opportunity
from .notify_email import render_html, send
from .sources.acc import AccSource
from .sources.arko_art import ArkoArtCenterSource
from .sources.dcaf import DcafSource
from .sources.ifac import IfacSource
from .sources.kawf import KawfSource
from .sources.mmca import MmcaSource
from .sources.mmca_residency import MmcaResidencySource
from .sources.ncas import NcasSource
from .sources.pcf import PcfSource
from .sources.sfac import SfacSource
from .state import SeenStore


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def gather_sources() -> list:
    return [
        KawfSource(),
        DcafSource(),
        SfacSource(),
        AccSource(),
        MmcaSource(),
        MmcaResidencySource(),
        ArkoArtCenterSource(),
        IfacSource(),
        PcfSource(),
        NcasSource(),
    ]


def run(dry_run: bool = False) -> int:
    root = Path(__file__).resolve().parent.parent
    cfg = load_config(root / "config.yaml")

    seen = SeenStore(root / "seen.json")
    active = ActiveStore(root / "active.json")

    rule = RuleFilter(
        include_keywords=cfg.get("include_keywords", []),
        exclude_keywords=cfg.get("exclude_keywords", []),
        regions_of_interest=cfg.get("regions_of_interest", []),
    )

    all_new: list[Opportunity] = []
    for src in gather_sources():
        print(f"[fetch] {src.name}")
        try:
            items = src.fetch_list(max_items=40)
        except Exception as e:
            print(f"  [error] {src.name} fetch_list failed: {e}")
            continue
        new_items = [it for it in items if not seen.is_seen(it.id)]
        print(f"  {len(items)} total, {len(new_items)} new")

        for it in new_items:
            try:
                src.fetch_detail(it)
            except Exception as e:
                print(f"  [warn] {src.name} detail fetch failed for {it.id}: {e}")
        all_new.extend(new_items)

    print(f"\n[rule] {len(all_new)} -> filtering by keywords/region...")
    rule_passed = rule.filter(all_new)
    print(f"  {len(rule_passed)} passed rule filter")

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key and rule_passed:
        print("[gemini] judging relevance...")
        gf = GeminiFilter(
            api_key=gemini_key,
            profile=cfg.get("profile", {}),
            work_summary=cfg.get("work_summary", ""),
            user_age=cfg.get("user_age_in_year", 22),
            user_birth_year=cfg.get("user_birth_year", 2003),
            threshold=0.55,
        )
        final = gf.filter(rule_passed)
        print(f"  {len(final)} passed Gemini filter")
        for o in rule_passed:
            verdict = "PASS" if o in final else "drop"
            print(f"  [{verdict}] {o.relevance_score:.2f} · {o.title[:55]}")
            print(f"         → {o.relevance_reason}")
    else:
        if not gemini_key:
            print("[gemini] GEMINI_API_KEY not set, skipping LLM filter")
        final = rule_passed

    final.sort(key=lambda o: o.relevance_score, reverse=True)

    if final:
        subject = f"[art_alarm] 예술 공모 {len(final)}건 · {datetime.now():%Y-%m-%d}"
        html = render_html(final)
        text_fallback = "\n\n".join(
            f"[{o.source}] {o.title}\n{o.url}\n이유: {o.relevance_reason}" for o in final
        )

        if dry_run:
            print("\n--- DRY RUN: email body preview ---")
            print(f"Subject: {subject}")
            for o in final:
                print(f"  - [{o.source}] score={o.relevance_score:.2f} {o.title}")
                print(f"    {o.url}")
                print(f"    reason: {o.relevance_reason}")
        else:
            smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
            smtp_port = int(os.environ.get("SMTP_PORT", "465"))
            smtp_user = os.environ["SMTP_USER"]
            smtp_pass = os.environ["SMTP_PASS"]
            to_addr = os.environ.get("NOTIFY_TO", cfg.get("profile", {}).get("email", smtp_user))

            send(
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                username=smtp_user,
                password=smtp_pass,
                from_addr=smtp_user,
                to_addr=to_addr,
                subject=subject,
                html_body=html,
                text_fallback=text_fallback,
            )
            print(f"[email] sent to {to_addr}")
    else:
        print("[result] nothing to notify today")

    # Gemini 에러 난 항목은 seen 에 넣지 않아 다음 실행 때 재시도
    conclusively_judged = {
        o.id for o in all_new
        if not (o.relevance_reason or "").startswith("[gemini error]")
    }
    seen.mark(conclusively_judged)
    seen.save()

    # 대시보드 아카이브 업데이트: 오늘 PASS 된 항목 추가 + 마감 지난 항목 제거
    active.add_or_update(final)
    removed = active.prune_expired()
    active.save()
    print(f"[active] {len(active.all_active())} active opportunities ({removed} expired removed)")

    # GitHub Pages 용 static 대시보드 생성
    render_dashboard(active.all_active(), root / "docs")
    print(f"[dashboard] docs/index.html generated")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch + filter but don't send email")
    args = parser.parse_args()
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
