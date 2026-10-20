import datetime
import html
import re
import unicodedata

try:
    from collapsible_blocks import MODE_FIELDS_MAIN
except Exception:
    MODE_FIELDS_MAIN = []

from utils import (
    gb, gs, gi, clean_shikimori_description, clean_template_output,
    html_code, html_spoiler, html_blockquote, html_link, html_zero_link,
    FLAG_RE, SEASON_RE, YEAR_RE, CLEAN_COUNTRY_RE
)
from constants import (
    TITLE_RU_TEMPLATES, TITLE_EN_TEMPLATES, SHIKI_STATUS_MAP,
    MOCK_PREVIEW_DATA, MOCK_DESC_EN, LABELS, ANILIST_URL_TEMPLATE, SHIKIMORI_URL_TEMPLATE,
    YOUTUBE_URL_TEMPLATE, HASH_REPLACE_DEFAULT, AUTHOR_ROLES,
    VIDEO_OP_KINDS, VIDEO_ED_KINDS, VIDEO_PV_KINDS, DEFAULT_PREVIEW_TEMPLATE,
    DEFAULT_LIST_TEMPLATE, DEFAULT_POPUP_TEMPLATE, SCORE_UNKNOWN,
    DAYS, POPUP_SECTION_ID_LABEL, POPUP_SECTION_NAME_LABEL,
    TEXT_LIST_HEADER_QUERY, TEXT_LIST_HEADER_QUERY_EMPTY,
    TEXT_LIST_HEADER_ONGOING, TEXT_LIST_HEADER_ONGOING_EMPTY,
    LIMIT_LIST_CHUNK, LIMIT_CARD_TEXT, LIMIT_CARD_CAPTION, HENTAI_KEYWORDS,
    RELATIONS_RU, BOOL_DEFAULTS_FALSE, DEFAULT_LIST_NUM_CUSTOM
)

HTML_TAGS_RE = re.compile(r'<[^>]+>')
NEWLINES_RE = re.compile(r'\n{3,}')
PLACEHOLDER_RE = re.compile(r'\{([a-zA-Z0-9_]+)\}')

PROTECTED_VARS = frozenset({
    "title", "title_raw", "a", "ru1", "en1", "flag", "num", "preview", "cover"
})

class PreviewMappingProxy:
    def __init__(self, base):
        self._base = base
        um = getattr(base, "universal_mapping", {}) or {}
        self.universal_mapping = dict(um)
        self.universal_mapping["main_genres"] = dict(um.get("main_genres", {}))
        self.universal_mapping["main_tags"] = dict(um.get("main_tags", {}))

    def __getattr__(self, item):
        return getattr(self._base, item)

def format_list_num(idx=1, mode=0, custom=DEFAULT_LIST_NUM_CUSTOM):
    try:
        m = int(mode or 0)
    except Exception:
        m = 0
    if m == 0:
        return f"{idx}."
    elif m == 1:
        return str(custom or DEFAULT_LIST_NUM_CUSTOM)
    return ""

def _format_score(val):
    if val is None or str(val).strip() in ("", "?", "?/10", "None", "0", "0.0"):
        return SCORE_UNKNOWN
    try:
        f = float(val)
        return f"{f:.1f}".replace(".0", "") + "/10"
    except Exception:
        return str(val)

def _get_mapped_val(mapping_dict, key, default=""):
    val = mapping_dict.get(key)
    if val is None:
        val = mapping_dict.get("UNKNOWN", default)
    if isinstance(val, list):
        return val[0] if val else default
    return str(val) if val else default

def _map_genres(raw_genres, mapping):
    if not mapping or not hasattr(mapping, "universal_mapping"):
        return raw_genres or []
    um = mapping.universal_mapping or {}
    main_g = um.get("main_genres") or {}
    add_g = um.get("additional_genres") or {}
    out = []
    for g in raw_genres or []:
        tr = main_g.get(g) or add_g.get(g) or [g]
        out.append(tr[0] if isinstance(tr, list) else tr)
    return out

def truncate_text(text, limit):
    if not text or len(text) <= limit:
        return text
    return text[:limit - 3] + "..."

def has_link(val):
    if not val:
        return False
    return bool(re.search(r'https?://|<a\s+[^>]*href', str(val), re.IGNORECASE))

def calc_plain_len(text):
    if not text:
        return 0
    clean = HTML_TAGS_RE.sub('', str(text))
    return len(html.unescape(clean))

def is_hentai_item(item):
    if not item:
        return False
    for k in HENTAI_KEYWORDS:
        for g in item.get("genres") or []:
            name = g.get("name") if isinstance(g, dict) else g
            if k in str(name).lower():
                return True
    return False

def parse_anilist_media_list(media, mapping):
    results = []
    um = mapping.universal_mapping if mapping and hasattr(mapping, "universal_mapping") else {}
    countries = um.get("countries") or {}
    seasons = um.get("seasons") or {}
    formats = um.get("formats") or {}
    flags = um.get("flags") or {}
    for m in media:
        t = m.get("title") or {}
        title = t.get("userPreferred") or t.get("romaji") or t.get("english") or t.get("native") or ""
        code = m.get("countryOfOrigin") or "UNKNOWN"
        flag = _get_mapped_val(flags, code)
        cname = _get_mapped_val(countries, code)
        season = m.get("season")
        year = m.get("seasonYear")
        sname = _get_mapped_val(seasons, season) if season else ""
        s_line = f"{sname} {year}" if sname and year else (str(year) if year else "")
        geo_str = f"{flag} {cname}".strip() if (flag or cname) else ""
        country_line = f"{geo_str}, {s_line}" if (geo_str and s_line) else (geo_str or s_line)
        score_val = m.get("averageScore")
        fmt = m.get("format", "")
        ci = m.get("coverImage") or {}
        cover_url = ci.get("extraLarge") or ci.get("large") or ci.get("medium") or ""
        raw_id = m.get("id")
        if not cover_url and raw_id is not None:
            cover_url = f"{LABELS['anilist_media_img']}{raw_id}"
        banner_url = m.get("bannerImage") or ""
        episodes = m.get("episodes")
        status = m.get("status")
        nae = m.get("nextAiringEpisode") or {}
        episodes_aired = episodes if status == "FINISHED" else (int(nae["episode"]) - 1 if nae and nae.get("episode") and int(nae.get("episode", 0)) > 1 else (0 if nae and nae.get("episode") else None))
        results.append({
            "id": raw_id,
            "al_id": str(raw_id) if raw_id is not None else "",
            "al_url": ANILIST_URL_TEMPLATE.format(raw_id) if raw_id is not None else "",
            "title": title,
            "genres": _map_genres(m.get("genres"), mapping),
            "cover_url": cover_url,
            "country_line": country_line,
            "score": _format_score(score_val / 10 if score_val is not None else None),
            "type_ru": _get_mapped_val(formats, fmt, fmt),
            "source": "anilist",
            "episodes": episodes,
            "episodes_aired": episodes_aired,
            "status": status,
            "year": year,
            "season": sname,
            "banner": banner_url,
            "banner_url": banner_url,
        })
    return results

