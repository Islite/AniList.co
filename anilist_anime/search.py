import time

from android_utils import run_on_ui_thread
from client_utils import run_on_queue, send_text

import api
from formatter import clean_template_output, format_media_full, get_description
from utils import is_cyrillic, show_error, show_success

def prefer_shiki(plugin, query=""):
    if plugin.primary_source == 1:
        return bool(plugin.use_shikimori)
    if plugin.use_shikimori and not plugin.use_anilist:
        return True
    return plugin.use_shikimori and is_cyrillic(query)

def cache_result(cache, cache_key, anilist_data, successful_original, shiki_data):
    packed = (anilist_data, successful_original, shiki_data, time.time())
    cache[cache_key] = packed
    if anilist_data and anilist_data.get("id") is not None:
        cache[f"data_{anilist_data.get('id')}"] = packed
    if shiki_data and shiki_data.get("id") is not None:
        cache[f"data_{shiki_data.get('id')}"] = packed
    return anilist_data, successful_original, shiki_data

def get_data_by_id_or_search(plugin, original_candidates, cache_key, cache):
    if cache_key in cache:
        c = cache[cache_key]
        ad = c[0] if isinstance(c, tuple) else c
        so = c[1] if isinstance(c, tuple) and len(c) > 1 else ""
        sd = c[2] if isinstance(c, tuple) and len(c) > 2 else None
        if ad is None and sd is not None and getattr(plugin, "use_anilist", True):
            try:
                mal = sd.get("myanimelist_id") or sd.get("id_mal")
                if mal:
                    ad = api.fetch_by_mal_id(mal)
                if ad is None:
                    en = sd.get("name") or (sd.get("english") or [None])[0]
                    if en:
                        ad = api.fetch_anilist(en)
                if ad is not None:
                    cache[cache_key] = (ad, so, sd)
            except Exception:
                pass
        return ad, so, sd
    anilist_data = shiki_data = None
    successful_original = ""
    first = original_candidates[0] if original_candidates else ""
    if first and first.isdigit():
        id_int = int(first)
        successful_original = first
        id_src = int(getattr(plugin, "id_api", getattr(plugin, "direct_id_source", 0)) or 0)
        if id_src == 0:
            if plugin.use_anilist:
                anilist_data = api.fetch_by_id(id_int)
            if anilist_data and plugin.use_shikimori:
                en = anilist_data["title"].get("english") or anilist_data["title"].get("romaji") or anilist_data["title"].get("userPreferred")
                shiki_data = api.search_shikimori(en, cache) if en else None
        else:
            if plugin.use_shikimori:
                shiki_data = api.search_shikimori(first, cache)
            if shiki_data and plugin.use_anilist:
                mal = shiki_data.get("myanimelist_id") or shiki_data.get("id_mal")
                if mal:
                    anilist_data = api.fetch_by_mal_id(int(mal))
                if not anilist_data:
                    en = shiki_data.get("name") or ""
                    if not en:
                        eng = shiki_data.get("english")
                        if isinstance(eng, list) and eng:
                            en = eng[0]
                        elif eng:
                            en = eng
                    if en:
                        anilist_data = api.fetch_anilist(str(en))
        if anilist_data or shiki_data:
            return cache_result(cache, cache_key, anilist_data, successful_original, shiki_data)
        return None, "", None

    pref = prefer_shiki(plugin, first)
    if pref and plugin.use_shikimori:
        for term in original_candidates:
            shiki_data = api.search_shikimori(term, cache)
            if shiki_data:
                successful_original = term
                anilist_en = shiki_data.get("name") or (shiki_data.get("english") or [None])[0] or term
                if plugin.use_anilist:
                    anilist_data = api.fetch_anilist(anilist_en)
                    if not anilist_data and (mal := shiki_data.get("myanimelist_id") or shiki_data.get("id_mal")):
                        anilist_data = api.fetch_by_mal_id(mal)
                return cache_result(cache, cache_key, anilist_data, successful_original, shiki_data)
    if plugin.use_anilist:
        for term in original_candidates:
            anilist_data = api.fetch_anilist(term)
            if anilist_data:
                successful_original = term
                en = anilist_data["title"].get("english") or anilist_data["title"].get("romaji") or anilist_data["title"].get("native")
                if plugin.use_shikimori and en:
                    shiki_data = api.search_shikimori(en, cache)
                return cache_result(cache, cache_key, anilist_data, successful_original, shiki_data)
    if not pref and plugin.use_shikimori:
        for term in original_candidates:
            shiki_data = api.search_shikimori(term, cache)
            if shiki_data:
                successful_original = term
                anilist_en = shiki_data.get("name") or (shiki_data.get("english") or [None])[0] or term
                if plugin.use_anilist:
                    anilist_data = api.fetch_anilist(anilist_en)
                    if not anilist_data and (mal := shiki_data.get("myanimelist_id") or shiki_data.get("id_mal")):
                        anilist_data = api.fetch_by_mal_id(mal)
                return cache_result(cache, cache_key, anilist_data, successful_original, shiki_data)
    return None, "", None

