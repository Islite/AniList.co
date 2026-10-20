from hook_utils import find_class
from android.util import TypedValue
from org.telegram.messenger import AndroidUtilities
from org.telegram.ui.ActionBar import Theme
from java import dynamic_proxy
from android_utils import OnClickListener
from constants import PLACEHOLDER_LABELS

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

NAMES_RU = [(f"{{ru{i}}}", f"ru{i}") for i in range(1, 6)]
NAMES_EN = [(f"{{en{i}}}", f"en{i}") for i in range(1, 6)]
NAMES_ALL = NAMES_RU + NAMES_EN
NAMES_LIST = [("{title}", "title")]

PLACES_CARD = [
    ("{preview}", "preview"),
    ("{a}", "a"),
    ("{flag}", "flag"),
    ("{country}", "country"),
    ("{season}", "season"),
    ("{year}", "year"),
    ("{format}", "format"),
    ("{audience}", "audience"),
    ("{genres}", "genres"),
    ("{tags}", "tags"),
    ("{link1}", "link1"),
    ("{link2}", "link2"),
    ("{description}", "description"),
    ("{id}", "id"),
    ("{episodes}", "episodes"),
    ("{duration}", "duration"),
    ("{score}", "score"),
    ("{status}", "status"),
    ("{source}", "source"),
    ("{studios}", "studios"),
    ("{author}", "author"),
    ("{banner}", "banner"),
    ("{cover}", "cover"),
    ("{relations}", "relations"),
    ("{trailer}", "trailer"),
    ("{opening}", "opening"),
    ("{ending}", "ending"),
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
    ("{link}", "link"),
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
    ("{banner}", "banner"),
]

def dp(x):
    return AndroidUtilities.dp(x)

def to_jcolor(c):
    c = int(c) & 0xFFFFFFFF
    if c >= 0x80000000:
        c -= 0x100000000
    return c

def th(key):
    try:
        return to_jcolor(Theme.getColor(key))
    except Exception:
        return 0

def th_alpha(key, alpha):
    c = th(key)
    return to_jcolor((int(c) & 0x00FFFFFF) | ((int(alpha) & 0xFF) << 24))

def make_bg(fill, stroke=None, radius=12, stroke_dp=1):
    bg = GradientDrawable()
    bg.setShape(GradientDrawable.RECTANGLE)
    bg.setCornerRadius(float(dp(radius)))
    bg.setColor(to_jcolor(fill))
    if stroke is not None:
        bg.setStroke(dp(stroke_dp), to_jcolor(stroke))
    return bg

def make_circle_bg(fill, stroke=None, stroke_dp=1):
    bg = GradientDrawable()
    bg.setShape(GradientDrawable.OVAL)
    bg.setColor(to_jcolor(fill))
    if stroke is not None:
        bg.setStroke(dp(stroke_dp), to_jcolor(stroke))
    return bg

def no_clip(v):
    for m in ("setClipChildren", "setClipToPadding", "setClipToOutline"):
        try:
            getattr(v, m)(False)
        except Exception:
            pass
    return v

def lp(w=ViewGroup.LayoutParams.MATCH_PARENT, h=ViewGroup.LayoutParams.WRAP_CONTENT, weight=0.0, ml=0, mt=0, mr=0, mb=0):
    p = LinearLayout.LayoutParams(w, h, weight) if weight else LinearLayout.LayoutParams(w, h)
    p.setMargins(dp(ml), dp(mt), dp(mr), dp(mb))
    return p

def get_drawable(name):
    try:
        r = getattr(R_drawable, name)
        if r:
            return r
    except Exception:
        pass
    return 0