def parse_shikimori_media_list(media, mapping=None):
    results = []
    um = mapping.universal_mapping if mapping and hasattr(mapping, "universal_mapping") else {}
    fs = um.get("format_shiki") or um.get("formats") or {}
    sm = um.get("season_month") or {}
    flags = um.get("flags") or {}
    countries = um.get("countries") or {}
    for m in media:
        title = m.get("russian") or m.get("name") or ""
        poster = m.get("poster") or m.get("cover") or {}
        path = str(poster.get("originalUrl") if isinstance(poster, dict) else "").strip()
        cover_url = ""
        if path and "missing" not in path:
            if path.startswith("http"):
                cover_url = path
            elif path.startswith("//"):
                cover_url = "https:" + path
            elif path.startswith("/"):
                cover_url = LABELS["shikimori_host"] + path
            else:
                cover_url = LABELS["shikimori_host"] + "/" + path.lstrip("/")
        if not cover_url:
            cover_url = LABELS["shiki_missing_img"]
        year_val = None
        s_line = ""
        ao = m.get("airedOn") or {}
        if isinstance(ao, dict):
            year_val = ao.get("year")
            date = ao.get("date")
            if date:
                try:
                    y, mo = str(date)[:10].split("-")[:2]
                    year_val = year_val or int(y)
                    sn = sm.get(str(int(mo))) or sm.get(int(mo), "")
                    sn = sn[0] if isinstance(sn, list) and sn else (sn or "")
                    s_line = f"{sn} {year_val}" if sn and year_val else (str(year_val) if year_val else "")
                except Exception:
                    pass
        if not s_line:
            shiki_season = m.get("season")
            if shiki_season and isinstance(shiki_season, str) and "_" in shiki_season:
                parts = shiki_season.split("_")
                if len(parts) > 1 and parts[1].isdigit():
                    year_val = int(parts[1])
                    s_line = str(year_val)
            elif m.get("seasonYear"):
                year_val = m.get("seasonYear")
                s_line = str(year_val)
        code = m.get("countryOfOrigin") or m.get("country_code") or "UNKNOWN"
        flag = _get_mapped_val(flags, code)
        cname = _get_mapped_val(countries, code)
        geo_str = f"{flag} {cname}".strip() if (flag or cname) else ""
        country_line = f"{geo_str}, {s_line}" if (geo_str and s_line) else (geo_str or s_line)
        kind = str(m.get("kind") or "").split(".")[-1].lower()
        status = str(m.get("status") or "").lower()
        gens = [g.get("russian") or g.get("name") if isinstance(g, dict) else g for g in (m.get("genres") or []) if g]
        episodes = m.get("episodes")
        raw_ea = m.get("episodesAired") or m.get("episodes_aired")
        episodes_aired = episodes if status in ("released", "finished") else (int(raw_ea) if raw_ea and int(raw_ea) > 0 else None)
        raw_id = m.get("id")
        sh_url = str(m.get("url") or "").strip()
        if sh_url:
            if sh_url.startswith("//"):
                sh_url = "https:" + sh_url
            elif sh_url.startswith("/"):
                sh_url = LABELS["shikimori_host"] + sh_url
            elif not sh_url.startswith("http"):
                sh_url = LABELS["shikimori_host"] + "/" + sh_url.lstrip("/")
        elif raw_id is not None:
            sh_url = SHIKIMORI_URL_TEMPLATE.format(raw_id)
        results.append({
            "id": raw_id,
            "sh_id": str(raw_id) if raw_id is not None else "",
            "sh_url": sh_url,
            "mal_id": m.get("malId") or m.get("myanimelist_id"),
            "title": title,
            "genres": [x for x in gens if x],
            "cover_url": cover_url,
            "country_line": country_line,
            "score": _format_score(m.get("score")),
            "type_ru": _get_mapped_val(fs, kind, kind.upper() if kind else ""),
            "source": "shikimori",
            "year": year_val,
            "aired_on": (ao.get("date") if isinstance(ao, dict) else None) or m.get("aired_on") or "",
            "episodes_aired": episodes_aired,
            "episodes": episodes,
            "nextEpisodeAt": m.get("nextEpisodeAt"),
            "status": status,
            "banner": "",
            "banner_url": "",
        })
    return results

def row_from_id_data(data, shiki, mapping, prefer_shiki=False, prefer_anilist_cover=True):
    shiki_rows = parse_shikimori_media_list([shiki], mapping) if shiki else []
    anilist_rows = parse_anilist_media_list([data], mapping) if data else []
    if prefer_shiki and shiki_rows:
        row = shiki_rows[0]
        if not prefer_anilist_cover and anilist_rows:
            row["cover_url"] = anilist_rows[0]["cover_url"]
        return row
    return anilist_rows[0] if anilist_rows else (shiki_rows[0] if shiki_rows else None)

def parse_ongoing_anilist_results(media, mapping, exclude_hentai=True):
    filtered = [m for m in media if not (exclude_hentai and is_hentai_item(m))]
    raw_results = parse_anilist_media_list(filtered, mapping)
    results = []
    for i, m in enumerate(filtered):
        if i >= len(raw_results):
            break
        r = raw_results[i]
        nae = m.get("nextAiringEpisode") or {}
        air = nae.get("airingAt")
        try:
            r["day"] = datetime.datetime.utcfromtimestamp(int(air)).weekday() if air else 6
        except Exception:
            r["day"] = 6
        r["episode"] = nae.get("episode")
        r["episodes_aired"] = int(nae["episode"]) - 1 if nae.get("episode") and int(nae.get("episode", 0)) > 1 else None
        results.append(r)
    return results

def parse_ongoing_shikimori_results(raw, mapping=None, exclude_hentai=True):
    mapped = []
    for it in raw:
        anime = it.get("anime") if isinstance(it, dict) and "anime" in it else it
        if not isinstance(anime, dict):
            continue
        if exclude_hentai and is_hentai_item(anime):
            continue
        rows = parse_shikimori_media_list([anime], mapping)
        if not rows:
            continue
        r = rows[0]
        ne = it.get("next_episode") if isinstance(it, dict) else None
        ne = ne if ne is not None else anime.get("episodesAired")
        if ne is not None:
            try:
                n = int(ne)
                r["episodes_aired"] = n
                r["episode"] = n + 1 if n > 0 else None
            except Exception:
                pass
        dt = (it.get("next_episode_at") if isinstance(it, dict) else None) or anime.get("nextEpisodeAt")
        if dt:
            try:
                t = str(dt).replace("Z", "+00:00")
                try:
                    r["day"] = datetime.datetime.fromisoformat(t).weekday()
                except Exception:
                    r["day"] = datetime.datetime.strptime(str(dt)[:19], "%Y-%m-%dT%H:%M:%S").weekday()
            except Exception:
                r["day"] = 6
        else:
            r["day"] = 6
        mapped.append(r)
    return mapped

def epl(r):
    if not isinstance(r, dict):
        return ""
    ea, et = r.get("episodes_aired"), r.get("episodes")
    if ea is not None and str(ea).isdigit() and int(ea) > 0:
        return f"{int(ea)}/{int(et)} {LABELS['ep']}" if et and str(et).isdigit() and int(et) > 0 else f"{int(ea)}/? {LABELS['ep']}"
    return f"{LABELS['ep_prefix']}{r.get('episode')}" if r.get("episode") is not None else ""

def extract_geo_fields(r):
    if not isinstance(r, dict):
        return "", "", "", ""
    flag = r.get("flag") or ""
    country = r.get("country_name") or (r.get("country") if r.get("country") != "JP" else "")
    season = r.get("season_ru") or (r.get("season") if r.get("season") not in ("FALL", "WINTER", "SPRING", "SUMMER") else "")
    year_raw = r.get("year") or r.get("seasonYear") or ""
    year = str(year_raw).replace("г.", "").strip() if year_raw else ""
    cline = r.get("country_line") or ""
    if cline:
        if not flag:
            m_flag = FLAG_RE.search(cline)
            if m_flag:
                flag = m_flag.group(0)
        if not season:
            m_s = SEASON_RE.search(cline)
            if m_s:
                season = m_s.group(1).lower()
        if not year:
            m_y = YEAR_RE.search(cline)
            if m_y:
                year = m_y.group(1).replace("г.", "").strip()
        if not country or country == cline:
            clean_c = cline.replace(flag, "") if flag else cline
            country = CLEAN_COUNTRY_RE.sub("", clean_c).strip(" ,")
    return flag, country, season, year

def is_valid_ongoing_year(year, years_back=2) -> bool:
    if not year:
        return True
    try:
        return int(year) >= (datetime.datetime.now().year - years_back)
    except Exception:
        return True

def format_item(name, use_underscore, use_hash, is_spoiler=False, spoiler_format=True):
    if not name:
        return ""
    t = str(name).strip()
    if use_hash:
        chars = [" ", ".", "-"] if use_underscore else [" ", ".", "-", "'", "+"]
        for c in chars:
            t = t.replace(c, "_" if use_underscore else "")
        if use_underscore:
            for c in ["'", "+"]:
                t = t.replace(c, "")
        t = "#" + t
    elif use_underscore:
        for c in [" ", ".", "-"]:
            t = t.replace(c, "_")
    return html_spoiler(t) if is_spoiler and spoiler_format else t

