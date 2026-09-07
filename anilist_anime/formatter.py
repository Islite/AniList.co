import re
import unicodedata

from utils import gb, gs

SHIKI_STATUS_MAP = {
    'released': 'FINISHED', 'ongoing': 'RELEASING', 'anons': 'NOT_YET_RELEASED',
    'latest': 'RELEASING', 'paused': 'HIATUS',
}

def format_item(name, use_underscore, use_hash, is_spoiler=False, spoiler_format=True):
    if not name:
        return ""
    t = str(name).strip()
    if use_underscore:
        t = t.replace("-", "_").replace(" ", "_")
    elif use_hash:
        t = t.replace(" ", "")
    if use_hash:
        t = "#" + t
    if is_spoiler and spoiler_format:
        t = "<spoiler>" + t + "</spoiler>"
    return t

def process_list(
    cand, sorting, show_main, show_unlisted,
    hash_master, hash_main, hash_unlisted,
    under_master, under_main, under_unlisted,
    comma_master, comma_main, comma_unlisted,
    show_separators, separator_labels, separator_enabled,
    sep_hash, sep_under, sep_comma, spoiler_format,
    unlisted_label="прочий",
):
    if not cand:
        return ""
    groups = []
    cur_items, cur_label, cur_enabled, cur_is_main = [], None, show_main, True
    cur_hash = hash_master and hash_main
    cur_under = under_master and under_main
    cur_comma = comma_master and comma_main
    used = set()

    def flush():
        nonlocal cur_items, cur_label, cur_enabled, cur_is_main, cur_hash, cur_under, cur_comma
        if cur_enabled and cur_items:
            groups.append((cur_label if show_separators else None, cur_items[:], cur_is_main, cur_comma))
        cur_items = []

    if not sorting:
        if show_main or show_unlisted:
            fmt = [
                format_item(tr, under_master and under_main, hash_master and hash_main, sp, spoiler_format)
                for name, (tr, sp) in cand.items()
            ]
            sep = ", " if (comma_master and comma_main) else " "
            body = sep.join(f for f in fmt if f)
            return body if body else ""
        return ""

    for key in sorting:
        if key.startswith("separator_"):
            flush()
            cur_label = separator_labels.get(key, key.replace("separator_", "").replace("_", " "))
            cur_enabled = separator_enabled.get(key, True)
            cur_is_main = False
            cur_hash = hash_master and sep_hash.get(key, True)
            cur_under = under_master and sep_under.get(key, True)
            cur_comma = comma_master and sep_comma.get(key, True)
            continue
        if not cur_enabled or key in used or key not in cand:
            continue
        tr, sp = cand[key]
        fmt = format_item(tr, cur_under, cur_hash, sp, spoiler_format)
        if fmt:
            cur_items.append(fmt)
        used.add(key)
    flush()

    leftover = [
        format_item(tr, under_master and under_unlisted, hash_master and hash_unlisted, sp, spoiler_format)
        for name, (tr, sp) in cand.items() if name not in used
    ]
    leftover = [f for f in leftover if f]
    if leftover and show_unlisted:
        groups.append((unlisted_label if show_separators else None, leftover, False, comma_master and comma_unlisted))

    lines = []
    for label, group_items, is_m, use_c in groups:
        body = (", ".join(group_items) if use_c else " ".join(group_items))
        if body:
            lines.append(f"{label}: {body}" if label else body)
    return "\n".join(lines) if show_separators and len(lines) > 1 else " ".join(lines)

def process_genres(plugin, data, mapping):
    if not data or not plugin.show_genres:
        return ""
    um = mapping.universal_mapping
    all_g = set(data.get("genres") or [])
    g_like = set(um.get("main_genres", {})) | set(um.get("additional_genres", {}))
    prom = [
        (t["name"], t.get("isMediaSpoiler", False))
        for t in (data.get("tags") or [])
        if t.get("name") in g_like and t.get("rank", 0) >= plugin.tag_min_rank
    ]
    all_g.update(p[0] for p in prom)
    main_m = um.get("main_genres", {})
    add_m = um.get("additional_genres", {})
    cand = {}
    for g in all_g:
        is_sp = next((p[1] for p in prom if p[0] == g), False)
        tr = (main_m.get(g) or add_m.get(g) or [g])
        tr = tr[0] if isinstance(tr, list) else tr
        cand[g] = (tr, is_sp)
    sorting = um.get("sorting_genres", um.get("ordered_genres", []))
    return process_list(
        cand, sorting, plugin.show_genres_main, plugin.show_genres_unlisted,
        plugin.hash_genres, plugin.hash_genres_main, plugin.hash_genres_unlisted,
        plugin.underscore_genres, plugin.underscore_genres_main, plugin.underscore_genres_unlisted,
        plugin.comma_genres, plugin.comma_genres_main, plugin.comma_genres_unlisted,
        plugin.show_separators, mapping.separator_labels, mapping.separator_enabled,
        mapping.sep_hash, mapping.sep_under, mapping.sep_comma, plugin.spoiler_format,
        "прочий жанр",
    )

