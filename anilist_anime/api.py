import time
from datetime import datetime
import requests
from constants import (
    ANILIST_GRAPHQL_URL, QUERIES, SHIKIMORI_GRAPHQL_URL,
    SHIKI_QSS, SHIKI_QID, SHIKI_QSO, SHIKI_QSO2,
)

_H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://anilist.co",
    "Referer": "https://anilist.co/",
}

_session = requests.Session()
_session.headers.update(_H)

def gql(url, q, v, tag="api", rt=2):
    for i in range(rt + 1):
        try:
            r = _session.post(url, json={"query": q, "variables": v}, timeout=10)
            sc = r.status_code
            if sc == 403:
                return None, tag + "_disabled"
            if sc == 429:
                if i < rt:
                    time.sleep(1)
                    continue
                return None, tag + "_rate"
            try:
                d = r.json()
            except Exception:
                d = None
            if d:
                if d.get("errors") and not d.get("data"):
                    return None, tag + "_error"
                if d.get("data"):
                    return d.get("data"), None
            if sc >= 400:
                return None, tag + "_error"
            return {}, None
        except Exception:
            if i == rt:
                return None, tag + "_error"
            time.sleep(0.5)
    return None, tag + "_error"

def _norm_anilist(item):
    if not item:
        return item
    if isinstance(item, list):
        return [_norm_anilist(i) for i in item]
    return item

def fetch_anilist_data(query_str, variables):
    d, e = gql(ANILIST_GRAPHQL_URL, query_str, variables, "anilist")
    if e or not d:
        return None
    if "Media" in d:
        return _norm_anilist(d["Media"])
    if "Page" in d and d["Page"].get("media"):
        return _norm_anilist(d["Page"]["media"][0])
    return None

def fetch_by_id(anime_id):
    return fetch_anilist_data(QUERIES["media"], {"id": int(anime_id)})

def fetch_by_mal_id(mal_id):
    return fetch_anilist_data(QUERIES["mal"], {"idMal": int(mal_id)})

def fetch_anilist(search):
    return fetch_anilist_data(QUERIES["search"], {"search": search})

def _norm_shiki(item):
    if not item or not isinstance(item, dict):
        return item
    if "seasonYear" not in item or not item["seasonYear"]:
        ao = item.get("airedOn") or {}
        if isinstance(ao, dict) and ao.get("year"):
            item["seasonYear"] = ao.get("year")
        else:
            shiki_season = item.get("season")
            if shiki_season and isinstance(shiki_season, str) and "_" in shiki_season:
                parts = shiki_season.split("_")
                if len(parts) > 1 and parts[1].isdigit():
                    item["seasonYear"] = int(parts[1])
    if item.get("season"):
        item["season"] = str(item["season"]).split("_")[0].upper()
    return item

def search_shikimori_by_id(aid, cache):
    ck = f"shiki_id_{aid}"
    if ck in cache:
        return cache[ck]
    d, e = gql(SHIKIMORI_GRAPHQL_URL, SHIKI_QID, {"ids": str(aid)}, "shiki")
    if e or not d:
        cache[ck] = None
        return None
    items = d.get("animes") or []
    result = _norm_shiki(items[0]) if items else None
    cache[ck] = result
    return result

def search_shikimori_gql(query):
    d, e = gql(SHIKIMORI_GRAPHQL_URL, SHIKI_QSS, {"q": query}, "shiki")
    if e:
        return None, e
    items = d.get("animes") or []
    return [_norm_shiki(i) for i in items], None

def search_shikimori(query, cache):
    q = str(query).strip()
    if q.isdigit():
        return search_shikimori_by_id(q, cache)
    ck = f"shiki_gql_{q.lower()}"
    if ck in cache:
        return cache[ck]
    items, err = search_shikimori_gql(q)
    if err or not items:
        cache[ck] = None
        return None
    result = items[0] if items else None
    cache[ck] = result
    return result

def enrich_shiki_poster(shiki, cache=None):
    if not shiki or not isinstance(shiki, dict):
        return shiki
    poster = shiki.get("poster")
    if isinstance(poster, dict) and (poster.get("originalUrl") or poster.get("mainUrl")):
        return shiki
    image = shiki.get("image")
    if isinstance(image, dict) and (image.get("original") or image.get("preview")):
        return shiki
    out = dict(shiki)
    fallback = "https://shikimori.io/assets/globals/missing/main@2x.png"
    if "poster" not in out or not out["poster"]:
        out["poster"] = {"originalUrl": fallback}
    if "image" not in out or not out["image"]:
        out["image"] = {"original": fallback, "preview": fallback}
    return out

def multi_search_anilist(query):
    d, e = gql(ANILIST_GRAPHQL_URL, QUERIES["multi_search"], {"q": query}, "anilist")
    if e or not d:
        return None
    media = d.get("Page", {}).get("media", []) or []
    return [_norm_anilist(m) for m in media]

def multi_search_anilist_genre(name, force_tag=False):
    def run(qstr):
        d, e = gql(ANILIST_GRAPHQL_URL, qstr, {"g": name}, "anilist")
        if e or not d:
            return None
        media = d.get("Page", {}).get("media", []) or []
        return [_norm_anilist(m) for m in media]
    first, second = (QUERIES["multi_tag"], QUERIES["multi_genre"]) if force_tag else (QUERIES["multi_genre"], QUERIES["multi_tag"])
    media = run(first)
    if media is None:
        return None
    if not media:
        media = run(second)
    return media

def multi_search_shikimori(query):
    q = str(query).strip()
    if q.isdigit():
        item = search_shikimori_by_id(q, {})
        return [item] if item else []
    items, err = search_shikimori_gql(q)
    if err:
        return None
    return items or []

def current_season():
    n = datetime.utcnow()
    seasons = ["WINTER", "SPRING", "SUMMER", "FALL"]
    return seasons[(n.month - 1) // 3], n.year

def fetch_ongoing_anilist(max_pages=4):
    s, y = current_season()
    out = []
    seen = set()
    for p in range(1, max_pages + 1):
        d, e = gql(ANILIST_GRAPHQL_URL, QUERIES["ongoing"], {"season": s, "year": y, "page": p}, "anilist")
        if e:
            break
        page = d.get("Page") or {}
        media = page.get("media") or []
        if not media:
            break
        for m in media:
            mid = m.get("id")
            if mid and mid not in seen:
                seen.add(mid)
                out.append(_norm_anilist(m))
        if not (page.get("pageInfo") or {}).get("hasNextPage"):
            break
    return out

def _sh_on_pages(q, vkey, vmax=4):
    out = []
    seen = set()
    err = None
    for p in range(1, vmax + 1):
        d, e = gql(SHIKIMORI_GRAPHQL_URL, q, {**vkey, "p": p}, "shiki")
        if e:
            err = e
            break
        media = d.get("animes") or []
        if not media:
            break
        for m in media:
            mid = m.get("id")
            if mid and mid not in seen:
                seen.add(mid)
                out.append(_norm_shiki(m))
        if len(media) < 50:
            break
    return out, err

def fetch_ongoing_shikimori():
    s, y = current_season()
    out, err = _sh_on_pages(SHIKI_QSO, {"s": f"{s.lower()}_{y}"})
    if not out:
        out, err = _sh_on_pages(SHIKI_QSO2, {}, 3)
    return out or []
