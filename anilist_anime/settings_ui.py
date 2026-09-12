from client_utils import run_on_queue
from ui.settings import Divider, Header, Input, Selector, Switch, Text, Custom
from android_utils import run_on_ui_thread
from client_utils import get_last_fragment
from ui.alert import AlertDialogBuilder

from constants import DEFAULT_MAPPING
from chat_preview_ui import make_preview_factory
from collapsible_ui import make_mode_picker, stub_mode_rows
from template_editor import TemplateEditor

def make_switch(plugin, key, text, default, store=None, prefix=None):
    def oc(val, k=key, s=store, p=prefix):
        if s is not None:
            s[k] = bool(val)
            try:
                plugin.set_setting(f"{p}{k}", bool(val), reload_settings=True)
            except TypeError:
                plugin.set_setting(f"{p}{k}", bool(val))
            plugin.update_settings()
        else:
            try:
                plugin.set_setting(key, bool(val), reload_settings=True)
            except TypeError:
                plugin.set_setting(key, bool(val))
            plugin.update_settings()
    full_key = key if store is None else f"{prefix}{key}"
    return Switch(key=full_key, text=text, default=default, on_change=oc, link_alias=full_key)

def build_sep_switches(plugin, mapping, scope, kind=None):
    if kind is None:
        return [
            make_switch(
                plugin, key, mapping.separator_labels.get(key, key),
                mapping.separator_enabled.get(key, True),
                mapping.separator_enabled, "sep_enabled_",
            )
            for key in mapping.separator_keys if mapping.sep_matches_scope(key, scope)
        ]
    prefix = {"hash": "hash_sep_", "under": "underscore_sep_", "comma": "comma_sep_"}[kind]
    store = {"hash": mapping.sep_hash, "under": mapping.sep_under, "comma": mapping.sep_comma}[kind]
    mark = {"hash": "# ", "under": "_ ", "comma": ", "}[kind]
    return [
        make_switch(
            plugin, key, f"{mark}{mapping.separator_labels.get(key, key)}",
            store.get(key, True), store, prefix,
        )
        for key in mapping.separator_keys if mapping.sep_matches_scope(key, scope)
    ]

def build_format_section(plugin, mapping, kind):
    plugin.update_settings()
    has = bool(mapping.separator_keys)
    cfg = {
        "hash": {
            "prefix": "# ",
            "master_g": ("hash_genres", "отображение жанров"),
            "main_g": ("hash_genres_main", "жанры"),
            "unlist_g": ("hash_genres_unlisted", "прочие жанры"),
            "master_t": ("hash_tags", "отображение тегов"),
            "main_t": ("hash_tags_main", "теги"),
            "unlist_t": ("hash_tags_unlisted", "прочие теги"),
            "top": [
                ("show_hash_anime", "Аниме"), ("hash_country", "Страна"), ("hash_format", "Формат"),
                ("hash_demographic", "Демография"), ("hash_studios", "Студии"),
                ("hash_source", "Источник"), ("hash_status", "Статус"),
            ],
        },
        "under": {
            "prefix": "_ ",
            "master_g": ("underscore_genres", "отображение жанров"),
            "main_g": ("underscore_genres_main", "жанры"),
            "unlist_g": ("underscore_genres_unlisted", "прочие жанры"),
            "master_t": ("underscore_tags", "отображение тегов"),
            "main_t": ("underscore_tags_main", "Теги"),
            "unlist_t": ("underscore_tags_unlisted", "прочие теги"),
            "top": [
                ("underscore_format", "_ формат"), ("underscore_studios", "_ студии"),
                ("underscore_source", "_ источник"), ("underscore_status", "_ статус"),
            ],
        },
        "comma": {
            "prefix": ", ",
            "master_g": ("comma_genres", "отображение жанров"),
            "main_g": ("comma_genres_main", "жанры"),
            "unlist_g": ("comma_genres_unlisted", "прочие жанры"),
            "master_t": ("comma_tags", "отображение тегов"),
            "main_t": ("comma_tags_main", "теги"),
            "unlist_t": ("comma_tags_unlisted", "прочие теги"),
            "top": [],
            "extra": [("comma_studios", ", студии")],
        },
    }[kind]
    items = []
    for key, text in cfg["top"]:
        items.append(make_switch(plugin, key, text, getattr(plugin, key)))
    if cfg["top"]:
        items.append(Divider())
    mg_key, mg_text = cfg["master_g"]
    items.append(make_switch(
        plugin, mg_key,
        f"{cfg['prefix']}{mg_text}" if kind != "hash" else mg_text,
        getattr(plugin, mg_key),
    ))
    if has:
        main_key, main_text = cfg["main_g"]
        items.append(make_switch(
            plugin, main_key,
            f"{cfg['prefix']}{main_text}" if kind != "hash" else main_text,
            getattr(plugin, main_key),
        ))
        items.extend(build_sep_switches(plugin, mapping, "genres", kind))
    ug_key, ug_text = cfg["unlist_g"]
    items.append(make_switch(
        plugin, ug_key,
        f"{cfg['prefix']}{ug_text}" if kind != "hash" else ug_text,
        getattr(plugin, ug_key),
    ))
    items.append(Divider())
    mt_key, mt_text = cfg["master_t"]
    items.append(make_switch(
        plugin, mt_key,
        f"{cfg['prefix']}{mt_text}" if kind != "hash" else mt_text,
        getattr(plugin, mt_key),
    ))
    if has:
        main_t_key, main_t_text = cfg["main_t"]
        items.append(make_switch(
            plugin, main_t_key,
            f"{cfg['prefix']}{main_t_text}" if kind != "hash" else main_t_text,
            getattr(plugin, main_t_key),
        ))
        items.extend(build_sep_switches(plugin, mapping, "tags", kind))
    ut_key, ut_text = cfg["unlist_t"]
    items.append(make_switch(
        plugin, ut_key,
        f"{cfg['prefix']}{ut_text}" if kind != "hash" else ut_text,
        getattr(plugin, ut_key),
    ))
    if cfg.get("extra"):
        items.append(Divider())
        for key, text in cfg["extra"]:
            items.append(make_switch(plugin, key, text, getattr(plugin, key)))
    return items

