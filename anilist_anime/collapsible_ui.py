
"""Сворачиваемые блоки настроек (на базе collapsible_settings_demo)."""
from android.widget import LinearLayout, TextView, FrameLayout, ImageView
from android.view import Gravity, View, ViewGroup
from android.graphics import PorterDuff, PorterDuffColorFilter
from android.graphics.drawable import GradientDrawable, LayerDrawable
from android.util import TypedValue
from android.text import TextUtils
from android.animation import ValueAnimator
from org.telegram.messenger import AndroidUtilities, LocaleController, R, ApplicationLoader
from org.telegram.ui.ActionBar import Theme
from android_utils import OnClickListener
from java import dynamic_proxy
from hook_utils import find_class
from androidx.core.content import ContextCompat
from ui.settings import SimpleSettingFactory

MP, WC, DUR = -1, -2, 220
CHILD_PAD = 54
_tc, _dr, _cl = {}, {}, [None, None]
AUL = find_class("android.animation.ValueAnimator$AnimatorUpdateListener")
TgSwitch = find_class("org.telegram.ui.Components.Switch")

def dp(v):
    return int(AndroidUtilities.dp(float(v)))

def rtl():
    return bool(LocaleController.isRTL)

def tc(*k):
    key = k[0] if k else ""
    if key in _tc:
        return _tc[key]
    for x in k:
        try:
            a = getattr(Theme, x, None)
            if a is not None:
                n = int(Theme.getColor(a)) & 0xFFFFFFFF
                v = n - 0x100000000 if n >= 0x80000000 else n
                if v:
                    _tc[key] = v
                    return v
        except Exception:
            pass
    _tc[key] = 0
    return 0

def dr(n, col=None):
    ck = (n, col)
    if ck in _dr:
        return _dr[ck]
    try:
        rid = getattr(R.drawable, n, 0)
        if not rid:
            _dr[ck] = None
            return None
        d = ContextCompat.getDrawable(ApplicationLoader.applicationContext, int(rid))
        if d is not None:
            d = d.mutate()
            if col:
                d.setColorFilter(PorterDuffColorFilter(int(col), PorterDuff.Mode.SRC_IN))
            _dr[ck] = d
            return d
    except Exception:
        pass
    _dr[ck] = None
    return None

def tv(ctx, t, sz, col, w=0):
    x = TextView(ctx)
    x.setText(t)
    x.setTextSize(TypedValue.COMPLEX_UNIT_DIP, sz)
    x.setTextColor(col)
    x.setSingleLine(True)
    try:
        x.setEllipsize(TextUtils.TruncateAt.END)
    except Exception:
        pass
    x.setLayoutParams(LinearLayout.LayoutParams(0 if w else WC, WC, float(w)))
    return x

def iv(ctx, sz, ml=0, mr=0):
    x = ImageView(ctx)
    try:
        x.setScaleType(ImageView.ScaleType.CENTER_INSIDE)
    except Exception:
        pass
    s = dp(sz)
    lp = LinearLayout.LayoutParams(s, s)
    lp.gravity = Gravity.CENTER_VERTICAL
    if ml:
        lp.leftMargin = dp(ml)
    if mr:
        lp.rightMargin = dp(mr)
    x.setLayoutParams(lp)
    return x

def sw(ctx, ck, cb):
    s = TgSwitch(ctx) if TgSwitch else None
    if s is None:
        return None, dp(42), dp(24)
    try:
        s.setColors(
            Theme.key_switchTrack, Theme.key_switchTrackChecked,
            Theme.key_windowBackgroundWhite, Theme.key_windowBackgroundWhite,
        )
    except Exception:
        pass
    try:
        s.setChecked(bool(ck), False)
    except Exception:
        try:
            s.setChecked(bool(ck))
        except Exception:
            pass
    st = [bool(ck)]

    def _o(v):
        try:
            st[0] = not st[0]
            try:
                s.setChecked(st[0], True)
            except Exception:
                s.setChecked(st[0])
            cb(st[0])
        except Exception:
            pass

    try:
        s.setOnClickListener(OnClickListener(_o))
    except Exception:
        pass
    return s, dp(42), dp(24)

def cl(on):
    i = 1 if on else 0
    _cl[i] = None
    bg = GradientDrawable()
    bg.setShape(1)
    if on:
        bg.setColor(int(tc(
            "key_windowBackgroundWhiteBlueText2", "key_windowBackgroundWhiteBlueText",
            "key_featuredStickers_addButton", "key_switchTrackChecked",
        )))
        ic = dr("msg_text_check", tc("key_featuredStickers_buttonText", "key_windowBackgroundWhite")) or dr("msg_text_check")
        if ic is not None:
            try:
                ld = LayerDrawable([bg, ic])
                pad = dp(4)
                ld.setLayerInset(1, pad, pad, pad, pad)
                _cl[i] = ld
                return ld
            except Exception:
                pass
        _cl[i] = bg
        return bg
    bg.setColor(0)
    g = tc("key_windowBackgroundWhiteGrayText", "key_windowBackgroundWhiteHintText", "key_dialogTextGray")
    if g:
        try:
            bg.setStroke(dp(1.5), int(g))
        except Exception:
            pass
    _cl[i] = bg
    return bg

