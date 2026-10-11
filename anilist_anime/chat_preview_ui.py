import re
from ui.settings import SimpleSettingFactory
from android.widget import LinearLayout, TextView, FrameLayout, ImageView, ScrollView
from android.view import Gravity, View, ViewGroup, MotionEvent
from android.graphics import Typeface, PorterDuff, PorterDuffColorFilter
from android.graphics.drawable import GradientDrawable, ColorDrawable
from android.util import TypedValue
from android.text import TextUtils, SpannableString, Spanned, StaticLayout, Layout
from android.text.style import StyleSpan, TypefaceSpan, ForegroundColorSpan
from java import dynamic_proxy
from org.telegram.messenger import AndroidUtilities, UserConfig, UserObject, R, MediaDataController, ImageReceiver, MessagesController, DialogObject
from org.telegram.ui.ActionBar import Theme
from org.telegram.ui.Components import AvatarDrawable, BackupImageView, LayoutHelper, AnimatedEmojiDrawable

MP, WC = -1, -2
_NK = ("key_avatar_nameInMessageRed", "key_avatar_nameInMessageOrange", "key_avatar_nameInMessageViolet", "key_avatar_nameInMessageGreen", "key_avatar_nameInMessageCyan", "key_avatar_nameInMessageBlue", "key_avatar_nameInMessagePink")
_RE_MD = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_RE_TOK = re.compile(r"\*\*\*([^*]+)\*\*\*|\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`|(#[\w]+)|(https?://[^\s\[\]<>]+)", re.UNICODE)

_PREVIEW_OBSERVERS = set()
_PREVIEW_RUNNABLE = None

def notify_preview_update():
    global _PREVIEW_RUNNABLE
    def _do():
        global _PREVIEW_RUNNABLE
        _PREVIEW_RUNNABLE = None
        for obs in list(_PREVIEW_OBSERVERS):
            try: obs()
            except: pass

    try:
        if _PREVIEW_RUNNABLE is not None:
            AndroidUtilities.cancelRunOnUIThread(_PREVIEW_RUNNABLE)
    except: pass

    class _R(dynamic_proxy(__import__("java.lang", fromlist=["Runnable"]).Runnable)):
        def run(self):
            _do()

    _PREVIEW_RUNNABLE = _R()
    try:
        AndroidUtilities.runOnUIThread(_PREVIEW_RUNNABLE, 120)
    except:
        try: _do()
        except: pass

def _dp(v): return int(AndroidUtilities.dp(float(v)))
def _i(v):
    try:
        n = int(v) & 0xFFFFFFFF
        return n - 0x100000000 if n >= 0x80000000 else n
    except: return 0

def _tc(*a):
    for n in a:
        if not isinstance(n, str) or n.startswith("#"): continue
        try:
            k = getattr(Theme, n, None)
            if k is not None:
                c = _i(Theme.getColor(k))
                if c: return c
        except: pass
    return 0

def _u16(s, i):
    if i <= 0: return 0
    return len(s[:i].encode("utf-16-le")) // 2 if i < len(s) else len(s.encode("utf-16-le")) // 2

def _nc(u):
    try:
        if not u: raise Exception()
        cid = UserObject.getColorId(u)
        if cid is not None:
            try:
                pc = MessagesController.getInstance(UserConfig.selectedAccount).peerColors.getColor(int(cid))
                if pc:
                    for m in ("getColor1", "getColor", "getAccentColor"):
                        v = getattr(pc, m, None)
                        if callable(v): v = v()
                        if v:
                            c = _i(v)
                            return c if c & 0xFF000000 else _i(0xFF000000 | c)
            except: pass
            if 0 <= int(cid) <= 6:
                k = getattr(Theme, _NK[int(cid)], None)
                if k:
                    c = _i(Theme.getColor(k))
                    if c: return c
        idx = AvatarDrawable.getColorIndex(int(u.id))
        if 0 <= idx < 7:
            k = getattr(Theme, _NK[idx], None)
            if k:
                c = _i(Theme.getColor(k))
                if c: return c
    except: pass
    return _tc("key_chats_name", "key_avatar_nameInMessageCyan")

def _bg_eid(u):
    try:
        e = UserObject.getEmojiId(u)
        if e: return int(e)
    except: pass
    try:
        p = getattr(getattr(u, "emoji_status", None), "pattern_document_id", None)
        if p: return int(p)
    except: pass
    return 0

def _a(c, a): return _i((max(0, min(255, int(a))) << 24) | (_i(c) & 0xFFFFFF))
def _bg(c, r):
    d = GradientDrawable(); d.setShape(0); d.setColor(_i(c)); d.setCornerRadius(float(_dp(r))); return d

def _sw(ctx):
    for f in (lambda: int(AndroidUtilities.displaySize.x), lambda: int(ctx.getResources().getDisplayMetrics().widthPixels)):
        try:
            v = f()
            if 0 < v < 100000: return v
        except: pass
    return _dp(360)

def _wp():
    for f in (Theme.getCachedWallpaper, Theme.getCachedWallpaperNonBlocking):
        try:
            d = f()
            if d: return d
        except: pass
    return ColorDrawable(_tc("key_windowBackgroundGray", "key_chat_wallpaper"))

def _ic(ctx, ns, c, sd=12):
    sz = _dp(sd); iv = ImageView(ctx)
    for n in ns:
        try:
            d = getattr(Theme, n, None)
            if d and not isinstance(d, int):
                iv.setImageDrawable(d.mutate() if hasattr(d, "mutate") else d); break
        except: pass
        try:
            r = getattr(R.drawable, n, 0)
            if r: iv.setImageResource(int(r)); break
        except: pass
    else:
        t = TextView(ctx); t.setText("•"); t.setTextSize(TypedValue.COMPLEX_UNIT_SP, 11); t.setTextColor(_i(c)); return t
    try: iv.setColorFilter(PorterDuffColorFilter(_i(c), PorterDuff.Mode.SRC_IN))
    except: pass
    iv.setScaleType(ImageView.ScaleType.FIT_CENTER)
    iv.setLayoutParams(LinearLayout.LayoutParams(sz, sz)); return iv

