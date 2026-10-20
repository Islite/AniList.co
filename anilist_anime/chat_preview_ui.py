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
from org.telegram.messenger import AndroidUtilities, UserConfig, UserObject, R, ImageReceiver, MessagesController, DialogObject
from org.telegram.ui.ActionBar import Theme
from org.telegram.ui.Components import AvatarDrawable, BackupImageView, AnimatedEmojiDrawable

MP, WC = -1, -2
_NK = ("key_avatar_nameInMessageRed", "key_avatar_nameInMessageOrange", "key_avatar_nameInMessageViolet", "key_avatar_nameInMessageGreen", "key_avatar_nameInMessageCyan", "key_avatar_nameInMessageBlue", "key_avatar_nameInMessagePink")
_RE_MD = re.compile(r"\[([^\]\r\n]+)\]\(([^)\s]+)\)")
_RE_TOK = re.compile(r"\*\*\*([^*]+)\*\*\*|\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`|(#[\w]+)|(https?://[^\s\[\]<>]+)", re.UNICODE)

_PREVIEW_OBSERVERS = set()
_PREVIEW_RUNNABLE = None

def notify_preview_update():
    global _PREVIEW_RUNNABLE
    def _do():
        global _PREVIEW_RUNNABLE
        _PREVIEW_RUNNABLE = None
        for obs in list(_PREVIEW_OBSERVERS):
            try:
                obs()
            except:
                pass

    try:
        if _PREVIEW_RUNNABLE is not None:
            AndroidUtilities.cancelRunOnUIThread(_PREVIEW_RUNNABLE)
    except:
        pass

    class _R(dynamic_proxy(__import__("java.lang", fromlist=["Runnable"]).Runnable)):
        def run(self):
            _do()

    _PREVIEW_RUNNABLE = _R()
    try:
        AndroidUtilities.runOnUIThread(_PREVIEW_RUNNABLE, 60)
    except:
        try:
            _do()
        except:
            pass

def _dp(v):
    return int(AndroidUtilities.dp(float(v)))

def _i(v):
    try:
        n = int(v) & 0xFFFFFFFF
        return n - 0x100000000 if n >= 0x80000000 else n
    except:
        return 0

def _tc(*a):
    for n in a:
        if not isinstance(n, str) or n.startswith("#"):
            continue
        try:
            k = getattr(Theme, n, None)
            if k is not None:
                c = _i(Theme.getColor(k))
                if c:
                    return c
        except:
            pass
    return 0

def _u16(s, i):
    if i <= 0:
        return 0
    return len(s[:i].encode("utf-16-le")) // 2 if i < len(s) else len(s.encode("utf-16-le")) // 2

def _nc(u):
    try:
        if not u:
            raise Exception()
        cid = UserObject.getColorId(u)
        if cid is not None:
            try:
                pc = MessagesController.getInstance(UserConfig.selectedAccount).peerColors.getColor(int(cid))
                if pc:
                    for m in ("getColor1", "getColor", "getAccentColor"):
                        v = getattr(pc, m, None)
                        if callable(v):
                            v = v()
                        if v:
                            c = _i(v)
                            return c if c & 0xFF000000 else _i(0xFF000000 | c)
            except:
                pass
            if 0 <= int(cid) <= 6:
                k = getattr(Theme, _NK[int(cid)], None)
                if k:
                    c = _i(Theme.getColor(k))
                    if c:
                        return c
        idx = AvatarDrawable.getColorIndex(int(u.id))
        if 0 <= idx < 7:
            k = getattr(Theme, _NK[idx], None)
            if k:
                c = _i(Theme.getColor(k))
                if c:
                    return c
    except:
        pass
    return _tc("key_chats_name", "key_avatar_nameInMessageCyan")

def _bg_eid(u):
    try:
        e = UserObject.getEmojiId(u)
        if e:
            return int(e)
    except:
        pass
    try:
        p = getattr(getattr(u, "emoji_status", None), "pattern_document_id", None)
        if p:
            return int(p)
    except:
        pass
    return 0

def _a(c, a):
    return _i((max(0, min(255, int(a))) << 24) | (_i(c) & 0xFFFFFF))

def _bg(c, r):
    d = GradientDrawable()
    d.setShape(0)
    d.setColor(_i(c))
    d.setCornerRadius(float(_dp(r)))
    return d

def _sw(ctx):
    for f in (lambda: int(AndroidUtilities.displaySize.x), lambda: int(ctx.getResources().getDisplayMetrics().widthPixels)):
        try:
            v = f()
            if 0 < v < 100000:
                return v
        except:
            pass
    return _dp(360)

def _wp():
    for f in (Theme.getCachedWallpaper, Theme.getCachedWallpaperNonBlocking):
        try:
            d = f()
            if d:
                return d
        except:
            pass
    return ColorDrawable(_tc("key_windowBackgroundGray", "key_chat_wallpaper") or 0x0F000000)