def build_send_params(account, base, text, parse_mode=None):
    p = {"peer": base["peer"], "text": text, "parse_mode": parse_mode}
    if base.get("replyToMsg"):
        p["replyToMsg"] = base["replyToMsg"]
    if base.get("replyToTopMsg"):
        p["replyToTopMsg"] = base["replyToTopMsg"]
    if base.get("messageThreadId") is not None:
        p["messageThreadId"] = base["messageThreadId"]
    return p

def send_only_success(plugin, text, account, base):
    try:
        cleaned = clean_template_output(text, None, plugin.empty_ph_space_mode)
        if not cleaned.strip():
            return
        p = build_send_params(account, base, cleaned, "HTML" if plugin.enable_html_card else None)
        send_text(account=account, **p)
        show_success("Отправлено")
    except Exception:
        pass

def send_description_separate(description_raw, account, base):
    if not description_raw.strip():
        return
    try:
        p = build_send_params(account, base, f"<blockquote expandable><b><i>{description_raw}</i></b></blockquote>", "HTML")
        send_text(account=account, **p)
    except Exception:
        pass

def _refresh_cover_via_bot(account, cover_url):
    """Тихо обновить webpage-кэш через @WebpageBot. Без сообщений в текущий чат."""
    if not cover_url:
        return
    url = str(cover_url).strip()
    if not url.startswith("http"):
        return
    def _send(peer):
        if peer is None:
            return
        try:
            send_text(int(peer), url, account=account)
        except Exception:
            try:
                send_text(account=account, peer=int(peer), text=url)
            except Exception:
                pass
    try:
        from org.telegram.tgnet import TLRPC
        from client_utils import send_request
        def _on_res(resp, err):
            try:
                if err or not resp:
                    return
                uid = None
                users = getattr(resp, "users", None)
                if users is not None:
                    u = None
                    try:
                        u = users.get(0) if hasattr(users, "get") else (users[0] if len(users) > 0 else None)
                    except Exception:
                        u = None
                    if u is not None:
                        uid = getattr(u, "id", None)
                if uid:
                    _send(int(uid))
            except Exception:
                pass
        req = TLRPC.TL_contacts_resolveUsername()
        req.username = "WebpageBot"
        try:
            send_request(req, _on_res, account=account)
        except TypeError:
            try:
                send_request(req, _on_res)
            except Exception:
                pass
    except Exception:
        pass





def _peer_from_base(base, account=None):
    try:
        if isinstance(base, dict) and base.get("peer") is not None:
            return int(base["peer"])
    except Exception:
        pass
    try:
        from org.telegram.ui import ChatActivity
        from client_utils import get_last_fragment
        frag = get_last_fragment()
        if frag and isinstance(frag, ChatActivity):
            return frag.getDialogId()
    except Exception:
        pass
    return None

def _setting_int(plugin, key, default=0):
    try:
        if hasattr(plugin, "get_setting"):
            v = plugin.get_setting(key, default)
            if v is not None and v != "":
                return int(v)
    except Exception:
        pass
    try:
        return int(getattr(plugin, key, default) or default)
    except Exception:
        return default

def _dl_cover_file(url, aid):
    import os, re, requests
    try:
        from org.telegram.messenger import FileLoader
        d = FileLoader.getDirectory(getattr(FileLoader, "MEDIA_DIR_IMAGE", 0))
        base = d.getAbsolutePath() if d is not None and hasattr(d, "getAbsolutePath") else (str(d) if d else "")
        if not base:
            try:
                from file_utils import get_images_dir
                base = str(get_images_dir() or "")
            except Exception:
                base = ""
        if not base:
            return None
        try:
            from file_utils import ensure_dir_exists
            ensure_dir_exists(base)
        except Exception:
            os.makedirs(base, exist_ok=True)
        safe = re.sub(r"[^a-zA-Z0-9_-]", "", str(aid or "x"))[:32] or "x"
        path = os.path.join(base, "aa_cover_" + safe + ".jpg")
        if os.path.isfile(path) and os.path.getsize(path) > 500:
            return path
        if not url or "missing_" in str(url):
            return None
        headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36", "Accept": "image/*,*/*"}
        resp = requests.get(url, timeout=12, headers=headers)
        if resp.status_code == 200 and resp.content and len(resp.content) >= 500:
            with open(path, "wb") as f:
                f.write(resp.content)
            if os.path.isfile(path) and os.path.getsize(path) > 500:
                return path
    except Exception:
        pass
    return None



