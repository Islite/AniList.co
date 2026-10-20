from client_utils import get_last_fragment, run_on_queue
from ui.bulletin import BulletinHelper
from ui.settings import Divider, Header, Input, Selector, Switch, Text, Custom

import api
from constants import (
    DEFAULT_MAPPING, ANILIST_PREVIEW_URL, SHIKIMORI_PREVIEW_URL,
    DEFAULT_ONGOING_MIN_SCORE, DEFAULT_LIST_NUM_CUSTOM, DEFAULT_SEARCH_REPLY_IGNORED
)
from chat_preview_ui import make_preview_factory
from collapsible_ui import make_mode_picker_and_blocks
from template_editor import TemplateEditor
from collapsible_blocks import is_item_enabled
from formatter import get_preview_text

def build_preview(plugin, mapping):
    return get_preview_text(plugin, mapping=mapping)

def _is_preview_enabled(plugin):
    return is_item_enabled(plugin, "coll_fields_main", "show_preview", True, True)

def _get_preview_cover_url(plugin):
    if not _is_preview_enabled(plugin):
        return None

    use_anilist = bool(plugin.get_setting("use_anilist", getattr(plugin, "use_anilist", True)))
    use_shikimori = bool(plugin.get_setting("use_shikimori", getattr(plugin, "use_shikimori", True)))

    if not use_anilist and not use_shikimori:
        return None

    pref_source = int(plugin.get_setting("cover_source", 0) if hasattr(plugin, "get_setting") else getattr(plugin, "cover_source", 0) or 0)

    if pref_source == 1:
        return SHIKIMORI_PREVIEW_URL if use_shikimori else (ANILIST_PREVIEW_URL if use_anilist else None)
    return ANILIST_PREVIEW_URL if use_anilist else (SHIKIMORI_PREVIEW_URL if use_shikimori else None)