def process_tags(plugin, data, mapping):
    if not data or not plugin.show_tags:
        return ""
    um = mapping.universal_mapping
    g_like = set(um.get("main_genres", {})) | set(um.get("additional_genres", {}))
    dem = set(um.get("demographics", {}))
    all_t = {}
    for t in (data.get("tags") or []):
        name = t.get("name")
        if not name or t.get("rank", 0) < plugin.tag_min_rank or name in dem or name in g_like:
            continue
        all_t[name] = t.get("isMediaSpoiler", False)
    main_m = um.get("main_tags", {})
    add_m = um.get("additional_tags", {})
    cand = {}
    for name, sp in all_t.items():
        tr = (main_m.get(name) or add_m.get(name) or [name])
        tr = tr[0] if isinstance(tr, list) else tr
        cand[name] = (tr, sp)
    sorting = um.get("sorting_tags", um.get("ordered_tags", []))
    return process_list(
        cand, sorting, plugin.show_tags_main, plugin.show_tags_unlisted,
        plugin.hash_tags, plugin.hash_tags_main, plugin.hash_tags_unlisted,
        plugin.underscore_tags, plugin.underscore_tags_main, plugin.underscore_tags_unlisted,
        plugin.comma_tags, plugin.comma_tags_main, plugin.comma_tags_unlisted,
        plugin.show_separators, mapping.separator_labels, mapping.separator_enabled,
        mapping.sep_hash, mapping.sep_under, mapping.sep_comma, plugin.spoiler_format,
        "прочий тег",
    )

def extract_titles(plugin, data, shiki_data):
    try:
        ru_count = max(0, int(getattr(plugin, "extra_ru_count", 1) or 0))
    except Exception:
        ru_count = 1
    try:
        en_count = max(0, int(getattr(plugin, "extra_en_count", 1) or 0))
    except Exception:
        en_count = 1
    titles = data.get("title", {}) if data else {}
    en = list(dict.fromkeys(filter(None, [
        titles.get("english"), titles.get("romaji"), titles.get("native"), titles.get("userPreferred")
    ] + (data.get("synonyms", []) if data else []))))
    en = [t for t in en if re.match(r"^[A-Za-z0-9\s\W]+$", unicodedata.normalize("NFD", t))]
    if shiki_data:
        en2 = list(dict.fromkeys(filter(None, [shiki_data.get("name")] + list(shiki_data.get("english") or []) + list(shiki_data.get("synonyms") or []))))
        en2 = [t for t in en2 if t and re.match(r"^[A-Za-z0-9\s\W]+$", unicodedata.normalize("NFD", str(t)))]
        if not en:
            en = en2
        else:
            for x in en2:
                if x not in en:
                    en.append(x)
    ru = []
    if shiki_data:
        ru = [shiki_data.get("russian")] + list(shiki_data.get("synonyms") or [])
        ru = [n for n in ru if n and re.match(r"^[А-Яа-яЁё0-9\s\W]+$", str(n))]
    if ru_count <= 0:
        ru_d = en[:en_count] if en_count > 0 else []
        en_d = []
    elif ru:
        ru_d = ru[:ru_count]
        en_d = en[:en_count]
    else:
        ru_d = en[:ru_count]
        en_d = en[ru_count:ru_count + en_count]
    return (
        (ru_d[0] if ru_d else ""),
        (ru_d[1:] if len(ru_d) > 1 else []),
        (en_d[0] if en_d else ""),
        (en_d[1:] if len(en_d) > 1 else []),
    )

def _is_anilist_media(obj):
    if not obj or not isinstance(obj, dict):
        return False
    if "coverImage" in obj or "averageScore" in obj or "countryOfOrigin" in obj:
        return True
    title = obj.get("title")
    if isinstance(title, dict) and any(k in title for k in ("romaji", "english", "native", "userPreferred")):
        return True
    return False

