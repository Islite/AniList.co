PICK_MODES = [
    ("= поля", "msg_list", "key_chats_archiveBackground", "tag_icon_3"),
    ("# хэштег", "caption_show", "key_chats_archiveBackground", "caption_show"),
    ("_ подчёркивание", "caption_limit", "key_chats_archiveBackground", "caption_limit"),
    (", запятая", "msg_delete", "key_dialogSwipeRemove", "swipe_delete"),
]

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
    try:
        v = plugin.get_setting(item_key, default_item)
    except Exception:
        return default_item
    return parse_bool(v, default_item)

def _sep_items(mapping, scope, kind=None):
    items = []
    if not mapping or not getattr(mapping, "separator_keys", None):
        return items
    for key in mapping.separator_keys:
        if not mapping.sep_matches_scope(key, scope):
            continue
        label = mapping.separator_labels.get(key, key)
        if kind is None:
            items.append((label, f"sep_enabled_{key}"))
        elif kind == "hash":
            items.append((label, f"hash_sep_{key}"))
        elif kind == "under":
            items.append((label, f"underscore_sep_{key}"))
        elif kind == "comma":
            items.append((label, f"comma_sep_{key}"))
    return items

def get_mode_blocks(mapping, idx):
    try:
        idx = int(idx) if idx is not None else 0
    except Exception:
        idx = 0
    has = bool(getattr(mapping, "separator_keys", None))

    if idx == 0:
        main = [
            ("Предпросмотр", "show_preview"),
            ("ID", "show_id"),
            ("Аниме", "show_anime_label"),
            ("Автор", "show_author"),
            ("Флаг страны", "show_flag"),
            ("Название страны", "show_country"),
            ("Сезон", "show_season"),
            ("Год", "show_year"),
            ("г.", "show_year_g"),
            ("Формат", "show_format"),
            ("Целевая аудитория", "show_demographic"),
            ("Серии", "show_episodes"),
            ("Оценка", "show_score"),
            ("Статус", "show_status"),
            ("Длительность", "show_duration"),
            ("Обложка", "show_cover"),
            ("Баннер", "show_banner"),
            ("Связанные", "show_relations"),
            ("Опенинг", "show_opening"),
            ("Эндинг", "show_ending"),
            ("Трейлер", "show_trailer"),
            ("Источник", "show_source"),
            ("Студии", "show_studios"),
        ]
        genres = _sep_items(mapping, "genres") if has else []
        tags = _sep_items(mapping, "tags") if has else []

        return [
            ("Основные", "coll_fields_main", main, True, True),
            ("Жанры", "show_genres", genres, True, True),
            ("Теги", "show_tags", tags, True, True),
        ]

    if idx == 1:
        main = [
            ("Аниме", "show_hash_anime"),
            ("Автор", "hash_author"),
            ("Страна", "hash_country"),
            ("Формат", "hash_format"),
            ("Аудитория", "hash_demographic"),
            ("Студии", "hash_studios"),
            ("Источник", "hash_source"),
            ("Статус", "hash_status"),
        ]
        genres = _sep_items(mapping, "genres", "hash") if has else []
        tags = _sep_items(mapping, "tags", "hash") if has else []
        return [
            ("Основные", "coll_hash_main", main, True, True),
            ("Жанры", "hash_genres", genres, True, True),
            ("Теги", "hash_tags", tags, True, True),
        ]

    if idx == 2:
        main = [
            ("Автор", "underscore_author"),
            ("Формат", "underscore_format"),
            ("Студии", "underscore_studios"),
            ("Источник", "underscore_source"),
            ("Статус", "underscore_status"),
        ]
        genres = _sep_items(mapping, "genres", "under") if has else []
        tags = _sep_items(mapping, "tags", "under") if has else []
        return [
            ("Основные", "coll_under_main", main, True, True),
            ("Жанры", "underscore_genres", genres, True, True),
            ("Теги", "underscore_tags", tags, True, True),
        ]

    if idx == 3:
        main = [
            ("Студии", "comma_studios"),
        ]
        genres = _sep_items(mapping, "genres", "comma") if has else []
        tags = _sep_items(mapping, "tags", "comma") if has else []
        return [
            ("Основные", "coll_comma_main", main, False, True),
            ("Жанры", "comma_genres", genres, False, True),
            ("Теги", "comma_tags", tags, False, True),
        ]

    return []