def _send_media_with_caption(peer, path, caption, invert=False, account=None):
    """Одно сообщение: фото + caption. Сначала client_utils.send_photo."""
    cap = str(caption or "")
    if len(cap) > 1024:
        cap = cap[:1020].rsplit("\n", 1)[0] + "…"
    try:
        from client_utils import send_photo
        kwargs = {"caption": cap, "parse_mode": "HTML"}
        if account is not None:
            kwargs["account"] = account
        if invert:
            try:
                kwargs["invert_media"] = True
                send_photo(peer, str(path), **kwargs)
                return True
            except TypeError:
                kwargs.pop("invert_media", None)
        try:
            send_photo(peer, str(path), **kwargs)
            return True
        except TypeError:
            send_photo(peer, str(path), caption=cap)
            return True
    except Exception:
        pass
    try:
        from org.telegram.messenger import SendMessagesHelper, AccountInstance, UserConfig
        from java.util import ArrayList
        from hook_utils import find_class
        from extera_utils.text_formatting import parse_text
        SMI = find_class("org.telegram.messenger.SendMessagesHelper$SendingMediaInfo")
        if SMI is None:
            raise Exception("SMI")
        plain, ents = cap, None
        try:
            parsed = parse_text(cap, parse_mode="HTML", is_caption=True)
            plain = parsed.get("caption") or parsed.get("message") or cap
            ents = parsed.get("entities")
        except Exception:
            pass
        info = SMI()
        info.path = str(path)
        try:
            info.caption = str(plain or "")
        except Exception:
            pass
        if ents is not None:
            try:
                if not hasattr(ents, "add"):
                    al = ArrayList()
                    for e in ents:
                        al.add(e)
                    ents = al
                info.entities = ents
            except Exception:
                pass
        media = ArrayList()
        media.add(info)
        acc = AccountInstance.getInstance(UserConfig.selectedAccount)
        inv = bool(invert)
        for args in (
            (acc, media, int(peer), None, None, None, None, False, False, None, True, 0, 0, 0, False, None, None, 0, inv, 0, 0, None),
            (acc, media, int(peer), None, None, None, None, False, False, None, None, True, 0, 0, 0, False, None, None, 0, inv, 0, 0, None),
        ):
            try:
                SendMessagesHelper.prepareSendingMedia(*args)
                return True
            except Exception:
                continue
    except Exception:
        pass
    return False

def _send_html_text(plugin, text, account, base, invert=False):
    cleaned = clean_template_output(text, None, getattr(plugin, "empty_ph_space_mode", 0))
    if not cleaned.strip():
        return False
    parse = "HTML" if getattr(plugin, "enable_html_card", True) else None
    params = build_send_params(account, base, cleaned, parse)
    # invert_media только если клиент принимает; иначе одно сообщение без invert
    if invert:
        try:
            params["invert_media"] = True
            send_text(account=account, **params)
            return True
        except TypeError:
            params.pop("invert_media", None)
        except Exception:
            # не делаем второй send — сообщение могло уже уйти
            params.pop("invert_media", None)
            return False
    try:
        send_text(account=account, **params)
        return True
    except Exception:
        return False

