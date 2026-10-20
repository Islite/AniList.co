import os
import re
import time
import requests
from datetime import datetime

from android_utils import run_on_ui_thread
from client_utils import run_on_queue, send_text

import api
from constants import (
    HENTAI_KEYWORDS,
    MSG_ERR_API,
    MSG_ERR_FAILED_SEND,
    MSG_ERR_LOAD,
    MSG_ERR_ONGOING,
    MSG_ERR_SEARCH,
    MSG_NOT_FOUND,
    MSG_NOT_FOUND_GENRE,
    MSG_SENT,
    MSG_ERR_MEDIA_LOAD,
    MSG_ERR_COVER,
    COVER_FILE_PREFIX,
    DESC_BLOCKQUOTE_TEMPLATE,
    ROUTING_KEYS,
    SEASONS_RU,
    WEBPAGE_BOT_USERNAME,
    SCORE_UNKNOWN,
    DEFAULT_ONGOING_MIN_SCORE,
    DEFAULT_SEARCH_REPLY_IGNORED,
    MSG_TOP_NOT_FOUND,
    MSG_TOP_SOURCE_UNAVAILABLE
)
from formatter import (
    calc_plain_len,
    clean_template_output,
    format_media_full,
    resolve_card_options,
    get_description,
    parse_anilist_media_list,
    parse_ongoing_anilist_results,
    parse_ongoing_shikimori_results,
    parse_shikimori_media_list,
    row_from_id_data,
)
from utils import is_cyrillic, show_error, show_success, gb, gf, gs

_REFRESHED_COVERS_CACHE = {}
_DL_COVER_CACHE = {}

def sanitize_reply_text(plugin, text):
    if not text:
        return ""
    ignored_raw = gs(plugin, "search_reply_ignored_words", DEFAULT_SEARCH_REPLY_IGNORED)
    tokens = [t.strip() for t in str(ignored_raw).split(",") if t.strip()]
    tokens.sort(key=len, reverse=True)
    cleaned = text
    for token in tokens:
        cleaned = re.sub(re.escape(token), " ", cleaned, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned).strip()

def sanitize_candidates(plugin, candidates):
    res = []
    for c in candidates or []:
        cleaned = sanitize_reply_text(plugin, c)
        if cleaned and cleaned not in res:
            res.append(cleaned)
        elif c and c not in res:
            res.append(c)
    return res or candidates

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
        cache[f"data_al_{anilist_data.get('id')}"] = packed
    if shiki_data and shiki_data.get("id") is not None:
        cache[f"data_{shiki_data.get('id')}"] = packed
        cache[f"data_shiki_{shiki_data.get('id')}"] = packed
    return anilist_data, successful_original, shiki_data

