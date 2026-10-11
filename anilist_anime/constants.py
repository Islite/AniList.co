ANILIST_GRAPHQL_URL = "https://graphql.anilist.co"
SHIKIMORI_GRAPHQL_URL = "https://shikimori.one/api/graphql"
DEFAULT_MAPPING = "https://raw.githubusercontent.com/Islite/mapping-genre-tag-list-ExteraGram/refs/heads/main/mapping_all_list.json"

ANILIST_URL_TEMPLATE = "https://anilist.co/anime/{}"
SHIKIMORI_URL_TEMPLATE = "https://shikimori.one/animes/{}"
YOUTUBE_URL_TEMPLATE = "https://youtu.be/{}"

YEAR_SUFFIX = "г."
HASH_REPLACE_DEFAULT = "|"
AUTHOR_ROLES = ("original", "story", "author", "creator")
VIDEO_OP_KINDS = ("op", "opening")
VIDEO_ED_KINDS = ("ed", "ending")
VIDEO_PV_KINDS = ("pv", "trailer")

LIMIT_LIST_CHUNK = 4096
LIMIT_CARD_TEXT = 4096
LIMIT_CARD_CAPTION = 1024

DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

QUERIES = {
    "search": "query($search:String){Page(perPage:1){media(search:$search,type:ANIME,sort:SEARCH_MATCH){id idMal title{romaji english native userPreferred}synonyms countryOfOrigin season seasonYear format genres tags{name rank isMediaSpoiler}episodes status description averageScore duration source studios{nodes{name}}coverImage{extraLarge large}bannerImage trailer{id site}relations{edges{relationType(version:2) node{id title{romaji english native userPreferred}format}}}staff(sort:[RELEVANCE,ROLE]){edges{role node{name{full native}}}}nextAiringEpisode{episode airingAt}}}}",
    "media": "query($id:Int){Media(id:$id,type:ANIME){id idMal title{romaji english native userPreferred}synonyms countryOfOrigin season seasonYear format genres tags{name rank isMediaSpoiler}episodes status description averageScore duration source studios{nodes{name}}coverImage{extraLarge large}bannerImage trailer{id site}relations{edges{relationType(version:2) node{id title{romaji english native userPreferred}format}}}staff(sort:[RELEVANCE,ROLE]){edges{role node{name{full native}}}}nextAiringEpisode{episode airingAt}}}",
    "mal": "query($idMal:Int){Media(idMal:$idMal,type:ANIME){id idMal title{romaji english native userPreferred}synonyms countryOfOrigin season seasonYear format genres tags{name rank isMediaSpoiler}episodes status description averageScore duration source studios{nodes{name}}coverImage{extraLarge large}bannerImage trailer{id site}relations{edges{relationType(version:2) node{id title{romaji english native userPreferred}format}}}staff(sort:[RELEVANCE,ROLE]){edges{role node{name{full native}}}}nextAiringEpisode{episode airingAt}}}",
    "multi_search": "query($q:String){Page(page:1,perPage:50){media(search:$q,type:ANIME){id idMal title{romaji english}genres coverImage{extraLarge large}bannerImage format averageScore countryOfOrigin season seasonYear episodes status nextAiringEpisode{episode airingAt}}}}",
    "multi_genre": "query($g:String){Page(page:1,perPage:50){media(genre:$g,type:ANIME,sort:POPULARITY_DESC){id idMal title{romaji english}genres coverImage{extraLarge large}bannerImage format averageScore countryOfOrigin season seasonYear episodes status nextAiringEpisode{episode airingAt}}}}",
    "multi_tag": "query($g:String){Page(page:1,perPage:50){media(tag:$g,type:ANIME,sort:POPULARITY_DESC){id idMal title{romaji english}genres coverImage{extraLarge large}bannerImage format averageScore countryOfOrigin season seasonYear episodes status nextAiringEpisode{episode airingAt}}}}",
    "ongoing": "query($season:MediaSeason,$year:Int,$page:Int){Page(page:$page,perPage:50){pageInfo{hasNextPage}media(type:ANIME,season:$season,seasonYear:$year,status:RELEASING,isAdult:false,sort:POPULARITY_DESC){id idMal title{romaji english}genres coverImage{extraLarge large}bannerImage format averageScore countryOfOrigin season seasonYear episodes status nextAiringEpisode{episode airingAt}}}}",
}

