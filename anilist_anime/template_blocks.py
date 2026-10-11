from hook_utils import find_class
from android.util import TypedValue
from org.telegram.messenger import AndroidUtilities
from org.telegram.ui.ActionBar import Theme
from java import dynamic_proxy
from android_utils import OnClickListener

LinearLayout = find_class("android.widget.LinearLayout")
HorizontalScrollView = find_class("android.widget.HorizontalScrollView")
ScrollView = find_class("android.widget.ScrollView")
Button = find_class("android.widget.Button")
ViewGroup = find_class("android.view.ViewGroup")
View = find_class("android.view.View")
GradientDrawable = find_class("android.graphics.drawable.GradientDrawable")
Gravity = find_class("android.view.Gravity")
Rect = find_class("android.graphics.Rect")
OnGlobalLayoutListener = find_class("android.view.ViewTreeObserver$OnGlobalLayoutListener")
R_drawable = find_class("org.telegram.messenger.R$drawable")

NAMES_RU = [("{ru1}", "ru1"), ("{ru2}", "ru2"), ("{ru3}", "ru3"), ("{ru4}", "ru4"), ("{ru5}", "ru5")]
NAMES_EN = [("{en1}", "en1"), ("{en2}", "en2"), ("{en3}", "en3"), ("{en4}", "en4"), ("{en5}", "en5")]
NAMES_ALL = NAMES_RU + NAMES_EN
NAMES_LIST = [("{title}", "title")]

PLACES_CARD = [
    ("{flag}", "flag"),
    ("{id}", "id"),
    ("{format}", "format"),
    ("{status}", "status"),
    ("{score}", "score"),
    ("{episodes}", "episodes"),
    ("{season}", "season"),
    ("{year}", "year"),
    ("{genres}", "genres"),
    ("{tags}", "tags"),
    ("{country}", "country"),
    ("{preview}", "preview"),
    ("{cover}", "cover"),
    ("{banner}", "banner"),
    ("{link1}", "link1"),
    ("{link2}", "link2"),
    ("{description}", "description"),
    ("{source}", "source"),
    ("{audience}", "audience"),
    ("{author}", "author"),
    ("{studios}", "studios"),
    ("{relations}", "relations"),
    ("{opening}", "opening"),
    ("{ending}", "ending"),
    ("{trailer}", "trailer"),
    ("{a}", "a")
]

PLACES_LIST = [
    ("{flag}", "flag"),
    ("{num}", "num"),
    ("{id}", "id"),
    ("{format}", "format"),
    ("{status}", "status"),
    ("{score}", "score"),
    ("{episodes}", "episodes"),
    ("{season}", "season"),
    ("{year}", "year"),
    ("{genres}", "genres"),
    ("{country}", "country"),
    ("{cover}", "cover"),
    ("{banner}", "banner"),
    ("{link}", "link")
]

PLACES_POPUP = [
    ("{flag}", "flag"),
    ("{id}", "id"),
    ("{format}", "format"),
    ("{status}", "status"),
    ("{score}", "score"),
    ("{episodes}", "episodes"),
    ("{season}", "season"),
    ("{year}", "year"),
    ("{genres}", "genres"),
    ("{country}", "country"),
    ("{banner}", "banner")
]

LABELS = {
    "ru1": "ру1", "ru2": "ру2", "ru3": "ру3", "ru4": "ру4", "ru5": "ру5",
    "en1": "англ1", "en2": "англ2", "en3": "англ3", "en4": "англ4", "en5": "англ5",
    "preview": "превью", "a": "аниме", "flag": "флаг", "country": "страна",
    "season": "сезон", "year": "год", "format": "формат", "audience": "целевая",
    "genres": "жанры", "tags": "теги", "episodes": "эпизоды", "score": "рейтинг",
    "status": "статус", "duration": "длительность", "source": "источник",
    "studios": "студии", "link1": "anilist", "link2": "shikimori", "link": "ссылка",
    "description": "описание", "id": "айди", "title": "название", "cover": "обложка",
    "relations": "связанные", "author": "автор", "banner": "баннер",
    "opening": "опенинг", "ending": "эндинг", "trailer": "трейлер", "num": "номер", "custom": "маркер"
}

PREVIEW_SAMPLES = {
    "preview": "", "a": "#аниме", "ru1": "Русское название", "ru2": "Русское название 2",
    "ru3": "Русское название 3", "ru4": "Русское название 4", "ru5": "Русское название 5",
    "en1": "English Title", "en2": "English Title 2", "en3": "English Title 3",
    "en4": "English Title 4", "en5": "English Title 5", "flag": "🇯🇵", "country": "Япония",
    "season": "лето", "year": "2018г.", "format": "TV Сериал", "audience": "сёнэн",
    "genres": "драма экшен", "tags": "психология", "episodes": "8/18 эп.", "score": "8.8/10",
    "status": "онгоинг", "duration": "24 мин.", "source": "манга", "studios": "MAPPA",
    "link1": "AniList", "link2": "Shikimori", "link": "Ссылка", "description": "описание",
    "id": "101280", "title": "Attack on Titan", "cover": "обложка",
    "relations": "Атака титанов 3", "author": "Хадзимэ Исаяма", "banner": "баннер",
    "opening": "The Rumbling", "ending": "Akuma no Ko", "trailer": "Трейлер",
    "num": "1", "custom": "•", "type_ru": "TV Сериал"
}