def get_data_by_id_or_search(plugin, original_candidates, cache_key, cache):
    candidates = sanitize_candidates(plugin, original_candidates)
    if cache_key in cache:
        c = cache[cache_key]
        if isinstance(c, tuple) and len(c) >= 4 and (time.time() - c[3] < 3600):
            return c[0], c[1], c[2]
        elif not isinstance(c, tuple):
            return c, "", None

    anilist_data = shiki_data = None
    successful_original = ""
    first = candidates[0] if candidates else ""

    if first and first.isdigit():
        id_int = int(first)
        successful_original = first
        id_src = int(getattr(plugin, "id_api", getattr(plugin, "direct_id_source", 0)) or 0)
        
        if id_src == 0:
            if plugin.use_anilist:
                try:
                    anilist_data = api.fetch_by_id(id_int)
                except Exception:
                    anilist_data = None
            if plugin.use_shikimori:
                mal_id = anilist_data.get("idMal") if anilist_data else None
                if mal_id:
                    try:
                        shiki_data = api.search_shikimori_by_id(str(mal_id), cache)
                    except Exception:
                        shiki_data = None
                if not shiki_data and anilist_data:
                    t = anilist_data.get("title") or {}
                    en = t.get("english") or t.get("romaji") or t.get("userPreferred")
                    if en:
                        try:
                            shiki_data = api.search_shikimori(en, cache)
                        except Exception:
                            shiki_data = None
        else:
            if plugin.use_shikimori:
                try:
                    shiki_data = api.search_shikimori_by_id(first, cache)
                except Exception:
                    shiki_data = None
            if plugin.use_anilist:
                mal = (shiki_data.get("malId") or shiki_data.get("myanimelist_id") or shiki_data.get("id_mal")) if shiki_data else None
                if mal:
                    try:
                        anilist_data = api.fetch_by_mal_id(int(mal))
                    except Exception:
                        anilist_data = None
                if not anilist_data and shiki_data:
                    en = shiki_data.get("name")
                    if not en and isinstance(shiki_data.get("english"), list) and shiki_data.get("english"):
                        en = shiki_data["english"][0]
                    if en:
                        try:
                            anilist_data = api.fetch_anilist(str(en))
                        except Exception:
                            anilist_data = None

        if anilist_data or shiki_data:
            return cache_result(cache, cache_key, anilist_data, successful_original, shiki_data)
        return None, "", None

    pref = prefer_shiki(plugin, first)
    if pref and plugin.use_shikimori:
        for term in candidates:
            try:
                shiki_data = api.search_shikimori(term, cache)
            except Exception:
                shiki_data = None
            if shiki_data:
                successful_original = term
                if plugin.use_anilist:
                    try:
                        mal = shiki_data.get("malId") or shiki_data.get("myanimelist_id") or shiki_data.get("id_mal")
                        if mal:
                            anilist_data = api.fetch_by_mal_id(int(mal))
                        if not anilist_data:
                            anilist_en = shiki_data.get("name") or (shiki_data.get("english") or [None])[0] or term
                            anilist_data = api.fetch_anilist(str(anilist_en))
                    except Exception:
                        anilist_data = None
                return cache_result(cache, cache_key, anilist_data, successful_original, shiki_data)
    if plugin.use_anilist:
        for term in candidates:
            try:
                anilist_data = api.fetch_anilist(term)
            except Exception:
                anilist_data = None
            if anilist_data:
                successful_original = term
                if plugin.use_shikimori:
                    try:
                        mal_id = anilist_data.get("idMal")
                        if mal_id:
                            shiki_data = api.search_shikimori_by_id(str(mal_id), cache)
                        if not shiki_data:
                            t = anilist_data.get("title") or {}
                            en = t.get("english") or t.get("romaji") or t.get("native")
                            if en:
                                shiki_data = api.search_shikimori(en, cache)
                    except Exception:
                        shiki_data = None
                return cache_result(cache, cache_key, anilist_data, successful_original, shiki_data)
    if not pref and plugin.use_shikimori:
        for term in candidates:
            try:
                shiki_data = api.search_shikimori(term, cache)
            except Exception:
                shiki_data = None
            if shiki_data:
                successful_original = term
                if plugin.use_anilist:
                    try:
                        mal = shiki_data.get("malId") or shiki_data.get("myanimelist_id") or shiki_data.get("id_mal")
                        if mal:
                            anilist_data = api.fetch_by_mal_id(int(mal))
                        if not anilist_data:
                            anilist_en = shiki_data.get("name") or (shiki_data.get("english") or [None])[0] or term
                            anilist_data = api.fetch_anilist(str(anilist_en))
                    except Exception:
                        anilist_data = None
                return cache_result(cache, cache_key, anilist_data, successful_original, shiki_data)
    return None, "", None

def build_send_params(account, base, text, parse_mode=None, no_webpage=False):
    p = {"peer": base["peer"], "text": text, "parse_mode": parse_mode}
    if no_webpage:
        p["no_webpage"] = True
    for k in ROUTING_KEYS:
        if base.get(k) is not None:
            p[k] = base[k]
    return p

def send_only_success(plugin, text, account, base, no_webpage=True):
    try:
        cleaned = clean_template_output(text, None)
        if not cleaned.strip():
            show_error(MSG_ERR_FAILED_SEND)
            return
        p = build_send_params(account, base, cleaned, "HTML" if plugin.enable_html_card else None, no_webpage=no_webpage)
        try:
            send_text(account=account, **p)
        except TypeError:
            p.pop("no_webpage", None)
            send_text(account=account, **p)
        show_success(MSG_SENT)
    except Exception:
        show_error(MSG_ERR_FAILED_SEND)