def ac(iv, on):
    try:
        iv.animate().cancel()
        iv.setScaleX(0.65)
        iv.setScaleY(0.65)
        d = cl(on)
        try:
            d = d.mutate()
        except Exception:
            pass
        iv.setImageDrawable(d)
        iv.invalidate()
        iv.animate().scaleX(1.0).scaleY(1.0).setDuration(140).start()
    except Exception:
        try:
            iv.setImageDrawable(cl(on))
            iv.invalidate()
        except Exception:
            pass

def sh(v, h):
    try:
        lp = v.getLayoutParams()
        if lp is not None:
            lp.height = int(h)
            v.setLayoutParams(lp)
            v.requestLayout()
    except Exception:
        pass

def ah(box, ex):
    try:
        box.setClipChildren(True)
        box.setClipToPadding(True)
    except Exception:
        pass
    inn = box.getChildAt(0) if box.getChildCount() > 0 else None

    def fh():
        w = 0
        try:
            pr = box.getParent()
            if pr is not None:
                w = pr.getWidth()
        except Exception:
            pass
        if w <= 0:
            try:
                w = box.getWidth()
            except Exception:
                pass
        if w <= 0:
            w = dp(360)
        t = inn if inn is not None else box
        try:
            if inn is not None:
                p = inn.getLayoutParams()
                if p is not None:
                    p.height = WC
                    inn.setLayoutParams(p)
            t.measure(
                View.MeasureSpec.makeMeasureSpec(w, View.MeasureSpec.EXACTLY),
                View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED),
            )
            return max(int(t.getMeasuredHeight()), dp(48))
        except Exception:
            return dp(96)

    def li(h):
        if inn is None:
            return
        try:
            p = FrameLayout.LayoutParams(MP, int(h) if isinstance(h, (int, float)) and h > 0 else WC)
            p.gravity = Gravity.TOP
            inn.setLayoutParams(p)
        except Exception:
            pass

    ca = getattr(box, "_va", None)
    if ca is not None:
        try:
            ca.cancel()
        except Exception:
            pass
    sh0 = box.getHeight() if box.getHeight() > 0 else (0 if ex else fh())
    th = fh() if ex else 0
    if ex:
        box.setVisibility(View.VISIBLE)
        li(th)
    an = ValueAnimator.ofInt(int(sh0), int(th))
    an.setDuration(DUR)

    class HU(dynamic_proxy(AUL)):
        def onAnimationUpdate(self, a):
            val = int(a.getAnimatedValue())
            sh(box, val)
            if not ex and val <= 0:
                box.setVisibility(View.GONE)
                li(WC)
                box._va = None
            elif ex and val >= th:
                sh(box, WC)
                li(WC)
                box._va = None

    box._va = an
    an.addUpdateListener(HU())
    an.start()

def hdr(ctx, title, icn, vh, m, oe, om, ar):
    r = rtl()
    cell = FrameLayout(ctx)
    cell.setMinimumHeight(dp(50))
    try:
        cell.setBackground(Theme.getSelectorDrawable(True))
    except Exception:
        pass
    cell.setClickable(True)
    cell.setFocusable(True)
    s, sww, swh = sw(ctx, m, om)
    dw, gap, side = max(1, dp(0.5)), dp(12), dp(16)
    left = LinearLayout(ctx)
    left.setOrientation(0)
    left.setGravity(Gravity.CENTER_VERTICAL)
    try:
        left.setPadding(0, dp(10), 0, dp(10))
    except Exception:
        pass
    if icn:
        icon = iv(ctx, 24, mr=14)
        d = dr(icn, tc("key_windowBackgroundWhiteBlueText2", "key_windowBackgroundWhiteBlueText")) or dr(icn) or dr("msg_list")
        if d is not None:
            icon.setImageDrawable(d)
        left.addView(icon)
    left.addView(tv(ctx, title, 16, tc("key_windowBackgroundWhiteBlackText", "key_dialogTextBlack"), 1))
    left.addView(View(ctx), LinearLayout.LayoutParams(dp(6), 1))
    t2 = tv(ctx, vh[0], 13, tc("key_windowBackgroundWhiteGrayText", "key_dialogTextGray"))
    left.addView(t2)
    vh[1] = t2
    arw = iv(ctx, 16, ml=2)
    ad = dr("arrow_more", tc("key_windowBackgroundWhiteGrayText", "key_windowBackgroundWhiteHintText", "key_dialogTextGray")) or dr("arrow_more")
    if ad is not None:
        arw.setImageDrawable(ad)
    try:
        arw.setRotation(180.0)
    except Exception:
        pass
    left.addView(arw)
    ar[0] = arw
    flp = FrameLayout.LayoutParams(MP, WC)
    flp.gravity = Gravity.CENTER_VERTICAL | (Gravity.RIGHT if r else Gravity.LEFT)
    if r:
        flp.rightMargin = side
        flp.leftMargin = side + sww + gap + dw + gap
    else:
        flp.leftMargin = side
        flp.rightMargin = side + sww + gap + dw + gap
    cell.addView(left, flp)
    if s is not None:
        vd = View(ctx)
        try:
            vd.setBackgroundColor(int(tc("key_divider", "key_windowBackgroundGray") or 0x1A000000))
        except Exception:
            pass
        vlp = FrameLayout.LayoutParams(dw, dp(24))
        vlp.gravity = Gravity.CENTER_VERTICAL | (Gravity.LEFT if r else Gravity.RIGHT)
        vlp.leftMargin = side + sww + gap if r else 0
        vlp.rightMargin = 0 if r else side + sww + gap
        cell.addView(vd, vlp)
        slp = FrameLayout.LayoutParams(sww, swh)
        slp.gravity = Gravity.CENTER_VERTICAL | (Gravity.LEFT if r else Gravity.RIGHT)
        slp.leftMargin = side if r else 0
        slp.rightMargin = 0 if r else side
        cell.addView(s, slp)
    cell.setOnClickListener(OnClickListener(lambda v: oe()))
    return cell