def send_card_and_desc(plugin, data, shiki, account, base, mapping, opts=None):
    if not getattr(plugin, "use_shikimori", True):
        shiki = None
    if not getattr(plugin, "use_anilist", True):
        data = None
    opts = opts or {}
    try:
        mode = int(opts["card_send_mode"]) if "card_send_mode" in opts else _setting_int(plugin, "card_send_mode", 0)
    except Exception:
        mode = 0
    no_link = bool(opts.get("no_link", False))
    # «Без ссылки» = режим медиа + без link1/link2
    if no_link:
        mode = 1
    if "invert" in opts:
        invert = bool(opts.get("invert"))
    else:
        try:
            if mode == 1:
                # media items=["Сверху","Снизу"]: как в search_box _inv media → p==1
                invert = _setting_int(plugin, "media_pos", 0) == 1
            else:
                # preview items=["Снизу","Сверху"]:
                # search_box: Сверху→invert True, Снизу→invert False
                # у нас 0=Снизу→False, 1=Сверху→True
                invert = _setting_int(plugin, "preview_pos", 0) == 1
        except Exception:
            invert = False
    from formatter import get_cover_url
    prefer_al = _setting_int(plugin, "cover_source", 0) == 0
    if not prefer_al and shiki:
        try:
            shiki = api.enrich_shiki_poster(shiki, {})
        except Exception:
            pass
    cover = get_cover_url(data, shiki, prefer_anilist=prefer_al)
    if not cover and prefer_al:
        cover = get_cover_url(data, shiki, prefer_anilist=False)
    # авто-обновление превью только если НЕ медиа
    if mode != 1 and getattr(plugin, "auto_update_cover", False) and cover:
        _refresh_cover_via_bot(account, cover)
    # no_link: отключить только ссылки Ani/Shiki и preview-shy
    card = format_media_full(
        plugin, data, plugin.card_template, shiki, mapping,
        no_link=no_link,
        no_preview=(mode == 1 or no_link),
    )
    cleaned = clean_template_output(card, None, getattr(plugin, "empty_ph_space_mode", 0))
    peer = _peer_from_base(base, account)
    if mode == 1 and peer is not None and cover:
        aid = None
        try:
            if data and data.get("id") is not None:
                aid = data.get("id")
            elif shiki and shiki.get("id") is not None:
                aid = shiki.get("id")
        except Exception:
            pass
        path = _dl_cover_file(cover, aid)
        if path:
            # ОДНО сообщение: обложка + caption с полной карточкой (HTML как есть)
            if _send_media_with_caption(peer, path, cleaned, invert=invert, account=account):
                show_success("Отправлено")
                desc = get_description(plugin, data, shiki)
                if plugin.show_description and desc.strip() and not plugin.description_in_card:
                    run_on_queue(lambda: send_description_separate(desc, account, base))
                return
        # если медиа не удалось — HTML-текстом
    ok = _send_html_text(plugin, card, account, base, invert=invert)
    if ok:
        show_success("Отправлено")
    else:
        show_error("Не удалось отправить")
    desc = get_description(plugin, data, shiki)
    if ok and plugin.show_description and desc.strip() and not plugin.description_in_card:
        run_on_queue(lambda: send_description_separate(desc, account, base))

def process_search(plugin, account, base, original_candidates, cache, mapping):
    try:
        ck = f"data_{original_candidates[0] if original_candidates else 'empty'}"
        data, _, shiki = get_data_by_id_or_search(plugin, original_candidates, ck, cache)
        if data or shiki:
            send_card_and_desc(plugin, data, shiki, account, base, mapping)
        else:
            show_error()
    except Exception:
        pass
        show_error("Ошибка при поиске")

def _map_genres(raw_genres, mapping):
    main_g = mapping.universal_mapping.get("main_genres") or {}
    add_g = mapping.universal_mapping.get("additional_genres") or {}
    out = []
    for g in raw_genres or []:
        tr = main_g.get(g) or add_g.get(g) or [g]
        out.append(tr[0] if isinstance(tr, list) else tr)
    return out

def parse_anilist_media_list(media, mapping):
    results = []
    countries = mapping.universal_mapping.get("countries") or {}
    seasons = mapping.universal_mapping.get("seasons") or {}
    formats = mapping.universal_mapping.get("formats") or {}
    flags = mapping.universal_mapping.get("flags") or {}
    for m in media:
        t = m.get("title") or {}
        title = t.get("userPreferred") or t.get("romaji") or t.get("english") or t.get("native") or "Unknown"
        code = m.get("countryOfOrigin") or "JP"
        flag = flags.get(code, "🇯🇵")
        cname = countries.get(code, ["Япония"])[0]
        season = m.get("season")
        year = m.get("seasonYear")
        sname = seasons.get(season, [""])[0] if season else ""
        country_line = f"{flag} {cname}, {sname} {year}г." if sname and year else f"{flag} {cname}"
        score_val = m.get("averageScore")
        fmt = m.get("format", "")
        results.append({
            "id": m.get("id"),
            "title": title,
            "genres": _map_genres(m.get("genres"), mapping),
            "cover_url": (("https://img.anili.st/media/%s" % m.get("id")) if m.get("id") is not None else ((m.get("coverImage") or {}).get("extraLarge") or (m.get("coverImage") or {}).get("large") or "")),
            "country_line": country_line,
            "score": f"{score_val / 10:.1f}" if score_val is not None else "?",
            "type_ru": formats.get(fmt, [fmt])[0] if fmt else "",
            "source": "anilist",
        })
    return results


def fill_missing_shiki_covers(results, cache, limit=20):
    """Для строк без обложки — точечный REST image (кэш). Лимит, чтобы не тормозить список."""
    if not results:
        return results
    n = 0
    for r in results:
        if n >= limit:
            break
        cu = str(r.get("cover_url") or "")
        if cu.startswith("http") and ("/uploads/" in cu or "/system/" in cu or cu.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))):
            continue
        aid = r.get("id")
        if aid is None:
            continue
        try:
            img = api.fetch_shiki_cover_rest(aid, cache)
        except Exception:
            img = None
        if not img or not isinstance(img, dict):
            continue
        path = img.get("original") or img.get("preview") or ""
        path = str(path).strip() if path else ""
        if not path or "missing" in path:
            continue
        if path.startswith("http"):
            r["cover_url"] = path
        elif path.startswith("//"):
            r["cover_url"] = "https:" + path
        elif path.startswith("/"):
            r["cover_url"] = "https://shikimori.io" + path
        else:
            r["cover_url"] = "https://shikimori.io/" + path.lstrip("/")
        n += 1
    return results