def build_display_fields(plugin, mapping):
    plugin.update_settings()
    has = bool(mapping.separator_keys)
    items = [
        Divider(),
        make_switch(plugin, "show_anime_label", "Аниме", plugin.show_anime_label),
        make_switch(plugin, "show_flag", "Флаг страны", plugin.show_flag),
        make_switch(plugin, "show_country", "Название страны", plugin.show_country),
        make_switch(plugin, "show_season", "Сезон", plugin.show_season),
        make_switch(plugin, "show_year", "Год", plugin.show_year),
        make_switch(plugin, "show_year_g", "г.", plugin.show_year_g),
        make_switch(plugin, "show_format", "Формат", plugin.show_format),
        make_switch(plugin, "show_demographic", "Целевая аудитория", plugin.show_demographic),
        make_switch(plugin, "show_episodes", "Серии", plugin.show_episodes),
        make_switch(plugin, "show_score", "Оценка", plugin.show_score),
        make_switch(plugin, "show_status", "Статус", plugin.show_status),
        make_switch(plugin, "show_duration", "Длительность", plugin.show_duration),
        make_switch(plugin, "show_source", "Источник", plugin.show_source),
        make_switch(plugin, "show_studios", "Студии", plugin.show_studios),
        Divider(),
        make_switch(plugin, "show_genres", "Отображение жанров", plugin.show_genres),
    ]
    if has:
        items.append(make_switch(plugin, "show_genres_main", "Жанры", plugin.show_genres_main))
        items.extend(build_sep_switches(plugin, mapping, "genres"))
    items += [
        make_switch(plugin, "show_genres_unlisted", "прочие жанры", plugin.show_genres_unlisted),
        Divider(),
        make_switch(plugin, "show_tags", "Отображение тегов", plugin.show_tags),
    ]
    if has:
        items.append(make_switch(plugin, "show_tags_main", "Теги", plugin.show_tags_main))
        items.extend(build_sep_switches(plugin, mapping, "tags"))
    items += [
        make_switch(plugin, "show_tags_unlisted", "прочие теги", plugin.show_tags_unlisted),
        Divider(),
        make_switch(plugin, "show_link_in_full", "Ссылка на AniList", plugin.show_link_in_full),
        make_switch(plugin, "show_shikimori_link", "Ссылка на Shikimori", plugin.show_shikimori_link),
        Divider(),
        make_switch(plugin, "show_description", "Описание", plugin.show_description),
        Selector(
            key="description_in_card", text="Способ отправки описания", default=0,
            items=["В карточке", "Отдельно"],
            on_change=lambda _: plugin.update_settings(), link_alias="description_in_card",
        ),
        Selector(
            key="desc_source", text="Источник описания", default=0,
            items=["Shikimori", "AniList"],
            on_change=lambda _: plugin.update_settings(), link_alias="desc_source",
        ),
    ]
    return items

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
    def fm(t, us, hs):
        if not t:
            return ""
        if us:
            t = t.replace("-", "_").replace(" ", "_")
        elif hs:
            t = t.replace(" ", "")
        return ("#" + t) if hs else t

    has = bool(mapping.separator_keys)
    gl, tl = [], []
    if plugin.show_genres:
        if plugin.show_genres_main or not has:
            g = fm("жанр", plugin.underscore_genres and plugin.underscore_genres_main, plugin.hash_genres and plugin.hash_genres_main)
            if g:
                gl.append(g)
        for k in mapping.separator_keys:
            if mapping.separator_scope.get(k) not in ("genres", "both") or not mapping.separator_enabled.get(k, True):
                continue
            lab = mapping.separator_labels.get(k, k)
            prev = mapping.separator_previews.get(k, "жанр")
            m = fm(prev, plugin.underscore_genres and mapping.sep_under.get(k, True), plugin.hash_genres and mapping.sep_hash.get(k, True))
            gl.append(f"{lab}: {m}" if plugin.show_separators else m)
        if plugin.show_genres_unlisted:
            g = fm("прочий жанр", plugin.underscore_genres and plugin.underscore_genres_unlisted, plugin.hash_genres and plugin.hash_genres_unlisted)
            if g:
                gl.append(f"прочий жанр: {g}" if plugin.show_separators else g)
    if plugin.show_tags:
        if plugin.show_tags_main or not has:
            t = fm("тег", plugin.underscore_tags and plugin.underscore_tags_main, plugin.hash_tags and plugin.hash_tags_main)
            if t:
                tl.append(t)
        for k in mapping.separator_keys:
            if mapping.separator_scope.get(k) not in ("tags", "both") or not mapping.separator_enabled.get(k, True):
                continue
            lab = mapping.separator_labels.get(k, k)
            prev = mapping.separator_previews.get(k, "тег")
            m = fm(prev, plugin.underscore_tags and mapping.sep_under.get(k, True), plugin.hash_tags and mapping.sep_hash.get(k, True))
            tl.append(f"{lab}: {m}" if plugin.show_separators else m)
        if plugin.show_tags_unlisted:
            t = fm("прочий тег", plugin.underscore_tags and plugin.underscore_tags_unlisted, plugin.hash_tags and plugin.hash_tags_unlisted)
            if t:
                tl.append(f"прочий тег: {t}" if plugin.show_separators else t)
    gs = "\n".join(gl) if plugin.show_separators else " ".join(gl)
    ts = "\n".join(tl) if plugin.show_separators else " ".join(tl)
    try:
        main_on = plugin.get_setting("coll_fields_main", True)
        if main_on is False or main_on == "false" or main_on == 0:
            main_on = False
        else:
            main_on = True
    except Exception:
        main_on = True
    from formatter import resolve_anime_label
    ap = resolve_anime_label(plugin, main_on)
    ft = fm("сериал", plugin.underscore_format, plugin.hash_format) if (main_on and plugin.show_format) else ""
    def _code(t):
        return ("`%s`" % t) if t else ""
    _ru_samples = ["Русское название", "Русское название 2", "Русское название 3", "Русское название 4", "Русское название 5"]
    _en_samples = ["English Title", "English Title 2", "English Title 3", "English Title 4", "English Title 5"]
    try:
        _rc = max(0, int(plugin.extra_ru_count or 0))
    except Exception:
        _rc = 1
    try:
        _ec = max(0, int(plugin.extra_en_count or 0))
    except Exception:
        _ec = 1
    _ru_vals = [""] * 5
    _en_vals = [""] * 5
    if _rc <= 0:
        for i in range(min(_ec, 5)):
            _ru_vals[i] = _code(_en_samples[i])
    else:
        for i in range(min(_rc, 5)):
            _ru_vals[i] = _code(_ru_samples[i])
        for i in range(min(_ec, 5)):
            _en_vals[i] = _code(_en_samples[i])
    mv = {
        "preview": "", "a": ap,
        "ru1": _ru_vals[0], "ru2": _ru_vals[1], "ru3": _ru_vals[2], "ru4": _ru_vals[3], "ru5": _ru_vals[4],
        "en1": _en_vals[0], "en2": _en_vals[1], "en3": _en_vals[2], "en4": _en_vals[3], "en5": _en_vals[4],
        "flag": "🇯🇵" if (main_on and plugin.show_flag) else "",
        "country": fm("Япония", False, plugin.hash_country) if (main_on and plugin.show_country) else "",
        "season": "лето" if (main_on and plugin.show_season) else "",
        "year": ("2018г." if plugin.show_year_g else "2018") if (main_on and plugin.show_year) else "",
        "format": ft,
        "audience": fm("сёнэн", False, plugin.hash_demographic) if (main_on and plugin.show_demographic) else "",
        "genres": gs if plugin.show_genres else "", "tags": ts if plugin.show_tags else "",
        "episodes": "8/18 эп." if (main_on and plugin.show_episodes) else "",
        "score": "8.8/10" if (main_on and plugin.show_score) else "",
        "status": fm("выходит", plugin.underscore_status, plugin.hash_status) if (main_on and plugin.show_status) else "",
        "duration": "24 мин." if (main_on and plugin.show_duration) else "",
        "source": fm("оригинал", plugin.underscore_source, plugin.hash_source) if (main_on and plugin.show_source) else "",
        "studios": fm("MAPPA", plugin.underscore_studios, plugin.hash_studios) if (main_on and plugin.show_studios) else "",
        "link1": ("[%s](https://anilist.co)" % (plugin.anilist_link_text or "AniList")) if plugin.show_link_in_full else "",
        "link2": ("[%s](https://shikimori.one)" % (plugin.shikimori_link_text or "Shikimori")) if plugin.show_shikimori_link else "",
        "description": "<b><i>описание</i></b>" if plugin.show_description and plugin.description_in_card else "",
    }
    try:
        from formatter import clean_template_output
        result = clean_template_output(plugin.card_template.format(**mv), mv, plugin.empty_ph_space_mode)
    except Exception as e:
        return "Ошибка в шаблоне: %s" % e
    if "#аниме" in result and ap != "#аниме":
        result = result.replace("#аниме", ap)
    return result