def _ic(ctx, ns, c, sd=12):
    sz = _dp(sd)
    iv = ImageView(ctx)
    for n in ns:
        try:
            d = getattr(Theme, n, None)
            if d and not isinstance(d, int):
                iv.setImageDrawable(d.mutate() if hasattr(d, "mutate") else d)
                break
        except:
            pass
        try:
            r = getattr(R.drawable, n, 0)
            if r:
                iv.setImageResource(int(r))
                break
        except:
            pass
    else:
        t = TextView(ctx)
        t.setText("•")
        t.setTextSize(TypedValue.COMPLEX_UNIT_SP, 11)
        t.setTextColor(_i(c))
        return t
    try:
        iv.setColorFilter(PorterDuffColorFilter(_i(c), PorterDuff.Mode.SRC_IN))
    except:
        pass
    iv.setScaleType(ImageView.ScaleType.FIT_CENTER)
    iv.setLayoutParams(LinearLayout.LayoutParams(sz, sz))
    return iv

def _html_to_md(s):
    if not s:
        return ""
    proc = str(s).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    proc = re.sub(r"(?is)<(?:b|strong)\b[^>]*>(.*?)</(?:b|strong)>", r"**\1**", proc)
    proc = re.sub(r"(?is)<(?:i|em)\b[^>]*>(.*?)</(?:i|em)>", r"*\1*", proc)
    proc = re.sub(r"(?is)<code\b[^>]*>(.*?)</code>", lambda m: "`" + re.sub(r"(?is)<[^>]+>", "", m.group(1)) + "`", proc)
    def _a(m):
        href = (m.group(1) or "").strip()
        txt = re.sub(r"(?is)<[^>]+>", "", m.group(2) or "").strip()
        return f"[{txt}]({href})" if href and txt and not bool(re.match(r"^[\u200b\ufeff\s]*$", txt)) else ""
    proc = re.sub(r'(?is)<a\b[^>]*?\bhref\s*=\s*["\']?([^"\'\s>]+)["\']?[^>]*>(.*?)</a>', _a, proc)
    return re.sub(r"(?is)<[^>]+>", "", proc)

def _rich(ctx, text, sp, c, lc):
    t = TextView(ctx)
    t.setTextSize(TypedValue.COMPLEX_UNIT_SP, float(sp))
    t.setTextColor(_i(c))
    t.setLineSpacing(0, 1.05)
    if not text:
        t.setText("")
        return t
    link_col = _i(lc) or _tc("key_chat_messageLinkIn", "key_chat_inReplyLine", "key_windowBackgroundWhiteBlueText") or 0xFF2A87D0
    s = _html_to_md(str(text))
    ch, pos = [], 0
    for m in _RE_MD.finditer(s):
        if m.start() > pos:
            ch.append((s[pos:m.start()], 0, None))
        ch.append((m.group(1), 1, m.group(2).strip()))
        pos = m.end()
    if pos < len(s):
        ch.append((s[pos:], 0, None))
    spans, out = [], []
    def em(p, k=0, e=None):
        if not p:
            return
        a = sum(len(x) for x in out)
        out.append(p)
        if k:
            spans.append((a, a + len(p), k, e))
    for p, k, e in ch:
        if k == 1:
            em(p, 1, e)
            continue
        q = 0
        for m in _RE_TOK.finditer(p):
            if m.start() > q:
                em(p[q:m.start()])
            g = m.groups()
            em(g[0] or g[1] or g[2] or g[3] or g[4] or (g[5].rstrip(".,;:!?)") if g[5] else ""), 5 if g[0] else 2 if g[1] else 6 if g[2] else 3 if g[3] else 4 if g[4] else 1 if g[5] else 0)
            q = m.end()
        if q < len(p):
            em(p[q:])
    plain = "".join(out)
    if not spans:
        t.setText(plain)
        return t
    try:
        ss = SpannableString(plain)
        for a, b, k, _ in spans:
            a, b = _u16(plain, a), _u16(plain, b)
            if a < 0 or b <= a:
                continue
            span_obj = StyleSpan(Typeface.BOLD_ITALIC) if k == 5 else StyleSpan(Typeface.BOLD) if k == 2 else StyleSpan(Typeface.ITALIC) if k == 6 else TypefaceSpan("monospace") if k == 3 else ForegroundColorSpan(link_col) if k in (1, 4) else None
            if span_obj:
                ss.setSpan(span_obj, a, b, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        t.setText(ss)
    except:
        t.setText(plain)
    return t

def _rwh(img):
    w = h = 0
    try:
        ir = img.getImageReceiver()
        if ir:
            try:
                bm = ir.getBitmap()
                if bm:
                    w, h = int(bm.getWidth()), int(bm.getHeight())
            except:
                pass
            if w <= 0 or h <= 0:
                try:
                    d = ir.getDrawable()
                    if d:
                        w, h = int(d.getIntrinsicWidth()), int(d.getIntrinsicHeight())
                except:
                    pass
    except:
        pass
    if w <= 0 or h <= 0:
        try:
            d = img.getDrawable()
            if d:
                w, h = int(d.getIntrinsicWidth()), int(d.getIntrinsicHeight())
        except:
            pass
    return w, h

def _asz(box, c, img, mw, mh, pt, pb, max_h=_dp(290)):
    def _do():
        try:
            mh_val = max(_dp(32), min(int(mh), int(max_h)))
            img.setLayoutParams(FrameLayout.LayoutParams(MP, mh_val))
            th = mh_val + pt + pb
            for v in (c, box):
                lp = v.getLayoutParams()
                if lp:
                    lp.height = th
                    v.setLayoutParams(lp)
            c.requestLayout()
            box.requestLayout()

            p = box
            root_view = None
            while p:
                try:
                    p.requestLayout()
                except:
                    pass
                if getattr(p, "getTag", lambda: None)() == "dcp_root":
                    root_view = p
                    break
                p = p.getParent()

            if root_view:
                body_wrap = None
                for i in range(root_view.getChildCount()):
                    ch = root_view.getChildAt(i)
                    if isinstance(ch, ScrollView) and ch.getChildCount() > 0:
                        body_wrap = ch.getChildAt(0)
                        break
                if body_wrap:
                    body_wrap.measure(
                        View.MeasureSpec.makeMeasureSpec(_sw(root_view.getContext()), View.MeasureSpec.AT_MOST),
                        View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED)
                    )
                    rh = max(_dp(48), body_wrap.getMeasuredHeight())
                    final_h = min(rh, _dp(650))
                    blp = body_wrap.getLayoutParams()
                    if blp:
                        blp.height = rh
                        body_wrap.setLayoutParams(blp)
                    rlp = root_view.getLayoutParams()
                    if rlp and rlp.height != final_h:
                        rlp.height = final_h
                        root_view.setLayoutParams(rlp)

                curr = root_view.getParent()
                while curr:
                    try:
                        clp = curr.getLayoutParams()
                        if clp and clp.height != WC and clp.height != MP:
                            clp.height = WC
                            curr.setLayoutParams(clp)
                        curr.requestLayout()
                    except:
                        pass
                    curr = curr.getParent()
        except:
            pass

    try:
        AndroidUtilities.runOnUIThread(_do)
    except:
        try:
            _do()
        except:
            pass