def dp(x): return AndroidUtilities.dp(x)

def to_jcolor(c):
    c = int(c) & 0xFFFFFFFF
    if c >= 0x80000000: c -= 0x100000000
    return c

def th(key):
    try:
        return to_jcolor(Theme.getColor(key))
    except:
        return 0

def th_alpha(key, alpha):
    c = th(key)
    return to_jcolor((int(c) & 0x00FFFFFF) | ((int(alpha) & 0xFF) << 24))

def make_bg(fill, stroke=None, radius=12, stroke_dp=1):
    bg = GradientDrawable()
    bg.setShape(GradientDrawable.RECTANGLE)
    bg.setCornerRadius(float(dp(radius)))
    bg.setColor(to_jcolor(fill))
    if stroke is not None: bg.setStroke(dp(stroke_dp), to_jcolor(stroke))
    return bg

def make_circle_bg(fill, stroke=None, stroke_dp=1):
    bg = GradientDrawable()
    bg.setShape(GradientDrawable.OVAL)
    bg.setColor(to_jcolor(fill))
    if stroke is not None: bg.setStroke(dp(stroke_dp), to_jcolor(stroke))
    return bg

def no_clip(v):
    for m in ("setClipChildren", "setClipToPadding", "setClipToOutline"):
        try: getattr(v, m)(False)
        except: pass
    return v

def lp(w=ViewGroup.LayoutParams.MATCH_PARENT, h=ViewGroup.LayoutParams.WRAP_CONTENT, weight=0.0, ml=0, mt=0, mr=0, mb=0):
    p = LinearLayout.LayoutParams(w, h, weight) if weight else LinearLayout.LayoutParams(w, h)
    p.setMargins(dp(ml), dp(mt), dp(mr), dp(mb))
    return p

def get_drawable(name):
    try:
        r = getattr(R_drawable, name)
        if r: return r
    except: pass
    return 0

