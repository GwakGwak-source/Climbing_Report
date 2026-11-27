"""소모임 공개 웹페이지에서 클라이밍 모임과 정모 일정을 읽어 온다.

robots.txt가 허용하는 공개 HTML 페이지만 읽는다(내부 API는 쓰지 않는다).
Next.js가 페이지에 심어 두는 데이터(self.__next_f.push)를 해석해서
모임 정보와 정모 목록을 얻고, 참석 인원은 렌더된 정모 카드에서 읽는다.
멤버 이름 같은 개인 정보는 저장하지 않는다.
"""
from __future__ import annotations

import gzip
import json
import re
import time
import urllib.parse
import urllib.request

BASE = "https://www.somoim.co.kr"
UA = "Mozilla/5.0 (compatible; climbing-report/1.1; +https://github.com/GwakGwak-source/Climbing_Report)"
CLIMBING_IT2 = "18007"  # 소모임 2차 관심사 코드: 운동/스포츠 > 클라이밍
CLIMB_WORDS = ("클라이밍", "클밍", "볼더링", "climb", "암장", "볼더")

_GID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{13}$")
_FLIGHT_RE = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)</script>', re.S)
_DECODER = json.JSONDecoder()


class Fetcher:
    """요청 간격과 하루 요청 수 상한을 지키는 단순한 HTTP 클라이언트."""

    def __init__(self, delay: float = 1.0, budget: int = 300):
        self.delay = delay
        self.budget = budget
        self.count = 0
        self._last = 0.0

    def get(self, path_or_url: str) -> str | None:
        if self.count >= self.budget:
            return None
        url = path_or_url if path_or_url.startswith("http") else BASE + quote_path(path_or_url)
        wait = self.delay - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        self.count += 1
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": UA, "Accept-Language": "ko-KR,ko", "Accept-Encoding": "gzip"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    self._last = time.monotonic()
                    body = r.read()
                    if r.headers.get("Content-Encoding") == "gzip":  # 압축해서 받아 전송량을 줄인다
                        body = gzip.decompress(body)
                    return body.decode("utf-8", "replace")
            except Exception as e:  # noqa: BLE001 - 네트워크 오류는 건너뛰고 계속
                self._last = time.monotonic()
                if attempt == 2:
                    print(f"  ! 요청 실패 {url}: {e}")
                    return None
                time.sleep(2 * (attempt + 1))
        return None


def quote_path(path: str) -> str:
    return urllib.parse.quote(path, safe="/?=&%")


def flight_data(html: str) -> str:
    """페이지에 심어진 Next.js 데이터 조각을 이어 붙인 문자열."""
    return "".join(json.loads(c) for c in _FLIGHT_RE.findall(html))


def _decode_after(text: str, key: str):
    i = text.find(key)
    if i < 0:
        return None
    try:
        value, _ = _DECODER.raw_decode(text, i + len(key))
        return value
    except ValueError:
        return None


def group_items(flight: str) -> list[dict]:
    """검색/추천/비슷한 모임 목록에 나오는 모임 카드(gid, gn, it2, 지역)를 모두 찾는다."""
    found: dict[str, dict] = {}
    for m in re.finditer(r'\{"(?:id|gid|gn)":"', flight):
        try:
            obj, _ = _DECODER.raw_decode(flight, m.start())
        except ValueError:
            continue
        if not isinstance(obj, dict) or "gn" not in obj or "jms" in obj:
            continue
        gid = obj.get("gid") or obj.get("id")
        if isinstance(gid, str) and _GID_RE.match(gid):
            found[gid] = _card(obj, gid)
    return list(found.values())


def _card(obj: dict, gid: str | None = None) -> dict:
    return {
        "gid": gid or obj["gid"],
        "gn": obj.get("gn", ""),
        "ge": (obj.get("ge") or "")[:200],
        "it2": obj.get("it2"),
        "loc1n": obj.get("loc1n", ""),
        "loc2n": obj.get("loc2n", ""),
    }


def page_group_ids(html: str) -> set[str]:
    """HTML 링크에 나오는 모임 id (구조화 데이터가 없을 때의 보조 수단)."""
    ids = set(re.findall(r'href="/([0-9a-f-]{37})(?:[?"])', html))
    return {i for i in ids if _GID_RE.match(i)}


def is_climbing(item: dict) -> bool:
    if item.get("it2") == CLIMBING_IT2:
        return True
    text = f"{item.get('gn', '')} {item.get('ge', '')}".lower()
    return any(w in text for w in CLIMB_WORDS)


def _strip(html: str) -> str:
    t = re.sub(r"<[^>]+>", "|", html)
    return re.sub(r"\|[\s|]*", "|", t)


def _joined_counts(html: str, events: list[dict]) -> dict[str, tuple[int, int]]:
    """정모 카드에 표시된 '참석 / 정원'을 정모 id별로 읽는다."""
    out: dict[str, tuple[int, int]] = {}
    marks = []
    for ev in events:
        img = ev.get("imgUrl") or ""
        key = img.rsplit("/", 1)[-1] if img else ""
        pos = html.find(key) if key else -1
        if pos < 0 and ev.get("en"):
            pos = html.find(f">{ev['en']}</h3>")
        if pos >= 0:
            marks.append((pos, ev["eid"]))
    marks.sort()
    for idx, (pos, eid) in enumerate(marks):
        end = marks[idx + 1][0] if idx + 1 < len(marks) else pos + 8000
        m = re.search(r"\|(\d+)\|/\|(\d+)\|", _strip(html[pos:end]))
        if m:
            out[eid] = (int(m.group(1)), int(m.group(2)))
    return out


def parse_group_page(html: str) -> dict | None:
    """모임 페이지 → {'group': {...}, 'events': [...], 'similar': [...]}"""
    flight = flight_data(html)
    info = _decode_after(flight, '"groupInfoData":')
    if not isinstance(info, dict) or "group" not in info:
        return None
    g = info["group"]
    raw_events = [e for e in info.get("events") or [] if isinstance(e, dict) and e.get("eid")]
    joined = _joined_counts(html, raw_events)
    events = []
    for e in raw_events:
        j, cap = joined.get(e["eid"], (None, e.get("emm")))
        events.append({
            "eid": e["eid"],
            "gid": e.get("gid"),
            "date": str(e.get("e_d")),          # YYYYMMDD
            "time": f"{int(e.get('e_t') or 0):04d}",  # HHMM
            "title": e.get("en", ""),
            "place": (e.get("el") or "").strip(),
            "cost": e.get("ee", ""),
            "joined": j,
            "capacity": cap,
        })
    similar = [_card(s) for s in info.get("similarGroups") or [] if isinstance(s, dict) and s.get("gid")]
    return {
        "group": {
            "gn": g.get("gn", ""),
            "ge": (g.get("ge") or "")[:200],
            "loc1n": g.get("loc1n", ""),
            "loc2n": g.get("loc2n", ""),
            "members": g.get("gmc"),
        },
        "events": events,
        "similar": similar,
    }