def process_list(cand, sorting, scope, hash_master, under_master, comma_master, show_separators, spoiler_format, mapping, plugin=None, drop_unlisted=False):
    if not cand or not mapping:
        return ""
    sections = []
    cur_section = None
    used = set()
    if sorting:
        for key in sorting:
            is_sep = (hasattr(mapping, "separator_keys") and key in mapping.separator_keys) or key.startswith("separator_")
            if is_sep:
                if hasattr(mapping, "sep_matches_scope") and not mapping.sep_matches_scope(key, scope):
                    cur_section = None
                    continue
                raw_lbl = mapping.separator_labels.get(key, key.replace("separator_", "").replace("_", " ")) if hasattr(mapping, "separator_labels") else key.replace("separator_", "").replace("_", " ")
                if isinstance(raw_lbl, dict):
                    raw_lbl = raw_lbl.get("label", raw_lbl.get("name", ""))
                lbl = str(raw_lbl).strip() if raw_lbl else ""
                cur_section = {
                    "key": key,
                    "label": lbl,
                    "items": [],
                    "enabled": gb(plugin, f"sep_enabled_{key}", mapping.separator_enabled.get(key, True)) if plugin and hasattr(mapping, "separator_enabled") else True,
                    "under": under_master and (gb(plugin, f"underscore_sep_{key}", True)),
                    "hash": hash_master and (gb(plugin, f"hash_sep_{key}", True)),
                    "comma": comma_master and (gb(plugin, f"comma_sep_{key}", mapping.sep_comma.get(key, True)) if mapping and hasattr(mapping, "sep_comma") else gb(plugin, f"comma_sep_{key}", True)),
                }
                sections.append(cur_section)
                continue
            if key in cand:
                if cur_section is None:
                    cur_section = {"key": "default", "label": "", "items": [], "enabled": True, "under": under_master, "hash": hash_master, "comma": comma_master}
                    sections.append(cur_section)
                if cur_section["enabled"]:
                    tr, sp = cand[key]
                    fmt = format_item(tr, cur_section["under"], cur_section["hash"], sp, spoiler_format)
                    if fmt:
                        cur_section["items"].append(fmt)
                used.add(key)
    remaining_keys = [k for k in cand if k not in used]
    if remaining_keys and not drop_unlisted:
        target = cur_section if cur_section is not None else {"key": "default", "label": "", "items": [], "enabled": True, "under": under_master, "hash": hash_master, "comma": comma_master}
        if cur_section is None:
            sections.append(target)
        if target["enabled"]:
            for key in remaining_keys:
                tr, sp = cand[key]
                fmt = format_item(tr, target["under"], target["hash"], sp, spoiler_format)
                if fmt:
                    target["items"].append(fmt)
    if not show_separators:
        first_lbl = ""
        for sec in sections:
            if sec["enabled"] and sec["items"] and sec["label"]:
                first_lbl = sec["label"]
                break
        all_items = []
        for sec in sections:
            if not sec["enabled"] or not sec["items"]:
                continue
            for item in sec["items"]:
                if item:
                    all_items.append(item)
        if not all_items:
            return ""
        body = ", ".join(all_items) if comma_master else " ".join(all_items)
        if first_lbl:
            hdr = first_lbl if first_lbl.endswith(":") else f"{first_lbl}:"
            return f"{hdr} {body}"
        return body
    lines = []
    for sec in sections:
        if not sec["enabled"] or not sec["items"]:
            continue
        body = (", ".join(sec["items"]) if sec["comma"] else " ".join(sec["items"]))
        if not body:
            continue
        lbl = sec["label"]
        if lbl:
            hdr = lbl if lbl.endswith(":") else f"{lbl}:"
            lines.append(f"{hdr} {body}")
        else:
            lines.append(body)
    if not lines:
        return ""
    return "\n".join(lines)

def process_genres(plugin, data, mapping, drop_unlisted=False):
    if not data or not gb(plugin, "show_genres", True) or not mapping:
        return ""
    um = mapping.universal_mapping or {}
    main_m, add_m = um.get("main_genres", {}), um.get("additional_genres", {})
    g_like = set(main_m) | set(add_m)
    all_g = set(data.get("genres") or [])
    prom = {t["name"]: t.get("isMediaSpoiler", False) for t in (data.get("tags") or []) if isinstance(t, dict) and t.get("name") in g_like}
    all_g.update(prom.keys())
    cand = {g: ((main_m.get(g) or add_m.get(g) or [g])[0] if isinstance(main_m.get(g) or add_m.get(g) or [g], list) else (main_m.get(g) or add_m.get(g) or g), prom.get(g, False)) for g in all_g}
    is_comma = gb(plugin, "comma_genres", False) or gb(plugin, "comma_genres_main", False) or gb(plugin, "comma_genres_unlisted", False)
    return process_list(cand, list(um.get("sorting_genres", um.get("ordered_genres", []))), "genres", gb(plugin, "hash_genres", True), gb(plugin, "underscore_genres", True), is_comma, gb(plugin, "show_separators", True), gb(plugin, "spoiler_format", True), mapping, plugin=plugin, drop_unlisted=drop_unlisted)

def process_tags(plugin, data, mapping, drop_unlisted=False):
    if not data or not gb(plugin, "show_tags", True) or not mapping:
        return ""
    um = mapping.universal_mapping or {}
    main_m, add_m = um.get("main_tags", {}), um.get("additional_tags", {})
    g_like = set(um.get("main_genres", {})) | set(um.get("additional_genres", {}))
    dem = set(um.get("demographics", {}))
    all_t = {t["name"]: t.get("isMediaSpoiler", False) for t in (data.get("tags") or []) if isinstance(t, dict) and t.get("name") and t["name"] not in dem and t["name"] not in g_like}
    cand = {k: ((main_m.get(k) or add_m.get(k) or [k])[0] if isinstance(main_m.get(k) or add_m.get(k) or [k], list) else (main_m.get(k) or add_m.get(k) or k), sp) for k, sp in all_t.items()}
    is_comma = gb(plugin, "comma_tags", False) or gb(plugin, "comma_tags_main", False) or gb(plugin, "comma_tags_unlisted", False)
    return process_list(cand, list(um.get("sorting_tags", um.get("ordered_tags", []))), "tags", gb(plugin, "hash_tags", True), gb(plugin, "underscore_tags", True), is_comma, gb(plugin, "show_separators", True), gb(plugin, "spoiler_format", True), mapping, plugin=plugin, drop_unlisted=drop_unlisted)