class TemplatePanelBuilder:
    def __init__(self, editor):
        self.editor = editor

    def ph_btn(self, act, sym, key, label=None):
        b = Button(act)
        b.setAllCaps(False)
        show = LABELS.get(key, str(key or "").replace("{", "").replace("}", ""))
        if not show: show = str(sym or "").replace("{", "").replace("}", "")
        b.setText(show)
        text_c = th(Theme.key_windowBackgroundWhiteBlackText)
        card = th(Theme.key_windowBackgroundWhite)
        b.setTextColor(int(text_c))
        b.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
        try: b.setBackground(make_bg(th_alpha(Theme.key_windowBackgroundWhite, 0xE6), None, 12, 0))
        except: b.setBackgroundColor(int(card))
        try:
            b.setElevation(0.0)
            b.setStateListAnimator(None)
        except: pass
        b.setPadding(dp(8), dp(8), dp(8), dp(8))
        b.setMinHeight(0)
        b.setMinimumHeight(0)
        try:
            b.setIncludeFontPadding(False)
            b.setHeight(dp(42))
        except: pass
        b.setOnClickListener(OnClickListener(lambda v, s=sym: self.editor._append_text(s)))
        return b

    def list_block_btn(self, act, label, block_key):
        b = Button(act)
        b.setAllCaps(False)
        b.setText(label)
        is_sel = (self.editor._current_tab == block_key)
        accent = th(Theme.key_windowBackgroundWhiteBlueText)
        text_c = th(Theme.key_windowBackgroundWhiteBlackText)
        card = th(Theme.key_windowBackgroundWhite)
        b.setTextColor(int(accent if is_sel else text_c))
        b.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
        bg_color = th_alpha(Theme.key_windowBackgroundWhiteBlueText, 0x55) if is_sel else th_alpha(Theme.key_windowBackgroundWhite, 0xE6)
        try: b.setBackground(make_bg(bg_color, None, 12, 0))
        except: b.setBackgroundColor(int(card))
        try:
            b.setElevation(0.0)
            b.setStateListAnimator(None)
        except: pass
        b.setPadding(dp(8), dp(8), dp(8), dp(8))
        b.setMinHeight(0)
        b.setMinimumHeight(0)
        try:
            b.setIncludeFontPadding(False)
            b.setHeight(dp(42))
        except: pass
        def on_click():
            if self.editor._current_tab != block_key:
                self.editor._templates[self.editor._current_tab] = self.editor._get_text()
                self.editor._current_tab = block_key
                self.editor._selected_list_block = block_key
                self.editor._set_text(self.editor._templates[block_key], push=False)
                self.editor._history = [(self.editor._templates[block_key], len(self.editor._templates[block_key]))]
                self.editor._hist_idx = 0
            else:
                self.editor._selected_list_block = block_key
            self.editor._refresh_panel()
        b.setOnClickListener(OnClickListener(lambda v: on_click()))
        return b

    def h_row(self, act, items):
        row = LinearLayout(act)
        no_clip(row)
        row.setOrientation(LinearLayout.HORIZONTAL)
        try: row.setGravity(Gravity.CENTER_VERTICAL)
        except: pass
        row.setLayoutParams(lp())
        for it in items:
            sym, key = it[0], it[1]
            if not self.editor._enabled(key): continue
            b = self.ph_btn(act, sym, key)
            p = lp(0, dp(42), 1.0, 2, 2, 2, 2)
            try: p.gravity = Gravity.CENTER_VERTICAL
            except: pass
            b.setLayoutParams(p)
            row.addView(b)
        return row

    def single_carousel(self, act, items):
        row = LinearLayout(act)
        row.setOrientation(LinearLayout.HORIZONTAL)
        try: row.setGravity(Gravity.CENTER_VERTICAL)
        except: pass
        row.setLayoutParams(lp(ViewGroup.LayoutParams.WRAP_CONTENT, dp(46)))
        for it in items:
            sym, key = it[0], it[1]
            if not self.editor._enabled(key): continue
            b = self.ph_btn(act, sym, key)
            p = lp(ViewGroup.LayoutParams.WRAP_CONTENT, dp(42), 0, 2, 2, 2, 2)
            try: p.gravity = Gravity.CENTER_VERTICAL
            except: pass
            b.setLayoutParams(p)
            row.addView(b)
        hsv = HorizontalScrollView(act)
        hsv.setHorizontalScrollBarEnabled(False)
        try: hsv.setOverScrollMode(View.OVER_SCROLL_IF_CONTENT_SCROLLS)
        except: pass
        try: hsv.setFillViewport(False)
        except: pass
        hsv.addView(row)
        hsv.setLayoutParams(lp(ViewGroup.LayoutParams.MATCH_PARENT, dp(46)))
        return hsv

    def vertical_block(self, act, lines):
        box = LinearLayout(act)
        box.setOrientation(LinearLayout.VERTICAL)
        box.setLayoutParams(lp())
        for line in lines:
            if not line: continue
            box.addView(self.h_row(act, line))
        try:
            for i in range(box.getChildCount()):
                ch = box.getChildAt(i)
                try:
                    ch.setClipChildren(True)
                    ch.setClipToPadding(True)
                except: pass
        except: pass
        row_h = dp(46)
        sv = ScrollView(act)
        sv.setVerticalScrollBarEnabled(True)
        try: sv.setOverScrollMode(View.OVER_SCROLL_IF_CONTENT_SCROLLS)
        except: pass
        try: sv.setFillViewport(False)
        except: pass
        try:
            sv.setClipChildren(True)
            sv.setClipToPadding(True)
        except: pass
        try:
            box.setClipChildren(True)
            box.setClipToPadding(True)
        except: pass
        sv.addView(box)
        sv.setLayoutParams(lp(ViewGroup.LayoutParams.MATCH_PARENT, row_h))
        try:
            class _TopClip(dynamic_proxy(OnGlobalLayoutListener)):
                def onGlobalLayout(self):
                    try:
                        w = int(sv.getWidth() or 0)
                        h = int(sv.getHeight() or 0)
                        if w > 0 and h > 0:
                            r = Rect(0, 0, w, h + dp(50))
                            sv.setClipBounds(r)
                            try: sv.getViewTreeObserver().removeOnGlobalLayoutListener(self)
                            except: pass
                    except: pass
            sv.getViewTreeObserver().addOnGlobalLayoutListener(_TopClip())
        except: pass
        return sv

    def chunk(self, items, n):
        return [items[i:i+n] for i in range(0, len(items), n)]

    def build_names_panel(self, act):
        if self.editor._current_tab == "popup":
            return View(act)
        if self.editor._current_tab == "list":
            return self.single_carousel(act, NAMES_LIST)
        if self.editor._is_vertical():
            return self.vertical_block(act, [NAMES_RU, NAMES_EN])
        return self.single_carousel(act, NAMES_ALL)

    def build_places_panel(self, act):
        if self.editor._current_tab == "list":
            source_list = PLACES_LIST
        elif self.editor._current_tab == "popup":
            source_list = PLACES_POPUP
        else:
            source_list = PLACES_CARD
        items = [it for it in source_list if self.editor._enabled(it[1])]
        if self.editor._is_vertical():
            lines = self.chunk(items, 4) or [[]]
            return self.vertical_block(act, lines)
        return self.single_carousel(act, items)

    def build_lists_panel(self, act):
        options = [("Карточка", "card"), ("Список", "list"), ("Окно поиска", "popup")]
        row = LinearLayout(act)
        no_clip(row)
        row.setOrientation(LinearLayout.HORIZONTAL)
        try: row.setGravity(Gravity.CENTER_VERTICAL)
        except: pass
        row.setLayoutParams(lp(ViewGroup.LayoutParams.MATCH_PARENT, dp(46)))
        for label, block_key in options:
            b = self.list_block_btn(act, label, block_key)
            p = lp(0, dp(42), 1.0, 2, 2, 2, 2)
            try: p.gravity = Gravity.CENTER_VERTICAL
            except: pass
            b.setLayoutParams(p)
            row.addView(b)
        return row