def parse_shikimori_media_list(media, mapping):
    results = []
    fs = mapping.universal_mapping.get("format_shiki") or {}
    sm = mapping.universal_mapping.get("season_month") or {}
    for m in media:
        title = m.get("russian") or m.get("name") or "Unknown"
        # GraphQL poster or old image
        path = ""
        poster = m.get("poster") or {}
        if isinstance(poster, dict):
            path = poster.get("originalUrl") or poster.get("mainUrl") or ""
        if not path:
            img = m.get("image")
            if isinstance(img, dict):
                path = img.get("original") or img.get("preview") or img.get("x96") or ""
            elif isinstance(img, str):
                path = img
        path = str(path).strip() if path else ""
        if path and "missing" in path:
            path = ""
        if path:
            if path.startswith("http"):
                cover_url = path
            elif path.startswith("//"):
                cover_url = "https:" + path
            elif path.startswith("/"):
                cover_url = "https://shikimori.io" + path
            else:
                cover_url = "https://shikimori.io/" + path.lstrip("/")
        else:
            cover_url = ""
        year_val = None
        country_line = ""
        ao = m.get("airedOn") or {}
        if isinstance(ao, dict):
            year_val = ao.get("year")
            date = ao.get("date")
            if date:
                try:
                    y, mo = str(date)[:10].split("-")[:2]
                    year_val = year_val or int(y)
                    sn = sm.get(str(int(mo)), sm.get(int(mo), ""))
                    if sn and year_val:
                        country_line = f"{sn} {year_val}г."
                    elif year_val:
                        country_line = f"{year_val}г."
                except Exception:
                    pass
        if not country_line:
            aired = m.get("aired_on") or m.get("released_on")
            if aired:
                try:
                    y, mo = str(aired).split("-")[:2]
                    year_val = int(y)
                    sn = sm.get(str(int(mo)), sm.get(int(mo), ""))
                    country_line = f"{sn} {y}г." if sn else f"{y}г."
                except Exception:
                    pass
            elif year_val:
                country_line = f"{year_val}г."
        kind = str(m.get("kind") or "").split(".")[-1].lower()
        gens = []
        for g in (m.get("genres") or []):
            if isinstance(g, dict):
                gens.append(g.get("russian") or g.get("name") or "")
            elif isinstance(g, str):
                gens.append(g)
        gens = [x for x in gens if x]
        results.append({
            "id": m.get("id"),
            "mal_id": m.get("malId") or m.get("myanimelist_id"),
            "title": title,
            "genres": gens,
            "cover_url": cover_url,
            "country_line": country_line,
            "score": f"{float(m.get('score')):.1f}" if m.get("score") else "?",
            "type_ru": fs.get(kind, kind.upper() if kind else ""),
            "source": "shikimori",
            "year": year_val,
            "aired_on": (ao.get("date") if isinstance(ao, dict) else None) or m.get("aired_on") or "",
            "episodes_aired": m.get("episodesAired") or m.get("episodes_aired"),
            "episodes": m.get("episodes"),
            "nextEpisodeAt": m.get("nextEpisodeAt"),
        })
    return fill_missing_shiki_covers(results, {})