def _shiki_cover(shiki_data):
    if not shiki_data or not isinstance(shiki_data, dict):
        return ""
    path = ""
    poster = shiki_data.get("poster")
    if isinstance(poster, dict):
        path = (
            poster.get("originalUrl")
            or poster.get("mainUrl")
            or poster.get("original")
            or poster.get("previewUrl")
            or poster.get("preview")
            or ""
        )
    elif isinstance(poster, str):
        path = poster
    if not path:
        img = shiki_data.get("image")
        if isinstance(img, dict):
            path = img.get("original") or img.get("preview") or img.get("x96") or ""
        elif isinstance(img, str):
            path = img
    if not path:
        path = shiki_data.get("image_url") or shiki_data.get("cover_url") or ""
    path = str(path).strip() if path else ""
    if path and "missing" in path:
        path = ""
    if path:
        if path.startswith("http"):
            # новый CDN: shikimori.io/uploads/...
            return path
        if path.startswith("//"):
            return "https:" + path
        if path.startswith("/"):
            return "https://shikimori.io" + path
        return "https://shikimori.io/" + path.lstrip("/")
    return ""

def get_cover_url(data, shiki_data=None, prefer_anilist=True):
    al_cover = ""
    if data and isinstance(data, dict):
        # стабильный URL для webpage-превью карточки
        if data.get("id") is not None:
            al_cover = "https://img.anili.st/media/%s" % data.get("id")
        else:
            ci = data.get("coverImage") or {}
            if isinstance(ci, dict):
                al_cover = ci.get("extraLarge") or ci.get("large") or ci.get("medium") or ""
    sh_cover = _shiki_cover(shiki_data)
    def _is_img(u):
        if not u:
            return False
        u = str(u).lower().split("?")[0]
        if u.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
            return True
        if "/system/" in u or "/uploads/" in u:
            return True
        if "img.anili.st" in u:
            return True
        if "anilist.co" in u or "anilist" in u:
            return True
        if "shikimori" in u and "/animes/" not in u:
            return True
        return False
    sh_img = sh_cover if _is_img(sh_cover) else ""
    if prefer_anilist:
        return al_cover or sh_img or ""
    return sh_img or ""

def get_country_info(plugin, data, mapping):
    code = data.get("countryOfOrigin", "JP") if data else "JP"
    flags = mapping.universal_mapping.get("flags") or {}
    flag = flags.get(code, "🇯🇵") if plugin.show_flag else ""
    txt = ""
    if plugin.show_country:
        txt = (mapping.universal_mapping.get("countries") or {}).get(code, ["Неизвестно"])[0]
        if plugin.hash_country:
            txt = "#" + txt
    return flag, txt, code

def get_season_year(plugin, data, shiki_data, mapping):
    season_val = year_val = ""
    if plugin.show_season or plugin.show_year:
        season_val = (mapping.universal_mapping.get("seasons") or {}).get(data.get("season"), [""])[0] if data and data.get("season") else ""
        year_val = data.get("seasonYear", "") if data else ""
        if not season_val and shiki_data and shiki_data.get("aired_on"):
            try:
                parts = shiki_data["aired_on"].split("-")
                year_val = year_val or parts[0]
                m = int(parts[1]) if len(parts) > 1 else 0
                sm = mapping.universal_mapping.get("season_month") or {}
                season_val = season_val or sm.get(str(m), sm.get(m, ""))
            except Exception:
                pass
    return (season_val if plugin.show_season else ""), (str(year_val) if year_val and year_val != "????" and plugin.show_year else "")

def get_description(plugin, data, shiki_data, force=False):
    if not force and not plugin.show_description:
        return ""
    desc = ""
    if plugin.desc_source == 0:
        if shiki_data:
            desc = shiki_data.get("description") or shiki_data.get("synopsis") or ""
    else:
        if data:
            desc = data.get("description") or ""
    return desc.strip() if desc else ""