def _rc(box):
    try:
        m = getattr(box, "_dcp", None)
        if not m:
            return
        w, h = _rwh(m["img"])
        if w > 0 and h > 0:
            max_h = m.get("max_h", _dp(290))
            _asz(box, m["c"], m["img"], m["mw"], max(_dp(40), min(int(m["mw"] * h / w), max_h)), m["pt"], m["pb"], max_h)
        else:
            retries = m.get("retries", 0)
            if retries < 15:
                m["retries"] = retries + 1
                img = m.get("img")
                if img:
                    img.postDelayed(lambda: _rc(box), 100)
    except:
        pass

def _bsz(box, c, img, mw, pt, pb, max_h=_dp(290)):
    try:
        box._dcp = {"img": img, "c": c, "mw": mw, "pt": pt, "pb": pb, "max_h": max_h, "retries": 0}
        class _D(dynamic_proxy(ImageReceiver.ImageReceiverDelegate)):
            def didSetImage(self, ir, set, thumb, memCache):
                try:
                    AndroidUtilities.runOnUIThread(lambda: _rc(box))
                except:
                    _rc(box)
            def onAnimationReady(self, ir):
                try:
                    AndroidUtilities.runOnUIThread(lambda: _rc(box))
                except:
                    _rc(box)

        class _A(dynamic_proxy(View.OnAttachStateChangeListener)):
            def onViewAttachedToWindow(self, v):
                try:
                    AndroidUtilities.runOnUIThread(lambda: _rc(box))
                except:
                    pass
            def onViewDetachedFromWindow(self, v):
                pass

        ir = img.getImageReceiver()
        if ir:
            ir.setDelegate(_D())
        try:
            img.addOnAttachStateChangeListener(_A())
        except:
            pass
        AndroidUtilities.runOnUIThread(lambda: _rc(box))
    except:
        pass

def _emoji_iv(ctx, doc_id, sz, color, col=False):
    iv = ImageView(ctx)
    iv.setScaleType(ImageView.ScaleType.CENTER_INSIDE)
    try:
        ct = getattr(AnimatedEmojiDrawable, "CACHE_TYPE_MESSAGES", 0)
        d = AnimatedEmojiDrawable.make(UserConfig.selectedAccount, ct, int(doc_id))
        d.setColorFilter(PorterDuffColorFilter(_i(color), PorterDuff.Mode.SRC_IN))
        d.setBounds(0, 0, sz, sz)
        iv.setImageDrawable(d)
        if hasattr(d, "addView"):
            d.addView(iv)
        return iv
    except:
        pass
    try:
        swap = AnimatedEmojiDrawable.SwapAnimatedEmojiDrawable(iv, sz)
        swap.setCurrentAccount(UserConfig.selectedAccount)
        swap.set(int(doc_id), False)
        swap.setColor(int(color))
        iv.setImageDrawable(swap)
        if not col:
            swap.attach()
        return iv
    except:
        return None