def send_description_separate(description_raw, account, base):
    if not description_raw.strip():
        return
    try:
        p = build_send_params(account, base, DESC_BLOCKQUOTE_TEMPLATE.format(description_raw), "HTML", no_webpage=True)
        try:
            send_text(account=account, **p)
        except TypeError:
            p.pop("no_webpage", None)
            send_text(account=account, **p)
    except Exception:
        show_error(MSG_ERR_FAILED_SEND)

def _refresh_cover_via_bot(account, cover_url):
    if not cover_url:
        return
    url = str(cover_url).strip()
    if not url.startswith("http"):
        return

    now = time.time()
    if url in _REFRESHED_COVERS_CACHE and (now - _REFRESHED_COVERS_CACHE[url]) < 86400:
        return
    _REFRESHED_COVERS_CACHE[url] = now

    def _send(peer):
        if peer is None:
            return
        try:
            send_text(int(peer), url, account=account)
        except Exception:
            try:
                send_text(account=account, peer=int(peer), text=url)
            except Exception:
                show_error(MSG_ERR_COVER)
    try:
        from org.telegram.tgnet import TLRPC
        from client_utils import send_request
        def _on_res(resp, err):
            try:
                if err or not resp:
                    show_error(MSG_ERR_COVER)
                    return
                uid = None
                users = getattr(resp, "users", None)
                if users is not None:
                    u = users.get(0) if hasattr(users, "get") else (users[0] if len(users) > 0 else None)
                    if u is not None:
                        uid = getattr(u, "id", None)
                if uid:
                    _send(int(uid))
            except Exception:
                show_error(MSG_ERR_COVER)
        req = TLRPC.TL_contacts_resolveUsername()
        req.username = WEBPAGE_BOT_USERNAME
        try:
            send_request(req, _on_res, account=account)
        except TypeError:
            try:
                send_request(req, _on_res)
            except Exception:
                show_error(MSG_ERR_COVER)
    except Exception:
        show_error(MSG_ERR_COVER)

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

def _dl_cover_file(url, aid):
    if not url:
        return None
        
    cache_key = f"{aid}_{url}"
    if cache_key in _DL_COVER_CACHE:
        cached_path = _DL_COVER_CACHE[cache_key]
        if os.path.isfile(cached_path) and os.path.getsize(cached_path) > 500:
            return cached_path

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
        path = os.path.join(base, COVER_FILE_PREFIX + safe + ".jpg")
        if os.path.isfile(path) and os.path.getsize(path) > 500:
            _DL_COVER_CACHE[cache_key] = path
            return path
            
        headers = {"User-Agent": api.get_current_user_agent(), "Accept": "image/*,*/*"}
        resp = requests.get(url, timeout=12, headers=headers)
        if resp.status_code == 200 and resp.content and len(resp.content) >= 500:
            with open(path, "wb") as f:
                f.write(resp.content)
            if os.path.isfile(path) and os.path.getsize(path) > 500:
                _DL_COVER_CACHE[cache_key] = path
                return path
    except Exception:
        show_error(MSG_ERR_MEDIA_LOAD)
    return None

def _send_media_with_caption(peer, path, caption, invert=False, account=None, base=None):
    cap = str(caption or "")
    if calc_plain_len(cap) > 2048:
        cap = re.sub(r'<[^>]+>', '', cap)[:2044] + "…"
        
    try:
        from client_utils import send_photo
        kwargs = {"caption": cap, "parse_mode": "HTML"}
        if account is not None:
            kwargs["account"] = account
            
        if base and isinstance(base, dict):
            for k in ROUTING_KEYS:
                if base.get(k) is not None:
                    kwargs[k] = base[k]

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

        reply_to_msg = base.get("replyToMsg") if base else None
        reply_top_msg = base.get("replyToTopMsg") if base else None

        for args in (
            (acc, media, int(peer), reply_to_msg, reply_top_msg, None, None, False, False, None, True, 0, 0, 0, False, None, None, 0, inv, 0, 0, None),
            (acc, media, int(peer), reply_to_msg, reply_top_msg, None, None, False, False, None, None, True, 0, 0, 0, False, None, None, 0, inv, 0, 0, None),
            (acc, media, int(peer), None, None, None, None, False, False, None, True, 0, 0, 0, False, None, None, 0, inv, 0, 0, None),
        ):
            try:
                SendMessagesHelper.prepareSendingMedia(*args)
                return True
            except Exception:
                continue
    except Exception:
        show_error(MSG_ERR_MEDIA_LOAD)
    return False