def ch(ctx, title, on, cb):
    r = rtl()
    cell = LinearLayout(ctx)
    cell.setOrientation(0)
    cell.setGravity(Gravity.CENTER_VERTICAL)
    cell.setMinimumHeight(dp(48))
    try:
        cell.setBackground(Theme.getSelectorDrawable(True))
    except Exception:
        pass
    cell.setClickable(True)
    cell.setFocusable(True)
    cell.setPadding(dp(CHILD_PAD if not r else 16), 0, dp(16 if not r else CHILD_PAD), 0)
    mk = iv(ctx, 22)
    mk.setImageDrawable(cl(on))
    cell.addView(mk)
    cell.addView(View(ctx), LinearLayout.LayoutParams(dp(14), 1))
    cell.addView(tv(ctx, title, 16, tc("key_windowBackgroundWhiteBlackText", "key_dialogTextBlack"), 1))
    st = [bool(on)]

    def _o(v):
        st[0] = not st[0]
        ac(mk, st[0])
        cb(st[0])

    cell.setOnClickListener(OnClickListener(_o))
    return cell

_COLL_CACHE = {}

def make_collapsible(plugin, title, icn, master_key, items, hb=False, default_master=True):
    """items: list of (label, setting_key)"""
    def _gs(k, d=True):
        try:
            v = plugin.get_setting(k, d)
        except Exception:
            return d
        if v is None:
            return d
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return v != 0
        s = str(v).strip().lower()
        if s in ("0", "false", "no", "off", "null", "none", ""):
            return False
        if s in ("1", "true", "yes", "on"):
            return True
        return bool(v)

    def _ss(k, v, reload=False):
        try:
            plugin.set_setting(k, bool(v), reload_settings=bool(reload))
        except TypeError:
            try:
                plugin.set_setting(k, bool(v))
            except Exception:
                pass
        try:
            plugin.update_settings()
        except Exception:
            pass

    def bb(ctx, view):
        m = _gs(master_key, default_master)
        st = [_gs(k, True) for _, k in items]
        vh = ["%d/%d" % (sum(st), len(items)), None]
        ar = [None]
        ex = [False]

        def om(v):
            _ss(master_key, v, reload=True)

        def upd():
            if vh[1] is not None:
                try:
                    vh[1].setText("%d/%d" % (sum(st), len(items)))
                except Exception:
                    pass

        def mc(i, k):
            def _c(v):
                st[i] = v
                _ss(k, v, reload=True)
                upd()
            return _c

        inn = LinearLayout(ctx)
        inn.setOrientation(1)
        for i, (lab, kk) in enumerate(items):
            inn.addView(ch(ctx, lab, st[i], mc(i, kk)), LinearLayout.LayoutParams(MP, WC))
        box = FrameLayout(ctx)
        try:
            box.setClipChildren(True)
            box.setClipToPadding(True)
        except Exception:
            pass
        box.addView(inn, FrameLayout.LayoutParams(MP, WC))
        box.setLayoutParams(LinearLayout.LayoutParams(MP, 0))
        box.setVisibility(View.GONE)
        sep = View(ctx)
        try:
            sep.setBackgroundColor(int(Theme.dividerPaint.getColor()) if Theme.dividerPaint else int(tc("key_divider") or 0x1A000000))
        except Exception:
            pass
        stroke = int(Theme.dividerPaint.getStrokeWidth()) if (Theme.dividerPaint and Theme.dividerPaint.getStrokeWidth() > 0) else max(1, dp(0.33))
        sl = LinearLayout.LayoutParams(MP, stroke)
        sl.leftMargin = dp(54 if icn else 16)
        sl.rightMargin = 0
        sep.setVisibility(View.VISIBLE if hb else View.GONE)

        def oe(_=None):
            ex[0] = not ex[0]
            if ar[0] is not None:
                try:
                    ar[0].animate().cancel()
                    ar[0].animate().rotation(0.0 if ex[0] else 180.0).setDuration(DUR).start()
                except Exception:
                    pass
            if not hb:
                sep.setVisibility(View.VISIBLE if ex[0] else View.GONE)
            ah(box, ex[0])

        view.addView(hdr(ctx, title, icn, vh, m, oe, om, ar), LinearLayout.LayoutParams(MP, WC))
        view.addView(sep, sl)
        view.addView(box)

    def cr(ctx, lv, acc, guid, rp):
        root = LinearLayout(ctx)
        root.setOrientation(1)
        root.setLayoutParams(ViewGroup.LayoutParams(MP, WC))
        try:
            bb(ctx, root)
        except Exception:
            pass
        return root

    def bn(view, item, div, ad, lv):
        try:
            if view.getChildCount() == 0:
                bb(view.getContext(), view)
        except Exception:
            pass

    ck = (title, master_key, tuple((a, b) for a, b in items), hb)
    if ck in _COLL_CACHE:
        return _COLL_CACHE[ck]
    fac = SimpleSettingFactory(cr, bn, is_clickable=False, is_shadow=False)
    _COLL_CACHE[ck] = fac
    return fac

