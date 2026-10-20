import html
import re
import time

from android_utils import run_on_ui_thread
from client_utils import get_last_fragment
from ui.bulletin import BulletinHelper

CLEAN_BB_RE1 = re.compile(r'\[(?:character|anime|manga|ranobe|person|author|producer)[^\]]*\](.*?)\[/(?:character|anime|manga|ranobe|person|author|producer)\]', re.IGNORECASE | re.DOTALL)
CLEAN_BB_RE2 = re.compile(r'\s*\[[^\]]*[\u3040-\u30FF\u4E00-\u9FAF][^\]]*\]')
CLEAN_BB_RE3 = re.compile(r'\[/?(?:b|i|u|s|center|left|right|justify|url|img|spoiler|quote|code|color|size|font|hr)[^\]]*\]', re.IGNORECASE)
CLEAN_WIKI_LINK_RE = re.compile(r'\[\[(?:[^|\]]*\|)?(.*?)\]\]')
CLEAN_JP_PAREN_RE = re.compile(r'\([^\)]*[\u3040-\u30FF\u4E00-\u9FAF][^\)]*\)')
CLEAN_DOUBLE_PAREN_RE = re.compile(r'\(\([^\)]*\)\)')
CLEAN_DOUBLE_BRACKET_RE = re.compile(r'\[\[[^\]]*\]\]')
CLEAN_TAGS_RE = re.compile(r'<[^>]+>')
CLEAN_SPACES_RE = re.compile(r'\s{2,}')
FLAG_RE = re.compile(r'[\U0001F1E6-\U0001F1FF]{2}')
SEASON_RE = re.compile(r'\b(зима|весна|лето|осень)\b', re.IGNORECASE)
YEAR_RE = re.compile(r'\b(\d{4})\b')
CLEAN_COUNTRY_RE = re.compile(r',?\s*(?:зима|весна|лето|осень)?\s*\d{4}', re.IGNORECASE)
PH_REGEX = re.compile(r'\{([a-zA-Z0-9_]+)\}')
EMPTY_TAGS_RE = re.compile(r'<(code|spoiler|b|i|u|s)>\s*</\1>')
MULTIPLE_COMMAS_RE = re.compile(r',\s*,')
SPACE_COMMA_RE = re.compile(r'\s+,')
COMMA_SPACE_RE = re.compile(r',\s+')
COND_BLOCK_RE = re.compile(r'\[\s*(-?)\s*["\'«“](.*?)["\'»”]\s*(-?)\s*\]')

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
    val = plugin.get_setting(key, default) if hasattr(plugin, "get_setting") else getattr(plugin, key, default)
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
        val = plugin.get_setting(key, default) if hasattr(plugin, "get_setting") else getattr(plugin, key, default)
        val = int(val)
    except Exception:
        val = default
    try:
        val = max(mn, val)
        return min(mx, val) if mx is not None else val
    except Exception:
        return default

def gf(plugin, key, default=0.0, mn=0.0, mx=None):
    try:
        val = plugin.get_setting(key, default) if hasattr(plugin, "get_setting") else getattr(plugin, key, default)
        val = float(str(val).replace(",", ".").strip())
    except Exception:
        val = default
    try:
        val = max(mn, val)
        return min(mx, val) if mx is not None else val
    except Exception:
        return default

def gs(plugin, key, default=""):
    val = plugin.get_setting(key, default) if hasattr(plugin, "get_setting") else getattr(plugin, key, default)
    return str(val).strip() if val is not None and str(val).strip() else default

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
    text = html.unescape(text)
    text = CLEAN_BB_RE1.sub(r'\1', text)
    text = CLEAN_WIKI_LINK_RE.sub(r'\1', text)
    text = CLEAN_BB_RE2.sub('', text)
    text = CLEAN_JP_PAREN_RE.sub('', text)
    text = CLEAN_DOUBLE_PAREN_RE.sub('', text)
    text = CLEAN_DOUBLE_BRACKET_RE.sub('', text)
    text = CLEAN_BB_RE3.sub('', text)
    text = CLEAN_TAGS_RE.sub('', text)
    return CLEAN_SPACES_RE.sub(' ', text).strip()

def _clean_side(text):
    t = COND_BLOCK_RE.sub("", text or "")
    t = CLEAN_TAGS_RE.sub("", t)
    return t.replace("\u200b", "")

def eval_conditional_blocks(rendered_line, raw_template_line, vars_dict):
    if not rendered_line or "[" not in rendered_line:
        return rendered_line
    matches = list(COND_BLOCK_RE.finditer(rendered_line))
    if not matches:
        return rendered_line
    raw_matches = list(COND_BLOCK_RE.finditer(raw_template_line))
    out = []
    last_idx = 0
    for i, m in enumerate(matches):
        prefix = rendered_line[last_idx:m.start()]
        last_idx = m.end()
        left_hyphen = m.group(1) == "-"
        content = m.group(2)
        right_hyphen = m.group(3) == "-"
        inner_phs = PH_REGEX.findall(content)
        if inner_phs:
            if vars_dict is not None and not any(vars_dict.get(ph) is not None and str(vars_dict.get(ph)).strip() for ph in inner_phs):
                continue
            if vars_dict is not None:
                for ph in inner_phs:
                    val = str(vars_dict.get(ph, "")).strip() if vars_dict.get(ph) is not None else ""
                    content = content.replace("{" + ph + "}", val)
        left_str = _clean_side(rendered_line[:m.start()])
        right_str = _clean_side(rendered_line[m.end():])
        raw_m = raw_matches[i] if i < len(raw_matches) else None
        orig_left = _clean_side(raw_template_line[:raw_m.start()]) if raw_m else ""
        orig_right = _clean_side(raw_template_line[raw_m.end():]) if raw_m else ""
        if orig_left.endswith(" ") or orig_left.endswith("\t"):
            has_left = bool(left_str.strip())
        else:
            has_left = bool(left_str) and not left_str.endswith(" ") and not left_str.endswith("\t")
        if orig_right.startswith(" ") or orig_right.startswith("\t"):
            has_right = bool(right_str.strip())
        else:
            has_right = bool(right_str) and not right_str.startswith(" ") and not right_str.startswith("\t")
        orig_has_left = bool(orig_left.strip())
        orig_has_right = bool(orig_right.strip())
        drop = False
        if left_hyphen and right_hyphen:
            if not has_left and not has_right:
                drop = True
        elif left_hyphen:
            if not has_left:
                drop = True
        elif right_hyphen:
            if not has_right:
                drop = True
        else:
            if orig_has_left and not has_left:
                drop = True
            elif orig_has_right and not has_right:
                drop = True
        if drop:
            prefix = prefix.rstrip(" ")
            out.append(prefix)
        else:
            out.append(prefix)
            out.append(content)
    out.append(rendered_line[last_idx:])
    return "".join(out)

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
        proc = eval_conditional_blocks(proc, l_stripped, vars_dict)
        proc = PH_REGEX.sub("", proc)
        proc = EMPTY_TAGS_RE.sub("", proc)
        proc = CLEAN_SPACES_RE.sub(" ", proc)
        proc = MULTIPLE_COMMAS_RE.sub(",", proc)
        proc = SPACE_COMMA_RE.sub(",", proc)
        proc = COMMA_SPACE_RE.sub(", ", proc).strip()
        if proc:
            cleaned.append(indent + proc)
    return "\n".join(cleaned)