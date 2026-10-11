import re
import time

from android_utils import run_on_ui_thread
from client_utils import get_last_fragment
from ui.bulletin import BulletinHelper

CLEAN_BB_RE1 = re.compile(r'\[(?:character|anime|manga|ranobe|person|author|producer)[^\]]*\](.*?)\[/(?:character|anime|manga|ranobe|person|author|producer)\]', re.IGNORECASE | re.DOTALL)
CLEAN_BB_RE2 = re.compile(r'\s*\[[^\]]*[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF][^\]]*\]')
CLEAN_BB_RE3 = re.compile(r'\[/?(?:b|i|u|s|center|left|right|justify|url|img|spoiler|quote|code|color|size|font|hr)[^\]]*\]', re.IGNORECASE)
CLEAN_TAGS_RE = re.compile(r'<[^>]+>')
CLEAN_SPACES_RE = re.compile(r'\s{2,}')
FLAG_RE = re.compile(r'[\U0001F1E6-\U0001F1FF]{2}')
SEASON_RE = re.compile(r'\b(зима|весна|лето|осень)\b', re.IGNORECASE)
YEAR_RE = re.compile(r'\b(\d{4})(?:г\.)?\b')
CLEAN_COUNTRY_RE = re.compile(r',?\s*(?:зима|весна|лето|осень)?\s*\d{4}(?:г\.)?', re.IGNORECASE)
PH_REGEX = re.compile(r'\{([a-zA-Z0-9_]+)\}')
EMPTY_TAGS_RE = re.compile(r'<(code|spoiler|b|i|u|s)>\s*</\1>')
MULTIPLE_COMMAS_RE = re.compile(r',\s*,')
SPACE_COMMA_RE = re.compile(r'\s+,')
COMMA_SPACE_RE = re.compile(r',\s+')

def html_code(text):
    return f"<code>{text}</code>" if text else ""

def html_spoiler(text):
    return f"<spoiler>{text}</spoiler>" if text else ""

def html_blockquote(text):
    return f"<blockquote expandable>{text}</blockquote>" if text else ""

def html_link(url, text):
    return f'<a href="{url}">{text}</a>' if url and text else ""

def html_zero_link(url):
    return f'<a href="{url}">\u200b</a>' if url else ""

def gb(plugin, key, default=True):
    val = plugin.get_setting(key, default)
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

def gi(plugin, key, default=0, mn=0, mx=None):
    try:
        val = int(plugin.get_setting(key, str(default)))
    except Exception:
        val = default
    val = max(mn, val)
    return min(mx, val) if mx is not None else val

def gs(plugin, key, default=""):
    val = plugin.get_setting(key, default)
    return str(val).strip() or default if val is not None else default

def is_cyrillic(text):
    return bool(text) and any("\u0400" <= ch <= "\u04FF" for ch in text)

def is_already_processed(store, msg_text, window=5, ttl=30):
    if not msg_text:
        return False
    key = hash(msg_text.strip()[:200])
    now = time.time()
    if key in store and now - store[key] < window:
        return True
    store[key] = now
    for k in list(store):
        if now - store[k] > ttl:
            store.pop(k, None)
    return False

def cleanup_old_cache(cache, ttl=1800):
    now = time.time()
    for k in [
        k for k, v in list(cache.items())
        if isinstance(v, tuple) and len(v) > 3 and now - v[-1] > ttl
    ]:
        cache.pop(k, None)

def show_success(text):
    run_on_ui_thread(lambda: BulletinHelper.show_success(text, get_last_fragment()))

def show_error(message):
    run_on_ui_thread(lambda: BulletinHelper.show_error(message, get_last_fragment()))

def show_info(message):
    run_on_ui_thread(lambda: BulletinHelper.show_info(message, get_last_fragment()))

def parse_cmd(msg_lower, msg, commands):
    for c in sorted(commands, key=len, reverse=True):
        pat = rf"^{re.escape(c)}"
        if len(msg) > len(c):
            pat += r"\s"
        if re.match(pat, msg_lower):
            return c
    return None

def clean_shikimori_description(text: str) -> str:
    if not text:
        return ""
    text = CLEAN_BB_RE1.sub(r'\1', text)
    text = CLEAN_BB_RE2.sub('', text)
    text = CLEAN_BB_RE3.sub('', text)
    text = CLEAN_TAGS_RE.sub('', text)
    return CLEAN_SPACES_RE.sub(' ', text).strip()

def clean_template_output(template_str, vars_dict, empty_ph_space_mode=0):
    if not template_str:
        return ""
    lines = str(template_str).split("\n")
    cleaned = []
    for line in lines:
        if not line.strip():
            cleaned.append("")
            continue
        l_stripped = line.lstrip()
        indent = line[:len(line) - len(l_stripped)]
        placeholders = PH_REGEX.findall(l_stripped)
        if placeholders and vars_dict is not None:
            if not any(vars_dict.get(ph) is not None and str(vars_dict.get(ph)).strip() for ph in placeholders):
                continue
            proc = l_stripped
            for ph in placeholders:
                val = str(vars_dict.get(ph, "")).strip() if vars_dict.get(ph) is not None else ""
                proc = proc.replace("{" + ph + "}", val)
        else:
            proc = l_stripped
        proc = PH_REGEX.sub("", proc)
        proc = EMPTY_TAGS_RE.sub("", proc)
        proc = CLEAN_SPACES_RE.sub(" ", proc)
        proc = MULTIPLE_COMMAS_RE.sub(",", proc)
        proc = SPACE_COMMA_RE.sub(",", proc)
        proc = COMMA_SPACE_RE.sub(", ", proc).strip()
        if proc:
            cleaned.append(indent + proc)
    return "\n".join(cleaned)