PICK = [
    ("Поля", "msg_list", "key_chats_archiveBackground", "tag_icon_3"),
    ("#", "caption_show", "key_chats_archiveBackground", "caption_show"),
    ("_", "caption_limit", "key_chats_archiveBackground", "caption_limit"),
    (",", "msg_delete", "key_dialogSwipeRemove", "swipe_delete"),
    ("Ничего", "msg_block", "key_chats_archivePinBackground", "swipe_disabled"),
]
TgPicker = find_class("org.telegram.ui.Components.NumberPicker")
NpListener = find_class("org.telegram.ui.Components.NumberPicker$OnValueChangeListener")
RLottieDrawable = find_class("org.telegram.ui.Components.RLottieDrawable")
RLottieImageView = find_class("org.telegram.ui.Components.RLottieImageView")
_lc = {}
try:
    from androidx.core.graphics import ColorUtils
except Exception:
    ColorUtils = None

def _al(col, a):
    try:
        n = int(col) & 0x00FFFFFF
        r = ((int(a) & 255) << 24) | n
        return r - 0x100000000 if n >= 0x80000000 else r
    except Exception:
        return col

def gd(col, r, sh=0):
    g = GradientDrawable()
    try:
        g.setShape(sh)
        g.setCornerRadius(float(r))
        g.setColor(int(col))
    except Exception:
        pass
    return g

def sf(k):
    a = tc(k, "key_chats_archiveBackground", "key_featuredStickers_addButton") or 0xFF66A9E0
    w = tc("key_windowBackgroundWhite") or 0xFF1C1C1C
    if ColorUtils is not None:
        try:
            return int(ColorUtils.blendARGB(int(w), int(a), 0.9))
        except Exception:
            pass
    return int(a)

def rid(n):
    try:
        return int(getattr(getattr(R, "raw", None), n, 0) or 0)
    except Exception:
        return 0

def si(i):
    try:
        _, ic, _, _ = PICK[int(i)]
        col = tc("key_chats_archiveIcon", "key_windowBackgroundWhite", "key_featuredStickers_buttonText")
        return dr(ic, col) or dr("msg_block", col) or dr(ic)
    except Exception:
        return None

def lt(i):
    i = int(i)
    if i in _lc:
        return _lc[i]
    if RLottieDrawable is None:
        _lc[i] = None
        return None
    try:
        _, _, ck, raw = PICK[i]
        r = rid(raw)
        if not r:
            _lc[i] = None
            return None
        d = RLottieDrawable(int(r), str(int(r)), dp(28), dp(28), True, None)
        col = tc("key_chats_archiveIcon", "key_windowBackgroundWhite", "key_featuredStickers_buttonText")
        if col:
            try:
                d.setColorFilter(PorterDuffColorFilter(int(col), PorterDuff.Mode.SRC_IN))
            except Exception:
                pass
        _lc[i] = d
        return d
    except Exception:
        _lc[i] = None
        return None

def pi(iv, idx, play):
    d = lt(idx)
    if d is not None:
        try:
            if play:
                try:
                    d.setCurrentFrame(0, False)
                except Exception:
                    d.setCurrentFrame(0)
            else:
                try:
                    d.setCurrentFrame(int(d.getFramesCount()) - 1)
                except Exception:
                    pass
            try:
                iv.setAnimation(d)
            except Exception:
                iv.setImageDrawable(d)
            if play:
                try:
                    iv.playAnimation()
                except Exception:
                    try:
                        d.start()
                    except Exception:
                        pass
            return
        except Exception:
            pass
    s = si(idx)
    if s is not None:
        try:
            iv.setImageDrawable(s)
        except Exception:
            pass

