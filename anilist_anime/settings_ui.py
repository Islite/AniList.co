from client_utils import run_on_queue, get_last_fragment
from ui.settings import Divider, Header, Input, Selector, Switch, Text, Custom
from android_utils import run_on_ui_thread
from ui.alert import AlertDialogBuilder

from constants import DEFAULT_MAPPING
from chat_preview_ui import make_preview_factory
from collapsible_ui import make_mode_picker_and_blocks
from template_editor import TemplateEditor
from collapsible_blocks import is_item_enabled
from formatter import get_preview_text

ANILIST_PREVIEW_URL = "https://img.anili.st/media/1"
SHIKIMORI_PREVIEW_URL = "https://shikimori.io/uploads/poster/animes/1/6ad45d9decad83014a484a54f4dba6a7.jpeg"

def make_switch(plugin, key, text, default, store=None, prefix=None):
    def oc(val, k=key, s=store, p=prefix):
        if s is not None:
            s[k] = bool(val)
            plugin.set_setting(f"{p}{k}", bool(val))
        else:
            plugin.set_setting(key, bool(val))
        plugin.update_settings()
    full_key = key if store is None else f"{prefix}{key}"
    return Switch(key=full_key, text=text, default=default, on_change=oc, link_alias=full_key)

def show_info_alert(title, text, positive_button="Закрыть"):
    fragment = get_last_fragment()
    if not fragment or not fragment.getParentActivity():
        return
    activity = fragment.getParentActivity()
    builder = AlertDialogBuilder(activity, AlertDialogBuilder.ALERT_TYPE_MESSAGE)
    builder.set_title(title)
    builder.set_message(text)
    builder.set_positive_button(positive_button, lambda d, w: run_on_ui_thread(builder.dismiss))
    run_on_ui_thread(lambda: (builder.show(), builder.set_cancelable(True), builder.set_canceled_on_touch_outside(True)))

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

    pref_source = int(getattr(plugin, "cover_source", 0) or 0)

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
            Text(icon="files_internal", text="Маппинги", link_alias="mappings", create_sub_fragment=lambda: [
                Input(
                    key="universal_mapping", text="Универсальный маппинг", default=DEFAULT_MAPPING,
                    subtext="JSON или URL. Пусто = без перевода и разделителей",
                    on_change=on_map, link_alias="universal_mapping",
                ),
            ]),
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
                Header("Настройки обложки"),
                Selector(key="cover_source", text="Источник превью", default=0, items=["AniList", "Shikimori"], on_change=oc, link_alias="cover_source"),
                Selector(key="card_send_mode", text="Выбор обложки", default=0, items=["Превью", "Медиа"], on_change=oc, link_alias="card_send_mode"),
                Selector(key="preview_pos", text="Положение превью", default=0, items=["Снизу", "Сверху"], on_change=oc, link_alias="preview_pos"),
                Selector(key="media_pos", text="Положение медиа", default=0, items=["Сверху", "Снизу"], on_change=oc, link_alias="media_pos"),
                Switch(key="auto_update_cover", text="Авто-обновление обложки через @WebpageBot", default=False, on_change=oc, link_alias="auto_update_cover"),
                Switch(key="exclude_hentai", text="Исключать хентай онгоинги", default=True, on_change=oc, link_alias="exclude_hentai"),
                Header("Настройки доп. ссылок"),
                Input(key="anilist_link_text", text="Текст ссылки на AniList", default="AniList", on_change=oc, link_alias="anilist_link_text"),
                Input(key="shikimori_link_text", text="Текст ссылки на Shikimori", default="Shikimori", on_change=oc, link_alias="shikimori_link_text"),
                Header("Доп. переключатели"),
                Switch(key="spoiler_format", text="Спойлерные теги", default=True, on_change=oc, link_alias="spoiler_format"),
                Switch(key="ona_clarify", text="Уточнять ONA", default=False, on_change=oc, link_alias="ona_clarify"),
                Switch(key="show_separators", text="Разделители", default=True, on_change=oc, link_alias="show_separators"),
                Header("Текст при выкл. Аниме"),
                Input(key="hash_anime_replace", text="Текст при выкл. Аниме", default="|", on_change=oc, link_alias="hash_anime_replace"),
                Header("Нумерация списка"),
                Selector(key="list_number_mode", text="Стиль нумерации", default=0, items=["Цифры", "Свой", "Ничего"], on_change=oc, link_alias="list_number_mode"),
                Input(key="list_number_custom", text="Свой маркер", default="•", on_change=oc, link_alias="list_number_custom"),
                Header("Доп. названия"),
                Selector(key="extra_ru_count", text="Max русских названий", default=1, items=["0", "1", "2", "3", "4", "5"], on_change=oc, link_alias="extra_ru_count"),
                Selector(key="extra_en_count", text="Max английских названий", default=1, items=["0", "1", "2", "3", "4", "5"], on_change=oc, link_alias="extra_en_count"),
            ]),
            Divider(),
            Custom(
                factory=make_mode_picker_and_blocks(
                    plugin, mapping, on_change_global=oc
                ).instance.java,
                link_alias="display_mode_pick",
            ),
            Divider(),
            Switch(key="show_link_in_full", text="Ссылка AniList", default=True, on_change=oc, link_alias="show_link_in_full"),
            Switch(key="show_shikimori_link", text="Ссылка Shikimori", default=True, on_change=oc, link_alias="show_shikimori_link"),
            Divider(),
            Header("Описание"),
            Switch(key="show_description", text="Описание", default=False, on_change=oc, link_alias="show_description"),
            Selector(key="description_in_card", text="Способ отправки описания", default=0, items=["В карточке", "Отдельно"], on_change=oc, link_alias="description_in_card"),
            Selector(key="desc_source", text="Источник описания", default=0, items=["Shikimori", "AniList"], on_change=oc, link_alias="desc_source"),
        ]),
        Divider(),
        Text(icon="msg_filled_general", text="Форматирование текста", link_alias="text_formatting", create_sub_fragment=lambda: [
            Header("Основная карточка"),
            Switch(key="enable_html_card", text="Включить HTML", default=True, on_change=oc, link_alias="enable_html_card"),
            Divider(),
            Header("Отдельное описание"),
            Switch(key="enable_html_desc", text="Включить HTML", default=True, on_change=oc, link_alias="enable_html_desc"),
            Divider(),
            Header("Очистка пустых плейсхолдеров"),
            Selector(
                key="empty_ph_space_mode", text="Удаление пробела", default=0,
                items=["После плейсхолдера", "До плейсхолдера"],
                on_change=oc, link_alias="empty_ph_space_mode",
            ),
        ]),
        Divider(),
        Text(icon="msg_retry", text="Очистить кэш поиска", link_alias="clear_search_cache", on_click=lambda _: clear_search_cache()),
        Text(icon="msg_retry", text="Полная очистить кэша плагина", link_alias="full_clear_cache", on_click=lambda _: full_clear_cache()),
    ]