def _row_from_id_data(data, shiki, mapping, prefer_shiki=False, prefer_anilist_cover=True):
    flags = mapping.universal_mapping.get("flags") or {}
    countries = mapping.universal_mapping.get("countries") or {}
    seasons = mapping.universal_mapping.get("seasons") or {}
    formats = mapping.universal_mapping.get("formats") or {}
    fs = mapping.universal_mapping.get("format_shiki") or {}
    sm = mapping.universal_mapping.get("season_month") or {}

    al_cover = ""
    if data and isinstance(data, dict):
        if data.get("id") is not None:
            al_cover = "https://img.anili.st/media/%s" % data.get("id")
        else:
            ci = data.get("coverImage") or {}
            al_cover = ci.get("extraLarge") or ci.get("large") or ci.get("medium") or ""
    sh_cover = ""
    if shiki:
        try:
            from formatter import _shiki_cover
            sh_cover = _shiki_cover(shiki) or ""
        except Exception:
            sh_cover = ""
        if not sh_cover or "/animes/" in sh_cover and not sh_cover.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            try:
                shiki = api.enrich_shiki_poster(shiki, {})
                from formatter import _shiki_cover
                sh_cover = _shiki_cover(shiki) or ""
            except Exception:
                pass
    if prefer_anilist_cover:
        cover = al_cover or sh_cover
    else:
        cover = sh_cover or ""

    country_line = ""
    type_ru = ""
    score = "?"
    genres = []
    if data and isinstance(data, dict):
        code = data.get("countryOfOrigin") or "JP"
        flag = flags.get(code, "🇯🇵")
        cname = (countries.get(code) or ["Япония"])[0]
        season = data.get("season")
        year = data.get("seasonYear")
        sname = (seasons.get(season) or [""])[0] if season else ""
        country_line = "%s %s, %s %sг." % (flag, cname, sname, year) if sname and year else "%s %s" % (flag, cname)
        score_val = data.get("averageScore")
        if score_val is not None:
            score = "%.1f" % (score_val / 10.0)
        fmt = data.get("format") or ""
        type_ru = (formats.get(fmt) or [fmt])[0] if fmt else ""
        genres = _map_genres(data.get("genres"), mapping)
    if shiki and (not country_line or score == "?" or not type_ru):
        if not country_line:
            country_line = ""
            aired = shiki.get("aired_on") or shiki.get("released_on")
            if aired:
                try:
                    y, mo = str(aired).split("-")[:2]
                    country_line = "%s %sг." % (sm.get(str(int(mo)), sm.get(int(mo), "зима")), y)
                except Exception:
                    pass
        if score == "?" and shiki.get("score"):
            try:
                score = "%.1f" % float(shiki.get("score"))
            except Exception:
                pass
        if not type_ru:
            kind = (shiki.get("kind") or "").lower()
            type_ru = fs.get(kind, kind.upper()) if kind else ""

    if prefer_shiki and shiki:
        rid = shiki.get("id")
        title = shiki.get("russian") or shiki.get("name") or "Unknown"
        return {
            "id": rid,
            "title": title,
            "genres": genres,
            "cover_url": cover,
            "country_line": country_line or "",
            "score": score,
            "type_ru": type_ru,
            "source": "shikimori",
        }
    if data:
        rid = data.get("id")
        tt = data.get("title") or {}
        title = tt.get("userPreferred") or tt.get("romaji") or tt.get("english") or tt.get("native") or "Unknown"
        return {
            "id": rid,
            "title": title,
            "genres": genres,
            "cover_url": cover,
            "country_line": country_line or "",
            "score": score,
            "type_ru": type_ru,
            "source": "anilist",
        }
    if shiki:
        rid = shiki.get("id")
        title = shiki.get("russian") or shiki.get("name") or "Unknown"
        return {
            "id": rid,
            "title": title,
            "genres": genres,
            "cover_url": cover,
            "country_line": country_line or "",
            "score": score,
            "type_ru": type_ru,
            "source": "shikimori",
        }
    return None

def multi_search_by_genre(plugin, query, pref, mapping, cache):
    shiki_id, shiki_en = mapping.resolve_shiki_genre(query)
    al_en, al_kind = mapping.resolve_anilist_genre(query)
    is_tag = al_kind == "tag"
    if pref:
        if shiki_id is not None:
            raw = api.multi_search_shikimori_genre(shiki_id)
            if raw:
                return parse_shikimori_media_list(raw, mapping), True
        name = al_en or shiki_en or query
        raw = api.multi_search_anilist_genre(name, force_tag=is_tag)
        if raw:
            return parse_anilist_media_list(raw, mapping), False
        return [], pref
    name = al_en or shiki_en or query
    raw = api.multi_search_anilist_genre(name, force_tag=is_tag)
    if raw:
        return parse_anilist_media_list(raw, mapping), False
    if shiki_id is not None:
        raw = api.multi_search_shikimori_genre(shiki_id)
        if raw:
            return parse_shikimori_media_list(raw, mapping), True
    return [], pref

def _text_multi_search(plugin, q, pref, cache, mapping):
    ck = f"multi_{pref}_{q.lower()}"
    now = time.time()
    if ck in cache and isinstance(cache[ck], tuple) and len(cache[ck]) >= 2 and now - cache[ck][-1] < 300:
        return cache[ck][0], cache[ck][1]
    results = None
    actual_shiki = False
    if pref and plugin.use_shikimori:
        raw = api.multi_search_shikimori(q)
        actual_shiki = True
        results = parse_shikimori_media_list(raw, mapping) if raw is not None else None
        if not results and plugin.use_anilist:
            raw = api.multi_search_anilist(q)
            results = parse_anilist_media_list(raw, mapping) if raw is not None else None
            actual_shiki = False
    else:
        raw = api.multi_search_anilist(q) if plugin.use_anilist else None
        results = parse_anilist_media_list(raw, mapping) if raw is not None else None
        actual_shiki = False
        if (not results) and plugin.use_shikimori:
            raw = api.multi_search_shikimori(q)
            results = parse_shikimori_media_list(raw, mapping) if raw is not None else None
            actual_shiki = True
    if results is not None:
        cache[ck] = (results, actual_shiki, time.time())
    return results, actual_shiki