def vs(v, show, an):
    try:
        AndroidUtilities.updateViewVisibilityAnimated(v, bool(show), 0.5, bool(an))
        return
    except Exception:
        pass
    try:
        v.animate().setListener(None).cancel()
        if show:
            v.setVisibility(View.VISIBLE)
            if an:
                v.setAlpha(0.0)
                v.setScaleX(0.5)
                v.setScaleY(0.5)
                v.animate().alpha(1.0).scaleX(1.0).scaleY(1.0).setDuration(150).start()
            else:
                v.setAlpha(1.0)
                v.setScaleX(1.0)
                v.setScaleY(1.0)
        else:
            if an:
                v.animate().alpha(0.0).scaleX(0.5).scaleY(0.5).setDuration(150).start()
            else:
                v.setAlpha(0.0)
                v.setScaleX(0.5)
                v.setScaleY(0.5)
                v.setVisibility(View.INVISIBLE)
    except Exception:
        try:
            v.setVisibility(View.VISIBLE if show else View.INVISIBLE)
        except Exception:
            pass

def aco(outer, st, tg):
    ca = st.get("va_col")
    if ca is not None:
        try:
            ca.cancel()
        except Exception:
            pass
    src = st.get("color", tg)
    if (not ColorUtils) or src == tg:
        try:
            outer.setBackground(gd(tg, dp(6)))
        except Exception:
            pass
        st["color"] = tg
        return
    an = ValueAnimator.ofArgb(int(src), int(tg))
    an.setDuration(100)

    class CU(dynamic_proxy(AUL)):
        def onAnimationUpdate(self, a):
            col = int(a.getAnimatedValue())
            try:
                outer.setBackground(gd(col, dp(6)))
            except Exception:
                pass
            st["color"] = col

    st["va_col"] = an
    an.addUpdateListener(CU())
    an.start()

def siw(st, an):
    nv = int(st.get("want", st.get("idx", 0)))
    views = st.get("views") or []
    if len(views) < 2:
        return
    host = st.get("host")
    prev = st.pop("_siw_run", None)
    if prev is not None and host is not None:
        try:
            host.removeCallbacks(prev)
        except Exception:
            pass
    st["busy"] = False
    st["_pending_siw"] = False
    cur = int(st.get("ii", 0)) % 2
    if nv == int(st.get("idx", -1)):
        try:
            for i, v in enumerate(views):
                try:
                    v.animate().cancel()
                except Exception:
                    pass
                if i == cur:
                    pi(v, nv, False)
                    v.setAlpha(1.0)
                    v.setScaleX(1.0)
                    v.setScaleY(1.0)
                    v.setVisibility(View.VISIBLE)
                else:
                    v.setAlpha(0.0)
                    v.setVisibility(View.INVISIBLE)
        except Exception:
            pass
        return
    nxt = (cur + 1) % 2
    try:
        views[cur].animate().cancel()
        views[nxt].animate().cancel()
    except Exception:
        pass
    try:
        views[cur].setAlpha(0.0)
        views[cur].setScaleX(0.5)
        views[cur].setScaleY(0.5)
        views[cur].setVisibility(View.INVISIBLE)
    except Exception:
        pass
    pi(views[nxt], nv, bool(an))
    try:
        views[nxt].setVisibility(View.VISIBLE)
        if an:
            views[nxt].setAlpha(0.0)
            views[nxt].setScaleX(0.5)
            views[nxt].setScaleY(0.5)
            views[nxt].animate().alpha(1.0).scaleX(1.0).scaleY(1.0).setDuration(120).start()
        else:
            views[nxt].setAlpha(1.0)
            views[nxt].setScaleX(1.0)
            views[nxt].setScaleY(1.0)
    except Exception:
        try:
            vs(views[nxt], True, False)
        except Exception:
            pass
    st["ii"] = nxt
    st["idx"] = nv

    class U(dynamic_proxy(find_class("java.lang.Runnable"))):
        def run(self):
            try:
                cur2 = int(st.get("ii", 0)) % 2
                want = int(st.get("want", st.get("idx", 0)))
                for i, v in enumerate(views):
                    try:
                        v.animate().cancel()
                    except Exception:
                        pass
                    if i == cur2:
                        pi(v, want, False)
                        v.setAlpha(1.0)
                        v.setScaleX(1.0)
                        v.setScaleY(1.0)
                        v.setVisibility(View.VISIBLE)
                    else:
                        v.setAlpha(0.0)
                        v.setVisibility(View.INVISIBLE)
            except Exception:
                pass

    try:
        r = U()
        st["_siw_run"] = r
        if host is not None:
            host.postDelayed(r, 140)
        else:
            AndroidUtilities.runOnUIThread(r, 140)
    except Exception:
        pass


