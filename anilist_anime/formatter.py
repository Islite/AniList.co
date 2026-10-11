import datetime
import re
import unicodedata

from utils import (
    gb, gs, clean_shikimori_description, clean_template_output,
    html_code, html_spoiler, html_blockquote, html_link, html_zero_link,
    FLAG_RE, SEASON_RE, YEAR_RE, CLEAN_COUNTRY_RE
)
from constants import (
    TITLE_RU_TEMPLATES, TITLE_EN_TEMPLATES, SHIKI_STATUS_MAP,
    MOCK_PREVIEW_DATA, LABELS, ANILIST_URL_TEMPLATE, SHIKIMORI_URL_TEMPLATE,
    YOUTUBE_URL_TEMPLATE, YEAR_SUFFIX, HASH_REPLACE_DEFAULT, AUTHOR_ROLES,
    VIDEO_OP_KINDS, VIDEO_ED_KINDS, VIDEO_PV_KINDS, DEFAULT_PREVIEW_TEMPLATE,
    DAYS, POPUP_SECTION_ID_LABEL, POPUP_SECTION_NAME_LABEL,
    TEXT_LIST_HEADER_QUERY, TEXT_LIST_HEADER_QUERY_EMPTY,
    TEXT_LIST_HEADER_ONGOING, TEXT_LIST_HEADER_ONGOING_EMPTY,
    LIMIT_LIST_CHUNK, LIMIT_CARD_TEXT, LIMIT_CARD_CAPTION
)

PROTECTED_VARS = frozenset({
    "title", "title_raw", "a", "ru1", "en1", "flag", "num", "preview", "cover"
})

class _PreviewMappingProxy:
    def __init__(self, target):
        self._target = target
        um = getattr(target, "universal_mapping", {}) or {}
        self.universal_mapping = dict(um)
        self.universal_mapping["main_genres"] = dict(um.get("main_genres", {}))
        self.universal_mapping["main_tags"] = dict(um.get("main_tags", {}))

    def __getattr__(self, name):
        return getattr(self._target, name)

