from constants import BOOL_DEFAULTS_FALSE

PICK_MODES = [
    ("= поля", "msg_list", "key_chats_archiveBackground", "tag_icon_3"),
    ("# хэштег", "caption_show", "key_chats_archiveBackground", "caption_show"),
    ("_ подчёркивание", "caption_limit", "key_chats_archiveBackground", "caption_limit"),
    (", запятая", "msg_delete", "key_dialogSwipeRemove", "swipe_delete"),
]

EXTRA_SECTIONS = [
    {
        "title": "Доп. названия",
        "items": [
            ("selector", "Max русских названий", "extra_ru_count", ["0", "1", "2", "3", "4", "5"], 1),
            ("selector", "Max английских названий", "extra_en_count", ["0", "1", "2", "3", "4", "5"], 1),
        ]
    },
    {
        "title": "Текст при выкл. Аниме",
        "items": [
            ("input", "Текст при выкл. Аниме", "hash_anime_replace", "|"),
        ]
    },
    {
        "title": "Настройки обложки",
        "items": [
            ("selector", "Источник превью", "cover_source", ["AniList", "Shikimori"], 0),
            ("selector", "Выбор обложки", "card_send_mode", ["Превью", "Медиа"], 0),
            ("selector", "Положение превью", "preview_pos", ["Снизу", "Сверху"], 0),
            ("selector", "Положение медиа", "media_pos", ["Сверху", "Снизу"], 0),
            ("switch", "Авто-обновление обложки", "auto_update_cover", False),
        ]
    },
    {
        "title": "Настройки доп. ссылок",
        "items": [
            ("input", "Текст ссылки на AniList", "anilist_link_text", "AniList"),
            ("input", "Текст ссылки на Shikimori", "shikimori_link_text", "Shikimori"),
        ]
    },
    {
        "title": "Доп. переключатели",
        "items": [
            ("switch", "Спойлерные теги", "spoiler_format", True),
            ("switch", "Уточнять ONA", "ona_clarify", False),
            ("switch", "Разделители", "show_separators", True),
        ]
    },
    {
        "title": "Описание",
        "items": [
            ("selector", "Источник", "desc_source", ["Shikimori", "AniList"], 0),
        ]
    }
]

MODE_FIELDS_MAIN = [
    ("Предпросмотр", "show_preview"),
    ("Аниме", "show_anime_label"),
    ("Флаг страны", "show_flag"),
    ("Название страны", "show_country"),
    ("Сезон", "show_season"),
    ("Год", "show_year"),
    ("Формат", "show_format"),
    ("Целевая аудитория", "show_demographic"),
    ("Ссылка AniList", "show_link_in_full"),
    ("Ссылка Shikimori", "show_shikimori_link"),
    ("Описание", "show_description"),
]

MODE_FIELDS_EXTRA = [
    ("ID", "show_id"),
    ("Серии", "show_episodes"),
    ("Длительность", "show_duration"),
    ("Оценка", "show_score"),
    ("Статус", "show_status"),
    ("Оригинал", "show_source"),
    ("Студии", "show_studios"),
    ("Автор", "show_author"),
    ("Баннер", "show_banner"),
    ("Обложка", "show_cover"),
    ("Связанные", "show_relations"),
    ("Трейлер", "show_trailer"),
    ("Опенинг", "show_opening"),
    ("Эндинг", "show_ending"),
]

MODE_FIELDS = {
    0: MODE_FIELDS_MAIN,
    1: [
        ("Аниме", "show_hash_anime"),
        ("Страна", "hash_country"),
        ("Формат", "hash_format"),
        ("Аудитория", "hash_demographic"),
        ("Статус", "hash_status"),
        ("Оригинал", "hash_source"),
        ("Студии", "hash_studios"),
        ("Автор", "hash_author"),
    ],
    2: [
        ("Формат", "underscore_format"),
        ("Статус", "underscore_status"),
        ("Оригинал", "underscore_source"),
        ("Студии", "underscore_studios"),
        ("Автор", "underscore_author"),
    ],
    3: [
        ("Студии", "comma_studios"),
    ]
}

MODE_KEY_CONFIG = {
    0: ("coll_fields_main", "show_genres", "show_tags", "sep_enabled_", True),
    1: ("coll_hash_main", "hash_genres", "hash_tags", "hash_sep_", True),
    2: ("coll_under_main", "underscore_genres", "underscore_tags", "under_sep_", True),
    3: ("coll_comma_main", "comma_genres", "comma_tags", "comma_sep_", False),
}

def parse_bool(val, default=True):
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val != 0
    s = str(val).strip().lower()
    if s in ("0", "false", "no", "off", "null", "none", ""):
        return False
    if s in ("1", "true", "yes", "on"):
        return True
    return bool(val)

def is_master_enabled(plugin, master_key, default=True):
    try:
        v = plugin.get_setting(master_key, default)
    except Exception:
        return default
    return parse_bool(v, default)

def is_item_enabled(plugin, master_key, item_key, default_master=True, default_item=True):
    if not is_master_enabled(plugin, master_key, default_master):
        return False
    actual_default = False if item_key in BOOL_DEFAULTS_FALSE else default_item
    try:
        v = plugin.get_setting(item_key, actual_default)
    except Exception:
        return actual_default
    return parse_bool(v, actual_default)

def get_extra_sections(idx):
    return EXTRA_SECTIONS if idx == 0 else []

def _build_sep_items(mapping, scope, prefix):
    if not mapping or not getattr(mapping, "separator_keys", None):
        return []
    items = []
    for key in mapping.separator_keys:
        if mapping.sep_matches_scope(key, scope):
            label = mapping.separator_labels.get(key, key)
            items.append((label, f"{prefix}{key}"))
    return items

def get_mode_blocks(mapping, idx):
    idx = int(idx) if idx in MODE_KEY_CONFIG else 0
    main_key, gen_key, tag_key, prefix, default_master = MODE_KEY_CONFIG[idx]
    genres = _build_sep_items(mapping, "genres", prefix)
    tags = _build_sep_items(mapping, "tags", prefix)
    if idx == 0:
        return [
            ("Основные", main_key, MODE_FIELDS_MAIN, True, True),
            ("Дополнительные", "coll_fields_extra", MODE_FIELDS_EXTRA, False, True),
            ("Жанры", gen_key, genres, True, True),
            ("Теги", tag_key, tags, True, True),
        ]
    return [
        ("Все", main_key, MODE_FIELDS.get(idx, []), default_master, True),
        ("Жанры", gen_key, genres, default_master, True),
        ("Теги", tag_key, tags, default_master, True),
    ]