class TemplatePanelBuilder:
    def __init__(self, editor):
        self.editor = editor

    def ph_btn(self, act, sym, key):
        b = Button(act)
        b.setAllCaps(False)
        show = PLACEHOLDER_LABELS.get(key, str(key or "").replace("{", "").replace("}", ""))
        b.setText(show if show else str(sym or "").replace("{", "").replace("}", ""))
        text_c = th(Theme.key_windowBackgroundWhiteBlackText)
        card = th(Theme.key_windowBackgroundWhite)
        b.setTextColor(int(text_c))
        b.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
        try:
            b.setBackground(make_bg(th_alpha(Theme.key_windowBackgroundWhite, 0xE6), None, 12, 0))
        except Exception:
            b.setBackgroundColor(int(card))
        try:
            b.setElevation(0.0)
            b.setStateListAnimator(None)
        except Exception:
            pass
        b.setPadding(dp(8), dp(8), dp(8), dp(8))
        b.setMinHeight(0)
        b.setMinimumHeight(0)
        try:
            b.setIncludeFontPadding(False)
            b.setHeight(dp(42))
        except Exception:
            pass
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
        try:
            b.setBackground(make_bg(bg_color, None, 12, 0))
        except Exception:
            b.setBackgroundColor(int(card))
        try:
            b.setElevation(0.0)
            b.setStateListAnimator(None)
        except Exception:
            pass
        b.setPadding(dp(8), dp(8), dp(8), dp(8))
        b.setMinHeight(0)
        b.setMinimumHeight(0)
        try:
            b.setIncludeFontPadding(False)
            b.setHeight(dp(42))
        except Exception:
            pass
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
        try:
            row.setGravity(Gravity.CENTER_VERTICAL)
        except Exception:
            pass
        row.setLayoutParams(lp())
        for sym, key in items:
            if not self.editor._enabled(key):
                continue
            b = self.ph_btn(act, sym, key)
            p = lp(0, dp(42), 1.0, 2, 2, 2, 2)
            try:
                p.gravity = Gravity.CENTER_VERTICAL
            except Exception:
                pass
            b.setLayoutParams(p)
            row.addView(b)
        return row

    def single_carousel(self, act, items):
        row = LinearLayout(act)
        row.setOrientation(LinearLayout.HORIZONTAL)
        try:
            row.setGravity(Gravity.CENTER_VERTICAL)
        except Exception:
            pass
        row.setLayoutParams(lp(ViewGroup.LayoutParams.WRAP_CONTENT, dp(46)))
        for sym, key in items:
            if not self.editor._enabled(key):
                continue
            b = self.ph_btn(act, sym, key)
            p = lp(ViewGroup.LayoutParams.WRAP_CONTENT, dp(42), 0, 2, 2, 2, 2)
            try:
                p.gravity = Gravity.CENTER_VERTICAL
            except Exception:
                pass
            b.setLayoutParams(p)
            row.addView(b)
        hsv = HorizontalScrollView(act)
        hsv.setHorizontalScrollBarEnabled(False)
        try:
            hsv.setOverScrollMode(View.OVER_SCROLL_IF_CONTENT_SCROLLS)
            hsv.setFillViewport(False)
        except Exception:
            pass
        hsv.addView(row)
        hsv.setLayoutParams(lp(ViewGroup.LayoutParams.MATCH_PARENT, dp(46)))
        return hsv

    def vertical_block(self, act, lines):
        box = LinearLayout(act)
        box.setOrientation(LinearLayout.VERTICAL)
        box.setLayoutParams(lp())
        for line in lines:
            if line:
                box.addView(self.h_row(act, line))
        sv = ScrollView(act)
        sv.setVerticalScrollBarEnabled(True)
        try:
            sv.setOverScrollMode(View.OVER_SCROLL_IF_CONTENT_SCROLLS)
            sv.setFillViewport(False)
        except Exception:
            pass
        sv.addView(box)
        sv.setLayoutParams(lp(ViewGroup.LayoutParams.MATCH_PARENT, dp(46)))
        try:
            class _TopClip(dynamic_proxy(OnGlobalLayoutListener)):
                def onGlobalLayout(self):
                    try:
                        w = int(sv.getWidth() or 0)
                        h = int(sv.getHeight() or 0)
                        if w > 0 and h > 0:
                            sv.setClipBounds(Rect(0, 0, w, h + dp(50)))
                            sv.getViewTreeObserver().removeOnGlobalLayoutListener(self)
                    except Exception:
                        pass
            sv.getViewTreeObserver().addOnGlobalLayoutListener(_TopClip())
        except Exception:
            pass
        return sv

    def chunk(self, items, n):
        return [items[i:i + n] for i in range(0, len(items), n)]

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
        try:
            row.setGravity(Gravity.CENTER_VERTICAL)
        except Exception:
            pass
        row.setLayoutParams(lp(ViewGroup.LayoutParams.MATCH_PARENT, dp(46)))
        for label, block_key in options:
            b = self.list_block_btn(act, label, block_key)
            p = lp(0, dp(42), 1.0, 2, 2, 2, 2)
            try:
                p.gravity = Gravity.CENTER_VERTICAL
            except Exception:
                pass
            b.setLayoutParams(p)
            row.addView(b)
        return row