def _format_score(val):
    if val is None or str(val).strip() in ("", "?", "None", "0", "0.0"):
        return "?"
    try:
        f = float(val)
        s = f"{f:.1f}".replace(".0", "")
        return f"{s}/10"
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
    main_g = mapping.universal_mapping.get("main_genres") or {}
    add_g = mapping.universal_mapping.get("additional_genres") or {}
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
    return len(re.sub(r'<[^>]+>', '', str(text)))

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
        s_line = f"{sname} {year}{YEAR_SUFFIX}" if sname and year else ""
        geo_str = f"{flag} {cname}".strip() if (flag or cname) else ""
        country_line = f"{geo_str}, {s_line}" if (geo_str and s_line) else (geo_str or s_line)
        score_val = m.get("averageScore")
        fmt = m.get("format", "")
        ci = m.get("coverImage") or {}
        cover_url = ci.get("extraLarge") or ci.get("large") or ci.get("medium") or ""
        if not cover_url and m.get("id") is not None:
            cover_url = f"{LABELS['anilist_media_img']}{m.get('id')}"
        banner_url = m.get("bannerImage") or ""
        episodes = m.get("episodes")
        status = m.get("status")
        nae = m.get("nextAiringEpisode") or {}
        episodes_aired = None
        if status == "FINISHED":
            episodes_aired = episodes
        elif nae and nae.get("episode") is not None:
            try:
                n = int(nae["episode"])
                episodes_aired = n - 1 if n > 1 else 0
            except Exception:
                pass
        results.append({
            "id": m.get("id"),
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
        path = poster.get("originalUrl") if isinstance(poster, dict) else ""
        path = str(path).strip() if path else ""
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
                    if isinstance(sn, list):
                        sn = sn[0] if sn else ""
                    if sn and year_val:
                        s_line = f"{sn} {year_val}{YEAR_SUFFIX}"
                    elif year_val:
                        s_line = f"{year_val}{YEAR_SUFFIX}"
                except Exception:
                    pass
        if not s_line:
            shiki_season = m.get("season")
            if shiki_season and isinstance(shiki_season, str) and "_" in shiki_season:
                parts = shiki_season.split("_")
                if len(parts) > 1 and parts[1].isdigit():
                    year_val = int(parts[1])
                    s_line = f"{year_val}{YEAR_SUFFIX}"
            elif m.get("seasonYear"):
                year_val = m.get("seasonYear")
                s_line = f"{year_val}{YEAR_SUFFIX}"
        code = m.get("countryOfOrigin") or m.get("country_code") or "UNKNOWN"
        flag = _get_mapped_val(flags, code)
        cname = _get_mapped_val(countries, code)
        geo_str = f"{flag} {cname}".strip() if (flag or cname) else ""
        country_line = f"{geo_str}, {s_line}" if (geo_str and s_line) else (geo_str or s_line)
        kind = str(m.get("kind") or "").split(".")[-1].lower()
        status = str(m.get("status") or "").lower()
        raw_gens = []
        for g in (m.get("genres") or []):
            if isinstance(g, dict):
                raw_gens.append(g.get("russian") or g.get("name") or "")
            elif isinstance(g, str):
                raw_gens.append(g)
        gens = [x for x in raw_gens if x]
        episodes = m.get("episodes")
        raw_ea = m.get("episodesAired") or m.get("episodes_aired")
        episodes_aired = None
        if status in ("released", "finished"):
            episodes_aired = episodes
        elif raw_ea and int(raw_ea) > 0:
            episodes_aired = int(raw_ea)
        results.append({
            "id": m.get("id"),
            "mal_id": m.get("malId") or m.get("myanimelist_id"),
            "title": title,
            "genres": gens,
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
    if anilist_rows:
        return anilist_rows[0]
    if shiki_rows:
        return shiki_rows[0]
    return None

def parse_ongoing_anilist_results(media, mapping):
    results = parse_anilist_media_list(media, mapping)
    for i, m in enumerate(media):
        if i >= len(results):
            break
        nae = m.get("nextAiringEpisode") or {}
        air = nae.get("airingAt")
        if air:
            try:
                results[i]["day"] = datetime.datetime.utcfromtimestamp(int(air)).weekday()
            except Exception:
                results[i]["day"] = None
        else:
            results[i]["day"] = None
        results[i]["episode"] = nae.get("episode")
        results[i]["episodes_aired"] = None
        if nae.get("episode") is not None:
            try:
                n = int(nae["episode"])
                results[i]["episodes_aired"] = n - 1 if n > 1 else None
            except Exception:
                pass
    return results

def parse_ongoing_shikimori_results(raw, mapping=None):
    mapped = []
    for it in raw:
        anime = it.get("anime") if isinstance(it, dict) and "anime" in it else it
        if not isinstance(anime, dict):
            continue
        rows = parse_shikimori_media_list([anime], mapping)
        if not rows:
            continue
        r = rows[0]
        sc = r.get("score")
        if not sc or sc == "?":
            continue
        ne = None
        if isinstance(it, dict):
            ne = it.get("next_episode") or anime.get("episodesAired")
        if ne is None:
            ne = anime.get("episodesAired")
        if ne is not None:
            try:
                n = int(ne)
                r["episodes_aired"] = n
                r["episode"] = n + 1 if n > 0 else None
            except Exception:
                pass
        dt = None
        if isinstance(it, dict):
            dt = it.get("next_episode_at") or anime.get("nextEpisodeAt")
        if not dt:
            dt = anime.get("nextEpisodeAt")
        if dt:
            try:
                t = str(dt).replace("Z", "+00:00")
                try:
                    dtp = datetime.datetime.fromisoformat(t)
                except Exception:
                    dtp = datetime.datetime.strptime(str(dt)[:19], "%Y-%m-%dT%H:%M:%S")
                r["day"] = dtp.weekday()
            except Exception:
                r["day"] = None
        else:
            r["day"] = None
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
    country = r.get("country") or r.get("country_name") or ""
    season = r.get("season") or ""
    year = r.get("year") or ""
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
                year = m_y.group(1) + YEAR_SUFFIX if not m_y.group(0).endswith(YEAR_SUFFIX) else m_y.group(0)
        if not country or country == cline:
            clean_c = cline
            if flag:
                clean_c = clean_c.replace(flag, "")
            clean_c = CLEAN_COUNTRY_RE.sub("", clean_c)
            country = clean_c.strip(" ,")
    if year and not str(year).endswith(YEAR_SUFFIX) and str(year).isdigit():
        year = str(year) + YEAR_SUFFIX
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
    if is_spoiler and spoiler_format:
        t = html_spoiler(t)
    return t

def process_list(
    cand, sorting, scope,
    hash_master, under_master, comma_master,
    show_separators, spoiler_format,
    mapping, plugin=None, drop_unlisted=False
):
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
                lbl = mapping.separator_labels.get(key, key.replace("separator_", "").replace("_", " ")) if hasattr(mapping, "separator_labels") else key.replace("separator_", "").replace("_", " ")
                sep_enabled = mapping.separator_enabled.get(key, True) if hasattr(mapping, "separator_enabled") else True
                sep_hash = mapping.sep_hash.get(key, True) if hasattr(mapping, "sep_hash") else True
                sep_under = mapping.sep_under.get(key, True) if hasattr(mapping, "sep_under") else True
                sep_comma = mapping.sep_comma.get(key, True) if hasattr(mapping, "sep_comma") else True
                if plugin:
                    en = gb(plugin, f"sep_enabled_{key}", sep_enabled)
                    h = hash_master and gb(plugin, f"hash_sep_{key}", sep_hash)
                    u = under_master and gb(plugin, f"underscore_sep_{key}", sep_under)
                    c = comma_master and gb(plugin, f"comma_sep_{key}", sep_comma)
                else:
                    en = sep_enabled
                    h = hash_master and sep_hash
                    u = under_master and sep_under
                    c = comma_master and sep_comma
                cur_section = {
                    "key": key,
                    "label": lbl,
                    "items": [],
                    "enabled": en,
                    "under": u,
                    "hash": h,
                    "comma": c,
                }
                sections.append(cur_section)
                continue
            if key in cand:
                if cur_section is None:
                    cur_section = {
                        "key": "default",
                        "label": "",
                        "items": [],
                        "enabled": True,
                        "under": under_master,
                        "hash": hash_master,
                        "comma": comma_master,
                    }
                    sections.append(cur_section)
                if cur_section["enabled"]:
                    tr, sp = cand[key]
                    fmt = format_item(tr, cur_section["under"], cur_section["hash"], sp, spoiler_format)
                    if fmt:
                        cur_section["items"].append(fmt)
                used.add(key)
    remaining_keys = [k for k in cand if k not in used]
    if remaining_keys and not drop_unlisted:
        if cur_section is not None:
            if cur_section["enabled"]:
                for key in remaining_keys:
                    tr, sp = cand[key]
                    fmt = format_item(tr, cur_section["under"], cur_section["hash"], sp, spoiler_format)
                    if fmt:
                        cur_section["items"].append(fmt)
                    used.add(key)
        else:
            default_section = {
                "key": "default",
                "label": "",
                "items": [],
                "enabled": True,
                "under": under_master,
                "hash": hash_master,
                "comma": comma_master,
            }
            for key in remaining_keys:
                tr, sp = cand[key]
                fmt = format_item(tr, default_section["under"], default_section["hash"], sp, spoiler_format)
                if fmt:
                    default_section["items"].append(fmt)
                used.add(key)
            sections.append(default_section)
    lines = []
    for sec in sections:
        if not sec["enabled"] or not sec["items"]:
            continue
        body = (", ".join(sec["items"]) if sec["comma"] else " ".join(sec["items"]))
        if body:
            if show_separators and sec["label"]:
                lines.append(f"{sec['label']}: {body}")
            else:
                lines.append(body)
    return "\n".join(lines) if len(lines) > 1 else (" ".join(lines) if lines else "")

def process_genres(plugin, data, mapping, drop_unlisted=False):
    if not data or not plugin.show_genres or not mapping:
        return ""
    um = mapping.universal_mapping
    all_g = set(data.get("genres") or [])
    g_like = set(um.get("main_genres", {})) | set(um.get("additional_genres", {}))
    prom = [(t["name"], t.get("isMediaSpoiler", False)) for t in (data.get("tags") or []) if isinstance(t, dict) and t.get("name") in g_like]
    all_g.update(p[0] for p in prom)
    main_m, add_m = um.get("main_genres", {}), um.get("additional_genres", {})
    cand = {}
    for g in all_g:
        is_sp = next((p[1] for p in prom if p[0] == g), False)
        tr = (main_m.get(g) or add_m.get(g) or [g])
        cand[g] = (tr[0] if isinstance(tr, list) else tr, is_sp)
    return process_list(
        cand,
        list(um.get("sorting_genres", um.get("ordered_genres", []))),
        "genres",
        plugin.hash_genres,
        plugin.underscore_genres,
        gb(plugin, "comma_genres", False),
        plugin.show_separators,
        plugin.spoiler_format,
        mapping,
        plugin=plugin,
        drop_unlisted=drop_unlisted
    )

def process_tags(plugin, data, mapping, drop_unlisted=False):
    if not data or not plugin.show_tags or not mapping:
        return ""
    um = mapping.universal_mapping
    g_like = set(um.get("main_genres", {})) | set(um.get("additional_genres", {}))
    dem = set(um.get("demographics", {}))
    all_t = {}
    for t in (data.get("tags") or []):
        if isinstance(t, dict) and t.get("name") and t["name"] not in dem and t["name"] not in g_like:
            all_t[t["name"]] = t.get("isMediaSpoiler", False)
    main_m, add_m = um.get("main_tags", {}), um.get("additional_tags", {})
    cand = {}
    for name, sp in all_t.items():
        tr = (main_m.get(name) or add_m.get(name) or [name])
        cand[name] = (tr[0] if isinstance(tr, list) else tr, sp)
    return process_list(
        cand,
        list(um.get("sorting_tags", um.get("ordered_tags", []))),
        "tags",
        plugin.hash_tags,
        plugin.underscore_tags,
        gb(plugin, "comma_tags", False),
        plugin.show_separators,
        plugin.spoiler_format,
        mapping,
        plugin=plugin,
        drop_unlisted=drop_unlisted
    )

def normalize_anime_data(data, shiki_data=None):
    if not data and not shiki_data:
        return {}
    if data and isinstance(data, dict) and "ru_titles" in data:
        return data
    al = data or {}
    sk = shiki_data or {}
    titles_al = al.get("title") or {}
    ru_titles, en_titles = [], []
    if sk.get("russian"):
        ru_titles.append(sk["russian"])
    for syn in (sk.get("synonyms") or []):
        if syn and re.match(r"^[А-Яа-яЁё0-9\s\W]+$", str(syn)) and syn not in ru_titles:
            ru_titles.append(syn)
    al_ru = titles_al.get("russian")
    if al_ru and al_ru not in ru_titles:
        ru_titles.append(al_ru)
    al_en = filter(None, [titles_al.get("english"), titles_al.get("romaji"), titles_al.get("native"), titles_al.get("userPreferred")] + (al.get("synonyms") or []))
    for t in al_en:
        if re.match(r"^[A-Za-z0-9\s\W]+$", unicodedata.normalize("NFD", str(t))) and t not in en_titles:
            en_titles.append(t)
    sk_en_list = [sk.get("name")]
    if sk.get("english"):
        if isinstance(sk.get("english"), list):
            sk_en_list.extend(sk.get("english"))
        else:
            sk_en_list.append(sk.get("english"))
    if sk.get("synonyms"):
        sk_en_list.extend(sk.get("synonyms"))
    sk_en = filter(None, sk_en_list)
    for t in sk_en:
        if re.match(r"^[A-Za-z0-9\s\W]+$", unicodedata.normalize("NFD", str(t))) and t not in en_titles:
            en_titles.append(t)
    raw_id = str(al.get("id") or sk.get("id") or "")
    al_cover = f"{LABELS['anilist_media_img']}{al.get('id')}" if al.get("id") else (al.get("coverImage", {}).get("extraLarge") if isinstance(al.get("coverImage"), dict) else "")
    sh_cover = _shiki_cover(sk)
    genres = al.get("genres") or [g.get("russian") or g.get("name") for g in sk.get("genres") or [] if isinstance(g, dict)]
    episodes_total = al.get("episodes") if al.get("episodes") is not None else sk.get("episodes")
    episodes_aired = al.get("episodes_aired") if al.get("episodes_aired") is not None else sk.get("episodesAired", sk.get("episodes_aired"))
    status_raw = al.get("status") or sk.get("status", "")
    if isinstance(status_raw, str) and status_raw.lower() in SHIKI_STATUS_MAP:
        status_raw = SHIKI_STATUS_MAP[status_raw.lower()]
    score_val = al.get("averageScore")
    if score_val is not None:
        score = _format_score(score_val / 10)
    elif sk.get("score") is not None and str(sk.get("score")) != "":
        score = _format_score(sk.get("score"))
    else:
        score = ""
    format_raw = al.get("format") or (str(sk.get("kind")).upper() if sk.get("kind") else "")
    studios = [s["name"] for s in al.get("studios", {}).get("nodes", []) if isinstance(s, dict) and s.get("name")] if al.get("studios") else [s.get("name") if isinstance(s, dict) else str(s) for s in sk.get("studios") or []]
    desc = clean_shikimori_description(sk.get("description") or sk.get("synopsis") or "") if sk.get("description") or sk.get("synopsis") else (al.get("description") or "")
    season_val = al.get("season") or sk.get("season")
    season_year_val = al.get("seasonYear") or sk.get("seasonYear")
    source_val = al.get("source") or (str(sk.get("source")).upper() if sk.get("source") else "")

    return {
        "id": raw_id, "ru_titles": ru_titles, "en_titles": en_titles,
        "country": al.get("countryOfOrigin", "UNKNOWN"), "season": season_val, "seasonYear": season_year_val,
        "al_cover": al_cover, "sh_cover": sh_cover, "bannerImage": al.get("bannerImage"),
        "format": format_raw, "episodes": episodes_total, "episodes_aired": episodes_aired,
        "status": status_raw, "score": score, "duration": al.get("duration") or sk.get("duration"),
        "source": source_val, "genres": genres, "tags": al.get("tags") or [],
        "studios": studios, "description": desc, "raw_al": al, "raw_shiki": sk,
    }

def get_sep_preview(mapping, sk, default_text=""):
    if not mapping:
        return default_text
    if hasattr(mapping, "separator_previews") and isinstance(mapping.separator_previews, dict):
        if sk in mapping.separator_previews:
            return mapping.separator_previews[sk]
    um = getattr(mapping, "universal_mapping", {}) or {}
    sep_map = um.get("separator") or um.get("separators") or {}
    if isinstance(sep_map, dict) and sk in sep_map:
        val = sep_map[sk]
        if isinstance(val, dict) and "preview" in val:
            return val["preview"]
        elif isinstance(val, str):
            return val
    return default_text

def get_mock_preview_data(mapping=None):
    data = dict(MOCK_PREVIEW_DATA)
    data["ru_titles"] = list(MOCK_PREVIEW_DATA["ru_titles"])
    data["en_titles"] = list(MOCK_PREVIEW_DATA["en_titles"])
    if not mapping or not getattr(mapping, "universal_mapping", None):
        return data
    if not isinstance(mapping, _PreviewMappingProxy):
        mapping = _PreviewMappingProxy(mapping)
    um = mapping.universal_mapping
    main_g = um.setdefault("main_genres", {})
    main_t = um.setdefault("main_tags", {})
    sorting_g = list(um.get("sorting_genres", um.get("ordered_genres", [])))
    g_set = []
    default_main_g_preview = get_sep_preview(mapping, "separator_genres", "")
    curr_g_preview = default_main_g_preview
    if sorting_g:
        has_item_for_curr_sep = False
        for k in sorting_g:
            if k.startswith("separator_"):
                curr_g_preview = get_sep_preview(mapping, k, default_main_g_preview)
                has_item_for_curr_sep = False
            else:
                if not has_item_for_curr_sep:
                    g_set.append(k)
                    main_g[k] = [curr_g_preview]
                    has_item_for_curr_sep = True
        if not has_item_for_curr_sep:
            extra_k = curr_g_preview if curr_g_preview not in sorting_g else f"{curr_g_preview}_extra"
            g_set.append(extra_k)
            main_g[extra_k] = [curr_g_preview]
    data["genres"] = g_set
    sorting_t = list(um.get("sorting_tags", um.get("ordered_tags", [])))
    t_list = []
    default_main_t_preview = get_sep_preview(mapping, "separator_tag", "")
    curr_t_preview = default_main_t_preview
    if sorting_t:
        has_item_for_curr_sep = False
        for k in sorting_t:
            if k.startswith("separator_"):
                curr_t_preview = get_sep_preview(mapping, k, default_main_t_preview)
                has_item_for_curr_sep = False
            else:
                if not has_item_for_curr_sep:
                    t_list.append({"name": k, "isMediaSpoiler": False})
                    main_t[k] = [curr_t_preview]
                    has_item_for_curr_sep = True
        if not has_item_for_curr_sep:
            extra_k = curr_t_preview if curr_t_preview not in sorting_t else f"{curr_t_preview}_extra"
            t_list.append({"name": extra_k, "isMediaSpoiler": False})
            main_t[extra_k] = [curr_t_preview]
    data["tags"] = t_list
    dem_map = um.get("demographics", {})
    data["audience"] = extract_demographic(data, dem_map)
    return data

def extract_titles(plugin, data, shiki_data=None):
    ru_count = max(0, int(getattr(plugin, "extra_ru_count", 1) or 0)) if getattr(plugin, "extra_ru_count", None) is not None else 1
    en_count = max(0, int(getattr(plugin, "extra_en_count", 1) or 0)) if getattr(plugin, "extra_en_count", None) is not None else 1
    ru = data.get("ru_titles", []) if data and "ru_titles" in data else ([shiki_data.get("russian")] if shiki_data and shiki_data.get("russian") else [])
    en = data.get("en_titles", []) if data and "en_titles" in data else ([shiki_data.get("name")] if shiki_data and shiki_data.get("name") else [])
    if ru_count <= 0:
        ru_d, en_d = en[:en_count], []
    elif ru:
        ru_d, en_d = ru[:ru_count], en[:en_count]
    else:
        ru_d, en_d = en[:ru_count], en[ru_count:ru_count + en_count]
    return (ru_d[0] if ru_d else ""), ru_d[1:], (en_d[0] if en_d else ""), en_d[1:]

def _shiki_cover(shiki_data):
    if not isinstance(shiki_data, dict):
        return ""
    poster = shiki_data.get("poster")
    path = (poster.get("originalUrl") or poster.get("mainUrl") or poster.get("original") or poster.get("previewUrl") or poster.get("preview") or "") if isinstance(poster, dict) else (poster or "")
    if not path:
        img = shiki_data.get("image")
        path = (img.get("original") or img.get("preview") or img.get("x96") or "") if isinstance(img, dict) else (img or "")
    if not path:
        path = shiki_data.get("image_url") or shiki_data.get("cover_url") or ""
    path = str(path).strip() if path else ""
    if path:
        return path if path.startswith("http") else ("https:" + path if path.startswith("//") else LABELS["shikimori_io"] + ("/" + path.lstrip("/")))
    return ""

def get_cover_url(data, shiki_data=None, prefer_anilist=True):
    al_cover = data.get("al_cover", "") if data and "al_cover" in data else (f"{LABELS['anilist_media_img']}{data.get('id')}" if data and data.get("id") else "")
    sh_cover = data.get("sh_cover", "") if data and "sh_cover" in data else _shiki_cover(shiki_data)
    if prefer_anilist:
        return al_cover or sh_cover or ""
    return sh_cover or al_cover or ""

def get_country_info(plugin, data, mapping, hash_main_on=True):
    code = data.get("countryOfOrigin", data.get("country", "UNKNOWN")) if data else "UNKNOWN"
    um = mapping.universal_mapping if mapping and hasattr(mapping, "universal_mapping") else {}
    flags = um.get("flags") or {}
    flag_val = _get_mapped_val(flags, code)
    flag = flag_val if plugin.show_flag else ""
    txt = ""
    if plugin.show_country:
        countries_map = um.get("countries") or {}
        country_val = _get_mapped_val(countries_map, code)
        txt = country_val
        if getattr(plugin, "hash_country", False) and hash_main_on and txt:
            txt = "#" + txt
    return flag, txt, code

def get_season_year(plugin, data, shiki_data, mapping):
    season_val, year_val = "", ""
    if plugin.show_season or plugin.show_year:
        if data and data.get("season"):
            seasons_map = mapping.universal_mapping.get("seasons") or {} if mapping and hasattr(mapping, "universal_mapping") else {}
            s_raw = str(data.get("season")).upper()
            season_val = _get_mapped_val(seasons_map, s_raw, s_raw)
        if data and (data.get("seasonYear") or data.get("year")):
            year_val = data.get("seasonYear") or data.get("year")
    return (season_val if plugin.show_season else ""), (str(year_val) if year_val and str(year_val) != "????" and plugin.show_year else "")

def get_description(plugin, data, shiki_data=None, force=False):
    if not force and not plugin.show_description:
        return ""
    return str(data.get("description", "")).strip() if data else ""

def resolve_anime_label(plugin, main_on=True, hash_main_on=True):
    if not main_on or not gb(plugin, "show_anime_label", True):
        return gs(plugin, "hash_anime_replace", HASH_REPLACE_DEFAULT) or HASH_REPLACE_DEFAULT
    return LABELS["hash_anime_default"] if gb(plugin, "show_hash_anime", True) and hash_main_on else LABELS["anime_default"]

def extract_demographic(data, dem_map):
    if not data:
        return ""
    aud = data.get("audience")
    if aud:
        if dem_map:
            lookup = {}
            for key, vals in dem_map.items():
                res_val = vals[0] if isinstance(vals, list) and vals else str(vals)
                lookup[key.lower()] = res_val
                if isinstance(vals, list):
                    for v in vals:
                        lookup[str(v).lower()] = res_val
                else:
                    lookup[str(vals).lower()] = res_val
            match = lookup.get(str(aud).strip().lower())
            if match:
                return match
        return str(aud)
    if not dem_map:
        return ""
    lookup = {}
    for key, vals in dem_map.items():
        res_val = vals[0] if isinstance(vals, list) and vals else str(vals)
        lookup[key.lower()] = res_val
        if isinstance(vals, list):
            for v in vals:
                lookup[str(v).lower()] = res_val
        else:
            lookup[str(vals).lower()] = res_val
    for t in (data.get("tags") or []):
        name = t.get("name") if isinstance(t, dict) else t
        if name:
            match = lookup.get(str(name).strip().lower())
            if match:
                return match
    for g in (data.get("genres") or []):
        name = (g.get("name") or g.get("russian")) if isinstance(g, dict) else g
        if name:
            match = lookup.get(str(name).strip().lower())
            if match:
                return match
    return ""

def extract_author(data):
    raw_al = data.get("raw_al") or data
    if isinstance(raw_al, dict) and raw_al.get("staff"):
        for edge in raw_al["staff"].get("edges", []):
            role = (edge.get("role") or "").lower()
            if any(k in role for k in AUTHOR_ROLES):
                node = edge.get("node") or {}
                return node.get("name", {}).get("full") or node.get("name", {}).get("native") or ""
    return ""

def extract_relations(data, shiki_data=None):
    rel_lines = []
    raw_al = data.get("raw_al") or data
    raw_sh = data.get("raw_shiki") or shiki_data
    if isinstance(raw_al, dict) and raw_al.get("relations"):
        for edge in raw_al["relations"].get("edges", []):
            rel_type = edge.get("relationType", "").replace("_", " ").title()
            node = edge.get("node") or {}
            rel_id = node.get("id")
            t_dict = node.get("title") or {}
            rel_title = t_dict.get("russian") or t_dict.get("romaji") or t_dict.get("english") or ""
            if rel_id and rel_title:
                rel_lines.append(f'• {rel_type}: {html_link(ANILIST_URL_TEMPLATE.format(rel_id), rel_title)}')
    elif isinstance(raw_sh, dict) and raw_sh.get("related"):
        for rel in raw_sh.get("related") or []:
            rel_kind = rel.get("relationKind") or ""
            anime_info = rel.get("anime") or {}
            rel_id = anime_info.get("id")
            rel_title = anime_info.get("russian") or anime_info.get("name") or ""
            if rel_id and rel_title:
                rel_lines.append(f'• {rel_kind}: {html_link(SHIKIMORI_URL_TEMPLATE.format(rel_id), rel_title)}')
    return html_blockquote("\n".join(rel_lines)) if rel_lines else ""

def extract_media_videos(data, shiki_data=None):
    op_list, ed_list, tr_list = [], [], []
    raw_sh = data.get("raw_shiki") or shiki_data
    if isinstance(raw_sh, dict) and raw_sh.get("videos"):
        for vid in raw_sh["videos"]:
            if not isinstance(vid, dict):
                continue
            v_kind = (vid.get("kind") or "").lower()
            v_url = vid.get("url") or ""
            v_name = vid.get("name") or ""
            if not v_url:
                continue
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
        site = t.get("site")
        t_id = t.get("id")
        if site == "youtube" and t_id:
            tr_list.append(f'• {html_link(YOUTUBE_URL_TEMPLATE.format(t_id), LABELS["trailer_yt"])}')
    op_text = html_blockquote("\n".join(op_list)) if op_list else ""
    ed_text = html_blockquote("\n".join(ed_list)) if ed_list else ""
    tr_text = html_blockquote("\n".join(tr_list)) if tr_list else ""
    return op_text, ed_text, tr_text

def build_template_vars(plugin, data, shiki_data=None, mapping=None, no_link=False, no_preview=False, num=None, drop_unlisted=False):
    if not data or "ru_titles" not in data:
        data = normalize_anime_data(data, shiki_data)
        shiki_data = None
    main_on = gb(plugin, "coll_fields_main", True)
    hash_main_on = gb(plugin, "coll_hash_main", True)
    under_main_on = gb(plugin, "coll_under_main", True)
    comma_main_on = gb(plugin, "coll_comma_main", False)
    f_on = lambda attr: main_on and gb(plugin, attr, True)
    main_ru, other_ru, main_en, other_en = extract_titles(plugin, data, shiki_data)
    raw_id = str(data.get("id")) if data and data.get("id") else ""
    formatted_id = html_code(raw_id) if (f_on("show_id") and raw_id) else ""
    cover = get_cover_url(data, shiki_data, prefer_anilist=(getattr(plugin, "cover_source", 0) == 0))
    preview = "" if no_preview or no_link or not f_on("show_preview") else html_zero_link(cover)
    cover_val = f'{html_link(cover, LABELS["cover"])}{html_zero_link(cover)}' if (f_on("show_cover") and cover) else ""
    banner = f'{html_link(data.get("bannerImage"), LABELS["banner"])}{html_zero_link(data.get("bannerImage"))}' if f_on("show_banner") and data and data.get("bannerImage") else ""
    author_name = data.get("author_name") or ""
    if not author_name and f_on("show_author"):
        author_name = extract_author(data)
    author_text = format_item(author_name, plugin.underscore_author and under_main_on, plugin.hash_author and hash_main_on) if (f_on("show_author") and author_name) else ""
    flag, country_text, _ = get_country_info(plugin, data, mapping, hash_main_on)
    if not f_on("show_flag"): flag = ""
    if not f_on("show_country"): country_text = ""
    season, year = get_season_year(plugin, data, shiki_data, mapping)
    if not f_on("show_season"): season = ""
    if not f_on("show_year"): year = ""
    ep_str = ""
    if f_on("show_episodes"):
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
    fmt_text = format_item(fmt_tr, plugin.underscore_format and under_main_on, plugin.hash_format and hash_main_on) if f_on("show_format") and fmt_tr else ""
    if plugin.ona_clarify and str(fmt_raw).upper() == "ONA":
        eps = data.get("episodes")
        ona = LABELS["movie"] if eps == 1 else (LABELS["series"] if eps and eps > 1 else "")
        if ona:
            fmt_text += " " + format_item(_get_mapped_val(um.get("formats_extra") or {}, ona, ona), plugin.underscore_format and under_main_on, plugin.hash_format and hash_main_on)
    dem_map = um.get("demographics", {})
    dem_tr = (data.get("audience") if data else None) or extract_demographic(data, dem_map)
    show_aud = main_on and (gb(plugin, "show_audience", gb(plugin, "show_demographic", True)))
    dem_text = format_item(dem_tr, getattr(plugin, "underscore_demographic", False) and under_main_on, getattr(plugin, "hash_demographic", True) and hash_main_on) if show_aud else ""
    genres_str = process_genres(plugin, data, mapping, drop_unlisted=drop_unlisted) if (data and plugin.show_genres and mapping) else ""
    tags_str = process_tags(plugin, data, mapping, drop_unlisted=drop_unlisted) if (data and plugin.show_tags and mapping) else ""
    score = data.get("score") or "" if f_on("show_score") else ""
    st_raw = data.get("status", "")
    st_tr = ""
    if st_raw:
        st_map = um.get("status") or {}
        key = SHIKI_STATUS_MAP.get(str(st_raw).lower(), st_raw)
        st_tr = _get_mapped_val(st_map, key, _get_mapped_val(st_map, str(st_raw), str(st_raw).lower()))
    st_text = format_item(str(st_tr), plugin.underscore_status and under_main_on, plugin.hash_status and hash_main_on) if f_on("show_status") and st_tr else ""
    dur = f"{data.get('duration')} {LABELS['min']}" if f_on("show_duration") and data.get("duration") else ""
    src_raw = data.get("source") if data else ""
    src_tr = _get_mapped_val(um.get("source") or {}, src_raw, src_raw.lower() if src_raw else "")
    src_text = format_item(src_tr, plugin.underscore_source and under_main_on, plugin.hash_source and hash_main_on) if f_on("show_source") and src_tr else ""
    studios = ""
    if f_on("show_studios") and data.get("studios"):
        stud_f = [format_item(sn, plugin.underscore_studios and under_main_on, plugin.hash_studios and hash_main_on) for sn in data.get("studios")]
        studios = (", " if gb(plugin, "comma_studios", True) and comma_main_on else " ").join(stud_f)
    link1 = html_link(ANILIST_URL_TEMPLATE.format(data.get("id")), getattr(plugin, "anilist_link_text", "AniList")) if (not no_link) and plugin.show_link_in_full and data.get("id") else ""
    link2 = html_link(SHIKIMORI_URL_TEMPLATE.format(data.get("id")), getattr(plugin, "shikimori_link_text", "Shikimori")) if (not no_link) and plugin.show_link_in_full and data.get("id") else ""
    desc = get_description(plugin, data, shiki_data, force=plugin.description_in_card)
    desc_val = html_blockquote(desc) if (plugin.description_in_card and desc and plugin.show_description and plugin.enable_html_card) else ""
    relations_text = data.get("relations") or ""
    if not f_on("show_relations"):
        relations_text = ""
    elif not relations_text:
        relations_text = extract_relations(data, shiki_data)
    opening_text = data.get("opening") or ""
    ending_text = data.get("ending") or ""
    trailer_text = data.get("trailer") or ""
    if not f_on("show_opening"): opening_text = ""
    if not f_on("show_ending"): ending_text = ""
    if not f_on("show_trailer"): trailer_text = ""
    if (f_on("show_opening") and not opening_text) or (f_on("show_ending") and not ending_text) or (f_on("show_trailer") and not trailer_text):
        op_t, ed_t, tr_t = extract_media_videos(data, shiki_data)
        if f_on("show_opening") and not opening_text: opening_text = op_t
        if f_on("show_ending") and not ending_text: ending_text = ed_t
        if f_on("show_trailer") and not trailer_text: trailer_text = tr_t
    t_ru = [gs(plugin, f"tpl_ru{i}", tmpl) for i, tmpl in enumerate(TITLE_RU_TEMPLATES, 1)]
    t_en = [gs(plugin, f"tpl_en{i}", tmpl) for i, tmpl in enumerate(TITLE_EN_TEMPLATES, 1)]
    title_val = main_ru or main_en or ""

    res_vars = {
        "num": str(num) if num is not None else "",
        "preview": preview, "cover": cover_val, "a": resolve_anime_label(plugin, main_on, hash_main_on),
        "title": html_code(title_val), "title_raw": title_val,
        "ru1": t_ru[0].format(title=main_ru) if main_ru else "",
        "ru2": t_ru[1].format(title=other_ru[0]) if len(other_ru) > 0 else "",
        "ru3": t_ru[2].format(title=other_ru[1]) if len(other_ru) > 1 else "",
        "ru4": t_ru[3].format(title=other_ru[2]) if len(other_ru) > 2 else "",
        "ru5": t_ru[4].format(title=other_ru[3]) if len(other_ru) > 3 else "",
        "en1": t_en[0].format(title=main_en) if main_en else "",
        "en2": t_en[1].format(title=other_en[0]) if len(other_en) > 0 else "",
        "en3": t_en[2].format(title=other_en[1]) if len(other_en) > 1 else "",
        "en4": t_en[3].format(title=other_en[2]) if len(other_en) > 2 else "",
        "en5": t_en[4].format(title=other_en[3]) if len(other_en) > 3 else "",
        "flag": flag, "country": country_text, "season": season, "year": f"{year}{YEAR_SUFFIX}" if year and plugin.show_year_g else year,
        "format": fmt_text, "audience": dem_text, "demographic": dem_text, "genres": genres_str, "tags": tags_str,
        "episodes": ep_str, "score": score, "status": st_text, "duration": dur,
        "source": src_text, "studios": studios, "link": link1 or link2, "link1": link1, "link2": link2,
        "description": desc_val, "id": formatted_id, "banner": banner, "author": author_text,
        "relations": relations_text, "opening": opening_text, "ending": ending_text, "trailer": trailer_text,
    }

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
        card_send_mode = getattr(plugin, "card_send_mode", 0)
    if max_len is None:
        max_len = LIMIT_CARD_CAPTION if (no_link or int(card_send_mode or 0) == 1) else LIMIT_CARD_TEXT

    vd = build_template_vars(plugin, data, shiki_data, mapping, no_link=no_link, no_preview=no_preview)
    sp_mode = getattr(plugin, "empty_ph_space_mode", 0)
    lbl = vd.get("a", "")

    def render():
        res = clean_template_output(template, vd, sp_mode)
        if "#аниме" in res and lbl != "#аниме":
            res = res.replace("#аниме", lbl)
        return re.sub(r"\n{3,}", "\n\n", res).strip()

    cur = render()
    if not max_len or calc_plain_len(cur) <= max_len:
        return cur

    for k in ("relations", "trailer", "ending", "opening"):
        if vd.get(k):
            vd[k] = ""
            cur = render()
            if calc_plain_len(cur) <= max_len:
                return cur

    if data and plugin.show_tags and mapping:
        t_clean = process_tags(plugin, data, mapping, drop_unlisted=True)
        if t_clean != vd.get("tags"):
            vd["tags"] = t_clean
            cur = render()
            if calc_plain_len(cur) <= max_len:
                return cur

    if data and plugin.show_genres and mapping:
        g_clean = process_genres(plugin, data, mapping, drop_unlisted=True)
        if g_clean != vd.get("genres"):
            vd["genres"] = g_clean
            cur = render()
            if calc_plain_len(cur) <= max_len:
                return cur

    if vd.get("description"):
        vd["description"] = ""
        cur = render()
        if calc_plain_len(cur) <= max_len:
            return cur

    matches = re.findall(r'\{([a-zA-Z0-9_]+)\}', template)
    seen = set()
    ordered = []
    for m in reversed(matches):
        if m not in seen and m not in PROTECTED_VARS:
            seen.add(m)
            ordered.append(m)

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
        raw_mode = int(getattr(plugin, "card_send_mode", 0) or 0)
    raw_mode = int(raw_mode)

    no_link = bool(opts.get("no_link", False))
    show_preview = bool(getattr(plugin, "show_preview", True))

    if no_link:
        is_media = show_preview
    else:
        is_media = (raw_mode == 1)

    prefer_al = int(getattr(plugin, "cover_source", 0) or 0) == 0
    cover = get_cover_url(data, shiki, prefer_anilist=prefer_al)
    if not cover:
        cover = get_cover_url(data, shiki, prefer_anilist=not prefer_al)

    temp_pos = opts.get("temp_pos")
    if temp_pos is not None:
        invert = (temp_pos == 0)
    else:
        if is_media:
            invert = (int(getattr(plugin, "media_pos", 0) or 0) == 0)
        else:
            invert = (int(getattr(plugin, "preview_pos", 0) or 0) == 1)

    max_len = LIMIT_CARD_CAPTION if (no_link or is_media) else LIMIT_CARD_TEXT

    card_text = format_media_full(
        plugin, data, plugin.card_template,
        shiki_data=shiki, mapping=mapping,
        no_link=no_link,
        no_preview=(is_media or no_link),
        max_len=max_len,
        card_send_mode=(1 if is_media else 0),
    )

    return {
        "text": card_text,
        "is_media": is_media,
        "cover_url": cover,
        "invert": invert,
        "no_link": no_link,
        "max_len": max_len,
    }

def format_popup(plugin, data, template, shiki_data=None, mapping=None, num=None):
    if not data and not shiki_data:
        return ""
    return clean_template_output(template, build_template_vars(plugin, data, shiki_data, mapping, num=num), getattr(plugin, "empty_ph_space_mode", 0))

def format_text_output(plugin, data, template, shiki_data=None, mapping=None, num=None):
    if not data and not shiki_data:
        return ""
    return clean_template_output(template, build_template_vars(plugin, data, shiki_data, mapping, num=num), getattr(plugin, "empty_ph_space_mode", 0))

def get_preview_text(plugin, template=None, mapping=None):
    if template is None and plugin is not None:
        template = getattr(plugin, "card_template", None) or gs(plugin, "card_template", "")
    if mapping and not isinstance(mapping, _PreviewMappingProxy):
        mapping = _PreviewMappingProxy(mapping)
    return format_media_full(plugin, get_mock_preview_data(mapping), template or DEFAULT_PREVIEW_TEMPLATE, None, mapping)

def get_preview_cover(plugin, mapping=None):
    return get_cover_url(MOCK_PREVIEW_DATA, None, prefer_anilist=(getattr(plugin, "cover_source", 0) == 0))

def format_popup_row_subtitle(res, template):
    title_val = res.get("title") or "—"
    raw_id = res.get("id")
    formatted_id = f"<code>{raw_id}</code>" if raw_id else ""
    flag, country, season, year = extract_geo_fields(res)
    vd = {
        "title": f"<code>{title_val}</code>",
        "title_raw": title_val,
        "id": formatted_id,
        "format": res.get("type_ru") or "",
        "type_ru": res.get("type_ru") or "",
        "status": res.get("status") or "",
        "score": str(res.get("score")) if res.get("score") is not None else "?",
        "episodes": epl(res) or "?",
        "season": season,
        "year": year,
        "genres": ", ".join(res.get("genres") or []) if res.get("genres") else "",
        "country": country,
        "flag": flag,
    }
    sub_text = format_mini_template(template, vd)
    return re.sub(r"<[^>]+>", "", sub_text)

def build_list_text_chunks(results, selected_indices, query, src_label, ongoing, list_template, list_num_custom="•"):
    o = sorted(selected_indices)
    if not o:
        return []
    if ongoing:
        header = TEXT_LIST_HEADER_ONGOING.format(src=src_label, q=query) if query else TEXT_LIST_HEADER_ONGOING_EMPTY.format(src=src_label)
    else:
        header = TEXT_LIST_HEADER_QUERY.format(src=src_label, q=query) if query else TEXT_LIST_HEADER_QUERY_EMPTY.format(src=src_label)
    parts = [header]
    counter = [0]
    def add_title(res_dict):
        n = counter[0]
        counter[0] = n + 1
        custom = list_num_custom or "•"
        title = res_dict.get("title") or "—"
        raw_id = res_dict.get("id")
        formatted_id = f"<code>{raw_id}</code>" if raw_id else ""
        c_url = res_dict.get("cover_url") or ""
        b_url = res_dict.get("banner_url") or ""
        cover_link = f'<a href="{c_url}">обложка</a>' if c_url else ""
        banner_link = f'<a href="{b_url}">баннер</a>' if b_url else ""
        link_url = ""
        if raw_id:
            if "shikimori" in str(res_dict.get("url", "")).lower() or res_dict.get("is_shiki"):
                link_url = f"https://shikimori.one/animes/{raw_id}"
            else:
                link_url = f"https://anilist.co/anime/{raw_id}"
        uni_link = f'<a href="{link_url}">ссылка</a>' if link_url else ""
        flag, country, season, year = extract_geo_fields(res_dict)
        vd = {
            "num": n + 1,
            "custom": custom,
            "title": f"<code>{title}</code>",
            "title_raw": title,
            "id": formatted_id,
            "format": res_dict.get("type_ru") or "",
            "type_ru": res_dict.get("type_ru") or "",
            "status": res_dict.get("status") or "",
            "score": str(res_dict.get("score") if res_dict.get("score") is not None else "?"),
            "episodes": epl(res_dict) or "?",
            "season": season,
            "year": year,
            "genres": ", ".join(res_dict.get("genres") or []) if res_dict.get("genres") else "",
            "country": country,
            "flag": flag,
            "cover": cover_link,
            "banner": banner_link,
            "link": uni_link,
        }
        return format_mini_template(list_template, vd)
    if ongoing:
        by = {}
        for i in o:
            if 0 <= i < len(results):
                r = results[i]
                d = r.get("day")
                key = d if d is not None else -1
                by.setdefault(key, []).append(r)
        for d in sorted(by.keys(), key=lambda x: 9 if x < 0 else x):
            items = by[d]
            mono = "\n".join(filter(None, (add_title(tt) for tt in items)))
            if mono:
                if 0 <= d < 7:
                    parts.append(DAYS[d])
                parts.append("<blockquote expandable>%s</blockquote>" % mono)
    else:
        has_id = any(results[i].get("_section") == "id" for i in o if 0 <= i < len(results))
        has_name = any(results[i].get("_section") == "name" for i in o if 0 <= i < len(results))
        if has_id and has_name:
            id_items = [results[i] for i in o if 0 <= i < len(results) and results[i].get("_section") == "id"]
            name_items = [results[i] for i in o if 0 <= i < len(results) and results[i].get("_section") == "name"]
            if id_items:
                parts.append(POPUP_SECTION_ID_LABEL)
                parts.append("<blockquote expandable>%s</blockquote>" % ("\n".join(filter(None, (add_title(tt) for tt in id_items)))))
            if name_items:
                parts.append(POPUP_SECTION_NAME_LABEL)
                parts.append("<blockquote expandable>%s</blockquote>" % ("\n".join(filter(None, (add_title(tt) for tt in name_items)))))
        else:
            items = [results[i] for i in o if 0 <= i < len(results)]
            parts.append("<blockquote expandable>%s</blockquote>" % ("\n".join(filter(None, (add_title(tt) for tt in items)))))
    chunks = []
    cur = []
    cur_len = 0
    for part in parts:
        pl = len(part) + 1
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