def _make_bar(ctx, lc, brf, bg_eid):
    bar = FrameLayout(ctx)
    bb = GradientDrawable()
    bb.setShape(0)
    bb.setColor(_i(lc))
    bb.setCornerRadii([brf, brf, 0, 0, 0, 0, brf, brf])
    bar.setBackground(bb)
    if bg_eid:
        sz = _dp(12)
        iv = _emoji_iv(ctx, bg_eid, sz, _tc("key_windowBackgroundWhite", "key_actionBarDefaultIcon"), True)
        if iv:
            try:
                iv.setAlpha(0.35)
            except:
                pass
            lp = FrameLayout.LayoutParams(sz, sz)
            lp.gravity = Gravity.CENTER
            bar.addView(iv, lp)
    return bar

def _rbox(ctx, nc, br, mr, ld, pl, pt, pr, pb, img, ih, mw, bg_eid=0):
    pl, pt, pr, pb = _dp(pl), _dp(pt), _dp(pr), _dp(pb)
    lw = max(1, _dp(ld))
    brf = float(_dp(br))
    th = ih + pt + pb
    box = LinearLayout(ctx)
    box.setOrientation(0)
    box.setClickable(False)
    box.setFocusable(False)
    lc = _i(nc) if nc else _tc("key_chat_inReplyLine", "key_chat_messageLinkIn")
    bc = _a(lc, 0x28)
    bg = GradientDrawable()
    bg.setShape(0)
    bg.setColor(_i(bc))
    bg.setCornerRadii([0, 0, brf, brf, brf, brf, 0, 0])
    box.setBackground(bg)
    box.addView(_make_bar(ctx, lc, brf, bg_eid), LinearLayout.LayoutParams(lw, MP))
    ct = FrameLayout(ctx)
    ct.setPadding(pl, pt, pr, pb)
    ct.addView(img, FrameLayout.LayoutParams(MP, ih))
    box.addView(ct, LinearLayout.LayoutParams(0, th, 1.0))
    _bsz(box, ct, img, mw, pt, pb, _dp(290))
    return box

def _media_image(ctx, ref, mw, nc, bg_eid=0):
    try:
        if not ref or not str(ref).strip().lower().startswith(("http://", "https://")):
            return None
        pl, pt, pr, pb = 5, 4, 5, 4
        lw = _dp(3)
        aw = max(1, mw - _dp(pl + pr) - lw)
        img = BackupImageView(ctx)
        img.setAspectFit(False)
        img.setRoundRadius(_dp(4))
        ref = str(ref).strip()
        ih = max(_dp(64), min(int(aw * 1.4), _dp(290)))
        img.setImage(ref, "%d" % aw, None)
        return _rbox(ctx, nc, 5, 4, 3, pl, pt, pr, pb, img, ih, aw, bg_eid)
    except:
        return None

def _media_attach(ctx, ref, mw, above=False):
    try:
        if not ref or not str(ref).strip().lower().startswith(("http://", "https://")):
            return None
        ref = str(ref).strip()
        inset = _dp(2)
        top = _dp(4) if above else 0
        aw = max(1, int(mw) - inset * 2)
        max_h = _dp(290)
        ih = max(_dp(96), min(int(aw * 1.4), max_h))
        img = BackupImageView(ctx)
        img.setAspectFit(False)
        img.setRoundRadius(_dp(10))
        img.setImage(ref, "%d" % aw, None)
        box = LinearLayout(ctx)
        box.setOrientation(1)
        box.setPadding(inset, 0, inset, 0)
        ct = FrameLayout(ctx)
        if top:
            ct.setPadding(0, top, 0, 0)
        ct.addView(img, FrameLayout.LayoutParams(MP, ih))
        box.addView(ct, LinearLayout.LayoutParams(MP, ih + top))
        _bsz(box, ct, img, aw, top, 0, max_h)
        return box
    except:
        return None

def _meta_on_media(ctx, ts, ed):
    tc = _tc("key_chat_mediaTimeText", "key_chat_serviceText", "key_chat_inTimeText")
    bgc = _tc("key_chat_mediaTimeBackground", "key_chat_serviceBackground") or _a(0x000000, 0x99)
    m = _meta(ctx, ts, ed, tc)
    d = GradientDrawable()
    d.setShape(0)
    d.setColor(_i(bgc))
    d.setCornerRadius(float(_dp(8)))
    m.setBackground(d)
    m.setPadding(_dp(6), _dp(3), _dp(6), _dp(3))
    return m