SHIKI_QF = "id malId name russian kind status score duration season episodes episodesAired url airedOn{year date}poster{originalUrl mainUrl}genres{russian name}studios{name}nextEpisodeAt description videos{id url name kind}related{anime{id name russian kind}relationKind}"
SHIKI_QSS = "query($q:String){animes(search:$q,limit:30,censored:false){" + SHIKI_QF + "}}"
SHIKI_QID = "query($ids:String){animes(ids:$ids,limit:1,censored:false){" + SHIKI_QF + "}}"
SHIKI_QSO = "query($s:SeasonString,$p:PositiveInt){animes(status:\"ongoing\",season:$s,page:$p,limit:50,order:popularity,censored:false){" + SHIKI_QF + "}}"
SHIKI_QSO2 = "query($p:PositiveInt){animes(status:\"ongoing\",page:$p,limit:50,order:popularity,censored:false){" + SHIKI_QF + "}}"
SHIKI_QCAL = "query{calendar{nextEpisode nextEpisodeAt anime{" + SHIKI_QF + "}}}"

SHIKI_STATUS_MAP = {
    'released': 'FINISHED',
    'ongoing': 'RELEASING',
    'anons': 'NOT_YET_RELEASED',
    'latest': 'RELEASING',
    'paused': 'HIATUS',
}

MOCK_PREVIEW_DATA = {
    "id": "1",
    "ru_titles": ["Русское Название 1", "Русское Название 2", "Русское Название 3", "Русское Название 4", "Русское Название 5"],
    "en_titles": ["English Title 1", "English Title 2", "English Title 3", "English Title 4", "English Title 5"],
    "country": "JP",
    "season": "FALL",
    "seasonYear": 2026,
    "format": "TV",
    "episodes": 12,
    "episodes_aired": 12,
    "status": "FINISHED",
    "score": "8.5/10",
    "duration": 24,
    "source": "MANGA",
    "genres": [],
    "tags": [],
    "studios": ["Sleepy Committee", "SC Production"],
    "author_name": "Islite test",
    "description": "Пример описания для отображения внутри карточки.",
    "al_cover": "L",
    "sh_cover": "L",
    "bannerImage": "L",
    "relations": '<blockquote expandable>• оригинал: <a href="L">манга</a></blockquote>',
    "opening": '<blockquote expandable>• <a href="L">OP 1</a>\n• <a href="L">OP 2</a></blockquote>',
    "ending": '<blockquote expandable>• <a href="L">ED 1</a>\n• <a href="L">ED 2</a></blockquote>',
    "trailer": '<blockquote expandable>• <a href="https://L">trailer 1</a>\n• <a href="L">trailer 2</a></blockquote>',
    "audience": "Shounen",
}

TITLE_RU_TEMPLATES = [
    "<code>{title}</code>",
    "| <code>{title}</code>",
    "| <code>{title}</code>",
    "| <code>{title}</code>",
    "| <code>{title}</code>"
]

TITLE_EN_TEMPLATES = [
    "| <code>{title}</code>",
    "| <code>{title}</code>",
    "| <code>{title}</code>",
    "| <code>{title}</code>",
    "| <code>{title}</code>"
]

TITLE_RU1_TEMPLATE, TITLE_RU2_TEMPLATE, TITLE_RU3_TEMPLATE, TITLE_RU4_TEMPLATE, TITLE_RU5_TEMPLATE = TITLE_RU_TEMPLATES
TITLE_EN1_TEMPLATE, TITLE_EN2_TEMPLATE, TITLE_EN3_TEMPLATE, TITLE_EN4_TEMPLATE, TITLE_EN5_TEMPLATE = TITLE_EN_TEMPLATES

