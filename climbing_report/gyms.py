"""정모 장소 글자를 암장 하나로 묶고 좌표를 붙인다.

1) gyms.json 사전(브랜드 + 지점 별칭)으로 먼저 맞춘다.
2) 사전에 없으면, KAKAO_REST_API_KEY 환경변수가 있을 때만 카카오 로컬 키워드 검색으로
   클라이밍 장소를 찾아 data/geocode_cache.json 에 저장해 둔다(같은 장소는 다시 묻지 않음).
3) 그래도 없으면 장소 글자를 다듬어 그대로 쓰고, 지도에는 표시하지 않는다.
"""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass

SHORT_REGION = {
    "서울": "서울특별시", "경기": "경기도", "인천": "인천광역시", "부산": "부산광역시",
    "대구": "대구광역시", "대전": "대전광역시", "광주": "광주광역시", "울산": "울산광역시",
    "세종": "세종특별자치시", "강원": "강원도", "강원특별자치도": "강원도", "충북": "충청북도",
    "충남": "충청남도", "전북": "전라북도", "전북특별자치도": "전라북도", "전남": "전라남도",
    "경북": "경상북도", "경남": "경상남도", "제주": "제주특별자치도", "제주특별자치도": "제주특별자치도",
}
# 장소 글자가 경기 도시 이름으로 시작하면(예: '수원', '성남 ○○') 경기권으로 본다
for _city in ("수원", "성남", "분당", "판교", "용인", "수지", "기흥", "안양", "평촌", "범계", "부천", "고양", "일산",
              "김포", "하남", "미사", "남양주", "다산", "화성", "동탄", "평택", "안산", "시흥", "광명", "의정부", "파주",
              "군포", "산본", "의왕", "오산", "이천", "구리", "광주", "양주", "포천", "과천"):
    SHORT_REGION.setdefault(_city, "경기도")


def compact(text: str) -> str:
    """비교용: 소문자, 한글·영문·숫자만 남긴다."""
    return re.sub(r"[^0-9a-z가-힣]", "", (text or "").lower())


def tidy(text: str) -> str:
    """표시용: 이모지·괄호 장식을 걷어내고 공백을 정리한다."""
    t = re.sub(r"[^\w\s가-힣()·&./-]", " ", text or "")
    return re.sub(r"\s+", " ", t).strip() or (text or "").strip()


@dataclass
class Gym:
    key: str
    name: str
    region: str | None = None
    lat: float | None = None
    lng: float | None = None
    matched: bool = True


