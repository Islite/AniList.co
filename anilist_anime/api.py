import hashlib
import threading
import time
import uuid
from datetime import datetime
import requests
from android_utils import run_on_ui_thread
from client_utils import get_last_fragment
from ui.bulletin import BulletinHelper

from constants import (
    ANILIST_GRAPHQL_URL, QUERIES, SHIKIMORI_GRAPHQL_URL,
    SHIKI_QSS, SHIKI_QID, SHIKI_QSO, SHIKI_QSO2,
)

class ApiRateLimiter:
    def __init__(self, name, min_interval, max_per_minute):
        self._name = name
        self._min_interval = min_interval
        self._max_per_minute = max_per_minute
        self._history = []
        self._last_call = 0.0
        self._lock = threading.Lock()

    def current_count(self):
        with self._lock:
            now = time.time()
            self._history = [t for t in self._history if now - t < 60.0]
            return len(self._history)

    def acquire(self):
        with self._lock:
            now = time.time()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            now = time.time()
            self._history = [t for t in self._history if now - t < 60.0]
            if len(self._history) >= self._max_per_minute:
                delay = 60.0 - (now - self._history[0]) + 0.1
                if delay > 0:
                    sec = int(round(delay))
                    run_on_ui_thread(lambda: BulletinHelper.show_error(
                        f"Лимит API {self._name} превышен. Доступно через {sec} сек.",
                        get_last_fragment()
                    ))
                    time.sleep(delay)
                    run_on_ui_thread(lambda: BulletinHelper.show_success(
                        f"Лимит API {self._name} сброшен. Поиск снова доступен.",
                        get_last_fragment()
                    ))
            self._last_call = time.time()
            self._history.append(self._last_call)

_anilist_limiter = ApiRateLimiter("AniList", 0.7, 85)
_shikimori_limiter = ApiRateLimiter("Shikimori", 0.25, 85)

def get_limits_info():
    al_used = _anilist_limiter.current_count()
    sh_used = _shikimori_limiter.current_count()
    al_left = max(0, 85 - al_used)
    sh_left = max(0, 85 - sh_used)
    return f"AniList: доступно {al_left}/85 в мин.\nShikimori: доступно {sh_left}/85 в мин."

def generate_unique_user_agent(seed_key=None):
    if not seed_key:
        try:
            from org.telegram.messenger import UserConfig
            seed_key = str(UserConfig.getInstance(UserConfig.selectedAccount).getClientUserId())
        except Exception:
            seed_key = str(uuid.uuid4())
    digest = hashlib.md5(str(seed_key).encode("utf-8")).hexdigest()
    major = 120 + (int(digest[:2], 16) % 15)
    minor = 5000 + (int(digest[2:6], 16) % 2000)
    build = 100 + (int(digest[6:8], 16) % 100)
    device_id = digest[8:16]
    return f"Mozilla/5.0 (Linux; Android 14; Mobile; {device_id}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{major}.0.{minor}.{build} Mobile Safari/537.36"

_USER_AGENT = generate_unique_user_agent()

_session = requests.Session()
_session.headers.update({
    "User-Agent": _USER_AGENT,
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://anilist.co",
    "Referer": "https://anilist.co/",
})

def update_session_user_agent(new_ua):
    global _USER_AGENT
    _USER_AGENT = str(new_ua)
    _session.headers["User-Agent"] = _USER_AGENT

def get_current_user_agent():
    return _USER_AGENT

def _throttle_request(url):
    if "anilist" in url:
        _anilist_limiter.acquire()
    elif "shikimori" in url:
        _shikimori_limiter.acquire()

def gql(url, q, v, tag="api", rt=2):
    for i in range(rt + 1):
        try:
            _throttle_request(url)
            r = _session.post(url, json={"query": q, "variables": v}, timeout=10)
            sc = r.status_code
            if sc == 403:
                return None, tag + "_disabled"
            if sc == 429:
                if i < rt:
                    time.sleep(1.5)
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

def fetch_top_anilist(genres=None, tags=None):
    g_list = [g for g in (genres or []) if g]
    t_list = [t for t in (tags or []) if t]
    if g_list and t_list:
        q = QUERIES["multi_top_both"]
        v = {"genres": g_list, "tags": t_list}
    elif g_list:
        q = QUERIES["multi_top_genres"]
        v = {"genres": g_list}
    elif t_list:
        q = QUERIES["multi_top_tags"]
        v = {"tags": t_list}
    else:
        return []
    d, e = gql(ANILIST_GRAPHQL_URL, q, v, "anilist")
    if e or not d:
        return None
    media = d.get("Page", {}).get("media", []) or []
    return [_norm_anilist(m) for m in media]

def multi_search_anilist_genre(name, force_tag=False):
    if not name:
        return []
    if force_tag:
        return fetch_top_anilist(tags=[name])
    return fetch_top_anilist(genres=[name])

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