def create_settings(plugin, mapping, clear_search_cache, full_clear_cache):
    run_on_queue(plugin.update_settings)

    def oc(_=None):
        def _do():
            plugin.update_settings()
            try:
                plugin.set_setting("__preview_tick", "1")
            except Exception:
                pass
        run_on_queue(_do)

    def on_map(_=None):
        run_on_queue(lambda: (mapping.load(force=True), _try_reload(plugin)))

    def _try_reload(p):
        try:
            p.set_setting("__internal_dummy__", True)
        except Exception:
            pass

    def show_limits():
        try:
            info = api.get_limits_info()
            BulletinHelper.show_info(info, get_last_fragment())
        except Exception as e:
            BulletinHelper.show_error(str(e), get_last_fragment())

    return [
        Input(
            key="anime_commands", icon="msg_search", text="Команды аниме",
            default=".а, .аниме, .a, .anime", subtext="Поиск по названию и ID",
            on_change=oc, link_alias="anime_commands",
        ),
        Input(
            key="tag_commands", icon="msg_pinnedlist", text="Фильтр по жанрам",
            default="т, t", subtext="Фильтрация аниме по жанру или тегу\n\nПрименение:\n.а т жанры/теги",
            on_change=oc, link_alias="tag_commands",
        ),
        Input(
            key="ongoing_commands", icon="msg_calendar", text="Команды онгоингов",
            default="о, o, онгоинг, ongoing", subtext="После команды аниме: .а о\nили отдельной командой из списка",
            on_change=oc, link_alias="ongoing_commands",
        ),
        Input(
            key="template_commands", icon="msg_edit", text="Команды редактора шаблона",
            default=".пл, .pl", subtext="Открыть окно редактирования плейсхолдеров",
            on_change=oc, link_alias="template_commands",
        ),
        Divider(),
        Text(icon="navbar_search_tag", text="Настройки поиска", link_alias="search_settings", create_sub_fragment=lambda: [
            Switch(key="use_anilist", text="Поиск через AniList", default=True, on_change=oc, link_alias="use_anilist"),
            Switch(key="use_shikimori", text="Поиск через Shikimori", default=True, on_change=oc, link_alias="use_shikimori"),
            Divider(),
            Selector(key="search_api", text="API обычного поиска", default=0, items=["AniList", "Shikimori"], on_change=oc, link_alias="search_api"),
            Selector(key="id_api", text="API поиска по ID", default=0, items=["AniList", "Shikimori"], on_change=oc, link_alias="id_api"),
            Selector(key="ongoing_api", text="API онгоингов", default=0, items=["AniList", "Shikimori"], on_change=oc, link_alias="ongoing_api"),
            Selector(key="search_ui_mode", text="Режим поиска", default=0, items=["Окно выбора", "Первое совпадение"], on_change=oc, link_alias="search_ui_mode"),
            Divider(),
            Input(
                key="search_reply_ignored_words", text="Игнорируемые слова при реплай поиске",
                default=DEFAULT_SEARCH_REPLY_IGNORED, subtext="Слова и символы через запятую",
                on_change=oc, link_alias="search_reply_ignored_words",
            ),
            Divider(),
            Text(icon="files_internal", text="Маппинги", link_alias="mappings", create_sub_fragment=lambda: [
                Input(
                    key="universal_mapping", text="Универсальный маппинг", default=DEFAULT_MAPPING,
                    subtext="JSON или URL. Пусто = без перевода и разделителей",
                    on_change=on_map, link_alias="universal_mapping",
                ),
            ]),
            Divider(),
            Text(
                icon="msg_info", text="Проверить лимиты API", link_alias="check_api_limits",
                on_click=lambda _: show_limits(),
            ),
        ]),
        Text(icon="menu_edit_appearance", text="Настройки отображения", link_alias="display_settings", create_sub_fragment=lambda: [
            Custom(factory=make_preview_factory(
                lambda: build_preview(plugin, mapping),
                lambda: _get_preview_cover_url(plugin),
                lambda: {
                    "mode": int(getattr(plugin, "card_send_mode", 0) or 0),
                    "above": (
                        int(getattr(plugin, "media_pos", 0) or 0) == 0
                        if int(getattr(plugin, "card_send_mode", 0) or 0) == 1
                        else int(getattr(plugin, "preview_pos", 0) or 0) == 1
                    ),
                    "show_preview": _is_preview_enabled(plugin) and (_get_preview_cover_url(plugin) is not None),
                },
            ).instance.java, link_alias="card_preview"),
            Divider(),
            Text(
                icon="menu_edit_appearance", text="Редактировать плейсхолдеры",
                link_alias="card_template",
                on_click=lambda _: TemplateEditor(plugin).open_keyboard(),
            ),
            Text(icon="msg_settings", text="Доп. настройки", link_alias="extra_settings", create_sub_fragment=lambda: [
                Header("Форматирование"),
                Switch(key="enable_html_card", text="Включить HTML", default=True, on_change=oc, link_alias="enable_html_card"),
                Divider(),
                Header("Онгоинги"),
                Input(
                    key="ongoing_min_score", text="Минимальный рейтинг онгоингов",
                    default=DEFAULT_ONGOING_MIN_SCORE, subtext="Число от 0 до 10 для фильтрации онгоингов",
                    on_change=oc, link_alias="ongoing_min_score",
                ),
                Switch(
                    key="ongoing_exclude_unknown_score", text="Исключать онгоинги без оценки",
                    default=True, on_change=oc, link_alias="ongoing_exclude_unknown_score",
                ),
                Switch(
                    key="exclude_hentai", text="Исключать хентай онгоинги",
                    default=True, on_change=oc, link_alias="exclude_hentai",
                ),
                Divider(),
                Header("Нумерация списка"),
                Selector(key="list_number_mode", text="Стиль нумерации", default=0, items=["Цифры", "Свой", "Ничего"], on_change=oc, link_alias="list_number_mode"),
                Input(key="list_number_custom", text="Свой маркер", default=DEFAULT_LIST_NUM_CUSTOM, on_change=oc, link_alias="list_number_custom"),
            ]),
            Divider(),
            Custom(
                factory=make_mode_picker_and_blocks(
                    plugin, mapping, on_change_global=oc
                ).instance.java,
                link_alias="display_mode_pick",
            ),
        ]),
        Divider(),
        Text(icon="msg_retry", text="Очистить кэш поиска", link_alias="clear_search_cache", on_click=lambda _: clear_search_cache()),
        Text(icon="msg_retry", text="Полная очистить кэша плагина", link_alias="full_clear_cache", on_click=lambda _: full_clear_cache()),
    ]