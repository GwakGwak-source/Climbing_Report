"""클라이밍 정모 리포트를 만든다.

    python main.py                # 수집 + 리포트 생성
    python main.py --max 40       # 요청 수를 줄여서 빠르게 시험
    python main.py --render-only  # 마지막 수집 결과로 페이지만 다시 생성
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

from climbing_report import somoim
from climbing_report.gyms import GymIndex
from climbing_report.render import render_archive, render_report

KST = timezone(timedelta(hours=9))
ROOT = os.path.dirname(os.path.abspath(__file__))


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)


def gid_from(text: str) -> str | None:
    """'https://www.somoim.co.kr/<id>?e_d=..' 나 id 그대로 → id"""
    for part in text.replace("?", "/").split("/"):
        if somoim._GID_RE.match(part):
            return part
    return None


def collect(cfg, groups: dict, now: datetime, max_requests: int) -> list[dict]:
    fetch = somoim.Fetcher(delay=cfg["request_delay_sec"], budget=max_requests)
    today = now.strftime("%Y-%m-%d")

    def remember(card: dict, source: str):
        if not somoim.is_climbing(card):
            return
        g = groups.setdefault(card["gid"], {"first_seen": today, "source": source})
        for k in ("gn", "loc1n", "loc2n"):
            if card.get(k):
                g[k] = card[k]

    # 1) 시작 목록: 검색·지역 페이지 + 직접 넣은 모임
    for path in cfg["seed_pages"]:
        html = fetch.get(path)
        if html:
            cards = somoim.group_items(somoim.flight_data(html))
            for c in cards:
                remember(c, path)
            print(f"[seed] {path}: 모임 {len(cards)}개")
    for ref in cfg.get("extra_groups", []):
        gid = gid_from(ref)
        if gid:
            groups.setdefault(gid, {"first_seen": today, "source": "extra"})["pinned"] = True

    # 2) 모임 페이지 방문 (최근 정모가 많았던 모임부터). 비슷한 모임으로 목록을 넓힌다.
    def priority(gid):
        g = groups[gid]
        return (0 if g.get("pinned") else 1, -(g.get("last_event_count") or 0), g.get("last_fetched") or "")

    queue = sorted(groups, key=priority)
    seen, events = set(), []
    while queue:
        gid = queue.pop(0)
        if gid in seen:
            continue
        seen.add(gid)
        html = fetch.get("/" + gid)
        if html is None:
            if fetch.count >= fetch.budget:
                print(f"[stop] 요청 상한 {fetch.budget}회 도달, 남은 모임 {len([q for q in queue if q not in seen])}개는 다음 실행에")
                break
            continue
        page = somoim.parse_group_page(html)
        g = groups[gid]
        g["last_fetched"] = today
        if not page:
            g["fail"] = g.get("fail", 0) + 1
            continue
        g.pop("fail", None)
        g.update({k: v for k, v in page["group"].items() if k in ("gn", "loc1n", "loc2n", "members") and v})
        g["last_event_count"] = len(page["events"])
        if page["events"]:
            g["last_active"] = today
        for e in page["events"]:
            e["group"] = g.get("gn", "")
            e["group_region"] = g.get("loc1n", "")
            events.append(e)
        if cfg.get("crawl_similar", True):
            for c in page["similar"]:
                if somoim.is_climbing(c) and c["gid"] not in groups:
                    remember(c, "similar")
                    queue.append(c["gid"])
    print(f"[done] 요청 {fetch.count}회, 모임 {len(seen)}곳 방문, 정모 {len(events)}건")

    # 오래 조용한 모임은 목록에서 뺀다
    cutoff = (now - timedelta(days=cfg.get("drop_group_after_idle_days", 60))).strftime("%Y-%m-%d")
    for gid in list(groups):
        g = groups[gid]
        if g.get("pinned"):
            continue
        if g.get("fail", 0) >= 3 or (g.get("last_fetched") and (g.get("last_active") or g["first_seen"]) < cutoff):
            del groups[gid]
    return events


def build_report(cfg, events, gyms: GymIndex, prev_eids: set, now: datetime, groups_count: int) -> dict:
    regions = cfg["regions"]
    eve_from = cfg["evening_from"].replace(":", "")
    start = now.date()
    dates = [(start + timedelta(days=i)) for i in range(cfg["days"])]
    keyset = {d.strftime("%Y%m%d") for d in dates}

    rows: dict[tuple, dict] = {}
    seen_eids = set()
    for e in events:
        if e["date"] not in keyset or e["eid"] in seen_eids:
            continue
        seen_eids.add(e["eid"])
        gym = gyms.match(e["place"])
        if gym.lat is None:
            # 장소 칸이 '-', '단톡참고'처럼 비어 있어도 제목에 '사당 더클 퇴근클'처럼 암장이 적힌 경우가 많다
            gym = gyms.match_title(e["title"]) or gym
        region = gym.region or e.get("group_region") or ""
        if regions and region not in regions:
            continue
        slot = "eve" if e["time"] >= eve_from else "day"
        key = (e["date"], slot, gym.key or e["place"])
        row = rows.setdefault(key, {
            "date": e["date"], "slot": slot, "gym": gym.name, "region": region,
            "lat": gym.lat, "lng": gym.lng, "matched": gym.matched, "events": [],
        })
        row["events"].append({
            "time": f"{e['time'][:2]}:{e['time'][2:]}",
            "title": e["title"], "group": e["group"], "gid": e["gid"],
            "url": f"{somoim.BASE}/{e['gid']}?e_d={e['date']}&e_t={e['time']}",
            "joined": e["joined"], "capacity": e["capacity"],
            "new": bool(prev_eids) and e["eid"] not in prev_eids,
        })
    for r in rows.values():
        r["events"].sort(key=lambda x: x["time"])
        r["joined"] = sum(x["joined"] or 0 for x in r["events"])
        r["new"] = any(x["new"] for x in r["events"])
    wd = "월화수목금토일"
    rel = {0: "오늘", 1: "내일", 2: "모레"}
    days = []
    for i, d in enumerate(dates):
        k = d.strftime("%Y%m%d")
        day_rows = sorted((r for r in rows.values() if r["date"] == k), key=lambda r: (-r["joined"], r["gym"]))
        days.append({
            "key": k,
            "label": f"{d.month}/{d.day} ({wd[d.weekday()]})",
            "rel": rel.get(i, ""),
            "rows": day_rows,
        })
    return {
        "title": cfg["title"],
        "generated": now.strftime("%Y-%m-%d %H:%M"),
        "date": now.strftime("%Y-%m-%d"),
        "regions": regions,
        "evening_from": cfg["evening_from"],
        "groups_count": groups_count,
        "days": days,
        "eids": sorted(seen_eids),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(ROOT, "config.json"))
    ap.add_argument("--max", type=int, help="이번 실행의 요청 수 상한")
    ap.add_argument("--render-only", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    cfg = load_json(args.config, None)
    if cfg is None:
        sys.exit(f"설정 파일을 읽을 수 없습니다: {args.config}")
    data_dir = os.path.join(ROOT, cfg["data_dir"])
    out_dir = os.path.join(ROOT, cfg["output_dir"])
    now = datetime.now(KST)

    groups = load_json(os.path.join(data_dir, "groups.json"), {})
    last = load_json(os.path.join(data_dir, "last_run.json"), {})
    gyms = GymIndex(os.path.join(ROOT, "gyms.json"), os.path.join(data_dir, "geocode_cache.json"))

    if args.render_only:
        events = last.get("events", [])
        prev_eids = set(last.get("prev_eids", []))
    else:
        events = collect(cfg, groups, now, args.max or cfg["max_requests"])
        # 같은 날 두 번 돌려도 NEW 기준은 '전날까지 본 정모'로 유지
        prev_eids = set(last.get("prev_eids", [])) if last.get("date") == now.strftime("%Y-%m-%d") else set(last.get("eids", []))

    report = build_report(cfg, events, gyms, prev_eids, now, len(groups))
    gyms.save_cache()

    os.makedirs(os.path.join(out_dir, "reports"), exist_ok=True)
    for path, href in ((os.path.join(out_dir, "index.html"), "archive.html"),
                       (os.path.join(out_dir, "reports", f"{report['date']}.html"), "../archive.html")):
        with open(path, "w", encoding="utf-8") as f:
            f.write(render_report(report, href))
    archive = sorted((n[:-5] for n in os.listdir(os.path.join(out_dir, "reports")) if n.endswith(".html")), reverse=True)
    with open(os.path.join(out_dir, "archive.html"), "w", encoding="utf-8") as f:
        f.write(render_archive(cfg["title"], archive))

    if not args.render_only:
        save_json(os.path.join(data_dir, "groups.json"), groups)
        save_json(os.path.join(data_dir, "last_run.json"), {
            "date": report["date"], "eids": report["eids"], "prev_eids": sorted(prev_eids), "events": events,
        })
    unmatched = sorted({r["gym"] for d in report["days"] for r in d["rows"] if not r["matched"]})
    total = sum(len(r["events"]) for d in report["days"] for r in d["rows"])
    print(f"[report] {out_dir}/index.html · 정모 {total}건 · 클라이밍 모임 {len(groups)}개")
    if unmatched:
        print(f"[gyms] 사전에 없는 장소 {len(unmatched)}곳 (gyms.json에 추가하면 지도에 나옵니다):")
        for u in unmatched:
            print("   -", u)


if __name__ == "__main__":
    main()