class GymIndex:
    def __init__(self, catalog_path: str, cache_path: str):
        with open(catalog_path, encoding="utf-8") as f:
            catalog = json.load(f)
        self.brands = []
        for b in catalog["brands"]:
            gyms = []
            for g in b["gyms"]:
                name = f"{b['brand']} {g['branch']}".strip()
                gyms.append({
                    "gym": Gym(compact(name), name, g.get("region"), g.get("lat"), g.get("lng")),
                    "branch": [compact(x) for x in g.get("branch_aliases") or ([g["branch"]] if g["branch"] else [])],
                    "aliases": [compact(x) for x in g.get("aliases") or []],
                })
            self.brands.append({"brand": b["brand"], "aliases": [compact(x) for x in b["brand_aliases"]], "gyms": gyms})
        self.cache_path = cache_path
        try:
            with open(cache_path, encoding="utf-8") as f:
                self.cache = json.load(f)
        except (OSError, ValueError):
            self.cache = {}
        self.kakao_key = os.environ.get("KAKAO_REST_API_KEY", "").strip()
        self.kakao_calls = 0

    def match_title(self, title: str) -> Gym | None:
        """정모 제목에서 암장을 찾는다. 제목에는 잡다한 글자가 많아서
        '브랜드 + 지점'이 함께 있거나 줄임말(논더클 등)이 있을 때만 인정한다."""
        c = compact(title)
        best, best_score = None, (0, 0)
        for b in self.brands:
            brand_hit = max((len(a) for a in b["aliases"] if a and a in c), default=0)
            for g in b["gyms"]:
                alias_hit = max((len(a) for a in g["aliases"] if a and a in c), default=0)
                branch_hit = max((len(a) for a in g["branch"] if a and a in c), default=0)
                score = (3, alias_hit) if alias_hit else (2, brand_hit + branch_hit) if brand_hit and branch_hit else None
                if score and score > best_score:
                    best, best_score = g["gym"], score
        return best

    def match(self, place: str) -> Gym:
        c = compact(place)
        if not c:
            return Gym("", "장소 미정", matched=False)
        best, best_score = None, (0, 0)
        for b in self.brands:
            brand_hit = max((len(a) for a in b["aliases"] if a and a in c), default=0)
            for g in b["gyms"]:
                alias_hit = max((len(a) for a in g["aliases"] if a and a in c), default=0)
                branch_hit = max((len(a) for a in g["branch"] if a and a in c), default=0)
                if alias_hit:
                    score = (3, alias_hit)
                elif brand_hit and branch_hit:
                    score = (2, brand_hit + branch_hit)
                elif brand_hit and len(b["gyms"]) == 1:
                    score = (1, brand_hit)
                else:
                    continue
                if score > best_score:
                    best, best_score = g["gym"], score
        if best:
            return best
        # '왕십리', '이태원'처럼 지점 이름만 적었고 그 지점이 사전에 하나뿐이면 그 암장으로 본다
        only = [g["gym"] for b in self.brands for g in b["gyms"] if c in g["branch"]]
        if len(only) == 1:
            return only[0]
        brand = next((b for b in self.brands if any(a and a in c for a in b["aliases"])), None)
        if brand:
            regions = {g["gym"].region for g in brand["gyms"]}
            region = regions.pop() if len(regions) == 1 else None
            return Gym(compact(brand["brand"]) + "?", f"{brand['brand']} (지점 확인 안 됨)", region, matched=False)
        gym = self._lookup(place, c)
        if not gym.region:
            # '서울 마포구 …', '경기 안양시 …'처럼 장소에 지역명이 적혀 있으면 그 지역으로 본다
            first = (place or "").strip().split(" ")[0]
            gym.region = SHORT_REGION.get(first) or (first if first in SHORT_REGION.values() else None)
        return gym

    def _lookup(self, place: str, c: str) -> Gym:
        hit = self.cache.get(c)
        if hit is None and self.kakao_key and c not in self.cache and self.kakao_calls < 200:
            hit = self._kakao(place)
            self.cache[c] = hit or False
        if hit:
            return Gym(compact(hit["name"]), hit["name"], hit.get("region"), hit["lat"], hit["lng"])
        return Gym(c, tidy(place), matched=False)

    def _kakao(self, place: str) -> dict | None:
        self.kakao_calls += 1
        q = tidy(place)
        if "클라이밍" not in q:
            q += " 클라이밍"
        url = "https://dapi.kakao.com/v2/local/search/keyword.json?" + urllib.parse.urlencode({"query": q, "size": 5})
        req = urllib.request.Request(url, headers={"Authorization": f"KakaoAK {self.kakao_key}"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                docs = json.load(r).get("documents", [])
        except Exception as e:  # noqa: BLE001
            print(f"  ! 카카오 검색 실패 '{q}': {e}")
            return None
        for d in docs:
            if "클라이밍" in d.get("category_name", "") or "클라이밍" in d.get("place_name", ""):
                first = (d.get("address_name") or "").split(" ")[0]
                return {
                    "name": d["place_name"],
                    "lat": float(d["y"]),
                    "lng": float(d["x"]),
                    "region": SHORT_REGION.get(first, first) or None,
                }
        return None

    def save_cache(self):
        if self.cache:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=1, sort_keys=True)