def _send_html_text(plugin, text, account, base, invert=False, no_webpage=False):
    cleaned = clean_template_output(text, None)
    if not cleaned.strip():
        return False
    parse = "HTML" if getattr(plugin, "enable_html_card", True) else None
    params = build_send_params(account, base, cleaned, parse, no_webpage=no_webpage)
    if invert:
        try:
            params["invert_media"] = True
            send_text(account=account, **params)
            return True
        except TypeError:
            params.pop("invert_media", None)
        except Exception:
            params.pop("invert_media", None)
            return False
    try:
        send_text(account=account, **params)
        return True
    except TypeError:
        params.pop("no_webpage", None)
        try:
            send_text(account=account, **params)
            return True
        except Exception:
            return False
    except Exception:
        return False

def send_card_and_desc(plugin, data, shiki, account, base, mapping, opts=None):
    if not getattr(plugin, "use_shikimori", True):
        shiki = None
    if not getattr(plugin, "use_anilist", True):
        data = None

    c_opts = resolve_card_options(plugin, data, shiki, opts, mapping=mapping)
    card = c_opts["text"]
    is_media = c_opts["is_media"]
    cover = c_opts["cover_url"]
    invert = c_opts["invert"]
    no_link = c_opts["no_link"]

    if not is_media and not no_link and getattr(plugin, "auto_update_cover", False) and cover:
        _refresh_cover_via_bot(account, cover)

    peer = _peer_from_base(base, account)
    if is_media and peer is not None and cover:
        src = (opts or {}).get("source")
        aid = None
        try:
            if src in ("shikimori", "shiki") and shiki and shiki.get("id") is not None:
                aid = shiki.get("id")
            elif data and data.get("id") is not None:
                aid = data.get("id")
            elif shiki and shiki.get("id") is not None:
                aid = shiki.get("id")
        except Exception:
            pass
        path = _dl_cover_file(cover, aid)
        if path:
            cleaned = clean_template_output(card, None)
            if _send_media_with_caption(peer, path, cleaned, invert=invert, account=account, base=base):
                show_success(MSG_SENT)
                desc = get_description(plugin, data, shiki)
                show_desc = gb(plugin, "coll_fields_main", True) and gb(plugin, "show_description", False)
                if show_desc and desc.strip() and not getattr(plugin, "description_in_card", True):
                    run_on_queue(lambda: send_description_separate(desc, account, base))
                return

    ok = _send_html_text(plugin, card, account, base, invert=invert, no_webpage=no_link)
    if ok:
        show_success(MSG_SENT)
    else:
        show_error(MSG_ERR_FAILED_SEND)
    desc = get_description(plugin, data, shiki)
    show_desc = gb(plugin, "coll_fields_main", True) and gb(plugin, "show_description", False)
    if ok and show_desc and desc.strip() and not getattr(plugin, "description_in_card", True):
        run_on_queue(lambda: send_description_separate(desc, account, base))

def process_search(plugin, account, base, original_candidates, cache, mapping):
    try:
        ck = f"data_{original_candidates[0] if original_candidates else 'empty'}"
        data, _, shiki = get_data_by_id_or_search(plugin, original_candidates, ck, cache)
        if (data and plugin.use_anilist) or (shiki and plugin.use_shikimori):
            send_card_and_desc(plugin, data, shiki, account, base, mapping)
        else:
            show_error(MSG_NOT_FOUND)
    except Exception:
        show_error(MSG_ERR_SEARCH)

def multi_search_by_genre(plugin, query, pref, mapping, cache):
    if not getattr(plugin, "use_anilist", True):
        return None, pref
    genres, tags = mapping.resolve_categories(query)
    if not genres and not tags:
        return [], pref
    try:
        raw = api.fetch_top_anilist(genres=genres, tags=tags)
    except Exception:
        return None, pref
    if raw is None:
        return None, pref
    matched = []
    req_g = [g.lower() for g in genres]
    req_t = [t.lower() for t in tags]
    for item in raw:
        item_genres = [str(g).lower() for g in (item.get("genres") or []) if g]
        item_tags = [str(t.get("name") if isinstance(t, dict) else t).lower() for t in (item.get("tags") or []) if t]
        if all(rg in item_genres for rg in req_g) and all(rt in item_tags for rt in req_t):
            matched.append(item)
    if matched:
        return parse_anilist_media_list(matched, mapping), False
    return [], pref