DEFAULT_TEMPLATE = (
    "{preview}{a} {ru1}\n{ru2}\n{ru3}\n{ru4}\n{ru5}\n"
    "{en1}\n{en2}\n{en3}\n{en4}\n{en5}\n"
    "{flag} {country}, {season} {year}\nформат {format}\nцелевая аудитория {audience}\n"
    "{genres}\n{tags}\n{link1} {link2}\n{description}\n"
    "студии: {studios}\nоригинал: {source}\nпродолжительность серии: {duration}\n"
    "статус: {status}\nрейтинг: {score}\nэпизоды: {episodes}"
)

DEFAULT_PREVIEW_TEMPLATE = "{preview}{a} {title}\n{genres}\n{episodes}"
DEFAULT_LIST_TEMPLATE = "{num}. {title}\n     {flag} {country}, {season} {year}"
DEFAULT_POPUP_TEMPLATE = "{format}, {score}\n{flag} {country}\n{genres}\n{episodes}"

TEXT_LIST_HEADER_QUERY = "{src} поиск: <code>{q}</code>"
TEXT_LIST_HEADER_QUERY_EMPTY = "{src} поиск"
TEXT_LIST_HEADER_ONGOING = "{src} поиск: онгоинги <code>{q}</code>"
TEXT_LIST_HEADER_ONGOING_EMPTY = "{src} поиск: онгоинги"

TEXT_LIST_NUMERIC_ITEM = "{num}. <code>{title}</code>"
TEXT_LIST_CUSTOM_ITEM = "{custom} <code>{title}</code>"
TEXT_LIST_PLAIN_ITEM = "<code>{title}</code>"

POPUP_SECTION_ID_LABEL = "По ID"
POPUP_SECTION_NAME_LABEL = "Совпадения по названию"
POPUP_ROW_SUBTITLE_TEMPLATE = "{format}, {score}\n{flag} {country}\n{genres}\n{episodes}"

POPUP_BTN_CLOSE = "Закрыть"
POPUP_BTN_CLEAR = "очистить"
POPUP_BTN_SELECT_ALL = "Выбрать всё"
POPUP_BTN_SELECT_BETWEEN = "Выбрать между"
POPUP_BTN_LIST = "Список"
POPUP_BTN_SEND = "Отправить"

POPUP_MSG_NOTHING_SELECTED = "Ничего не выбрано"
POPUP_MSG_EMPTY = "Пусто"
POPUP_MSG_SENT_TEXT = "Отправлено текстом"
POPUP_ERR_NO_ACTIVITY = "Activity not found"

POPUP_CONFIRM_TITLE = "Подтверждение"
POPUP_CONFIRM_MSG = "Отправка нескольких карточек может занять много времени"

POPUP_LABEL_COVER_PREFIX = "Обложка: "
POPUP_COVER_DEFAULT = "По умолчанию"
POPUP_COVER_BELOW = "Снизу"
POPUP_COVER_ABOVE = "Сверху"

POPUP_MENU_MEDIA = "Медиа"
POPUP_MENU_PREVIEW = "Превью"
POPUP_MENU_NOLINK = "Без ссылки"

POPUP_TITLE_SEARCH_ONG_Q = "%s поиск: онгоинги %s"
POPUP_TITLE_SEARCH_ONG = "%s поиск: онгоинги"
POPUP_TITLE_SEARCH_Q = "%s поиск: %s"
POPUP_TITLE_SEARCH = "%s поиск"