def normalize_anime_data(data, shiki_data=None, desc_source=0):
    if not data and not shiki_data:
        return {}
    if data and isinstance(data, dict) and "ru_titles" in data:
        return data
    al, sk = data or {}, shiki_data or {}
    titles_al = al.get("title") or {}
    ru_titles, en_titles = [], []
    if sk.get("russian"):
        ru_titles.append(sk["russian"])
    for syn in (sk.get("synonyms") or []):
        if syn and re.match(r"^[А-Яа-яЁё0-9\s\W]+$", str(syn)) and syn not in ru_titles:
            ru_titles.append(syn)
    if titles_al.get("russian") and titles_al["russian"] not in ru_titles:
        ru_titles.append(titles_al["russian"])
    for t in filter(None, [titles_al.get("english"), titles_al.get("romaji"), titles_al.get("native"), titles_al.get("userPreferred")] + (al.get("synonyms") or [])):
        if re.match(r"^[A-Za-z0-9\s\W]+$", unicodedata.normalize("NFD", str(t))) and t not in en_titles:
            en_titles.append(t)
    sk_en = [sk.get("name")] + (sk.get("english") if isinstance(sk.get("english"), list) else [sk.get("english")]) + (sk.get("synonyms") or [])
    for t in filter(None, sk_en):
        if re.match(r"^[A-Za-z0-9\s\W]+$", unicodedata.normalize("NFD", str(t))) and t not in en_titles:
            en_titles.append(t)
    status_raw = al.get("status") or sk.get("status", "")
    if isinstance(status_raw, str) and status_raw.lower() in SHIKI_STATUS_MAP:
        status_raw = SHIKI_STATUS_MAP[status_raw.lower()]
    score_val = al.get("averageScore")
    score = _format_score(score_val / 10) if score_val is not None else (_format_score(sk.get("score")) if sk.get("score") is not None and str(sk.get("score")) != "" else SCORE_UNKNOWN)
    
    raw_studios = [s["name"] for s in al.get("studios", {}).get("nodes", []) if isinstance(s, dict) and s.get("name")] if al.get("studios") else [s.get("name") if isinstance(s, dict) else str(s) for s in sk.get("studios") or []]
    studios = [re.sub(r'\s*&\s*', ' and ', str(st)).strip() for st in raw_studios if st]

    shiki_desc = clean_shikimori_description(sk.get("description") or sk.get("synopsis") or "") if sk.get("description") or sk.get("synopsis") else ""
    al_desc = al.get("description") or ""
    desc = (al_desc or shiki_desc) if int(desc_source or 0) == 1 else (shiki_desc or al_desc)
    raw_title = titles_al.get("userPreferred") or titles_al.get("romaji") or titles_al.get("english") or sk.get("name") or (ru_titles[0] if ru_titles else "")
    al_id = str(al["id"]) if al.get("id") is not None else ""
    sh_id = str(sk["id"]) if sk.get("id") is not None else ""
    al_url = ANILIST_URL_TEMPLATE.format(al_id) if al_id else ""
    sh_url = str(sk.get("url") or "").strip()
    if sh_url:
        if sh_url.startswith("//"):
            sh_url = "https:" + sh_url
        elif sh_url.startswith("/"):
            sh_url = LABELS["shikimori_host"] + sh_url
        elif not sh_url.startswith("http"):
            sh_url = LABELS["shikimori_host"] + "/" + sh_url.lstrip("/")
    elif sh_id:
        sh_url = SHIKIMORI_URL_TEMPLATE.format(sh_id)

    al_genres = al.get("genres") or []
    al_tags = al.get("tags") or []
    if al_genres:
        final_genres = al_genres
    elif not al_tags and sk.get("genres"):
        final_genres = [g.get("russian") or g.get("name") for g in sk.get("genres") or [] if isinstance(g, dict)]
    else:
        final_genres = []

    return {
        "id": al_id or sh_id, "al_id": al_id, "sh_id": sh_id, "al_url": al_url, "sh_url": sh_url,
        "title": raw_title, "ru_titles": ru_titles, "en_titles": en_titles,
        "country": al.get("countryOfOrigin", "UNKNOWN"), "season": al.get("season") or sk.get("season"),
        "seasonYear": al.get("seasonYear") or sk.get("seasonYear"),
        "al_cover": f"{LABELS['anilist_media_img']}{al_id}" if al_id else (al.get("coverImage", {}).get("extraLarge") if isinstance(al.get("coverImage"), dict) else ""),
        "sh_cover": _shiki_cover(sk), "bannerImage": al.get("bannerImage"),
        "format": al.get("format") or (str(sk.get("kind")).upper() if sk.get("kind") else ""),
        "episodes": al.get("episodes") if al.get("episodes") is not None else sk.get("episodes"),
        "episodes_aired": al.get("episodes_aired") if al.get("episodes_aired") is not None else sk.get("episodesAired", sk.get("episodes_aired")),
        "status": status_raw, "score": score, "duration": al.get("duration") or sk.get("duration"),
        "source": al.get("source") or (str(sk.get("source")).upper() if sk.get("source") else ""),
        "genres": final_genres,
        "tags": al_tags, "studios": studios, "description": desc, "raw_al": al, "raw_shiki": sk,
    }

def get_sep_preview(mapping, sk, default_text=""):
    if not mapping:
        return default_text
    if hasattr(mapping, "separator_previews") and isinstance(mapping.separator_previews, dict) and sk in mapping.separator_previews:
        val = mapping.separator_previews[sk]
        return str(val).strip() if val else default_text
    um = getattr(mapping, "universal_mapping", {}) or {}
    sep_map = um.get("separator") or um.get("separators") or {}
    if isinstance(sep_map, dict) and sk in sep_map:
        val = sep_map[sk]
        raw_val = val.get("preview", default_text) if isinstance(val, dict) else (val or default_text)
        return str(raw_val).strip() if raw_val else default_text
    return default_text

def get_mock_preview_data(mapping=None, plugin=None):
    data = dict(MOCK_PREVIEW_DATA)
    data["ru_titles"] = list(MOCK_PREVIEW_DATA["ru_titles"])
    data["en_titles"] = list(MOCK_PREVIEW_DATA["en_titles"])
    desc_source = gi(plugin, "desc_source", 0, 0, 1) if plugin else 0
    if desc_source == 1:
        data["description"] = MOCK_DESC_EN
    mode = gi(plugin, "list_number_mode", 0, 0, 2) if plugin else 0
    custom = gs(plugin, "list_number_custom", DEFAULT_LIST_NUM_CUSTOM) if plugin else DEFAULT_LIST_NUM_CUSTOM
    data["num"] = format_list_num(1, mode, custom)
    data["custom"] = custom
    if not mapping or not getattr(mapping, "universal_mapping", None):
        return data
    um = mapping.universal_mapping
    main_g = um.setdefault("main_genres", {})
    main_t = um.setdefault("main_tags", {})
    sorting_g = list(um.get("sorting_genres", um.get("ordered_genres", [])))
    sorting_t = list(um.get("sorting_tags", um.get("ordered_tags", [])))

    mock_sorting_g = []
    g_set = []
    default_g_prev = get_sep_preview(mapping, "separator_genres", "жанр")
    for k in sorting_g:
        mock_sorting_g.append(k)
        if k.startswith("separator_"):
            item_k = f"mock_{k}"
            mock_sorting_g.append(item_k)
            g_set.append(item_k)
            main_g[item_k] = [get_sep_preview(mapping, k, default_g_prev)]
    if not g_set and sorting_g:
        item_k = "mock_genres"
        mock_sorting_g.append(item_k)
        g_set.append(item_k)
        main_g[item_k] = [default_g_prev]

    um["sorting_genres"] = mock_sorting_g
    data["genres"] = g_set

    mock_sorting_t = []
    t_list = []
    default_t_prev = get_sep_preview(mapping, "separator_tag", "тег")
    for k in sorting_t:
        mock_sorting_t.append(k)
        if k.startswith("separator_"):
            item_k = f"mock_{k}"
            mock_sorting_t.append(item_k)
            t_list.append({"name": item_k, "isMediaSpoiler": False})
            main_t[item_k] = [get_sep_preview(mapping, k, default_t_prev)]
    if not t_list and sorting_t:
        item_k = "mock_tag"
        mock_sorting_t.append(item_k)
        t_list.append({"name": item_k, "isMediaSpoiler": False})
        main_t[item_k] = [default_t_prev]

    um["sorting_tags"] = mock_sorting_t
    data["tags"] = t_list
    data["audience"] = extract_demographic(data, um.get("demographics", {}))
    return data

def extract_titles(plugin, data, shiki_data=None):
    ru_raw = plugin.get_setting("extra_ru_count", 1) if hasattr(plugin, "get_setting") else getattr(plugin, "extra_ru_count", 1)
    en_raw = plugin.get_setting("extra_en_count", 1) if hasattr(plugin, "get_setting") else getattr(plugin, "extra_en_count", 1)
    ru_count = max(0, int(ru_raw if ru_raw is not None else 1))
    en_count = max(0, int(en_raw if en_raw is not None else 1))
    ru = [x for x in (data.get("ru_titles", []) if data and "ru_titles" in data else ([shiki_data.get("russian")] if shiki_data and shiki_data.get("russian") else [])) if x]
    en = [x for x in (data.get("en_titles", []) if data and "en_titles" in data else ([shiki_data.get("name")] if shiki_data and shiki_data.get("name") else [])) if x]
    main_en = en[0] if en else ""
    other_en = en[1:en_count] if en_count > 1 else []
    if not ru:
        main_ru = main_en
        other_ru = []
    else:
        main_ru = ru[0]
        other_ru = ru[1:ru_count] if ru_count > 1 else []
    return main_ru, other_ru, main_en, other_en

def _shiki_cover(shiki_data):
    if not isinstance(shiki_data, dict):
        return ""
    poster = shiki_data.get("poster")
    path = (poster.get("originalUrl") or poster.get("mainUrl") or poster.get("original") or poster.get("previewUrl") or poster.get("preview") or "") if isinstance(poster, dict) else (poster or "")
    if not path:
        img = shiki_data.get("image")
        path = (img.get("original") or img.get("preview") or img.get("x96") or "") if isinstance(img, dict) else (img or "")
    path = str(path or shiki_data.get("image_url") or shiki_data.get("cover_url") or "").strip()
    if path:
        return path if path.startswith("http") else ("https:" + path if path.startswith("//") else LABELS["shikimori_io"] + ("/" + path.lstrip("/")))
    return ""