def _cu():
    try:
        return UserConfig.getInstance(UserConfig.selectedAccount).getCurrentUser()
    except:
        return None

def _un(u):
    if not u:
        return "User"
    try:
        return str(UserObject.getFirstName(u) or getattr(u, "first_name", "") or "User")
    except:
        return "User"

def _av(ctx, sd, u=None):
    sz = _dp(sd)
    try:
        av = BackupImageView(ctx)
        av.setRoundRadius(sz // 2)
        d = AvatarDrawable()
        if u:
            try:
                d.setInfo(u)
            except:
                d.setInfo(UserConfig.selectedAccount, u)
            av.setForUserOrChat(u, d)
        else:
            d.setInfo(0, "")
            av.setImage(None, None, d)
        return av, sz
    except:
        a = TextView(ctx)
        a.setGravity(Gravity.CENTER)
        a.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13)
        a.setTextColor(_tc("key_windowBackgroundWhiteBlackText", "key_chats_name"))
        a.setTypeface(Typeface.DEFAULT_BOLD)
        d = GradientDrawable()
        d.setShape(1)
        d.setColor(_tc("key_chats_actionBackground", "key_avatar_backgroundInProfileBlue"))
        a.setBackground(d)
        return a, sz

def _meta(ctx, ts, ed, tc):
    m = LinearLayout(ctx)
    m.setOrientation(0)
    m.setGravity(Gravity.CENTER_VERTICAL)
    m.setPadding(_dp(4), 0, 0, 0)
    if ed:
        ic = _ic(ctx, ["pencil", "msg_edit", "group_edit_profile"], tc, 12)
        lp = LinearLayout.LayoutParams(_dp(12), _dp(12))
        lp.gravity = Gravity.CENTER_VERTICAL
        m.addView(ic, lp)
        m.addView(View(ctx), LinearLayout.LayoutParams(_dp(2), 1))
    tv = TextView(ctx)
    tv.setText(ts)
    tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12.1)
    tv.setTextColor(_i(tc))
    tv.setIncludeFontPadding(False)
    lp = LinearLayout.LayoutParams(WC, WC)
    lp.gravity = Gravity.CENTER_VERTICAL
    m.addView(tv, lp)
    return m

def _is_col(u):
    try:
        es = getattr(u, "emoji_status", None)
        if not es:
            return False
        cn = type(es).__name__
        return "Collectible" in cn or "collectible" in cn.lower() or getattr(es, "collectible_id", None) is not None or getattr(es, "pattern_document_id", None) is not None
    except:
        return False

def _name_view(ctx, name, nc, u):
    row = LinearLayout(ctx)
    row.setOrientation(0)
    row.setGravity(Gravity.CENTER_VERTICAL)
    tv = TextView(ctx)
    tv.setText(name)
    tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13)
    tv.setTextColor(_i(nc))
    tv.setTypeface(Typeface.DEFAULT_BOLD)
    tv.setSingleLine(True)
    tv.setEllipsize(TextUtils.TruncateAt.END)
    tv.setIncludeFontPadding(False)
    tv.setGravity(Gravity.CENTER_VERTICAL)
    doc_id = 0
    try:
        if u and getattr(u, "emoji_status", None):
            es = u.emoji_status
            doc_id = int(DialogObject.getEmojiStatusDocumentId(es) if hasattr(DialogObject, "getEmojiStatusDocumentId") else getattr(es, "document_id", 0) or 0)
    except:
        doc_id = 0
    badge = None
    sz = _dp(16)
    if doc_id:
        badge = _emoji_iv(ctx, doc_id, sz, nc, _is_col(u))
    elif u and getattr(u, "premium", False):
        for n in ("msg_premium_liststar", "premium_liststar", "star"):
            r = getattr(R.drawable, n, 0)
            if r:
                try:
                    d = ctx.getResources().getDrawable(int(r)).mutate()
                    d.setColorFilter(PorterDuffColorFilter(_i(nc), PorterDuff.Mode.MULTIPLY))
                    badge = ImageView(ctx)
                    badge.setScaleType(ImageView.ScaleType.CENTER_INSIDE)
                    badge.setImageDrawable(AnimatedEmojiDrawable.WrapSizeDrawable(d, sz, sz))
                    break
                except:
                    pass
    if badge:
        row.addView(tv, LinearLayout.LayoutParams(0, WC, 1.0))
        lp = LinearLayout.LayoutParams(sz, sz)
        lp.gravity = Gravity.CENTER_VERTICAL
        row.addView(badge, lp)
        def _place():
            try:
                lay = tv.getLayout()
                tw = float(lay.getLineWidth(0)) if lay and lay.getLineCount() > 0 else float(tv.getPaint().measureText(str(tv.getText())))
                vw = float(tv.getWidth())
                if vw > 0:
                    badge.setTranslationX(0 if tw + _dp(2) >= vw else tw + _dp(2) - vw)
            except:
                pass
        class _LL(dynamic_proxy(View.OnLayoutChangeListener)):
            def onLayoutChange(self, v, l, t, r, b, ol, ot, or_, ob):
                _place()
        row.addOnLayoutChangeListener(_LL())
        row._dcp_has_badge = True
        row._dcp_badge_sz = sz
    else:
        row.addView(tv, LinearLayout.LayoutParams(WC, WC))
        row._dcp_has_badge = False
        row._dcp_badge_sz = 0
    return row