def process_multi_search(plugin, query, is_genre, account, base, cache, mapping, show_popup_cb, on_select_cb):
    q = (query or "").strip()
    pref = prefer_shiki(plugin, q)
    id_row = None
    actual_shiki = pref

    if not is_genre and q.isdigit():
        ck = f"data_{q}"
        data, _, shiki = get_data_by_id_or_search(plugin, [q], ck, cache)
        if data or shiki:
            id_pref = int(getattr(plugin, "id_api", getattr(plugin, "direct_id_source", 0)) or 0) == 1
            cover_pref = int(getattr(plugin, "cover_source", 0) or 0) == 0
            id_row = _row_from_id_data(data, shiki, mapping, prefer_shiki=id_pref, prefer_anilist_cover=cover_pref)
            actual_shiki = bool(shiki and not data)

    if is_genre:
        results, actual_shiki = multi_search_by_genre(plugin, q, pref, mapping, cache)
    else:
        results, text_shiki = _text_multi_search(plugin, q, pref, cache, mapping)
        if results is None and id_row is None:
            show_error("Ошибка API")
            return
        if results is None:
            results = []
        else:
            actual_shiki = text_shiki

    if id_row is not None:
        rid = id_row.get("id")
        id_src = id_row.get("source")
        id_row["_section"] = "id"
        rest = []
        for r in (results or []):
            if r.get("id") == rid and r.get("source") == id_src:
                continue
            r = dict(r)
            r["_section"] = "name"
            rest.append(r)
        results = [id_row] + rest
        actual_shiki = id_row.get("source") == "shikimori"

    if results is None:
        show_error("Ошибка API")
        return
    if not results:
        show_error("Ничего не найдено" if not is_genre else "Жанр/тег не найден")
        return
    if plugin.search_ui_mode == 1:
        run_on_queue(lambda: on_select_cb(results[0], account, base))
        return
    run_on_ui_thread(lambda: show_popup_cb(results, q, actual_shiki, is_genre, account, base))

def on_popup_select(plugin, res, account, base, cache, mapping, opts=None):
    try:
        anilist_data = shiki_data = None
        rid = res.get("id")
        ck = f"data_{rid}" if rid is not None else None
        if ck and ck in cache:
            c = cache[ck]
            anilist_data = c[0] if isinstance(c, tuple) else c
            shiki_data = c[2] if isinstance(c, tuple) and len(c) > 2 else None
        if res.get("source") == "shikimori":
            if not shiki_data:
                shiki_data = api.search_shikimori(str(rid), cache)
            if shiki_data and plugin.use_anilist and not anilist_data:
                mal = shiki_data.get("myanimelist_id") or shiki_data.get("id_mal") or shiki_data.get("malId")
                if mal:
                    anilist_data = api.fetch_by_mal_id(mal)
                if not anilist_data:
                    en = shiki_data.get("name") or shiki_data.get("russian")
                    if not en:
                        eng = shiki_data.get("english")
                        if isinstance(eng, list) and eng:
                            en = eng[0]
                        elif eng:
                            en = eng
                    if en:
                        anilist_data = api.fetch_anilist(str(en))
        else:
            if plugin.use_anilist and rid and not anilist_data:
                anilist_data = api.fetch_by_id(int(rid))
            if anilist_data and plugin.use_shikimori and not shiki_data:
                en = anilist_data["title"].get("english") or anilist_data["title"].get("romaji") or anilist_data["title"].get("userPreferred")
                shiki_data = api.search_shikimori(en, cache) if en else None
        # если источник обложки Shikimori — обязательно подтянуть shiki_data
        try:
            need_sh = int(plugin.get_setting("cover_source", getattr(plugin, "cover_source", 0)) or 0) == 1
        except Exception:
            need_sh = int(getattr(plugin, "cover_source", 0) or 0) == 1
        if need_sh and not shiki_data and getattr(plugin, "use_shikimori", True):
            q = None
            if anilist_data:
                t = anilist_data.get("title") or {}
                q = t.get("english") or t.get("romaji") or t.get("userPreferred")
            if not q and rid:
                q = str(rid)
            if q:
                shiki_data = api.search_shikimori(str(q), cache)
        if shiki_data and int(getattr(plugin, "cover_source", 0) or 0) == 1:
            try:
                shiki_data = api.enrich_shiki_poster(shiki_data, cache)
            except Exception:
                pass
        if anilist_data or shiki_data:
            send_card_and_desc(plugin, anilist_data, shiki_data, account, base, mapping, opts)
        else:
            show_error()
    except Exception:
        pass
        show_error("Ошибка при загрузке")