def _safe_stub(plugin, mapping):
    try:
        idx = plugin.get_setting("display_mode_pick", 0)
        try:
            idx = int(idx or 0)
        except Exception:
            idx = 0
        return stub_mode_rows(plugin, mapping, idx) or []
    except Exception:
        return []

def create_settings(plugin, mapping, clear_search_cache, full_clear_cache):
    run_on_queue(plugin.update_settings)

    def oc(_):
        def _do():
            plugin.update_settings()
            try:
                plugin.set_setting("__preview_tick", "1", reload_settings=True)
            except Exception:
                pass
        run_on_queue(_do)

    def on_map(_=None):
        run_on_queue(lambda: (mapping.load(force=True), _try_reload(plugin)))

    def _try_reload(p):
        try:
            p.set_setting("__internal_dummy__", True, reload_settings=True)
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
                lambda: (
                    "https://shikimori.io/uploads/poster/animes/1/6ad45d9decad83014a484a54f4dba6a7.jpeg"
                    if int(getattr(plugin, "cover_source", 0) or 0) == 1
                    else "https://img.anili.st/media/1"
                ),
                lambda: {
                    "mode": int(getattr(plugin, "card_send_mode", 0) or 0),
                    "above": (
                        int(getattr(plugin, "media_pos", 0) or 0) == 0
                        if int(getattr(plugin, "card_send_mode", 0) or 0) == 1
                        else int(getattr(plugin, "preview_pos", 0) or 0) == 1
                    ),
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
            Custom(factory=make_mode_picker(plugin).instance.java, link_alias="display_mode_pick"),
            Divider(),
            *(_safe_stub(plugin, mapping)),

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
        Text(icon="msg_retry", text="Полная очистка кэша плагина", link_alias="full_clear_cache", on_click=lambda _: full_clear_cache()),
    ]