def get_cover_url(data, shiki_data=None, prefer_anilist=True):
    al = data.get("al_cover", "") if data and "al_cover" in data else (f"{LABELS['anilist_media_img']}{data.get('al_id') or data.get('id')}" if data and (data.get("al_id") or data.get("id")) else "")
    sh = data.get("sh_cover", "") if data and "sh_cover" in data else _shiki_cover(shiki_data)
    return (al or sh) if prefer_anilist else (sh or al)

def get_country_info(plugin, data, mapping, hash_main_on=True, main_on=True):
    code = data.get("countryOfOrigin", data.get("country", "UNKNOWN")) if data else "UNKNOWN"
    um = mapping.universal_mapping if mapping and hasattr(mapping, "universal_mapping") else {}
    flag = _get_mapped_val(um.get("flags") or {}, code) if (main_on and gb(plugin, "show_flag", True)) else ""
    txt = _get_mapped_val(um.get("countries") or {}, code) if (main_on and gb(plugin, "show_country", True)) else ""
    if not flag and code == "JP" and (main_on and gb(plugin, "show_flag", True)):
        flag = "🇯🇵"
    if not txt and (code == "JP" or not data) and (main_on and gb(plugin, "show_country", True)):
        txt = "Япония"
    elif not txt and data and data.get("country_name"):
        txt = data.get("country_name")
    if txt and gb(plugin, "hash_country", True) and hash_main_on:
        txt = "#" + txt
    return flag, txt, code

def get_season_year(plugin, data, shiki_data, mapping, main_on=True):
    season_val, year_val = "", ""
    show_s = main_on and gb(plugin, "show_season", True)
    show_y = main_on and gb(plugin, "show_year", True)
    if data and (show_s or show_y):
        if show_s and data.get("season"):
            s_raw = str(data.get("season")).upper()
            season_val = _get_mapped_val(mapping.universal_mapping.get("seasons") or {} if mapping and hasattr(mapping, "universal_mapping") else {}, s_raw, s_raw)
            if not season_val:
                season_val = str(data.get("season"))
        if show_y and (data.get("seasonYear") or data.get("year")):
            year_val = data.get("seasonYear") or data.get("year")
            year_val = str(year_val).replace("г.", "").strip()
    return season_val, (str(year_val) if year_val and str(year_val) != "????" else "")

def get_description(plugin, data, shiki_data=None):
    return str(data.get("description", "")).strip() if data else ""

def resolve_anime_label(plugin, main_on=True, hash_main_on=True):
    if not main_on or not gb(plugin, "show_anime_label", True):
        return gs(plugin, "hash_anime_replace", HASH_REPLACE_DEFAULT) or HASH_REPLACE_DEFAULT
    return LABELS["hash_anime_default"] if gb(plugin, "show_hash_anime", True) and hash_main_on else LABELS["anime_default"]

def extract_demographic(data, dem_map):
    if not data:
        return ""
    lookup = {str(k).lower(): (v[0] if isinstance(v, list) and v else str(v)) for k, v in (dem_map or {}).items()}
    aud = data.get("audience")
    if aud:
        aud_s = str(aud).strip()
        if aud_s.lower() in lookup:
            return lookup[aud_s.lower()]
        return aud_s
    for t in (data.get("tags") or []):
        name = str(t.get("name") if isinstance(t, dict) else t).strip().lower()
        if name in lookup:
            return lookup[name]
    for g in (data.get("genres") or []):
        name = str(g.get("name") or g.get("russian") if isinstance(g, dict) else g).strip().lower()
        if name in lookup:
            return lookup[name]
    return ""

def extract_author(data):
    raw_al = data.get("raw_al") or data
    if isinstance(raw_al, dict) and raw_al.get("staff"):
        for edge in raw_al["staff"].get("edges", []):
            role = (edge.get("role") or "").lower()
            if any(k in role for k in AUTHOR_ROLES):
                node = edge.get("node") or {}
                return node.get("name", {}).get("full") or node.get("name", {}).get("native") or ""
    return data.get("author_name") or ""

def extract_relations(data, shiki_data=None, mapping=None):
    rel_lines = []
    raw_al = data.get("raw_al") or data
    raw_sh = data.get("raw_shiki") or shiki_data
    um = mapping.universal_mapping if mapping and hasattr(mapping, "universal_mapping") else {}
    um_rel = um.get("relations") or {}
    if isinstance(raw_al, dict) and raw_al.get("relations"):
        for edge in raw_al["relations"].get("edges", []):
            raw_type = edge.get("relationType", "")
            key = str(raw_type).replace("_", " ").strip().lower()
            rel_type = um_rel.get(key) or RELATIONS_RU.get(key) or key.title()
            node = edge.get("node") or {}
            rel_id = node.get("id")
            t_dict = node.get("title") or {}
            rel_title = t_dict.get("russian") or t_dict.get("romaji") or t_dict.get("english") or ""
            if rel_id and rel_title:
                rel_lines.append(f'• {rel_type}: {html_link(ANILIST_URL_TEMPLATE.format(rel_id), rel_title)}')
    elif isinstance(raw_sh, dict) and raw_sh.get("related"):
        for rel in raw_sh.get("related") or []:
            raw_kind = rel.get("relationKind") or ""
            key = str(raw_kind).replace("_", " ").strip().lower()
            rel_kind = um_rel.get(key) or RELATIONS_RU.get(key) or key.title()
            anime_info = rel.get("anime") or {}
            rel_id = anime_info.get("id")
            rel_title = anime_info.get("russian") or anime_info.get("name") or ""
            if rel_id and rel_title:
                rel_url = anime_info.get("url") or SHIKIMORI_URL_TEMPLATE.format(rel_id)
                if rel_url and not str(rel_url).startswith("http"):
                    rel_url = LABELS["shikimori_host"] + ("" if str(rel_url).startswith("/") else "/") + str(rel_url)
                rel_lines.append(f'• {rel_kind}: {html_link(rel_url, rel_title)}')
    return html_blockquote(f'{LABELS["relations_header"]}\n' + "\n".join(rel_lines)) if rel_lines else ""

def extract_media_videos(data, shiki_data=None):
    op_list, ed_list, tr_list = [], [], []
    raw_sh = data.get("raw_shiki") or shiki_data
    if isinstance(raw_sh, dict) and raw_sh.get("videos"):
        for vid in raw_sh["videos"]:
            if not isinstance(vid, dict) or not vid.get("url"):
                continue
            v_kind, v_url, v_name = (vid.get("kind") or "").lower(), vid["url"], vid.get("name") or ""
            item_str = f'• {html_link(v_url, v_name)}' if v_name else f'• {html_link(v_url, LABELS["video"])}'
            if any(k in v_kind for k in VIDEO_OP_KINDS):
                op_list.append(item_str)
            elif any(k in v_kind for k in VIDEO_ED_KINDS):
                ed_list.append(item_str)
            elif any(k in v_kind for k in VIDEO_PV_KINDS):
                tr_list.append(item_str)
    raw_al = data.get("raw_al") or data
    if not tr_list and isinstance(raw_al, dict) and raw_al.get("trailer"):
        t = raw_al.get("trailer")
        if t.get("site") == "youtube" and t.get("id"):
            tr_list.append(f'• {html_link(YOUTUBE_URL_TEMPLATE.format(t["id"]), LABELS["trailer_yt"])}')
    return (html_blockquote(f'{LABELS["openings_header"]}\n' + "\n".join(op_list)) if op_list else "",
            html_blockquote(f'{LABELS["endings_header"]}\n' + "\n".join(ed_list)) if ed_list else "",
            html_blockquote(f'{LABELS["trailers_header"]}\n' + "\n".join(tr_list)) if tr_list else "")