def _text_multi_search(plugin, q, pref, cache, mapping):
    ck = f"multi_{pref}_{q.lower()}"
    now = time.time()
    if ck in cache and isinstance(cache[ck], tuple) and len(cache[ck]) >= 3 and now - cache[ck][-1] < 300:
        return cache[ck][0], cache[ck][1]
    results = None
    actual_shiki = False
    if pref and plugin.use_shikimori:
        try:
            raw = api.multi_search_shikimori(q)
        except Exception:
            raw = None
        actual_shiki = True
        results = parse_shikimori_media_list(raw, mapping) if raw is not None else None
        if not results and plugin.use_anilist:
            try:
                raw = api.multi_search_anilist(q)
            except Exception:
                raw = None
            results = parse_anilist_media_list(raw, mapping) if raw is not None else None
            actual_shiki = False
    else:
        try:
            raw = api.multi_search_anilist(q) if plugin.use_anilist else None
        except Exception:
            raw = None
        results = parse_anilist_media_list(raw, mapping) if raw is not None else None
        actual_shiki = False
        if (not results) and plugin.use_shikimori:
            try:
                raw = api.multi_search_shikimori(q)
            except Exception:
                raw = None
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
            id_row = row_from_id_data(data, shiki, mapping, prefer_shiki=id_pref, prefer_anilist_cover=cover_pref)
            actual_shiki = id_pref

    if is_genre:
        if not getattr(plugin, "use_anilist", True):
            show_error(MSG_TOP_SOURCE_UNAVAILABLE)
            return
        results, actual_shiki = multi_search_by_genre(plugin, q, pref, mapping, cache)
        if results is None:
            show_error(MSG_TOP_SOURCE_UNAVAILABLE)
            return
        if not results:
            show_error(MSG_TOP_NOT_FOUND)
            return
    else:
        results, text_shiki = _text_multi_search(plugin, q, pref, cache, mapping)
        if results is None and id_row is None:
            show_error(MSG_ERR_API)
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
        actual_shiki = id_row.get("source") in ("shikimori", "shiki")

    if results is None:
        show_error(MSG_ERR_API)
        return
    if not results:
        show_error(MSG_NOT_FOUND if not is_genre else MSG_TOP_NOT_FOUND)
        return
    if plugin.search_ui_mode == 1:
        run_on_queue(lambda: on_select_cb(results[0], account, base))
        return
    run_on_ui_thread(lambda: show_popup_cb(results, q, actual_shiki, is_genre, account, base))

def on_popup_select(plugin, res, account, base, cache, mapping, opts=None):
    try:
        anilist_data = shiki_data = None
        rid = res.get("id")
        source = res.get("source")
        ck = f"data_{rid}" if rid is not None else None
        if ck and ck in cache:
            c = cache[ck]
            anilist_data = c[0] if isinstance(c, tuple) else c
            shiki_data = c[2] if isinstance(c, tuple) and len(c) > 2 else None

        opts = opts or {}
        if source:
            opts["source"] = source

        is_shiki_src = source in ("shikimori", "shiki")
        use_al = getattr(plugin, "use_anilist", True)
        use_sh = getattr(plugin, "use_shikimori", True)

        if is_shiki_src or (not use_al and use_sh):
            if use_sh and not shiki_data and rid:
                try:
                    shiki_data = api.search_shikimori_by_id(str(rid), cache)
                except Exception:
                    shiki_data = None
            if shiki_data and use_al and not anilist_data:
                mal = shiki_data.get("malId") or shiki_data.get("myanimelist_id") or shiki_data.get("id_mal")
                if mal:
                    try:
                        anilist_data = api.fetch_by_mal_id(int(mal))
                    except Exception:
                        anilist_data = None
                if not anilist_data:
                    en = shiki_data.get("name")
                    if not en and isinstance(shiki_data.get("english"), list) and shiki_data.get("english"):
                        en = shiki_data["english"][0]
                    if en:
                        try:
                            anilist_data = api.fetch_anilist(str(en))
                        except Exception:
                            anilist_data = None
        else:
            if use_al and rid and not anilist_data:
                try:
                    anilist_data = api.fetch_by_id(int(rid))
                except Exception:
                    anilist_data = None
            if anilist_data and use_sh and not shiki_data:
                mal_id = anilist_data.get("idMal")
                if mal_id:
                    try:
                        shiki_data = api.search_shikimori_by_id(str(mal_id), cache)
                    except Exception:
                        shiki_data = None
                if not shiki_data:
                    t = anilist_data.get("title") or {}
                    en = t.get("english") or t.get("romaji") or t.get("userPreferred")
                    if en:
                        try:
                            shiki_data = api.search_shikimori(en, cache)
                        except Exception:
                            shiki_data = None

        if shiki_data and use_sh and int(getattr(plugin, "cover_source", 0) or 0) == 1:
            try:
                shiki_data = api.enrich_shiki_poster(shiki_data, cache)
            except Exception:
                pass

        final_al = anilist_data if use_al else None
        final_sh = shiki_data if use_sh else None

        if final_al or final_sh:
            send_card_and_desc(plugin, final_al, final_sh, account, base, mapping, opts)
        else:
            show_error(MSG_NOT_FOUND)
    except Exception:
        show_error(MSG_ERR_LOAD)