def clean_template_output(text, vars_dict, empty_ph_space_mode=0):
    if not text:
        return ""
    empty, non_empty = set(), []
    if vars_dict:
        for k, v in vars_dict.items():
            val = str(v).strip()
            if not val:
                empty.add(k)
            else:
                non_empty.append(val)
    lines, cleaned = text.split("\n"), []
    mode = empty_ph_space_mode
    hang = re.compile(
        r"^(студии|источник|статус|длительность|формат|целевая аудитория|жанры|теги|ссылки|описание|оригинал|продолжительность серии|рейтинг|эпизоды)[\s:]*$",
        re.I | re.UNICODE,
    )
    pure = re.compile(r"^[\s|#\-–—.,;:]+$", re.UNICODE)
    for line in lines:
        if not line.strip():
            continue
        proc = line
        for key in empty:
            ph = "{" + key + "}"
            if mode == 0:
                proc = re.sub(r"\s*" + re.escape(ph), "", proc)
            else:
                proc = re.sub(re.escape(ph) + r"\s*", "", proc)
            proc = proc.replace(ph, "")
        proc = proc.strip()
        if not proc:
            continue
        if proc in ("|", "| ", " |", "||"):
            continue
        if vars_dict:
            has = any(v.rstrip(",").strip() and (v.rstrip(",").strip() in proc or v in proc) for v in non_empty)
            if not has and (hang.match(proc) or pure.match(proc)):
                continue
        proc = re.sub(r"\s{2,}", " ", proc)
        proc = re.sub(r",\s*,", ",", proc)
        proc = re.sub(r"\s+,", ",", proc)
        proc = re.sub(r",\s+", ", ", proc)
        cleaned.append(proc)
    res = "\n".join(cleaned)
    return re.sub(r"\n{3,}", "\n\n", res).strip()

def _setting_on(plugin, key, default=True):
    return gb(plugin, key, default)


def resolve_anime_label(plugin, main_on=True):
    if not main_on or not gb(plugin, "show_anime_label", True):
        return gs(plugin, "hash_anime_replace", "|") or "|"
    if gb(plugin, "show_hash_anime", True):
        return "#аниме"
    return "аниме"