def _build_row_meta(res, num=None, custom="•", mapping=None, num_mode=0):
    title = res.get("title") or (res.get("ru_titles")[0] if res.get("ru_titles") else "—")
    raw_id = res.get("id")
    um = mapping.universal_mapping if mapping and hasattr(mapping, "universal_mapping") else {}
    flag, country, season, year = extract_geo_fields(res)
    if not flag:
        flag = _get_mapped_val(um.get("flags") or {}, res.get("country", ""), "") or ("🇯🇵" if res.get("country") == "JP" else "")
    if not country:
        country = _get_mapped_val(um.get("countries") or {}, res.get("country", ""), "") or ("Япония" if res.get("country") == "JP" else "")
    if not season and res.get("season"):
        s_val = str(res.get("season")).upper()
        season = _get_mapped_val(um.get("seasons") or {}, s_val, s_val)
    if not year and (res.get("seasonYear") or res.get("year")):
        y_val = str(res.get("seasonYear") or res.get("year")).replace("г.", "").strip()
        year = str(y_val) if y_val else ""
    fmt_raw = res.get("format") or ""
    fmt_tr = _get_mapped_val(um.get("formats") or um.get("format_shiki") or {}, fmt_raw, res.get("type_ru") or fmt_raw)
    st_raw = res.get("status", "")
    st_tr = _get_mapped_val(um.get("status") or {}, SHIKI_STATUS_MAP.get(str(st_raw).lower(), st_raw), str(st_raw))
    gens = res.get("genres") or []
    if isinstance(gens, list) and mapping:
        gens = _map_genres(gens, mapping)
    genres_text = ", ".join(gens) if isinstance(gens, list) else str(gens or "")
    c_url = res.get("cover_url") or res.get("al_cover") or res.get("sh_cover") or ""
    b_url = res.get("banner_url") or res.get("bannerImage") or ""
    link_url = res.get("sh_url") or res.get("al_url") or ""
    if not link_url and raw_id:
        if res.get("source") == "shikimori" or "shikimori" in str(res.get("url", "")).lower() or res.get("is_shiki"):
            link_url = res.get("url") or SHIKIMORI_URL_TEMPLATE.format(raw_id)
        else:
            link_url = ANILIST_URL_TEMPLATE.format(raw_id)
    ep_str = epl(res) or (f"{res.get('episodes_aired')}/{res.get('episodes')} {LABELS['ep']}" if res.get("episodes_aired") and res.get("episodes") else (f"{res.get('episodes')} {LABELS['ep']}" if res.get("episodes") else "?"))
    raw_sc = res.get("score")
    score_out = str(raw_sc) if raw_sc and raw_sc != "?" else SCORE_UNKNOWN

    if num is not None:
        idx = int(num) if str(num).isdigit() else 1
        num_str = format_list_num(idx, num_mode, custom)
    else:
        num_str = str(res.get("num", ""))

    return {
        "num": num_str,
        "custom": custom or str(res.get("custom", DEFAULT_LIST_NUM_CUSTOM)),
        "title": f"<code>{title}</code>",
        "title_raw": title,
        "id": f"<code>{raw_id}</code>" if raw_id else "",
        "format": fmt_tr,
        "type_ru": fmt_tr,
        "status": st_tr,
        "score": score_out,
        "episodes": ep_str,
        "season": season,
        "year": year,
        "genres": genres_text,
        "country": country,
        "flag": flag,
        "cover": f'<a href="{c_url}">обложка</a>' if c_url else "",
        "banner": f'<a href="{b_url}">баннер</a>' if b_url else "",
        "link": f'<a href="{link_url}">ссылка</a>' if link_url else "",
    }