def _html_to_md(s):
    if not s: return s
    s = str(s)
    s = re.sub(r"(?is)<br\s*/?>", "\n", s)
    s = re.sub(r"(?is)</p\s*>", "\n", s)
    s = re.sub(r"(?is)<p\b[^>]*>", "", s)
    s = re.sub(r"(?is)&shy;|&#173;|\u00ad", "", s)
    s = re.sub(r"(?is)&nbsp;", " ", s)
    s = re.sub(r"(?is)&amp;", "&", s)
    s = re.sub(r"(?is)&lt;", "<", s)
    s = re.sub(r"(?is)&gt;", ">", s)
    s = re.sub(r"(?is)<b\b[^>]*>\s*<i\b[^>]*>(.*?)</i>\s*</b>", lambda m: "***" + re.sub(r"(?is)<[^>]+>", "", m.group(1)) + "***", s)
    s = re.sub(r"(?is)<i\b[^>]*>\s*<b\b[^>]*>(.*?)</b>\s*</i>", lambda m: "***" + re.sub(r"(?is)<[^>]+>", "", m.group(1)) + "***", s)
    s = re.sub(r"(?is)<(?:b|strong)\b[^>]*>(.*?)</(?:b|strong)>", lambda m: "**" + re.sub(r"(?is)<[^>]+>", "", m.group(1)) + "**", s)
    s = re.sub(r"(?is)<(?:i|em)\b[^>]*>(.*?)</(?:i|em)>", lambda m: "*" + re.sub(r"(?is)<[^>]+>", "", m.group(1)) + "*", s)
    def _code(m):
        inner = re.sub(r"(?is)<[^>]+>", "", m.group(1))
        return "`" + inner + "`"
    s = re.sub(r"(?is)<code\b[^>]*>(.*?)</code>", _code, s)
    def _a(m):
        href = (m.group(1) or "").strip()
        text = re.sub(r"(?is)<[^>]+>", "", m.group(2) or href)
        return "[" + text + "](" + href + ")" if href else text
    s = re.sub(r'(?is)<a\s+[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', _a, s)
    return re.sub(r"(?is)<[^>]+>", "", s)