def ap(outer, st, idx, an):
    try:
        n = len(PICK)
        i = int(idx) % n
        if i < 0:
            i += n
        st["want"] = i
        _, _, ck, _ = PICK[i]
        tg = sf(ck)
        if an:
            aco(outer, st, tg)
        else:
            try:
                outer.setBackground(gd(tg, dp(6)))
            except Exception:
                pass
            st["color"] = tg
        views = st.get("views") or []
        if not an and views:
            pi(views[int(st.get("ii", 0)) % 2], i, False)
            st["idx"] = i
        else:
            siw(st, True)
    except Exception:
        pass

def mm(ctx):
    iv = RLottieImageView(ctx) if RLottieImageView is not None else ImageView(ctx)
    if RLottieImageView is None:
        try:
            iv.setScaleType(ImageView.ScaleType.CENTER_INSIDE)
        except Exception:
            pass
    mlp = FrameLayout.LayoutParams(dp(28), dp(28))
    mlp.gravity = Gravity.CENTER_VERTICAL | Gravity.RIGHT
    mlp.rightMargin = dp(184)
    iv.setLayoutParams(mlp)
    try:
        iv.setAlpha(0.0)
        iv.setScaleX(0.5)
        iv.setScaleY(0.5)
        iv.setVisibility(View.INVISIBLE)
    except Exception:
        pass
    return iv

def pl(ctx, rm, yo):
    v = View(ctx)
    v.setBackground(gd(_al(tc("key_switchTrack") or 0xFF888888, 57), dp(2.5)))
    lp = FrameLayout.LayoutParams(MP, dp(5))
    lp.gravity = Gravity.CENTER_VERTICAL
    lp.leftMargin = dp(23)
    lp.rightMargin = dp(rm)
    lp.topMargin = dp(yo)
    v.setLayoutParams(lp)
    return v

def pd(ctx, top):
    v = View(ctx)
    col = tc("key_radioBackgroundChecked", "key_featuredStickers_addButton", "key_windowBackgroundWhiteBlueText")
    v.setBackground(gd(int(col) if col else 0xFF64B5F6, dp(1)))
    lp = FrameLayout.LayoutParams(dp(128), dp(2))
    lp.gravity = Gravity.RIGHT | (Gravity.TOP if top else Gravity.BOTTOM)
    lp.rightMargin = dp(23)
    if top:
        lp.topMargin = dp(31)
    else:
        lp.bottomMargin = dp(31)
    v.setLayoutParams(lp)
    return v