def format_media_full(plugin, data, template, shiki_data, mapping, no_link=False, no_preview=False):
    if not data:
        data = None
    if not data and not shiki_data:
        return "Не найдено"
    main_on = _setting_on(plugin, "coll_fields_main", True)
    hash_main_on = _setting_on(plugin, "coll_hash_main", True)
    under_main_on = _setting_on(plugin, "coll_under_main", True)
    def f_on(attr, master=True):
        if not master:
            return False
        return gb(plugin, attr, True)
    show_flag = f_on("show_flag", main_on)
    show_country = f_on("show_country", main_on)
    show_season = f_on("show_season", main_on)
    show_year = f_on("show_year", main_on)
    show_year_g = f_on("show_year_g", main_on)
    show_format = f_on("show_format", main_on)
    show_demographic = f_on("show_demographic", main_on)
    show_episodes = f_on("show_episodes", main_on)
    show_score = f_on("show_score", main_on)
    show_status = f_on("show_status", main_on)
    show_duration = f_on("show_duration", main_on)
    show_source = f_on("show_source", main_on)
    show_studios = f_on("show_studios", main_on)
    main_ru, other_ru, main_en, other_en = extract_titles(plugin, data, shiki_data)
    try:
        _cs = plugin.get_setting("cover_source", getattr(plugin, "cover_source", 0)) if hasattr(plugin, "get_setting") else getattr(plugin, "cover_source", 0)
        prefer_al = int(_cs or 0) == 0
    except Exception:
        prefer_al = True
    cover = get_cover_url(data, shiki_data, prefer_anilist=prefer_al)
    if not cover and prefer_al:
        cover = get_cover_url(data, shiki_data, prefer_anilist=False)
    preview = "" if no_preview or no_link else (f'<a href="{cover}">&shy;</a>' if cover else "")
    flag, country_text, _ = get_country_info(plugin, data, mapping)
    if not show_flag:
        flag = ""
    if not show_country:
        country_text = ""
    season, year = get_season_year(plugin, data, shiki_data, mapping)
    if not show_season:
        season = ""
    if not show_year:
        year = ""
    ep_raw = None
    st_raw = ""
    if data:
        ep_raw = data.get("episodes")
        st_raw = data.get("status") or ""
    elif shiki_data:
        ep_raw = shiki_data.get("episodes")
        st_raw = shiki_data.get("status") or ""
    ep_str = ""
    if show_episodes:
        ea = None
        et = ep_raw
        if data:
            if st_raw == "FINISHED" and ep_raw:
                ep_str = f"{ep_raw}/{ep_raw} эп."
            else:
                nae = data.get("nextAiringEpisode") if isinstance(data.get("nextAiringEpisode"), dict) else None
                if nae and nae.get("episode") is not None:
                    try:
                        ea = int(nae["episode"]) - 1
                        if ea < 0:
                            ea = 0
                    except Exception:
                        ea = None
                if ea is None and data.get("episodes_aired") is not None:
                    try:
                        ea = int(data.get("episodes_aired"))
                    except Exception:
                        pass
                if ea is not None and ea >= 0:
                    if et and int(et) > 0:
                        ep_str = f"{ea}/{int(et)} эп."
                    else:
                        ep_str = f"{ea}/? эп."
                elif et:
                    ep_str = f"?/{int(et)} эп." if st_raw == "RELEASING" else f"{int(et)} эп."
                else:
                    ep_str = "? эп."
        elif shiki_data:
            ea = shiki_data.get("episodes_aired")
            et = shiki_data.get("episodes")
            try:
                if ea is not None and int(ea or 0) > 0:
                    if et and int(et) > 0:
                        ep_str = f"{int(ea)}/{int(et)} эп."
                    else:
                        ep_str = f"{int(ea)}/? эп."
                elif et:
                    ep_str = f"{int(et)} эп."
                else:
                    ep_str = "? эп."
            except Exception:
                ep_str = "? эп."
    fmt_raw = ""
    fmt_tr = ""
    if data:
        fmt_raw = data.get("format") or ""
        fmt_tr = (mapping.universal_mapping.get("formats") or {}).get(fmt_raw, [fmt_raw])[0] if fmt_raw else ""
    elif shiki_data:
        kind = (shiki_data.get("kind") or "").lower()
        fs = mapping.universal_mapping.get("format_shiki") or {}
        fmt_tr = fs.get(kind, kind.upper() if kind else "")
        fmt_raw = kind
    fmt_text = format_item(fmt_tr, plugin.underscore_format and under_main_on, plugin.hash_format and hash_main_on) if show_format and fmt_tr else ""
    if plugin.ona_clarify and str(fmt_raw).upper() == "ONA":
        eps = ep_raw
        ona = "фильм" if eps == 1 else ("сериал" if eps and eps > 1 else "")
        if ona:
            ot = (mapping.universal_mapping.get("formats_extra") or {}).get(ona, [ona])[0]
            fmt_text += " " + format_item(ot, plugin.underscore_format and under_main_on, plugin.hash_format and hash_main_on)
    dem_raw = ""
    if data and "tags" in data:
        for tag in data["tags"]:
            if tag.get("rank", 0) > 90 and tag["name"] in ("Shounen", "Shoujo", "Seinen", "Josei", "Kids"):
                dem_raw = tag["name"]
                break
    dem_tr = (mapping.universal_mapping.get("demographics") or {}).get(dem_raw, [dem_raw])[0] if dem_raw else "отсутствует"
    dem_text = format_item(dem_tr, False, plugin.hash_demographic and hash_main_on) if show_demographic and dem_tr else ""
    genres_str = process_genres(plugin, data, mapping) if (data and plugin.show_genres) else ""
    tags_str = process_tags(plugin, data, mapping) if (data and plugin.show_tags) else ""
    if not genres_str and shiki_data and plugin.show_genres:
        raw_g = shiki_data.get("genres") or []
        um = mapping.universal_mapping
        main_m = um.get("main_genres", {})
        add_m = um.get("additional_genres", {})
        names = []
        for g in raw_g:
            if isinstance(g, dict):
                en = g.get("name") or ""
                ru = g.get("russian") or ""
                tr = main_m.get(en) or add_m.get(en) or main_m.get(ru) or add_m.get(ru)
                if tr:
                    names.append(tr[0] if isinstance(tr, list) else tr)
                else:
                    names.append(ru or en)
            else:
                s = str(g)
                tr = main_m.get(s) or add_m.get(s)
                names.append((tr[0] if isinstance(tr, list) else tr) if tr else s)
        names = [n for n in names if n]
        if names:
            if plugin.hash_genres:
                names = ["#" + n.replace(" ", "") for n in names]
            genres_str = ", ".join(names) if plugin.comma_genres else " ".join(names)
    score = ""
    if show_score:
        if data and data.get("averageScore") is not None:
            score = f"{data.get('averageScore') / 10:.1f}/10"
        elif shiki_data and shiki_data.get("score"):
            try:
                score = f"{float(shiki_data.get('score')):.1f}/10"
            except Exception:
                score = ""
    st_map = mapping.universal_mapping.get("status") or {}
    st_tr = ""
    if st_raw:
        key = st_raw
        if key not in st_map and str(key).lower() in SHIKI_STATUS_MAP:
            key = SHIKI_STATUS_MAP[str(key).lower()]
        raw_val = st_map.get(key) or st_map.get(str(st_raw)) or st_map.get(str(st_raw).lower())
        if isinstance(raw_val, list):
            st_tr = raw_val[0] if raw_val else str(st_raw).lower()
        elif raw_val:
            st_tr = str(raw_val)
        else:
            st_tr = str(st_raw).lower()
    st_text = format_item(str(st_tr), plugin.underscore_status and under_main_on, plugin.hash_status and hash_main_on) if show_status and st_tr else ""
    dur = ""
    if show_duration:
        if data and data.get("duration"):
            dur = f"{data.get('duration')} мин."
        elif shiki_data and shiki_data.get("duration"):
            dur = f"{shiki_data.get('duration')} мин."
    src_raw = data.get("source") if data else ""
    src_tr = (mapping.universal_mapping.get("source") or {}).get(src_raw, [src_raw.lower() if src_raw else "?"])[0] if src_raw else ""
    src_text = format_item(src_tr, plugin.underscore_source and under_main_on, plugin.hash_source and hash_main_on) if show_source and src_tr else ""
    studs = []
    if show_studios:
        if data and data.get("studios"):
            studs = [s["name"] for s in data.get("studios", {}).get("nodes", [])]
        elif shiki_data and shiki_data.get("studios"):
            for s in shiki_data.get("studios") or []:
                if isinstance(s, dict):
                    studs.append(s.get("name") or "")
                else:
                    studs.append(str(s))
            studs = [s for s in studs if s]
    stud_f = [format_item(sn, plugin.underscore_studios and under_main_on, plugin.hash_studios and hash_main_on) for sn in studs]
    studios = ", ".join(stud_f) if plugin.comma_studios else " ".join(stud_f)
    link1 = f'<a href="https://anilist.co/anime/{data.get("id")}">{plugin.anilist_link_text}</a>' if (not no_link) and plugin.show_link_in_full and data and data.get("id") else ""
    link2 = f'<a href="https://shikimori.one/animes/{shiki_data.get("id")}">{plugin.shikimori_link_text}</a>' if (not no_link) and plugin.show_shikimori_link and shiki_data and shiki_data.get("id") else ""
    anime_label = resolve_anime_label(plugin, main_on)
    desc = get_description(plugin, data, shiki_data, force=plugin.description_in_card)
    if plugin.description_in_card and desc and plugin.show_description:
        desc = f"<b><i>{desc}</i></b>"
        if plugin.enable_html_card:
            desc = f"<blockquote expandable>{desc}</blockquote>"
    else:
        desc = ""
    year_str = f"{year}г." if year and plugin.show_year_g else year
    vd = {
        "preview": preview, "a": anime_label,
        "ru1": f"<code>{main_ru}</code>" if main_ru else "",
        "ru2": f"<code>{other_ru[0]}</code>" if len(other_ru) > 0 else "",
        "ru3": f"<code>{other_ru[1]}</code>" if len(other_ru) > 1 else "",
        "ru4": f"<code>{other_ru[2]}</code>" if len(other_ru) > 2 else "",
        "ru5": f"<code>{other_ru[3]}</code>" if len(other_ru) > 3 else "",
        "en1": f"<code>{main_en}</code>" if main_en else "",
        "en2": f"<code>{other_en[0]}</code>" if len(other_en) > 0 else "",
        "en3": f"<code>{other_en[1]}</code>" if len(other_en) > 1 else "",
        "en4": f"<code>{other_en[2]}</code>" if len(other_en) > 2 else "",
        "en5": f"<code>{other_en[3]}</code>" if len(other_en) > 3 else "",
        "flag": flag, "country": country_text, "season": season, "year": year_str,
        "format": fmt_text, "audience": dem_text, "genres": genres_str, "tags": tags_str,
        "episodes": ep_str, "score": score, "status": st_text, "duration": dur,
        "source": src_text, "studios": studios, "link1": link1, "link2": link2, "description": desc,
    }
    try:
        result = template.format(**vd)
    except Exception:
        result = "Ошибка в шаблоне карточки"
    result = clean_template_output(result, vd, plugin.empty_ph_space_mode)
    if "#аниме" in result and anime_label != "#аниме":
        result = result.replace("#аниме", anime_label)
    return result