def build_template_vars(plugin, data, shiki_data=None, mapping=None, no_link=False, no_preview=False, num=None, drop_unlisted=False):
    desc_source = gi(plugin, "desc_source", 0, 0, 1) if plugin else 0
    if not data or "ru_titles" not in data:
        data = normalize_anime_data(data, shiki_data, desc_source=desc_source)
        shiki_data = None
    main_on = gb(plugin, "coll_fields_main", True)
    extra_on = gb(plugin, "coll_fields_extra", False)
    hash_main_on = gb(plugin, "coll_hash_main", True)
    under_main_on = gb(plugin, "coll_under_main", True)

    f_main = lambda attr, d=True: main_on and gb(plugin, attr, False if attr in BOOL_DEFAULTS_FALSE else d)
    f_extra = lambda attr, d=True: extra_on and gb(plugin, attr, False if attr in BOOL_DEFAULTS_FALSE else d)

    is_ep_main = any(k == "show_episodes" for _, k in MODE_FIELDS_MAIN)
    is_sc_main = any(k == "show_score" for _, k in MODE_FIELDS_MAIN)
    show_ep = f_main("show_episodes") if is_ep_main else f_extra("show_episodes")
    show_sc = f_main("show_score") if is_sc_main else f_extra("show_score")

    main_ru, other_ru, main_en, other_en = extract_titles(plugin, data, shiki_data)
    raw_id = str(data.get("id")) if data and data.get("id") else ""
    cov_src = gi(plugin, "cover_source", 0, 0, 1) if plugin else 0
    cover = get_cover_url(data, shiki_data, prefer_anilist=(cov_src == 0))
    preview = "" if no_preview or no_link or not f_main("show_preview") else html_zero_link(cover)
    cover_val = f'{html_link(cover, LABELS["cover"])}{html_zero_link(cover)}' if (f_extra("show_cover") and cover and not no_preview) else (html_link(cover, LABELS["cover"]) if (f_extra("show_cover") and cover) else "")
    banner = f'{html_link(data.get("bannerImage"), LABELS["banner"])}{html_zero_link(data.get("bannerImage"))}' if f_extra("show_banner") and data and data.get("bannerImage") and not no_preview else (html_link(data.get("bannerImage"), LABELS["banner"]) if f_extra("show_banner") and data and data.get("bannerImage") else "")
    author_name = data.get("author_name") or (extract_author(data) if f_extra("show_author") else "")
    author_text = format_item(author_name, gb(plugin, "underscore_author", True) and under_main_on, gb(plugin, "hash_author", True) and hash_main_on) if (f_extra("show_author") and author_name) else ""
    flag, country_text, _ = get_country_info(plugin, data, mapping, hash_main_on, main_on)
    season, year = get_season_year(plugin, data, shiki_data, mapping, main_on)
    year_clean = str(year).replace("г.", "").strip() if year else ""
    year_text = year_clean if f_main("show_year") else ""
    
    ep_str = ""
    if show_ep:
        ea, et, st_raw = data.get("episodes_aired"), data.get("episodes"), data.get("status", "")
        if st_raw == "FINISHED" and et:
            ep_str = f"{et}/{et} {LABELS['ep']}"
        elif ea is not None and int(ea) >= 0:
            ep_str = f"{ea}/{int(et)} {LABELS['ep']}" if et and int(et) > 0 else f"{ea}/? {LABELS['ep']}"
        elif et:
            ep_str = f"?/{int(et)} {LABELS['ep']}" if st_raw == "RELEASING" else f"{int(et)} {LABELS['ep']}"
        else:
            ep_str = f"? {LABELS['ep']}"
            
    fmt_raw = data.get("format") or ""
    um = mapping.universal_mapping if mapping and hasattr(mapping, "universal_mapping") else {}
    fmt_tr = _get_mapped_val(um.get("formats") or um.get("format_shiki") or {}, fmt_raw, fmt_raw)
    fmt_text = format_item(fmt_tr, gb(plugin, "underscore_format", True) and under_main_on, gb(plugin, "hash_format", True) and hash_main_on) if f_main("show_format") and fmt_tr else ""
    if gb(plugin, "ona_clarify", False) and str(fmt_raw).upper() == "ONA":
        eps = data.get("episodes")
        ona = LABELS["movie"] if eps == 1 else (LABELS["series"] if eps and eps > 1 else "")
        if ona:
            fmt_text += " " + format_item(_get_mapped_val(um.get("formats_extra") or {}, ona, ona), gb(plugin, "underscore_format", True) and under_main_on, gb(plugin, "hash_format", True) and hash_main_on)
    dem_tr = extract_demographic(data, um.get("demographics", {}))
    show_aud = f_main("show_demographic")
    if show_aud:
        dem_val = dem_tr if dem_tr else "отсутствует"
        dem_text = format_item(dem_val, gb(plugin, "underscore_demographic", False) and under_main_on, gb(plugin, "hash_demographic", True) and hash_main_on)
    else:
        dem_text = ""
    genres_str = process_genres(plugin, data, mapping, drop_unlisted=drop_unlisted) if (data and gb(plugin, "show_genres", True) and mapping) else ""
    tags_str = process_tags(plugin, data, mapping, drop_unlisted=drop_unlisted) if (data and gb(plugin, "show_tags", True) and mapping) else ""
    st_raw = data.get("status", "")
    st_tr = _get_mapped_val(um.get("status") or {}, SHIKI_STATUS_MAP.get(str(st_raw).lower(), st_raw), str(st_raw).lower()) if st_raw else ""
    st_text = format_item(str(st_tr), gb(plugin, "underscore_status", True) and under_main_on, gb(plugin, "hash_status", True) and hash_main_on) if f_extra("show_status") and st_tr else ""
    src_raw = data.get("source") if data else ""
    src_tr = _get_mapped_val(um.get("source") or {}, src_raw, src_raw.lower() if src_raw else "")
    src_text = format_item(src_tr, gb(plugin, "underscore_source", True) and under_main_on, gb(plugin, "hash_source", True) and hash_main_on) if f_extra("show_source") and src_tr else ""
    studios = ""
    if f_extra("show_studios") and data.get("studios"):
        stud_f = [format_item(sn, gb(plugin, "underscore_studios", True) and under_main_on, gb(plugin, "hash_studios", True) and hash_main_on) for sn in data.get("studios")]
        is_comma_studios = gb(plugin, "comma_studios", True) and (gb(plugin, "coll_comma_main", True))
        studios = (", " if is_comma_studios else " ").join(stud_f)
    al_link_title = gs(plugin, "anilist_link_text", "AniList") or "AniList"
    sh_link_title = gs(plugin, "shikimori_link_text", "Shikimori") or "Shikimori"
    al_url = data.get("al_url") or (ANILIST_URL_TEMPLATE.format(data["al_id"]) if data.get("al_id") else "")
    sh_url = data.get("sh_url") or (SHIKIMORI_URL_TEMPLATE.format(data["sh_id"]) if data.get("sh_id") else "")
    link1 = html_link(al_url, al_link_title) if (not no_link) and f_main("show_link_in_full", False) and al_url else ""
    link2 = html_link(sh_url, sh_link_title) if (not no_link) and f_main("show_shikimori_link", False) and sh_url else ""
    desc = get_description(plugin, data, shiki_data)
    desc_val = ""
    if f_main("show_description", False) and desc:
        desc_val = html_blockquote(desc) if gb(plugin, "enable_html_card", True) else desc
    relations_text = (data.get("relations") or extract_relations(data, shiki_data, mapping)) if f_extra("show_relations") else ""
    opening_text, ending_text, trailer_text = data.get("opening") or "", data.get("ending") or "", data.get("trailer") or ""
    if (f_extra("show_opening") and not opening_text) or (f_extra("show_ending") and not ending_text) or (f_extra("show_trailer") and not trailer_text):
        op_t, ed_t, tr_t = extract_media_videos(data, shiki_data)
        opening_text = opening_text or op_t
        ending_text = ending_text or ed_t
        trailer_text = trailer_text or tr_t
    title_val = data.get("title") or main_ru or main_en or ""
    
    score_clean = data.get("score")
    score_str = (str(score_clean) if score_clean and score_clean != "?" else SCORE_UNKNOWN) if show_sc else ""

    num_mode = gi(plugin, "list_number_mode", 0, 0, 2) if plugin else 0
    custom_mark = gs(plugin, "list_number_custom", DEFAULT_LIST_NUM_CUSTOM) if plugin else DEFAULT_LIST_NUM_CUSTOM
    num_val = format_list_num(num if num is not None else 1, num_mode, custom_mark)

    res_vars = {
        "num": num_val,
        "custom": custom_mark,
        "preview": preview, "cover": cover_val, "a": resolve_anime_label(plugin, main_on, hash_main_on),
        "title": html_code(title_val), "title_raw": title_val,
        "flag": flag if f_main("show_flag") else "",
        "country": country_text if f_main("show_country") else "",
        "season": season if f_main("show_season") else "",
        "year": year_text,
        "format": fmt_text, "audience": dem_text, "demographic": dem_text, "genres": genres_str, "tags": tags_str,
        "episodes": ep_str, "score": score_str,
        "status": st_text, "duration": f"{data.get('duration')} {LABELS['min']}" if f_extra("show_duration") and data.get("duration") else "",
        "source": src_text, "studios": studios, "link": link2 or link1, "link1": link1, "link2": link2,
        "description": desc_val, "id": html_code(raw_id) if (f_extra("show_id") and raw_id) else "",
        "banner": banner, "author": author_text, "relations": relations_text,
        "opening": opening_text if f_extra("show_opening") else "",
        "ending": ending_text if f_extra("show_ending") else "",
        "trailer": trailer_text if f_extra("show_trailer") else "",
    }
    ru_list = [main_ru] + other_ru if main_ru else []
    en_list = [main_en] + other_en if main_en else []
    for i in range(5):
        t_ru = gs(plugin, f"tpl_ru{i+1}", TITLE_RU_TEMPLATES[i])
        t_en = gs(plugin, f"tpl_en{i+1}", TITLE_EN_TEMPLATES[i])
        res_vars[f"ru{i+1}"] = t_ru.format(title=ru_list[i]) if i < len(ru_list) and ru_list[i] else ""
        res_vars[f"en{i+1}"] = t_en.format(title=en_list[i]) if i < len(en_list) and en_list[i] else ""
    if no_link:
        for k, v in list(res_vars.items()):
            if has_link(v):
                res_vars[k] = ""
    return res_vars

def format_mini_template(template, kwargs):
    return clean_template_output(template, kwargs) if template else ""

def format_media_full(plugin, data, template, shiki_data=None, mapping=None, no_link=False, no_preview=False, max_len=None, card_send_mode=None):
    if not data and not shiki_data:
        return ""
    if card_send_mode is None:
        card_send_mode = gi(plugin, "card_send_mode", 0, 0, 1) if plugin else 0
    if max_len is None:
        max_len = LIMIT_CARD_CAPTION if (no_link or int(card_send_mode or 0) == 1) else LIMIT_CARD_TEXT
    vd = build_template_vars(plugin, data, shiki_data, mapping, no_link=no_link, no_preview=no_preview)
    lbl = vd.get("a", "")
    def render():
        res = clean_template_output(template, vd)
        if "#аниме" in res and lbl != "#аниме":
            res = res.replace("#аниме", lbl)
        return NEWLINES_RE.sub("\n\n", res).strip()
    cur = render()
    cur_len = calc_plain_len(cur)
    if not max_len or cur_len <= max_len:
        return cur
    overflow = cur_len - max_len
    if vd.get("description"):
        desc_len = calc_plain_len(vd["description"])
        if overflow > 150 or desc_len >= overflow:
            vd["description"] = ""
            cur = render()
            cur_len = calc_plain_len(cur)
            if cur_len <= max_len:
                return cur
            overflow = cur_len - max_len
    for k in ("relations", "trailer", "ending", "opening"):
        if vd.get(k):
            vd[k] = ""
            cur = render()
            cur_len = calc_plain_len(cur)
            if cur_len <= max_len:
                return cur
            overflow = cur_len - max_len
    if data and gb(plugin, "show_tags", True) and mapping and vd.get("tags"):
        t_clean = process_tags(plugin, data, mapping, drop_unlisted=True)
        if t_clean != vd.get("tags"):
            vd["tags"] = t_clean
            cur = render()
            cur_len = calc_plain_len(cur)
            if cur_len <= max_len:
                return cur
            overflow = cur_len - max_len
    if data and gb(plugin, "show_genres", True) and mapping and vd.get("genres"):
        g_clean = process_genres(plugin, data, mapping, drop_unlisted=True)
        if g_clean != vd.get("genres"):
            vd["genres"] = g_clean
            cur = render()
            cur_len = calc_plain_len(cur)
            if cur_len <= max_len:
                return cur
            overflow = cur_len - max_len
    if vd.get("description"):
        vd["description"] = ""
        cur = render()
        cur_len = calc_plain_len(cur)
        if cur_len <= max_len:
            return cur
    matches = PLACEHOLDER_RE.findall(template)
    seen = set()
    ordered = [m for m in reversed(matches) if not (m in seen or seen.add(m)) and m not in PROTECTED_VARS]
    for k in ordered:
        if vd.get(k):
            vd[k] = ""
            cur = render()
            if calc_plain_len(cur) <= max_len:
                return cur
    return cur