def make_mode_picker(plugin, on_mode=None):
    """Vertical NumberPicker: Поля / # / _ / ,"""

    def _gs(k, d=0):
        try:
            return int(plugin.get_setting(k, d))
        except Exception:
            return d

    def _ss(k, v, reload=False):
        try:
            plugin.set_setting(k, int(v), reload_settings=reload)
        except TypeError:
            try:
                plugin.set_setting(k, int(v))
            except Exception:
                pass
        if on_mode:
            try:
                on_mode(int(v))
            except Exception:
                pass

    def bp(ctx, view):
        from android.view import HapticFeedbackConstants
        view.setOrientation(1)
        title = TextView(ctx)
        title.setText("Режим отображения")
        title.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 16)
        title.setTextColor(tc("key_windowBackgroundWhiteBlackText", "key_dialogTextBlack"))
        try:
            title.setSingleLine(True)
            title.setEllipsize(TextUtils.TruncateAt.END)
        except Exception:
            pass
        title.setPadding(dp(21), dp(16), dp(21), dp(2))
        view.addView(title, LinearLayout.LayoutParams(MP, WC))
        cell = FrameLayout(ctx)
        cell.setLayoutParams(LinearLayout.LayoutParams(MP, dp(102)))
        cell.setMinimumHeight(dp(102))
        try:
            cell.setClipChildren(False)
        except Exception:
            pass
        outer = FrameLayout(ctx)
        olp = FrameLayout.LayoutParams(MP, dp(48))
        olp.gravity = Gravity.CENTER_VERTICAL
        olp.leftMargin, olp.rightMargin = dp(21), dp(169)
        outer.setLayoutParams(olp)
        try:
            outer.setClipChildren(True)
            outer.setClipToPadding(True)
        except Exception:
            pass
        inner = FrameLayout(ctx)
        try:
            inner.setClipChildren(True)
            inner.setClipToPadding(True)
        except Exception:
            pass
        inner.setBackground(gd(tc("key_windowBackgroundWhite") or 0xFF1C1C1C, dp(6)))
        sc = tc("key_switchTrack")
        try:
            inner.getBackground().setStroke(max(1, dp(1)), int(_al(sc, 31) if sc else 0x1F000000))
        except Exception:
            pass
        ilp = FrameLayout.LayoutParams(MP, MP)
        ilp.rightMargin = dp(58)
        circ = View(ctx)
        circ.setBackground(gd(_al(tc("key_switchTrack") or 0xFF888888, 60), dp(15), 1))
        clp = FrameLayout.LayoutParams(dp(30), dp(30))
        clp.gravity = Gravity.CENTER_VERTICAL | Gravity.LEFT
        clp.leftMargin = -dp(15)
        inner.addView(circ, clp)
        inner.addView(pl(ctx, 68, -6))
        inner.addView(pl(ctx, 23, 6))
        outer.addView(inner, ilp)
        vdiv = View(ctx)
        try:
            vdiv.setBackgroundColor(int(tc("key_divider", "key_windowBackgroundGray") or 0x1A000000))
        except Exception:
            pass
        vdlp = FrameLayout.LayoutParams(max(1, dp(0.5)), dp(36))
        vdlp.gravity = Gravity.CENTER_VERTICAL | Gravity.RIGHT
        vdlp.rightMargin = dp(58)
        outer.addView(vdiv, vdlp)
        cell.addView(outer)
        m0, m1 = mm(ctx), mm(ctx)
        cell.addView(m0)
        cell.addView(m1)
        n = len(PICK)
        labels = [t for t, _, _, _ in PICK]
        cur = 0
        try:
            cur = int(_gs("display_mode_pick", 0))
        except Exception:
            cur = 0
        if cur < 0 or cur >= n:
            cur = 0
        st = {"idx": -1, "want": cur, "ii": 0, "busy": False, "views": [m0, m1], "host": cell, "color": 0}
        try:
            m0.setVisibility(View.VISIBLE)
            m0.setAlpha(1.0)
            m0.setScaleX(1.0)
            m0.setScaleY(1.0)
        except Exception:
            pass
        pk = None
        try:
            pk = TgPicker(ctx, 13)
        except Exception:
            try:
                pk = TgPicker(ctx)
            except Exception:
                pk = None
        if pk is not None:
            try:
                pk.setMinValue(0)
                pk.setDrawDividers(False)
                pk.setMaxValue(n - 1)
                pk.setAllItemsCount(n)
                pk.setWrapSelectorWheel(True)
                pk.setDisplayedValues(labels)
                pk.setTextColor(int(tc("key_windowBackgroundWhiteBlackText", "key_dialogTextBlack")))
                pk.setValue(int(cur))
                pk.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO)
                pk.setDescendantFocusability(393216)
            except Exception:
                pass

            def ov(p, o, nv):
                try:
                    old = int(_gs("display_mode_pick", 0))
                    nv = int(nv)
                    ap(outer, st, nv, True)
                    if old != nv:
                        _ss("display_mode_pick", nv, False)
                        try:
                            host = st.get("host")
                            prev = st.get("_rl_run")
                            class _R(dynamic_proxy(find_class("java.lang.Runnable"))):
                                def run(self):
                                    try:
                                        cur2 = int(_gs("display_mode_pick", 0))
                                        if cur2 == nv:
                                            try:
                                                plugin.set_setting("display_mode_pick", int(nv), reload_settings=True)
                                            except TypeError:
                                                plugin.set_setting("display_mode_pick", int(nv))
                                    except Exception:
                                        pass
                            r = _R()
                            st["_rl_run"] = r
                            if host is not None:
                                if prev is not None:
                                    try:
                                        host.removeCallbacks(prev)
                                    except Exception:
                                        pass
                                host.postDelayed(r, 500)
                            else:
                                AndroidUtilities.runOnUIThread(r, 500)
                        except Exception:
                            try:
                                plugin.set_setting("display_mode_pick", int(nv), reload_settings=True)
                            except Exception:
                                pass
                    else:
                        _ss("display_mode_pick", nv, False)
                    try:
                        p.performHapticFeedback(
                            HapticFeedbackConstants.KEYBOARD_TAP,
                            HapticFeedbackConstants.FLAG_IGNORE_GLOBAL_SETTING,
                        )
                    except Exception:
                        try:
                            p.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
                        except Exception:
                            pass
                except Exception:
                    pass

            try:
                class L(dynamic_proxy(NpListener)):
                    def onValueChange(self, p, o, nv):
                        ov(p, o, nv)

                pk.setOnValueChangedListener(L())
            except Exception:
                pass
            plp = FrameLayout.LayoutParams(dp(132), MP)
            plp.gravity = Gravity.RIGHT
            plp.leftMargin = plp.rightMargin = dp(21)
            cell.addView(pk, plp)
            cell.addView(pd(ctx, True))
            cell.addView(pd(ctx, False))
        else:
            fb = TextView(ctx)
            fb.setText(labels[cur])
            fb.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 13)
            fb.setTextColor(tc("key_windowBackgroundWhiteBlackText", "key_dialogTextBlack"))
            fb.setGravity(Gravity.CENTER)
            flp = FrameLayout.LayoutParams(dp(132), MP)
            flp.gravity = Gravity.RIGHT
            flp.rightMargin = dp(21)
            cell.addView(fb, flp)
        ap(outer, st, cur, False)
        view.addView(cell)

    def cr(ctx, lv, acc, guid, rp):
        root = LinearLayout(ctx)
        root.setOrientation(1)
        root.setLayoutParams(ViewGroup.LayoutParams(MP, WC))
        try:
            bp(ctx, root)
        except Exception:
            pass
        return root

    def bn(view, item, div, ad, lv):
        try:
            if view.getChildCount() == 0:
                bp(view.getContext(), view)
        except Exception:
            pass

    return SimpleSettingFactory(cr, bn, is_clickable=False, is_shadow=False)

