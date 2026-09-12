import time
from datetime import datetime
import requests

from constants import (
    ANILIST_GRAPHQL_URL, QUERIES, SHIKIMORI_GRAPHQL_URL,
    SHIKI_QSS, SHIKI_QID, SHIKI_QG, SHIKI_QSO, SHIKI_QSO2,
)

# Заголовки, имитирующие браузерный запрос для обхода защиты Cloudflare
_H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://anilist.co",
    "Referer": "https://anilist.co/",
}

def gql(url, q, v, tag="api", rt=2):
    for i in range(rt + 1):
        try:
            r = requests.post(url, json={"query": q, "variables": v}, headers=_H, timeout=10)
            sc = r.status_code
            if sc == 403:
                return None, tag + "_disabled"
            if sc == 429:
                if i < rt:
                    time.sleep(1)
                    continue
                return None, tag + "_rate"
            if sc >= 400:
                return None, tag + "_error"
            d = r.json()
            if d.get("errors") and not d.get("data"):
                return None, tag + "_error"
            return d.get("data") or {}, None
        except Exception:
            if i == rt:
                return None, tag + "_error"
            time.sleep(0.5)
    return None, tag + "_error"

def fetch_anilist_data(query_str, variables):
    d, e = gql(ANILIST_GRAPHQL_URL, query_str, variables, "anilist")
    if e or not d:
        return None
    if "Media" in d:
        return d["Media"]
    if "Page" in d and d["Page"].get("media"):
        return d["Page"]["media"][0]
    return None

def fetch_by_id(anime_id):
    return fetch_anilist_data(QUERIES["media"], {"id": int(anime_id)})

def fetch_by_mal_id(mal_id):
    return fetch_anilist_data(QUERIES["mal"], {"idMal": int(mal_id)})

def fetch_anilist(search):
    return fetch_anilist_data(QUERIES["search"], {"search": search})

def search_shikimori_by_id(aid, cache):
    ck = f"shiki_id_{aid}"
    if ck in cache:
        return cache[ck]
    d, e = gql(SHIKIMORI_GRAPHQL_URL, SHIKI_QID, {"ids": str(aid)}, "shiki")
    if e or not d:
        cache[ck] = None
        return None
    items = d.get("animes") or []
    result = items[0] if items else None
    cache[ck] = result
    return result

def search_shikimori_gql(query):
    d, e = gql(SHIKIMORI_GRAPHQL_URL, SHIKI_QSS, {"q": query}, "shiki")
    if e:
        return None, e
    return d.get("animes") or [], None

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

def fetch_shiki_cover_rest(aid, cache=None):
    """Точечный REST только за image, если GraphQL не отдал poster. Кэш по id."""
    if cache is None:
        cache = {}
    ck = f"shiki_cover_rest_{aid}"
    if ck in cache:
        return cache[ck]
    try:
        r = requests.get(
            f"https://shikimori.io/api/animes/{aid}",
            headers={"User-Agent": _H["User-Agent"], "Accept": "application/json"},
            timeout=6,
        )
        if r.status_code == 200:
            data = r.json() or {}
            img = data.get("image")
            if isinstance(img, dict) and (img.get("original") or img.get("preview")):
                cache[ck] = img
                return img
    except Exception:
        pass
    cache[ck] = None
    return None

def enrich_shiki_poster(shiki, cache=None):
    """Если в GraphQL-ответе нет poster — подтянуть image из REST один раз."""
    if not shiki or not isinstance(shiki, dict):
        return shiki
    from formatter import _shiki_cover
    if _shiki_cover(shiki):
        return shiki
    aid = shiki.get("id")
    if aid is None:
        return shiki
    img = fetch_shiki_cover_rest(aid, cache if cache is not None else {})
    if not img:
        return shiki
    out = dict(shiki)
    out["image"] = img
    return out

def multi_search_anilist(query):
    d, e = gql(ANILIST_GRAPHQL_URL, QUERIES["multi_search"], {"q": query}, "anilist")
    if e or not d:
        return None
    return d.get("Page", {}).get("media", []) or []

def multi_search_anilist_genre(name, force_tag=False):
    def run(qstr):
        d, e = gql(ANILIST_GRAPHQL_URL, qstr, {"g": name}, "anilist")
        if e or not d:
            return None
        return d.get("Page", {}).get("media", []) or []

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

def multi_search_shikimori_genre(genre_id):
    d, e = gql(SHIKIMORI_GRAPHQL_URL, SHIKI_QG, {"g": str(genre_id), "p": 1}, "shiki")
    if e or not d:
        return None
    return d.get("animes") or []

def current_season():
    n = datetime.utcnow()
    m, y = n.month, n.year
    if m in (1, 2, 3):
        return "WINTER", y
    if m in (4, 5, 6):
        return "SPRING", y
    if m in (7, 8, 9):
        return "SUMMER", y
    return "FALL", y

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
                out.append(m)
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
                out.append(m)
        if len(media) < 50:
            break
    return out, err

def fetch_ongoing_shikimori():
    s, y = current_season()
    out, err = _sh_on_pages(SHIKI_QSO, {"s": f"{s.lower()}_{y}"})
    if not out:
        out, err = _sh_on_pages(SHIKI_QSO2, {}, 3)
    return out or []