def process_ongoing_search(plugin, account, base, cache, mapping, show_popup_cb, on_select_cb):
    try:
        from datetime import datetime
        results = []
        actual_shiki = False
        ong_src = int(getattr(plugin, "ongoing_api", 0) or 0)
        pref = (ong_src == 1 and plugin.use_shikimori) or (not plugin.use_anilist and plugin.use_shikimori)
        def _fill_al_days(media, results):
            for i, m in enumerate(media):
                if i >= len(results):
                    break
                nae = m.get("nextAiringEpisode") or {}
                air = nae.get("airingAt")
                if air:
                    try:
                        results[i]["day"] = datetime.utcfromtimestamp(int(air)).weekday()
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
        def _map_sh_on(raw):
            mapped = []
            for it in raw:
                anime = it.get("anime") if isinstance(it, dict) and "anime" in it else it
                if not isinstance(anime, dict):
                    continue
                rows = parse_shikimori_media_list([anime], mapping)
                if not rows:
                    continue
                r = rows[0]
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
                            dtp = datetime.fromisoformat(t)
                        except Exception:
                            dtp = datetime.strptime(str(dt)[:19], "%Y-%m-%dT%H:%M:%S")
                        r["day"] = dtp.weekday()
                    except Exception:
                        r["day"] = None
                else:
                    r["day"] = None
                mapped.append(r)
            return mapped
        from datetime import datetime as _dt0
        _n0 = _dt0.utcnow()
        _cy = _n0.year
        if _n0.month == 12:
            _cy = _n0.year + 1
        def _filter_year(rows, year):
            out = []
            for r in rows:
                y = r.get("year") or r.get("seasonYear")
                if y is None:
                    aired = r.get("aired_on") or ""
                    if isinstance(aired, str) and len(aired) >= 4 and aired[:4].isdigit():
                        y = int(aired[:4])
                try:
                    if y is None or int(y) != int(year):
                        continue
                except Exception:
                    continue
                out.append(r)
            return out
        if pref and plugin.use_shikimori:
            raw = api.fetch_ongoing_shikimori()
            if raw:
                actual_shiki = True
                results = _map_sh_on(raw)
                results = _filter_year(results, _cy)
            if not results and plugin.use_anilist:
                media = api.fetch_ongoing_anilist()
                if media:
                    results = parse_anilist_media_list(media, mapping)
                    _fill_al_days(media, results)
        elif plugin.use_anilist:
            media = api.fetch_ongoing_anilist()
            if media:
                results = parse_anilist_media_list(media, mapping)
                _fill_al_days(media, results)
            if not results and plugin.use_shikimori:
                raw = api.fetch_ongoing_shikimori()
                if raw:
                    actual_shiki = True
                    results = _map_sh_on(raw)
                    results = _filter_year(results, _cy)
        elif plugin.use_shikimori:
            raw = api.fetch_ongoing_shikimori()
            if raw:
                actual_shiki = True
                results = _map_sh_on(raw)
                results = _filter_year(results, _cy)
        def _has_aired(r):
            ea = r.get("episodes_aired")
            if ea is not None:
                try:
                    return int(ea) > 0
                except Exception:
                    pass
            ep = r.get("episode")
            if ep is not None:
                try:
                    return int(ep) > 1
                except Exception:
                    pass
            return False
        results = [r for r in results if _has_aired(r)]
        if getattr(plugin, "exclude_hentai", True):
            def _is_hentai(r):
                try:
                    return any("хентай" in str(g).lower() or "hentai" in str(g).lower() for g in (r.get("genres") or []))
                except Exception:
                    return False
            results = [r for r in results if not _is_hentai(r)]
        if not results:
            from utils import show_error
            show_error("Ничего не найдено")
            return
        results.sort(key=lambda x: (x.get("day") if x.get("day") is not None else 9, x.get("title") or ""))
        from datetime import datetime as _dt
        n = _dt.utcnow()
        m, y = n.month, n.year
        if m in (12, 1, 2):
            lab, y = "зима", y + (1 if m == 12 else 0)
        elif m in (3, 4, 5):
            lab = "весна"
        elif m in (6, 7, 8):
            lab = "лето"
        else:
            lab = "осень"
        q = f"{lab} {y}г."
        run_on_ui_thread(lambda: show_popup_cb(results, q, actual_shiki, False, account, base, ongoing=True))
    except Exception:
        from utils import show_error
        show_error("Ошибка онгоингов")