def _touch():
    class _T(dynamic_proxy(View.OnTouchListener)):
        def onTouch(self, v, e):
            try:
                p = v.getParent()
                while p:
                    p.requestDisallowInterceptTouchEvent(e.getActionMasked() in (MotionEvent.ACTION_DOWN, MotionEvent.ACTION_MOVE))
                    p = p.getParent()
            except:
                pass
            return False
    return _T()

def _quote_box(ctx, text, sp, c, nc):
    box = LinearLayout(ctx)
    box.setOrientation(0)
    brf = float(_dp(3))
    lc = _i(nc) if nc else _tc("key_chat_inReplyLine", "key_chat_messageLinkIn")
    bg = GradientDrawable()
    bg.setShape(0)
    bg.setColor(_i(_a(lc, 0x1A)))
    bg.setCornerRadii([brf, brf, brf, brf, brf, brf, brf, brf])
    box.setBackground(bg)
    line = FrameLayout(ctx)
    lb = GradientDrawable()
    lb.setShape(0)
    lb.setColor(_i(lc))
    lb.setCornerRadii([brf, brf, 0, 0, 0, 0, brf, brf])
    line.setBackground(lb)
    box.addView(line, LinearLayout.LayoutParams(_dp(3), MP))
    content = FrameLayout(ctx)
    tv = _rich(ctx, text, sp, c, lc)
    tv.setPadding(_dp(6), _dp(4), _dp(16), _dp(4))
    content.addView(tv, FrameLayout.LayoutParams(WC, WC))
    qt = ImageView(ctx)
    qt.setScaleType(ImageView.ScaleType.CENTER_INSIDE)
    r = getattr(R.drawable, "mini_quote", 0)
    if r:
        try:
            qt.setImageResource(int(r))
            qt.setColorFilter(PorterDuffColorFilter(_i(lc), PorterDuff.Mode.SRC_IN))
        except:
            pass
    qlp = FrameLayout.LayoutParams(_dp(13), _dp(13))
    qlp.gravity = Gravity.TOP | Gravity.END
    qlp.setMargins(0, _dp(6), _dp(6), 0)
    content.addView(qt, qlp)
    box.addView(content, LinearLayout.LayoutParams(MP, WC))
    return box, tv