def _parse_score_float(score_str):
    if not score_str or score_str in (SCORE_UNKNOWN, "?", "?/10", "None", ""):
        return None
    try:
        clean = str(score_str).replace("/10", "").strip()
        return float(clean)
    except Exception:
        return None

def process_ongoing_search(plugin, account, base, cache, mapping, show_popup_cb, on_select_cb):
    try:
        results = []
        actual_shiki = False
        ong_src = int(getattr(plugin, "ongoing_api", 0) or 0)
        pref = (ong_src == 1 and plugin.use_shikimori) or (not plugin.use_anilist and plugin.use_shikimori)

        if pref and plugin.use_shikimori:
            raw = None
            try:
                raw = api.fetch_ongoing_shikimori()
            except Exception:
                raw = None
            if raw:
                actual_shiki = True
                results = parse_ongoing_shikimori_results(raw, mapping)
            if not results and plugin.use_anilist:
                media = None
                try:
                    media = api.fetch_ongoing_anilist()
                except Exception:
                    media = None
                if media:
                    results = parse_ongoing_anilist_results(media, mapping)
        elif plugin.use_anilist:
            media = None
            try:
                media = api.fetch_ongoing_anilist()
            except Exception:
                media = None
            if media:
                results = parse_ongoing_anilist_results(media, mapping)
            if not results and plugin.use_shikimori:
                raw = None
                try:
                    raw = api.fetch_ongoing_shikimori()
                except Exception:
                    raw = None
                if raw:
                    actual_shiki = True
                    results = parse_ongoing_shikimori_results(raw, mapping)
        elif plugin.use_shikimori:
            raw = None
            try:
                raw = api.fetch_ongoing_shikimori()
            except Exception:
                raw = None
            if raw:
                actual_shiki = True
                results = parse_ongoing_shikimori_results(raw, mapping)

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

        min_score = gf(plugin, "ongoing_min_score", float(DEFAULT_ONGOING_MIN_SCORE), 0.0, 10.0)
        exclude_unknown = gb(plugin, "ongoing_exclude_unknown_score", True)

        def _score_ok(r):
            val = _parse_score_float(r.get("score"))
            if val is None:
                return not exclude_unknown
            return val >= min_score

        results = [r for r in results if _score_ok(r)]

        if getattr(plugin, "exclude_hentai", True):
            def _is_hentai(r):
                try:
                    return any(kw in str(g).lower() for g in (r.get("genres") or []) for kw in HENTAI_KEYWORDS)
                except Exception:
                    return False
            results = [r for r in results if not _is_hentai(r)]

        if not results:
            show_error(MSG_NOT_FOUND)
            return

        results.sort(key=lambda x: (x.get("day") if x.get("day") is not None else 6, x.get("title") or ""))
        
        n = datetime.utcnow()
        lab, year_offset = SEASONS_RU.get(n.month, ("осень", 0))
        q = f"{lab} {n.year + year_offset}"
        run_on_ui_thread(lambda: show_popup_cb(results, q, actual_shiki, False, account, base, ongoing=True))
    except Exception:
        show_error(MSG_ERR_ONGOING)