MSG_SENT = "Отправлено"
MSG_ERR_FAILED_SEND = "Не удалось отправить"
MSG_ERR_SEARCH = "Ошибка при поиске"
MSG_ERR_API = "Ошибка API"
MSG_NOT_FOUND = "Ничего не найдено"
MSG_NOT_FOUND_GENRE = "Жанр/тег не найден"
MSG_ERR_ONGOING = "Ошибка онгоингов"
MSG_ERR_LOAD = "Ошибка при загрузке"
MSG_ERR_MEDIA_LOAD = "Не удалось загрузить медиа"
MSG_ERR_COVER = "Не удалось обновить обложку"

MSG_CACHE_CLEARED = "Кэш поиска очищен"
MSG_FULL_CACHE_CLEARED = "Полный кэш плагина очищен"
MSG_SEARCH_STARTED = "Поиск начат..."
MSG_ERR_EXEC = "Ошибка запуска команды"

COVER_FILE_PREFIX = "aa_cover_"
DESC_BLOCKQUOTE_TEMPLATE = "<blockquote expandable><b><i>{}</i></b></blockquote>"

LABELS = {
    "cover": "обложка",
    "banner": "баннер",
    "min": "мин.",
    "ep": "эп.",
    "ep_prefix": "эп. ",
    "movie": "фильм",
    "series": "сериал",
    "video": "Видео",
    "trailer_yt": "Трейлер на YouTube",
    "anime_default": "аниме",
    "hash_anime_default": "#аниме",
    "shikimori_host": "https://shikimori.one",
    "shikimori_io": "https://shikimori.io",
    "anilist_media_img": "https://img.anili.st/media/",
    "shiki_missing_img": "https://shikimori.one/assets/globals/missing_original.jpg",
}

SEASONS_RU = {
    12: ("зима", 1), 1: ("зима", 0), 2: ("зима", 0),
    3: ("весна", 0), 4: ("весна", 0), 5: ("весна", 0),
    6: ("лето", 0), 7: ("лето", 0), 8: ("лето", 0),
    9: ("осень", 0), 10: ("осень", 0), 11: ("осень", 0)
}

HENTAI_KEYWORDS = ("хентай", "hentai")
WEBPAGE_BOT_USERNAME = "WebpageBot"

ROUTING_KEYS = (
    "replyToMsg", "replyToTopMsg", "messageThreadId",
    "reply_to_msg_id", "top_msg_id", "replyToMsgId", "replyToTopId"
)

BOOL_FLAGS = (
    "use_shikimori", "use_anilist", "show_flag", "show_country",
    "show_season", "show_year", "show_year_g", "show_format", "show_demographic", "show_genres", "show_genres_main",
    "show_genres_unlisted", "show_tags", "show_tags_main", "show_tags_unlisted", "spoiler_format", "show_anime_label",
    "show_hash_anime", "show_description", "show_episodes", "enable_html_card", "enable_html_desc", "ona_clarify",
    "show_score", "show_status", "show_duration", "show_source", "show_studios", "show_link_in_full",
    "show_shikimori_link", "show_separators", "hash_country", "hash_format", "hash_demographic", "hash_studios",
    "hash_source", "hash_status", "hash_genres", "hash_genres_main", "hash_genres_unlisted", "hash_tags",
    "hash_tags_main", "hash_tags_unlisted", "underscore_format", "underscore_studios", "underscore_source",
    "underscore_status", "underscore_genres", "underscore_genres_main", "underscore_genres_unlisted",
    "underscore_tags", "underscore_tags_main", "underscore_tags_unlisted", "comma_genres", "comma_genres_main",
    "comma_genres_unlisted", "comma_tags", "comma_tags_main", "comma_tags_unlisted", "comma_studios",
    "auto_update_cover", "exclude_hentai", "show_author", "hash_author", "underscore_author",
    "show_relations", "show_id", "show_banner", "show_opening", "show_ending", "show_trailer",
    "show_preview", "show_cover",
)

BOOL_DEFAULTS_FALSE = frozenset({
    "show_description", "ona_clarify", "comma_genres", "comma_tags", "comma_studios", "auto_update_cover",
})