def _sep_items(mapping, scope, kind=None):
    """(label, setting_key) for separators of scope genres|tags."""
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

def stub_mode_rows(plugin, mapping, idx):
    """Rows under the picker for current mode. Separators auto from mapping."""
    from ui.settings import Custom, Divider, Header, Selector, Switch
    idx = int(idx) if idx is not None else 0
    has = bool(getattr(mapping, "separator_keys", None))
    if idx == 0:
        main = [
            ("Аниме", "show_anime_label"),
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
            ("Источник", "show_source"),
            ("Студии", "show_studios"),
        ]
        genres = [("Основные", "show_genres_main")]
        if has:
            genres.extend(_sep_items(mapping, "genres"))
        genres.append(("Прочие", "show_genres_unlisted"))
        tags = [("Основные", "show_tags_main")]
        if has:
            tags.extend(_sep_items(mapping, "tags"))
        tags.append(("Прочие", "show_tags_unlisted"))
        rows = [
            Custom(factory=make_collapsible(plugin, "Основные", None, "coll_fields_main", main, True).instance.java),
            Custom(factory=make_collapsible(plugin, "Жанры", None, "show_genres", genres).instance.java),
            Custom(factory=make_collapsible(plugin, "Теги", None, "show_tags", tags).instance.java),
            Divider(),
            Switch(key="show_link_in_full", text="Ссылка AniList", default=True, on_change=lambda _: plugin.update_settings(), link_alias="show_link_in_full"),
            Switch(key="show_shikimori_link", text="Ссылка Shikimori", default=True, on_change=lambda _: plugin.update_settings(), link_alias="show_shikimori_link"),
            Divider(),
            Switch(key="show_description", text="Описание", default=False, on_change=lambda _: plugin.update_settings(), link_alias="show_description"),
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
        return rows

    if idx == 1:  # #
        main = [
            ("Аниме", "show_hash_anime"),
            ("Страна", "hash_country"),
            ("Формат", "hash_format"),
            ("Аудитория", "hash_demographic"),
            ("Студии", "hash_studios"),
            ("Источник", "hash_source"),
            ("Статус", "hash_status"),
        ]
        genres = [("Основные", "hash_genres_main")]
        if has:
            genres.extend(_sep_items(mapping, "genres", "hash"))
        genres.append(("Прочие", "hash_genres_unlisted"))
        tags = [("Основные", "hash_tags_main")]
        if has:
            tags.extend(_sep_items(mapping, "tags", "hash"))
        tags.append(("Прочие", "hash_tags_unlisted"))
        return [
            Custom(factory=make_collapsible(plugin, "Основные", None, "coll_hash_main", main, True).instance.java),
            Custom(factory=make_collapsible(plugin, "Жанры", None, "hash_genres", genres).instance.java),
            Custom(factory=make_collapsible(plugin, "Теги", None, "hash_tags", tags).instance.java),
        ]

    if idx == 2:  # _
        main = [
            ("Формат", "underscore_format"),
            ("Студии", "underscore_studios"),
            ("Источник", "underscore_source"),
            ("Статус", "underscore_status"),
        ]
        genres = [("Основные", "underscore_genres_main")]
        if has:
            genres.extend(_sep_items(mapping, "genres", "under"))
        genres.append(("Прочие", "underscore_genres_unlisted"))
        tags = [("Основные", "underscore_tags_main")]
        if has:
            tags.extend(_sep_items(mapping, "tags", "under"))
        tags.append(("Прочие", "underscore_tags_unlisted"))
        return [
            Custom(factory=make_collapsible(plugin, "Основные", None, "coll_under_main", main, True).instance.java),
            Custom(factory=make_collapsible(plugin, "Жанры", None, "underscore_genres", genres).instance.java),
            Custom(factory=make_collapsible(plugin, "Теги", None, "underscore_tags", tags).instance.java),
        ]

    if idx == 3:
        genres = [("Основные", "comma_genres_main")]
        if has:
            genres.extend(_sep_items(mapping, "genres", "comma"))
        genres.append(("Прочие", "comma_genres_unlisted"))
        tags = [("Основные", "comma_tags_main")]
        if has:
            tags.extend(_sep_items(mapping, "tags", "comma"))
        tags.append(("Прочие", "comma_tags_unlisted"))
        return [
            Custom(factory=make_collapsible(plugin, "Жанры", None, "comma_genres", genres, True).instance.java),
            Custom(factory=make_collapsible(plugin, "Теги", None, "comma_tags", tags).instance.java),
        ]
    return []