def resolve_card_options(plugin, data, shiki=None, opts=None, mapping=None):
    opts = opts or {}
    raw_mode = opts.get("card_send_mode")
    if raw_mode is None:
        raw_mode = gi(plugin, "card_send_mode", 0, 0, 1) if plugin else 0
    raw_mode = int(raw_mode)
    no_link = bool(opts.get("no_link", False))
    main_on = gb(plugin, "coll_fields_main", True)
    show_preview = main_on and gb(plugin, "show_preview", True)
    is_media = show_preview if no_link else (raw_mode == 1)
    cov_src = gi(plugin, "cover_source", 0, 0, 1) if plugin else 0
    prefer_al = (cov_src == 0)
    cover = get_cover_url(data, shiki, prefer_anilist=prefer_al) or get_cover_url(data, shiki, prefer_anilist=not prefer_al)
    temp_pos = int(opts.get("temp_pos") or 0)
    if temp_pos == 1:
        invert = True
    elif temp_pos == 2:
        invert = False
    else:
        pos_key = "media_pos" if is_media else "preview_pos"
        pos_val = gi(plugin, pos_key, 0, 0, 1) if plugin else 0
        invert = (pos_val == 1)
    max_len = LIMIT_CARD_CAPTION if (no_link or is_media) else LIMIT_CARD_TEXT
    card_template = plugin.card_template if hasattr(plugin, "card_template") else gs(plugin, "card_template", "")
    card_text = format_media_full(plugin, data, card_template, shiki_data=shiki, mapping=mapping, no_link=no_link, no_preview=(is_media or no_link), max_len=max_len, card_send_mode=(1 if is_media else 0))
    return {
        "text": card_text,
        "is_media": is_media,
        "cover_url": cover,
        "invert": invert,
        "no_link": no_link,
        "max_len": max_len,
    }

def format_row_output(data, template, mapping=None, num=None, custom=DEFAULT_LIST_NUM_CUSTOM, strip_html=False, num_mode=0):
    if not data:
        return ""
    meta = _build_row_meta(data, num=num, custom=custom, mapping=mapping, num_mode=num_mode)
    res = format_mini_template(template, meta)
    return HTML_TAGS_RE.sub("", res) if strip_html else res

def format_popup(plugin, data, template, shiki_data=None, mapping=None, num=None):
    mode = gi(plugin, "list_number_mode", 0, 0, 2) if plugin else 0
    custom = gs(plugin, "list_number_custom", DEFAULT_LIST_NUM_CUSTOM) if plugin else DEFAULT_LIST_NUM_CUSTOM
    return format_row_output(data or shiki_data, template, mapping=mapping, num=num, custom=custom, strip_html=True, num_mode=mode)

def format_text_output(plugin, data, template, shiki_data=None, mapping=None, num=None):
    mode = gi(plugin, "list_number_mode", 0, 0, 2) if plugin else 0
    custom = gs(plugin, "list_number_custom", DEFAULT_LIST_NUM_CUSTOM) if plugin else DEFAULT_LIST_NUM_CUSTOM
    return format_row_output(data or shiki_data, template, mapping=mapping, num=num, custom=custom, strip_html=False, num_mode=mode)

def get_template_preview(plugin, template_type, template=None, mapping=None):
    mock_mapping = PreviewMappingProxy(mapping) if (mapping and getattr(mapping, "universal_mapping", None)) else mapping
    data = get_mock_preview_data(mock_mapping, plugin=plugin)
    mode = gi(plugin, "list_number_mode", 0, 0, 2) if plugin else 0
    custom = gs(plugin, "list_number_custom", DEFAULT_LIST_NUM_CUSTOM) if plugin else DEFAULT_LIST_NUM_CUSTOM
    if template_type == "card":
        tpl = template or getattr(plugin, "card_template", None) or gs(plugin, "card_template", "") or DEFAULT_PREVIEW_TEMPLATE
        return format_media_full(plugin, data, tpl, None, mock_mapping)
    if template_type == "list":
        tpl = template or getattr(plugin, "list_template", None) or gs(plugin, "list_template", "") or DEFAULT_LIST_TEMPLATE
        return format_row_output(data, tpl, mapping=mock_mapping, num=1, custom=custom, strip_html=False, num_mode=mode)
    if template_type == "popup":
        tpl = template or getattr(plugin, "popup_template", None) or gs(plugin, "popup_template", "") or DEFAULT_POPUP_TEMPLATE
        return format_row_output(data, tpl, mapping=mock_mapping, num=1, custom=custom, strip_html=True, num_mode=mode)
    return ""

def get_preview_text(plugin, template=None, mapping=None):
    return get_template_preview(plugin, "card", template=template, mapping=mapping)

def get_preview_cover(plugin, mapping=None):
    cov_src = gi(plugin, "cover_source", 0, 0, 1) if plugin else 0
    return get_cover_url(MOCK_PREVIEW_DATA, None, prefer_anilist=(cov_src == 0))

def format_popup_row_subtitle(res, template, mapping=None):
    return format_row_output(res, template, mapping=mapping, strip_html=True)

def build_list_text_chunks(results, selected_indices, query, src_label, ongoing, list_template, list_num_custom=DEFAULT_LIST_NUM_CUSTOM, mapping=None, list_num_mode=0, *args, **kwargs):
    if isinstance(mapping, int):
        list_num_mode = mapping
        mapping = kwargs.get("mapping")
    o = sorted(selected_indices)
    if not o:
        return []
    header = (TEXT_LIST_HEADER_ONGOING if ongoing else TEXT_LIST_HEADER_QUERY).format(src=src_label, q=query) if query else (TEXT_LIST_HEADER_ONGOING_EMPTY if ongoing else TEXT_LIST_HEADER_QUERY_EMPTY).format(src=src_label)
    parts = [header]
    counter = [0]
    def add_title(res_dict):
        counter[0] += 1
        return format_row_output(res_dict, list_template, mapping=mapping, num=counter[0], custom=list_num_custom, strip_html=False, num_mode=list_num_mode)
    if ongoing:
        by = {}
        for i in o:
            if 0 <= i < len(results):
                r = results[i]
                d = r.get("day")
                if d is None or not isinstance(d, int) or d < 0 or d > 6:
                    d = 6
                by.setdefault(d, []).append(r)
        for d in range(7):
            if d not in by:
                continue
            mono = "\n".join(filter(None, (add_title(tt) for tt in by[d])))
            if mono:
                parts.append(DAYS[d])
                parts.append(f"<blockquote expandable>{mono}</blockquote>")
    else:
        has_id = any(results[i].get("_section") == "id" for i in o if 0 <= i < len(results))
        has_name = any(results[i].get("_section") == "name" for i in o if 0 <= i < len(results))
        if has_id and has_name:
            id_items = [results[i] for i in o if 0 <= i < len(results) and results[i].get("_section") == "id"]
            name_items = [results[i] for i in o if 0 <= i < len(results) and results[i].get("_section") == "name"]
            if id_items:
                parts.append(POPUP_SECTION_ID_LABEL)
                parts.append(f"<blockquote expandable>{chr(10).join(filter(None, (add_title(tt) for tt in id_items)))}</blockquote>")
            if name_items:
                parts.append(POPUP_SECTION_NAME_LABEL)
                parts.append(f"<blockquote expandable>{chr(10).join(filter(None, (add_title(tt) for tt in name_items)))}</blockquote>")
        else:
            items = [results[i] for i in o if 0 <= i < len(results)]
            parts.append(f"<blockquote expandable>{chr(10).join(filter(None, (add_title(tt) for tt in items)))}</blockquote>")
    chunks = []
    cur = []
    cur_len = 0
    for part in parts:
        pl = calc_plain_len(part) + 1
        if cur and cur_len + pl > LIMIT_LIST_CHUNK:
            chunks.append("\n".join(cur))
            cur = [part]
            cur_len = pl
        else:
            cur.append(part)
            cur_len += pl
    if cur:
        chunks.append("\n".join(cur))
    return chunks