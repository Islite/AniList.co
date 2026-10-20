import re

from android_utils import run_on_ui_thread
from base_plugin import BasePlugin, HookResult, HookStrategy
from client_utils import get_last_fragment, run_on_queue
from ui.bulletin import BulletinHelper

import api
from constants import (
    BOOL_DEFAULTS_FALSE, BOOL_FLAGS, DEFAULT_TEMPLATE, DEFAULT_LIST_TEMPLATE, 
    DEFAULT_POPUP_TEMPLATE, ROUTING_KEYS
)
from mapping import MappingState
from search import (
    on_popup_select, process_multi_search, process_ongoing_search, 
    process_search, send_card_and_desc, sanitize_reply_text
)
from settings_ui import create_settings
from popup_ui import show_popup
from template_editor import TemplateEditor
from utils import cleanup_old_cache, gb, gi, gs, is_already_processed, parse_cmd, show_info

class Anilist_Anime(BasePlugin):
    def __init__(self):
        super().__init__()
        self.card_template = ""
        self.commands = {}
        self.tag_commands = set()
        self.search_cache = {}
        self._processed_messages = {}
        self.mapping = MappingState(self)
        self.update_settings()

    def update_settings(self):
        self.commands = {
            "anime": {
                c.strip().lower()
                for c in gs(self, "anime_commands", ".а, .аниме, .a, .anime").split(",")
                if c.strip()
            }
        }
        self.tag_commands = {
            c.strip().lower()
            for c in gs(self, "tag_commands", ".т, .t").split(",")
            if c.strip()
        }
        self.ongoing_commands = {
            c.strip().lower().lstrip(".")
            for c in gs(self, "ongoing_commands", "о, o, онгоинг, ongoing").split(",")
            if c.strip()
        }
        self.template_commands = {
            c.strip().lower()
            for c in gs(self, "template_commands", ".пл, .pl").split(",")
            if c.strip()
        }
        for k in BOOL_FLAGS:
            setattr(self, k, gb(self, k, k not in BOOL_DEFAULTS_FALSE))
        self.search_api = gi(self, "search_api", gi(self, "primary_source", 0))
        self.id_api = gi(self, "id_api", gi(self, "direct_id_source", 0))
        self.ongoing_api = gi(self, "ongoing_api", 0)
        self.primary_source = self.search_api
        self.direct_id_source = self.id_api
        self.search_ui_mode = gi(self, "search_ui_mode", 0)
        self.cover_source = gi(self, "cover_source", 0)
        self.card_send_mode = gi(self, "card_send_mode", 0)
        self.preview_pos = gi(self, "preview_pos", 0)
        self.media_pos = gi(self, "media_pos", 0)
        self.tag_min_rank = gi(self, "tag_min_rank", 20, 0, 100)
        self.extra_ru_count = gi(self, "extra_ru_count", 1, 0, 5)
        self.extra_en_count = gi(self, "extra_en_count", 1, 0, 5)
        self.description_in_card = gi(self, "description_in_card", 0) == 0
        self.desc_source = gi(self, "desc_source", 0)
        self.anilist_link_text = gs(self, "anilist_link_text", "AniList")
        self.hash_anime_replace = gs(self, "hash_anime_replace", "|")
        self.shikimori_link_text = gs(self, "shikimori_link_text", "Shikimori")
        custom_ua = gs(self, "custom_user_agent", "")
        if not custom_ua:
            custom_ua = api.generate_unique_user_agent()
            try:
                self.set_setting("custom_user_agent", custom_ua)
            except Exception:
                pass
        api.update_session_user_agent(custom_ua)
        tpl = self.get_setting("card_template")
        self.card_template = tpl.strip().replace("{links}", "{link1} {link2}") if tpl else DEFAULT_TEMPLATE
        for key in list(self.mapping.separator_keys):
            self.mapping.separator_enabled[key] = gb(self, f"sep_enabled_{key}", True)
            self.mapping.sep_hash[key] = gb(self, f"hash_sep_{key}", True)
            self.mapping.sep_under[key] = gb(self, f"underscore_sep_{key}", True)
            self.mapping.sep_comma[key] = gb(self, f"comma_sep_{key}", True)
        run_on_queue(self.mapping.load)

    def on_plugin_load(self):
        self.add_on_send_message_hook(priority=100)
        run_on_queue(lambda: self.mapping.load(force=True))

    def _clear_search_cache(self):
        self.search_cache.clear()
        run_on_ui_thread(lambda: BulletinHelper.show_success("Кэш поиска очищен", get_last_fragment()))

    def _full_clear_cache(self):
        self.search_cache.clear()
        self.mapping._last_mapping_raw = None
        self.mapping._shiki_alias = self.mapping._anilist_alias = None
        run_on_queue(lambda: self.mapping.load(force=True))
        run_on_ui_thread(lambda: BulletinHelper.show_success("Полный кэш плагина очищен", get_last_fragment()))

    def create_settings(self):
        return create_settings(self, self.mapping, self._clear_search_cache, self._full_clear_cache)

    def _parse_query_genre(self, raw_query):
        q = raw_query.strip()
        parts = q.split(None, 1)
        if len(parts) >= 2 and parts[0].lower() in ("t", "т"):
            return parts[1].strip(), True
        return q, False

    def _on_popup_select(self, res, account, base, opts=None):
        on_popup_select(self, res, account, base, self.search_cache, self.mapping, opts)

    def open_template_editor(self):
        try:
            TemplateEditor(self).open_keyboard()
        except Exception as e:
            run_on_ui_thread(lambda: BulletinHelper.show_error(str(e), get_last_fragment()))

    def _show_popup(self, results, query, use_shiki, is_genre, account, base, ongoing=False):
        lm = gi(self, "list_number_mode", 0)
        lc = gs(self, "list_number_custom", "•")
        csm = getattr(self, "card_send_mode", 0) or 0
        pp = getattr(self, "preview_pos", 0) or 0
        mp = getattr(self, "media_pos", 0) or 0
        pt = gs(self, "popup_template", DEFAULT_POPUP_TEMPLATE) or DEFAULT_POPUP_TEMPLATE
        lt = gs(self, "list_template", DEFAULT_LIST_TEMPLATE) or DEFAULT_LIST_TEMPLATE
        show_popup(
            results, query, use_shiki, is_genre, account, base, self._on_popup_select,
            ongoing=ongoing, list_num_mode=lm, list_num_custom=lc, card_send_mode=csm,
            preview_pos=pp, media_pos=mp, popup_template=pt, list_template=lt
        )

    def on_send_message_hook(self, account, params):
        try:
            msg_text = getattr(params, "message", "") or ""
            if is_already_processed(self._processed_messages, msg_text):
                return HookResult()
            self.update_settings()
            cleanup_old_cache(self.search_cache)
            msg = (params.message or "").strip()
            if not msg or msg.startswith("http://") or msg.startswith("https://"):
                return HookResult()
            msg_lower = msg.lower()
            if msg_lower in self.template_commands or any(msg_lower == c or msg_lower.startswith(c + " ") for c in self.template_commands):
                run_on_ui_thread(self.open_template_editor)
                return HookResult(strategy=HookStrategy.CANCEL)
            base = {"peer": params.peer}
            for key in ROUTING_KEYS:
                if hasattr(params, key):
                    val = getattr(params, key)
                    if val is not None:
                        base[key] = val
            is_tag_cmd = False
            cmd = parse_cmd(msg_lower, msg, self.tag_commands)
            if cmd:
                is_tag_cmd = True
            else:
                cmd = parse_cmd(msg_lower, msg, self.commands.get("anime", set()))
            if not cmd:
                return HookResult()
            show_info("Поиск начат...")
            query = msg[len(cmd):].lstrip()
            reply_text = ""
            if hasattr(params, "replyToMsg") and params.replyToMsg:
                rm = params.replyToMsg
                if hasattr(rm, "messageOwner") and rm.messageOwner:
                    reply_text = getattr(rm.messageOwner, "message", "") or ""
            if not query.strip() and reply_text:
                first_reply_line = ""
                for line in reply_text.splitlines():
                    cleaned_line = line.strip()
                    if cleaned_line:
                        first_reply_line = cleaned_line
                        break
                query = sanitize_reply_text(self, first_reply_line)
            qcheck = query.strip().lower().lstrip(".")
            if qcheck in self.ongoing_commands:
                run_on_queue(lambda: process_ongoing_search(
                    self, account, base, self.search_cache, self.mapping,
                    self._show_popup, self._on_popup_select,
                ))
                return HookResult(strategy=HookStrategy.CANCEL)
            if is_tag_cmd:
                q = query.strip()
                if not q:
                    return HookResult()
                run_on_queue(lambda: process_multi_search(
                    self, q, True, account, base, self.search_cache, self.mapping,
                    self._show_popup, self._on_popup_select,
                ))
                return HookResult(strategy=HookStrategy.CANCEL)
            if self.search_ui_mode == 0:
                q, is_genre = self._parse_query_genre(query)
                if not q:
                    return HookResult()
                run_on_queue(lambda: process_multi_search(
                    self, q, is_genre, account, base, self.search_cache, self.mapping,
                    self._show_popup, self._on_popup_select,
                ))
                return HookResult(strategy=HookStrategy.CANCEL)
            clean_q = sanitize_reply_text(self, query)
            orig = [clean_q] if clean_q else []
            if not orig:
                return HookResult()
            ck = f"data_{orig[0]}"
            if ck in self.search_cache:
                c = self.search_cache[ck]
                ad = c[0] if isinstance(c, tuple) else c
                sd = c[2] if isinstance(c, tuple) and len(c) > 2 else None
                send_card_and_desc(self, ad, sd, account, base, self.mapping)
                return HookResult(strategy=HookStrategy.CANCEL)
            run_on_queue(lambda: process_search(self, account, base, orig, self.search_cache, self.mapping))
            return HookResult(strategy=HookStrategy.CANCEL)
        except Exception:
            run_on_ui_thread(lambda: BulletinHelper.show_error("Ошибка запуска команды", get_last_fragment()))
            return HookResult()