def _rich(ctx, text, sp, c, lc):
    t = TextView(ctx); t.setTextSize(TypedValue.COMPLEX_UNIT_SP, float(sp)); t.setTextColor(_i(c)); t.setLineSpacing(0, 1.05)
    if not text: t.setText(""); return t
    s = _html_to_md(str(text)); ch = []; pos = 0
    for m in _RE_MD.finditer(s):
        if m.start() > pos: ch.append((s[pos:m.start()], 0, None))
        ch.append((m.group(1), 1, m.group(2).strip())); pos = m.end()
    if pos < len(s): ch.append((s[pos:], 0, None))
    spans = []; out = []
    def em(p, k=0, e=None):
        if not p: return
        a = sum(len(x) for x in out); out.append(p)
        if k: spans.append((a, a + len(p), k, e))
    for p, k, e in ch:
        if k == 1: em(p, 1, e); continue
        q = 0
        for m in _RE_TOK.finditer(p):
            if m.start() > q: em(p[q:m.start()])
            g = m.groups()
            if g[0] is not None: em(g[0], 5)
            elif g[1] is not None: em(g[1], 2)
            elif g[2] is not None: em(g[2], 6)
            elif g[3] is not None: em(g[3], 3)
            elif g[4] is not None: em(g[4], 4)
            elif g[5] is not None:
                u = g[5].rstrip(".,;:!?)"); em(u, 1, u)
            q = m.end()
        if q < len(p): em(p[q:])
    plain = "".join(out)
    if not spans: t.setText(plain); return t
    try:
        ss = SpannableString(plain)
        for a, b, k, _ in spans:
            a, b = _u16(plain, a), _u16(plain, b)
            if a < 0 or b <= a: continue
            if k == 5:
                try: ss.setSpan(StyleSpan(Typeface.BOLD_ITALIC), a, b, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                except: ss.setSpan(StyleSpan(Typeface.BOLD), a, b, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            elif k == 2: ss.setSpan(StyleSpan(Typeface.BOLD), a, b, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            elif k == 6:
                try: ss.setSpan(StyleSpan(Typeface.ITALIC), a, b, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                except: pass
            elif k == 3:
                try: ss.setSpan(TypefaceSpan("monospace"), a, b, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                except: pass
            elif k in (1, 4): ss.setSpan(ForegroundColorSpan(_i(lc)), a, b, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        t.setText(ss)
    except: t.setText(plain)
    return t

def _rwh(img):
    w = h = 0
    try:
        ir = img.getImageReceiver()
        if ir:
            try:
                bm = ir.getBitmap()
                if bm: w, h = int(bm.getWidth()), int(bm.getHeight())
            except: pass
            if w <= 0 or h <= 0:
                try:
                    d = ir.getDrawable()
                    if d: w, h = int(d.getIntrinsicWidth()), int(d.getIntrinsicHeight())
                except: pass
    except: pass
    if w <= 0 or h <= 0:
        try:
            d = img.getDrawable()
            if d: w, h = int(d.getIntrinsicWidth()), int(d.getIntrinsicHeight())
        except: pass
    return w, h

def _asz(box, c, img, mw, mh, pt, pb, max_h=_dp(290)):
    def _do():
        try:
            mh_val = max(_dp(32), min(int(mh), int(max_h)))
            img.setLayoutParams(FrameLayout.LayoutParams(MP, mh_val))
            th = mh_val + pt + pb
            for v in (c, box):
                lp = v.getLayoutParams()
                if lp: lp.height = th; v.setLayoutParams(lp)
            c.requestLayout(); box.requestLayout()

            p = box
            root_view = None
            while p:
                try: p.requestLayout()
                except: pass
                if getattr(p, "getTag", lambda: None)() == "dcp_root":
                    root_view = p
                    break
                p = p.getParent()

            if root_view:
                row = None
                for i in range(root_view.getChildCount()):
                    ch = root_view.getChildAt(i)
                    if isinstance(ch, ScrollView) and ch.getChildCount() > 0:
                        row = ch.getChildAt(0); break
                if row:
                    row.measure(
                        View.MeasureSpec.makeMeasureSpec(_sw(root_view.getContext()), View.MeasureSpec.AT_MOST),
                        View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED)
                    )
                    rh = max(_dp(1), row.getMeasuredHeight())
                    final_h = min(rh, _dp(650))
                    lp = row.getLayoutParams()
                    if lp: lp.height = rh; row.setLayoutParams(lp)
                    plp = root_view.getLayoutParams()
                    if plp: plp.height = final_h; root_view.setLayoutParams(plp)

                curr = root_view.getParent()
                while curr:
                    try:
                        clp = curr.getLayoutParams()
                        if clp and clp.height != WC and clp.height != MP:
                            clp.height = WC
                            curr.setLayoutParams(clp)
                        curr.requestLayout()
                    except: pass
                    curr = curr.getParent()
        except: pass

    try: AndroidUtilities.runOnUIThread(_do)
    except:
        try: _do()
        except: pass

def _rc(box):
    try:
        m = getattr(box, "_dcp", None)
        if not m: return
        w, h = _rwh(m["img"])
        if w > 0 and h > 0:
            max_h = m.get("max_h", _dp(290))
            _asz(box, m["c"], m["img"], m["mw"], max(_dp(40), min(int(m["mw"] * h / w), max_h)), m["pt"], m["pb"], max_h)
        else:
            retries = m.get("retries", 0)
            if retries < 15:
                m["retries"] = retries + 1
                img = m.get("img")
                if img: img.postDelayed(lambda: _rc(box), 100)
    except: pass

def _bsz(box, c, img, mw, pt, pb, max_h=_dp(290)):
    try:
        box._dcp = {"img": img, "c": c, "mw": mw, "pt": pt, "pb": pb, "max_h": max_h, "retries": 0}
        class _D(dynamic_proxy(ImageReceiver.ImageReceiverDelegate)):
            def didSetImage(self, ir, set, thumb, memCache):
                try: AndroidUtilities.runOnUIThread(lambda: _rc(box))
                except:
                    try: _rc(box)
                    except: pass
            def onAnimationReady(self, ir):
                try: AndroidUtilities.runOnUIThread(lambda: _rc(box))
                except:
                    try: _rc(box)
                    except: pass

        class _A(dynamic_proxy(View.OnAttachStateChangeListener)):
            def onViewAttachedToWindow(self, v):
                try: AndroidUtilities.runOnUIThread(lambda: _rc(box))
                except: pass
            def onViewDetachedFromWindow(self, v): pass

        ir = img.getImageReceiver()
        if ir: ir.setDelegate(_D())
        try: img.addOnAttachStateChangeListener(_A())
        except: pass
        try: AndroidUtilities.runOnUIThread(lambda: _rc(box))
        except:
            try: _rc(box)
            except: pass
    except: pass

def _emoji_iv(ctx, doc_id, sz, color, col=False):
    iv = ImageView(ctx); iv.setScaleType(ImageView.ScaleType.CENTER_INSIDE)
    try: iv.setAdjustViewBounds(True)
    except: pass
    try:
        ct = getattr(AnimatedEmojiDrawable, "CACHE_TYPE_MESSAGES", 0)
        if col:
            try: ct = getattr(AnimatedEmojiDrawable, "CACHE_TYPE_NOANIMATE_FOLDER", ct)
            except: pass
        d = AnimatedEmojiDrawable.make(UserConfig.selectedAccount, ct, int(doc_id))
        try: d.setColorFilter(PorterDuffColorFilter(_i(color), PorterDuff.Mode.SRC_IN))
        except:
            try: d.setColor(int(color))
            except: pass
        try: d.setBounds(0, 0, sz, sz)
        except: pass
        iv.setImageDrawable(d)
        try:
            if hasattr(d, "addView"): d.addView(iv)
        except: pass
        return iv
    except: pass
    try:
        swap = AnimatedEmojiDrawable.SwapAnimatedEmojiDrawable(iv, sz)
        try: swap.setCurrentAccount(UserConfig.selectedAccount)
        except: pass
        swap.set(int(doc_id), False)
        try: swap.setColor(int(color))
        except: pass
        iv.setImageDrawable(swap)
        if not col:
            try: swap.attach()
            except: pass
        return iv
    except: return None

def _make_bar(ctx, lc, brf, bg_eid):
    bar = FrameLayout(ctx)
    try:
        bb = GradientDrawable(); bb.setShape(0); bb.setColor(_i(lc)); bb.setCornerRadii([brf, brf, 0, 0, 0, 0, brf, brf])
        bar.setBackground(bb)
    except: bar.setBackgroundColor(_i(lc))
    if bg_eid:
        try:
            sz = _dp(12)
            iv = _emoji_iv(ctx, bg_eid, sz, _tc("key_windowBackgroundWhite", "key_actionBarDefaultIcon"), True)
            if iv:
                try: iv.setAlpha(0.35)
                except: pass
                lp = FrameLayout.LayoutParams(sz, sz); lp.gravity = Gravity.CENTER
                bar.addView(iv, lp)
        except: pass
    return bar

def _rbox(ctx, nc, br, mr, ld, pl, pt, pr, pb, img, ih, mw, bg_eid=0):
    pl, pt, pr, pb = _dp(pl), _dp(pt), _dp(pr), _dp(pb)
    lw = max(1, _dp(ld)); brf = float(_dp(br)); th = ih + pt + pb
    box = LinearLayout(ctx); box.setOrientation(0)
    box.setClickable(False); box.setFocusable(False)
    try: box.setClipToPadding(True); box.setClipChildren(True)
    except: pass
    lc = _i(nc) if nc else _tc("key_chat_inReplyLine", "key_chat_messageLinkIn")
    bc = _a(lc, 0x28)
    try:
        bg = GradientDrawable(); bg.setShape(0); bg.setColor(_i(bc)); bg.setCornerRadii([0, 0, brf, brf, brf, brf, 0, 0]); box.setBackground(bg)
    except: box.setBackground(_bg(bc, br))
    box.addView(_make_bar(ctx, lc, brf, bg_eid), LinearLayout.LayoutParams(lw, MP))
    ct = FrameLayout(ctx); ct.setPadding(pl, pt, pr, pb)
    try: ct.setClipToPadding(True); ct.setClipChildren(True)
    except: pass
    ct.addView(img, FrameLayout.LayoutParams(MP, ih))
    box.addView(ct, LinearLayout.LayoutParams(0, th, 1.0))
    _bsz(box, ct, img, mw, pt, pb, _dp(290))
    return box

def _media_image(ctx, ref, mw, nc, bg_eid=0):
    try:
        if mw <= 0: mw = _dp(200)
        if not ref or not str(ref).strip().lower().startswith(("http://", "https://")): return None
        pl, pt, pr, pb = 5, 4, 5, 4
        lw = _dp(3); aw = max(1, mw - _dp(pl + pr) - lw)
        img = BackupImageView(ctx)
        try: img.setAspectFit(False)
        except: pass
        try: img.setRoundRadius(_dp(4))
        except: pass
        ref = str(ref).strip()
        ih = max(_dp(64), min(int(aw * 1.4), _dp(290)))
        f = "%d" % aw
        try: img.setImage(ref, f, None)
        except:
            try: img.setImage(ref, None, None)
            except: pass
        return _rbox(ctx, nc, 5, 4, 3, pl, pt, pr, pb, img, ih, aw, bg_eid)
    except: return None

def _media_attach(ctx, ref, mw, above=False):
    try:
        if mw <= 0: mw = _dp(200)
        if not ref or not str(ref).strip().lower().startswith(("http://", "https://")): return None
        ref = str(ref).strip()
        inset = _dp(2)
        top = _dp(4) if above else 0
        aw = max(1, int(mw) - inset * 2)
        max_h = _dp(290)
        ih = max(_dp(96), min(int(aw * 1.4), max_h))
        img = BackupImageView(ctx)
        try: img.setAspectFit(False)
        except: pass
        br_out = 12; ir = max(0, br_out - 2)
        try: img.setRoundRadius(_dp(ir))
        except: pass
        f = "%d" % aw
        try: img.setImage(ref, f, None)
        except:
            try: img.setImage(ref, None, None)
            except: pass
        box = LinearLayout(ctx); box.setOrientation(1)
        try: box.setClipToPadding(True); box.setClipChildren(True)
        except: pass
        box.setPadding(inset, 0, inset, 0)
        ct = FrameLayout(ctx)
        try: ct.setClipToPadding(True); ct.setClipChildren(True)
        except: pass
        if top: ct.setPadding(0, top, 0, 0)
        ct.addView(img, FrameLayout.LayoutParams(MP, ih))
        th = ih + top
        box.addView(ct, LinearLayout.LayoutParams(MP, th))
        _bsz(box, ct, img, aw, top, 0, max_h)
        return box
    except: return None

def _meta_on_media(ctx, ts, ed):
    tc = _tc("key_chat_mediaTimeText", "key_chat_serviceText", "key_chat_inTimeText")
    bgc = _tc("key_chat_mediaTimeBackground", "key_chat_serviceBackground") or _a(0x000000, 0x99)
    m = _meta(ctx, ts, ed, tc)
    try:
        d = GradientDrawable(); d.setShape(0); d.setColor(_i(bgc)); d.setCornerRadius(float(_dp(8)))
        m.setBackground(d)
    except: m.setBackgroundColor(_i(bgc))
    m.setPadding(_dp(6), _dp(3), _dp(6), _dp(3))
    return m

def _cu():
    try: return UserConfig.getInstance(UserConfig.selectedAccount).getCurrentUser()
    except: return None

def _un(u):
    if not u: return "User"
    try:
        n = UserObject.getFirstName(u)
        if n: return str(n)
    except: pass
    try:
        if getattr(u, "first_name", None): return str(u.first_name)
    except: pass
    return "User"

def _av(ctx, sd, u=None):
    sz = _dp(sd)
    try:
        av = BackupImageView(ctx); av.setRoundRadius(sz // 2); d = AvatarDrawable()
        if u:
            try: d.setInfo(u)
            except:
                try: d.setInfo(UserConfig.selectedAccount, u)
                except: pass
            av.setForUserOrChat(u, d)
        else: d.setInfo(0, "U"); av.setImage(None, None, d)
        return av, sz
    except:
        a = TextView(ctx); a.setText("U"); a.setGravity(Gravity.CENTER); a.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13)
        a.setTextColor(_tc("key_windowBackgroundWhiteBlackText", "key_chats_name")); a.setTypeface(Typeface.DEFAULT_BOLD)
        d = GradientDrawable(); d.setShape(1); d.setColor(_tc("key_chats_actionBackground", "key_avatar_backgroundInProfileBlue")); a.setBackground(d)
        return a, sz

def _meta(ctx, ts, ed, tc):
    m = LinearLayout(ctx); m.setOrientation(0); m.setGravity(Gravity.CENTER_VERTICAL); m.setPadding(_dp(4), 0, 0, 0)
    if ed:
        ic = _ic(ctx, ["pencil", "msg_edit", "group_edit_profile"], tc, 12)
        lp = LinearLayout.LayoutParams(_dp(12), _dp(12)); lp.gravity = Gravity.CENTER_VERTICAL; m.addView(ic, lp)
        m.addView(View(ctx), LinearLayout.LayoutParams(_dp(2), 1))
    tv = TextView(ctx); tv.setText(ts); tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12.1); tv.setTextColor(_i(tc)); tv.setIncludeFontPadding(False)
    lp = LinearLayout.LayoutParams(WC, WC); lp.gravity = Gravity.CENTER_VERTICAL; m.addView(tv, lp)
    return m

def _is_col(u):
    try:
        es = getattr(u, "emoji_status", None)
        if not es: return False
        cn = type(es).__name__
        if "Collectible" in cn or "collectible" in cn.lower(): return True
        if getattr(es, "collectible_id", None) is not None: return True
        if getattr(es, "pattern_document_id", None) is not None: return True
        if getattr(es, "text_color", None) is not None and getattr(es, "center_color", None) is not None: return True
    except: pass
    return False

def _name_view(ctx, name, nc, u):
    row = LinearLayout(ctx); row.setOrientation(0); row.setGravity(Gravity.CENTER_VERTICAL)
    try: row.setClipChildren(False); row.setClipToPadding(False)
    except: pass
    tv = TextView(ctx); tv.setText(name); tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13); tv.setTextColor(_i(nc))
    tv.setTypeface(Typeface.DEFAULT_BOLD); tv.setSingleLine(True); tv.setEllipsize(TextUtils.TruncateAt.END)
    tv.setIncludeFontPadding(False); tv.setGravity(Gravity.CENTER_VERTICAL)
    doc_id = 0; col = False
    try:
        if u:
            es = getattr(u, "emoji_status", None)
            if es:
                col = _is_col(u)
                try: doc_id = int(DialogObject.getEmojiStatusDocumentId(es))
                except:
                    try: doc_id = int(getattr(es, "document_id", 0) or 0)
                    except: doc_id = 0
    except: pass
    prem = bool(getattr(u, "premium", False)) if u else False
    bc = nc
    badge = None; sz = _dp(16)
    try:
        if doc_id: badge = _emoji_iv(ctx, doc_id, sz, bc, col)
        if not badge and prem:
            d = None
            for n in ("msg_premium_liststar", "premium_liststar", "star"):
                try:
                    r = getattr(R.drawable, n, 0)
                    if r: d = ctx.getResources().getDrawable(int(r)).mutate(); break
                except: pass
            if d:
                try: d.setColorFilter(PorterDuffColorFilter(_i(bc), PorterDuff.Mode.MULTIPLY))
                except: pass
                iv = ImageView(ctx); iv.setScaleType(ImageView.ScaleType.CENTER_INSIDE)
                try: iv.setImageDrawable(AnimatedEmojiDrawable.WrapSizeDrawable(d, sz, sz))
                except: iv.setImageDrawable(d)
                badge = iv
    except: pass
    if badge:
        row.addView(tv, LinearLayout.LayoutParams(0, WC, 1.0))
        lp = LinearLayout.LayoutParams(sz, sz); lp.gravity = Gravity.CENTER_VERTICAL
        row.addView(badge, lp)
        def _place():
            try:
                lay = tv.getLayout()
                tw = float(lay.getLineWidth(0)) if lay and lay.getLineCount() > 0 else float(tv.getPaint().measureText(str(tv.getText())))
                vw = float(tv.getWidth())
                if vw <= 0: return
                badge.setTranslationX(0 if tw + _dp(2) >= vw else tw + _dp(2) - vw)
            except: pass
        class _LL(dynamic_proxy(View.OnLayoutChangeListener)):
            def onLayoutChange(self, v, l, t, r, b, ol, ot, or_, ob): _place()
        try: row.addOnLayoutChangeListener(_LL()); tv.addOnLayoutChangeListener(_LL())
        except: pass
        class _R(dynamic_proxy(__import__("java.lang", fromlist=["Runnable"]).Runnable)):
            def run(self): _place()
        try: tv.post(_R()); row.post(_R())
        except: pass
        row._dcp_has_badge = True; row._dcp_badge_sz = sz
    else:
        row.addView(tv, LinearLayout.LayoutParams(WC, WC))
        row._dcp_has_badge = False; row._dcp_badge_sz = 0
    return row

def _touch():
    class _T(dynamic_proxy(View.OnTouchListener)):
        def onTouch(self, v, e):
            try:
                a = e.getActionMasked()
                dis = a in (MotionEvent.ACTION_DOWN, MotionEvent.ACTION_MOVE)
                p = v.getParent()
                while p:
                    try: p.requestDisallowInterceptTouchEvent(dis)
                    except: pass
                    p = p.getParent()
            except: pass
            return False
    return _T()

def _quote_box(ctx, text, sp, c, nc):
    box = LinearLayout(ctx); box.setOrientation(0)
    brf = float(_dp(3))
    lc = _i(nc) if nc else _tc("key_chat_inReplyLine", "key_chat_messageLinkIn")
    bgc = _a(lc, 0x1A)
    try:
        bg = GradientDrawable(); bg.setShape(0); bg.setColor(_i(bgc))
        bg.setCornerRadii([brf, brf, brf, brf, brf, brf, brf, brf]); box.setBackground(bg)
    except: box.setBackgroundColor(_i(bgc))
    line = FrameLayout(ctx)
    try:
        lb = GradientDrawable(); lb.setShape(0); lb.setColor(_i(lc))
        lb.setCornerRadii([brf, brf, 0, 0, 0, 0, brf, brf]); line.setBackground(lb)
    except: line.setBackgroundColor(_i(lc))
    box.addView(line, LinearLayout.LayoutParams(_dp(3), MP))
    
    content = FrameLayout(ctx)
    tv = _rich(ctx, text, 14, c, lc)
    tv.setPadding(_dp(6), _dp(4), _dp(16), _dp(4))
    content.addView(tv, FrameLayout.LayoutParams(WC, WC))
    
    qt = ImageView(ctx)
    qt.setScaleType(ImageView.ScaleType.CENTER_INSIDE)
    try:
        r = getattr(R.drawable, "mini_quote", 0)
        if r:
            qt.setImageResource(int(r))
            qt.setColorFilter(PorterDuffColorFilter(_i(lc), PorterDuff.Mode.SRC_IN))
    except: pass
    
    qlp = FrameLayout.LayoutParams(_dp(13), _dp(13))
    qlp.gravity = Gravity.TOP | Gravity.END
    qlp.setMargins(0, _dp(6), _dp(6), 0)
    content.addView(qt, qlp)
    
    box.addView(content, LinearLayout.LayoutParams(MP, WC))
    
    return box, tv

def _build(ctx, text, cover=None, mode=0, above=False, show_preview=True):
    text = text or ""
    u = _cu(); name = _un(u); nc = _nc(u); bg_eid = _bg_eid(u)
    ts = "18:58"
    pad = _dp(8); pt_bg = _dp(8); pb_bg = _dp(8)
    scr = _sw(ctx)
    avm = max(_dp(140), scr - pad * 2 - _dp(42))
    aw = min(avm, int(avm * 0.92))
    if aw < _dp(160): aw = min(avm, _dp(160))
    mb = max(_dp(100), min(avm, aw - _dp(56)))
    root = FrameLayout(ctx); root.setTag("dcp_root"); root.setLayoutParams(ViewGroup.LayoutParams(MP, WC))
    wp = ImageView(ctx); wp.setTag("dcp_wp"); wp.setScaleType(ImageView.ScaleType.CENTER_CROP); wp.setAdjustViewBounds(False); wp.setImageDrawable(_wp())
    root.addView(wp, FrameLayout.LayoutParams(MP, MP))
    row = LinearLayout(ctx); row.setTag("dcp_row"); row.setOrientation(0); row.setGravity(Gravity.BOTTOM); row.setPadding(pad, pt_bg, pad, pb_bg)
    av, sz = _av(ctx, 36, u=u); avw = av
    lp = LinearLayout.LayoutParams(sz, sz); lp.rightMargin = _dp(6); lp.gravity = Gravity.BOTTOM; row.addView(av, lp)
    attach = (int(mode) == 1)
    bub = LinearLayout(ctx); bub.setOrientation(1)
    bub.setBackground(_bg(_tc("key_chat_inBubble"), 12))
    if attach:
        bub.setPadding(0, 0, 0, _dp(4))
        try: bub.setClipChildren(True); bub.setClipToPadding(True)
        except: pass
    else:
        bub.setPadding(_dp(10), _dp(6), _dp(10), _dp(6))
    bub.setClickable(True); bub.setLongClickable(True); bub.setFocusable(True)
    name_w = 0
    if not attach:
        nv = _name_view(ctx, name, nc, u)
        has_b = bool(getattr(nv, "_dcp_has_badge", False))
        bub.addView(nv, LinearLayout.LayoutParams(MP if has_b else WC, WC))
        try:
            tv = None
            for i in range(nv.getChildCount()):
                ch = nv.getChildAt(i)
                if isinstance(ch, TextView): tv = ch; break
            if tv:
                try: name_w = int(tv.getPaint().measureText(str(tv.getText())))
                except:
                    tv.measure(View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED), View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
                    name_w = tv.getMeasuredWidth()
            if has_b: name_w += int(nv._dcp_badge_sz) + _dp(2)
            if name_w <= 0:
                nv.measure(View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED), View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
                name_w = nv.getMeasuredWidth()
        except: pass

    body = LinearLayout(ctx); body.setOrientation(1)
    raw_text = text or ""
    blocks = []; pos = 0
    for m in re.finditer(r"(?is)<blockquote\b[^>]*>(.*?)</blockquote>", str(raw_text)):
        if m.start() > pos: blocks.append((raw_text[pos:m.start()], False))
        blocks.append((m.group(1), True)); pos = m.end()
    if pos < len(raw_text): blocks.append((raw_text[pos:], False))
    
    last_tv = None; last_is_quote = False
    for txt, is_q in blocks:
        txt = re.sub(r"(?is)^(?:\s|<br\s*/?>)+|(?:\s|<br\s*/?>)+$", "", txt)
        if not txt: continue
        if is_q:
            qbox, tv = _quote_box(ctx, txt, 15, _tc("key_chat_messageTextIn"), nc)
            last_tv = tv; last_is_quote = True
            lp = LinearLayout.LayoutParams(MP, WC); lp.topMargin = _dp(4); lp.bottomMargin = _dp(4)
            body.addView(qbox, lp)
        else:
            tv = _rich(ctx, txt, 15, _tc("key_chat_messageTextIn"), _tc("key_chat_messageLinkIn"))
            last_tv = tv; last_is_quote = False
            body.addView(tv, LinearLayout.LayoutParams(WC, WC))

    meta = _meta(ctx, ts, False, _tc("key_chat_inTimeText"))
    pvs = []
    cover_ref = str(cover).strip() if (show_preview and cover) else None
    im = _media_attach(ctx, cover_ref, mb, bool(above)) if attach else _media_image(ctx, cover_ref, mb - _dp(20), nc, bg_eid)
    if im: pvs.append(im)
    if pvs:
        pad_x = _dp(10) if attach else 0
        if attach:
            try: body.setPadding(pad_x, _dp(2), pad_x, 0)
            except: pass
        def _add_meta_row():
            mr_l = LinearLayout(ctx); mr_l.setOrientation(0); mr_l.setGravity(Gravity.END | Gravity.CENTER_VERTICAL)
            mr_l.setPadding(pad_x, _dp(2), pad_x, 0) if attach else mr_l.setPadding(0, _dp(3), 0, 0)
            mr_l.addView(meta, LinearLayout.LayoutParams(WC, WC))
            bub.addView(mr_l, LinearLayout.LayoutParams(MP, WC))
        def _place_default_time():
            gap = _dp(6); inner = max(_dp(80), mb - _dp(20) - pad_x * 2)
            try:
                meta.measure(View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED), View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
                mww = meta.getMeasuredWidth()
            except: mww = _dp(48)
            tw = 0
            try:
                body.measure(View.MeasureSpec.makeMeasureSpec(inner, View.MeasureSpec.AT_MOST), View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
                tw = body.getMeasuredWidth()
            except: pass
            lc_cnt = 1; last = float(inner)
            try:
                if last_tv:
                    tx = last_tv.getText(); pt = last_tv.getPaint()
                    try: sl = StaticLayout.Builder.obtain(tx, 0, tx.length(), pt, inner).build()
                    except: sl = StaticLayout(tx, pt, inner, Layout.Alignment.ALIGN_NORMAL, 1.05, 0.0, False)
                    lc_cnt = sl.getLineCount()
                    if lc_cnt > 0: last = float(sl.getLineWidth(lc_cnt - 1))
            except: pass
            
            if last_is_quote:
                fits_side = False
                fits_last = False
            else:
                fits_side = lc_cnt <= 1 and tw + mww + gap <= inner and tw > 0 and pad_x == 0
                fits_last = last + mww + gap <= inner
                
            if fits_side:
                line = LinearLayout(ctx); line.setOrientation(0); line.setGravity(Gravity.BOTTOM | Gravity.START)
                line.addView(body, LinearLayout.LayoutParams(WC, WC))
                line.addView(View(ctx), LinearLayout.LayoutParams(0, 1, 1.0))
                mlp = LinearLayout.LayoutParams(WC, WC); mlp.gravity = Gravity.BOTTOM
                line.addView(meta, mlp)
                bub.addView(line, LinearLayout.LayoutParams(MP, WC))
            elif fits_last:
                area = FrameLayout(ctx)
                area.addView(body, FrameLayout.LayoutParams(MP, WC))
                mlp = FrameLayout.LayoutParams(WC, WC); mlp.gravity = Gravity.BOTTOM | Gravity.END
                if pad_x: mlp.setMargins(0, 0, pad_x, 0)
                area.addView(meta, mlp)
                bub.addView(area, LinearLayout.LayoutParams(MP, WC))
            else:
                bub.addView(body, LinearLayout.LayoutParams(MP, WC))
                _add_meta_row()
        if attach and above:
            for pv in pvs: bub.addView(pv, LinearLayout.LayoutParams(MP, WC))
            _place_default_time()
        elif attach and not above:
            bub.addView(body, LinearLayout.LayoutParams(MP, WC))
            for pv in pvs:
                wrap = FrameLayout(ctx)
                try: wrap.setClipToPadding(True); wrap.setClipChildren(True)
                except: pass
                wrap.addView(pv, FrameLayout.LayoutParams(MP, WC))
                mom = _meta_on_media(ctx, ts, False)
                mlp = FrameLayout.LayoutParams(WC, WC); mlp.gravity = Gravity.BOTTOM | Gravity.END
                mlp.setMargins(0, 0, _dp(6), _dp(6))
                wrap.addView(mom, mlp)
                lp = LinearLayout.LayoutParams(MP, WC); lp.topMargin = _dp(6)
                bub.addView(wrap, lp)
        elif above:
            for pv in pvs: bub.addView(pv, LinearLayout.LayoutParams(MP, WC))
            _place_default_time()
        else:
            bub.addView(body, LinearLayout.LayoutParams(MP, WC))
            for pv in pvs:
                lp = LinearLayout.LayoutParams(MP, WC); lp.topMargin = _dp(6); bub.addView(pv, lp)
            _add_meta_row()
        bw = mb
    else:
        gap = _dp(6); inner = max(_dp(80), mb - _dp(20))
        try:
            meta.measure(View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED), View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
            mw = meta.getMeasuredWidth()
        except: mw = _dp(48)
        tw = 0
        try:
            body.measure(View.MeasureSpec.makeMeasureSpec(inner, View.MeasureSpec.AT_MOST), View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
            tw = body.getMeasuredWidth()
        except: pass
        lc_cnt = 1; last = float(inner)
        try:
            if last_tv:
                tx = last_tv.getText(); pt = last_tv.getPaint()
                try: sl = StaticLayout.Builder.obtain(tx, 0, tx.length(), pt, inner).build()
                except: sl = StaticLayout(tx, pt, inner, Layout.Alignment.ALIGN_NORMAL, 1.05, 0.0, False)
                lc_cnt = sl.getLineCount()
                if lc_cnt > 0: last = float(sl.getLineWidth(lc_cnt - 1))
        except: pass
        
        if last_is_quote:
            fits_side = False
            fits_last = False
        else:
            fits_side = lc_cnt <= 1 and tw + mw + gap <= inner and tw > 0
            fits_last = last + mw + gap <= inner
            
        if fits_side: content_min = tw + mw + gap
        elif fits_last: content_min = max(tw, int(last) + mw + gap)
        else: content_min = max(tw, mw)
        try: pad_h = bub.getPaddingLeft() + bub.getPaddingRight()
        except: pad_h = _dp(20)
        prefer_bw = min(mb, max(_dp(56), name_w + pad_h, content_min + pad_h))
        if fits_side or (lc_cnt <= 1 and fits_last):
            line = LinearLayout(ctx); line.setOrientation(0); line.setGravity(Gravity.BOTTOM)
            line.addView(body, LinearLayout.LayoutParams(WC, WC))
            line.addView(View(ctx), LinearLayout.LayoutParams(0, 1, 1.0))
            mlp = LinearLayout.LayoutParams(WC, WC); mlp.gravity = Gravity.BOTTOM
            line.addView(meta, mlp)
            bub.addView(line, LinearLayout.LayoutParams(MP, WC))
        elif fits_last:
            area = FrameLayout(ctx)
            area.addView(body, FrameLayout.LayoutParams(MP, WC))
            mlp = FrameLayout.LayoutParams(WC, WC); mlp.gravity = Gravity.BOTTOM | Gravity.END
            area.addView(meta, mlp)
            bub.addView(area, LinearLayout.LayoutParams(MP, WC))
        else:
            bub.addView(body, LinearLayout.LayoutParams(MP, WC))
            mr_l = LinearLayout(ctx); mr_l.setOrientation(0); mr_l.setGravity(Gravity.END | Gravity.CENTER_VERTICAL)
            mr_l.addView(meta, LinearLayout.LayoutParams(WC, WC))
            bub.addView(mr_l, LinearLayout.LayoutParams(MP, WC))
        try:
            bub.measure(View.MeasureSpec.makeMeasureSpec(prefer_bw if prefer_bw > 0 else mb, View.MeasureSpec.AT_MOST), View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
            bw = min(mb, max(_dp(56), bub.getMeasuredWidth(), prefer_bw))
        except: bw = prefer_bw if prefer_bw > 0 else mb
    blp = LinearLayout.LayoutParams(bw, WC); blp.gravity = Gravity.BOTTOM
    row.addView(bub, blp)

    try:
        row.measure(View.MeasureSpec.makeMeasureSpec(_sw(ctx), View.MeasureSpec.AT_MOST), View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
        rh = max(_dp(1), row.getMeasuredHeight())
    except: rh = _dp(80)

    final_h = min(rh, _dp(650))
    sv = ScrollView(ctx)
    try:
        sv.setFillViewport(True)
        sv.setVerticalScrollBarEnabled(True)
        sv.setSmoothScrollingEnabled(True)
        sv.setOverScrollMode(View.OVER_SCROLL_IF_CONTENT_SCROLLS)
        sv.setNestedScrollingEnabled(False)
    except: pass
    try: sv.setOnTouchListener(_touch())
    except: pass

    sv.addView(row, ViewGroup.LayoutParams(MP, WC))
    root.addView(sv, FrameLayout.LayoutParams(MP, MP))

    try:
        rlp = root.getLayoutParams()
        if not rlp: rlp = ViewGroup.LayoutParams(MP, final_h)
        rlp.height = final_h
        root.setLayoutParams(rlp)
    except: pass

    try:
        wlp = wp.getLayoutParams()
        if wlp:
            wlp.width = MP; wlp.height = MP; wp.setLayoutParams(wlp)
    except: pass

    return root, rh, avw, bub, bw

def _cr(ctx, lv, acc, guid, rp):
    w = LinearLayout(ctx); w.setOrientation(1); w.setLayoutParams(ViewGroup.LayoutParams(MP, WC))
    h = FrameLayout(ctx); h.setTag("ph"); h.setLayoutParams(ViewGroup.LayoutParams(MP, WC))
    w.addView(h, LayoutHelper.createLinear(MP, WC))
    return w

def make_preview_factory(get_text_fn, get_cover_fn=None, get_opts_fn=None):
    def _bn(view, item, div, ad, lv):
        try:
            try:
                lp = view.getLayoutParams()
                if lp: lp.width = MP; view.setLayoutParams(lp)
            except: pass

            def _refresh():
                try:
                    h = None
                    for i in range(view.getChildCount()):
                        c = view.getChildAt(i)
                        if c.getTag() == "ph": h = c; break
                    if not h: return
                    h.removeAllViews()
                    ctx = view.getContext()
                    text = get_text_fn() or "" if get_text_fn else ""
                    cover_url = get_cover_fn() if get_cover_fn else None
                    mode = 0; above = False; show_preview = True
                    if get_opts_fn:
                        try:
                            o = get_opts_fn() or {}
                            mode = int(o.get("mode", 0) or 0)
                            above = bool(o.get("above", False))
                            if "show_preview" in o:
                                show_preview = bool(o.get("show_preview"))
                        except: pass
                    
                    built, rh, avw, bub, bw = _build(ctx, text, cover_url, mode=mode, above=above, show_preview=show_preview)
                    h.addView(built, FrameLayout.LayoutParams(MP, WC))
                    try:
                        hlp = h.getLayoutParams()
                        if hlp: hlp.height = WC; hlp.width = MP; h.setLayoutParams(hlp)
                    except: pass
                except: pass

            _refresh()

            class _ObsListener(dynamic_proxy(View.OnAttachStateChangeListener)):
                def onViewAttachedToWindow(self, v):
                    _PREVIEW_OBSERVERS.add(_refresh)
                    _refresh()
                def onViewDetachedFromWindow(self, v):
                    _PREVIEW_OBSERVERS.discard(_refresh)

            try:
                old_ls = getattr(view, "_dcp_listener", None)
                if old_ls:
                    try: view.removeOnAttachStateChangeListener(old_ls)
                    except: pass
                ls = _ObsListener()
                view._dcp_listener = ls
                view.addOnAttachStateChangeListener(ls)
                _PREVIEW_OBSERVERS.add(_refresh)
            except: pass
        except: pass
    return SimpleSettingFactory(_cr, _bn, is_clickable=False, is_shadow=False)