def _layout_meta_and_body(ctx, bub, body, meta, mb, pad_x, last_tv, last_is_quote):
    gap = _dp(6)
    inner = max(_dp(80), mb - _dp(20) - pad_x * 2)
    try:
        meta.measure(View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED), View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
        mww = meta.getMeasuredWidth()
    except:
        mww = _dp(48)
    try:
        body.measure(View.MeasureSpec.makeMeasureSpec(inner, View.MeasureSpec.AT_MOST), View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
        tw = body.getMeasuredWidth()
    except:
        tw = 0
    lc_cnt, last = 1, float(inner)
    if last_tv and not last_is_quote:
        try:
            tx = last_tv.getText()
            pt = last_tv.getPaint()
            try:
                sl = StaticLayout.Builder.obtain(tx, 0, tx.length(), pt, inner).build()
            except:
                sl = StaticLayout(tx, pt, inner, Layout.Alignment.ALIGN_NORMAL, 1.05, 0.0, False)
            lc_cnt = sl.getLineCount()
            if lc_cnt > 0:
                last = float(sl.getLineWidth(lc_cnt - 1))
        except:
            pass

    fits_side = not last_is_quote and lc_cnt <= 1 and tw + mww + gap <= inner and tw > 0 and pad_x == 0
    fits_last = not last_is_quote and last + mww + gap <= inner
    if fits_side:
        line = LinearLayout(ctx)
        line.setOrientation(0)
        line.setGravity(Gravity.BOTTOM | Gravity.START)
        line.addView(body, LinearLayout.LayoutParams(WC, WC))
        line.addView(View(ctx), LinearLayout.LayoutParams(0, 1, 1.0))
        mlp = LinearLayout.LayoutParams(WC, WC)
        mlp.gravity = Gravity.BOTTOM
        line.addView(meta, mlp)
        bub.addView(line, LinearLayout.LayoutParams(MP, WC))
    elif fits_last:
        area = FrameLayout(ctx)
        area.addView(body, FrameLayout.LayoutParams(MP, WC))
        mlp = FrameLayout.LayoutParams(WC, WC)
        mlp.gravity = Gravity.BOTTOM | Gravity.END
        if pad_x:
            mlp.setMargins(0, 0, pad_x, 0)
        area.addView(meta, mlp)
        bub.addView(area, LinearLayout.LayoutParams(MP, WC))
    else:
        bub.addView(body, LinearLayout.LayoutParams(MP, WC))
        mr = LinearLayout(ctx)
        mr.setOrientation(0)
        mr.setGravity(Gravity.END | Gravity.CENTER_VERTICAL)
        mr.setPadding(pad_x, _dp(2), pad_x, 0) if pad_x else mr.setPadding(0, _dp(3), 0, 0)
        mr.addView(meta, LinearLayout.LayoutParams(WC, WC))
        bub.addView(mr, LinearLayout.LayoutParams(MP, WC))

def _build(ctx, text, cover=None, mode=0, above=False, show_preview=True):
    u = _cu()
    name = _un(u)
    nc = _nc(u)
    bg_eid = _bg_eid(u)
    pad = _dp(8)
    scr = _sw(ctx)
    avm = max(_dp(140), scr - pad * 2 - _dp(42))
    aw = min(avm, max(_dp(160), int(avm * 0.92)))
    mb = max(_dp(100), min(avm, aw - _dp(56)))

    root = FrameLayout(ctx)
    root.setTag("dcp_root")
    wp = ImageView(ctx)
    wp.setTag("dcp_wp")
    wp.setScaleType(ImageView.ScaleType.CENTER_CROP)
    wp.setImageDrawable(_wp())
    root.addView(wp, FrameLayout.LayoutParams(MP, MP))

    av, sz = _av(ctx, 36, u=u)
    av_lp = FrameLayout.LayoutParams(sz, sz)
    av_lp.gravity = Gravity.BOTTOM | Gravity.START
    av_lp.leftMargin = pad
    av_lp.bottomMargin = pad
    root.addView(av, av_lp)

    content_area = FrameLayout(ctx)
    content_area.setPadding(pad + sz + _dp(6), pad, pad, pad)

    cover_ref = str(cover).strip() if (show_preview and cover and str(cover).strip() != "L") else None
    attach = (int(mode) == 1 and bool(cover_ref))

    bub = LinearLayout(ctx)
    bub.setOrientation(1)
    bub.setBackground(_bg(_tc("key_chat_inBubble") or 0xFFFFFFFF, 12))
    bub.setPadding(0, 0, 0, _dp(4)) if attach else bub.setPadding(_dp(10), _dp(6), _dp(10), _dp(6))
    bub.setClickable(True)
    bub.setFocusable(True)

    name_w = 0
    if not attach:
        nv = _name_view(ctx, name, nc, u)
        has_b = bool(getattr(nv, "_dcp_has_badge", False))
        bub.addView(nv, LinearLayout.LayoutParams(MP if has_b else WC, WC))
        try:
            tv = nv.getChildAt(0)
            name_w = int(tv.getPaint().measureText(str(tv.getText()))) + (int(nv._dcp_badge_sz) + _dp(2) if has_b else 0)
        except:
            name_w = 0

    body = LinearLayout(ctx)
    body.setOrientation(1)
    raw_text = str(text or "")
    blocks, pos = [], 0
    for m in re.finditer(r"(?is)<blockquote\b[^>]*>(.*?)</blockquote>", raw_text):
        if m.start() > pos:
            blocks.append((raw_text[pos:m.start()], False))
        blocks.append((m.group(1), True))
        pos = m.end()
    if pos < len(raw_text):
        blocks.append((raw_text[pos:], False))

    last_tv, last_is_quote = None, False
    for txt, is_q in blocks:
        txt = txt.strip("\r\n")
        if not txt:
            continue
        if is_q:
            qbox, tv = _quote_box(ctx, txt, 14, _tc("key_chat_messageTextIn"), nc)
            last_tv, last_is_quote = tv, True
            lp = LinearLayout.LayoutParams(MP, WC)
            lp.topMargin = lp.bottomMargin = _dp(4)
            body.addView(qbox, lp)
        else:
            tv = _rich(ctx, txt, 15, _tc("key_chat_messageTextIn"), _tc("key_chat_messageLinkIn"))
            last_tv, last_is_quote = tv, False
            body.addView(tv, LinearLayout.LayoutParams(WC, WC))

    meta = _meta(ctx, "12:00", False, _tc("key_chat_inTimeText"))
    pv = (_media_attach(ctx, cover_ref, mb, bool(above)) if attach else _media_image(ctx, cover_ref, mb - _dp(20), nc, bg_eid)) if cover_ref else None

    pad_x = _dp(10) if attach else 0
    if attach:
        body.setPadding(pad_x, _dp(2), pad_x, 0)

    if pv:
        if attach and not above:
            bub.addView(body, LinearLayout.LayoutParams(MP, WC))
            wrap = FrameLayout(ctx)
            wrap.addView(pv, FrameLayout.LayoutParams(MP, WC))
            mom = _meta_on_media(ctx, "12:00", False)
            mlp = FrameLayout.LayoutParams(WC, WC)
            mlp.gravity = Gravity.BOTTOM | Gravity.END
            mlp.setMargins(0, 0, _dp(6), _dp(6))
            wrap.addView(mom, mlp)
            lp = LinearLayout.LayoutParams(MP, WC)
            lp.topMargin = _dp(6)
            bub.addView(wrap, lp)
        else:
            if above or attach:
                bub.addView(pv, LinearLayout.LayoutParams(MP, WC))
                _layout_meta_and_body(ctx, bub, body, meta, mb, pad_x, last_tv, last_is_quote)
            else:
                bub.addView(body, LinearLayout.LayoutParams(MP, WC))
                lp = LinearLayout.LayoutParams(MP, WC)
                lp.topMargin = _dp(6)
                bub.addView(pv, lp)
                mr = LinearLayout(ctx)
                mr.setOrientation(0)
                mr.setGravity(Gravity.END | Gravity.CENTER_VERTICAL)
                mr.setPadding(0, _dp(3), 0, 0)
                mr.addView(meta, LinearLayout.LayoutParams(WC, WC))
                bub.addView(mr, LinearLayout.LayoutParams(MP, WC))
        bw = mb
    else:
        _layout_meta_and_body(ctx, bub, body, meta, mb, 0, last_tv, last_is_quote)
        try:
            bub.measure(View.MeasureSpec.makeMeasureSpec(mb, View.MeasureSpec.AT_MOST), View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
            bw = min(mb, max(_dp(56), bub.getMeasuredWidth(), name_w + _dp(20)))
        except:
            bw = mb

    clp = FrameLayout.LayoutParams(bw, WC)
    clp.gravity = Gravity.BOTTOM | Gravity.START
    content_area.addView(bub, clp)

    try:
        content_area.measure(View.MeasureSpec.makeMeasureSpec(_sw(ctx), View.MeasureSpec.AT_MOST), View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
        rh = max(_dp(48), content_area.getMeasuredHeight())
    except:
        rh = _dp(80)

    final_h = min(rh, _dp(650))
    sv = ScrollView(ctx)
    sv.setFillViewport(True)
    sv.setVerticalScrollBarEnabled(True)
    sv.setOverScrollMode(View.OVER_SCROLL_IF_CONTENT_SCROLLS)
    sv.setOnTouchListener(_touch())
    sv.addView(content_area, FrameLayout.LayoutParams(MP, WC))
    root.addView(sv, FrameLayout.LayoutParams(MP, MP))
    root.setLayoutParams(ViewGroup.LayoutParams(MP, final_h))

    return root, final_h, av, bub, bw

def _cr(ctx, lv, acc, guid, rp):
    w = LinearLayout(ctx)
    w.setOrientation(1)
    w.setLayoutParams(ViewGroup.LayoutParams(MP, WC))
    h = FrameLayout(ctx)
    h.setTag("ph")
    h.setLayoutParams(LinearLayout.LayoutParams(MP, WC))
    w.addView(h)
    return w

def make_preview_factory(get_text_fn, get_cover_fn=None, get_opts_fn=None):
    def _bn(view, item, div, ad, lv):
        try:
            def _refresh():
                try:
                    h = None
                    for i in range(view.getChildCount()):
                        c = view.getChildAt(i)
                        if c.getTag() == "ph":
                            h = c
                            break
                    if not h:
                        return
                    h.removeAllViews()
                    ctx = view.getContext()
                    text = get_text_fn() or "" if get_text_fn else ""
                    cover_url = get_cover_fn() if get_cover_fn else None
                    mode = 0
                    above = False
                    show_preview = True
                    if get_opts_fn:
                        try:
                            o = get_opts_fn() or {}
                            mode = int(o.get("mode", 0) or 0)
                            above = bool(o.get("above", False))
                            if "show_preview" in o:
                                show_preview = bool(o.get("show_preview"))
                        except:
                            pass

                    built, final_h, avw, bub, bw = _build(ctx, text, cover_url, mode=mode, above=above, show_preview=show_preview)
                    h.addView(built, FrameLayout.LayoutParams(MP, final_h))

                    hlp = h.getLayoutParams()
                    if hlp and hlp.height != WC:
                        hlp.height = WC
                        h.setLayoutParams(hlp)

                    vlp = view.getLayoutParams()
                    if vlp and vlp.height != WC:
                        vlp.height = WC
                        view.setLayoutParams(vlp)

                    view.requestLayout()
                    if lv:
                        try:
                            lv.requestLayout()
                        except:
                            pass
                except:
                    pass

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
                    view.removeOnAttachStateChangeListener(old_ls)
                ls = _ObsListener()
                view._dcp_listener = ls
                view.addOnAttachStateChangeListener(ls)
                _PREVIEW_OBSERVERS.add(_refresh)
            except:
                pass
        except:
            pass
    return SimpleSettingFactory(_cr, _bn, is_clickable=False, is_shadow=False)