from android.widget import LinearLayout, TextView, FrameLayout, ImageView, HorizontalScrollView
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

from chat_preview_ui import notify_preview_update

from collapsible_blocks import (
    PICK_MODES,
    is_master_enabled,
    parse_bool,
    get_mode_blocks,
)

MP, WC, DUR = -1, -2, 220
CHILD_PAD = 54
AUL = find_class("android.animation.ValueAnimator$AnimatorUpdateListener")
TgSwitch = find_class("org.telegram.ui.Components.Switch")

def dp(v):
    return int(AndroidUtilities.dp(float(v)))

def rtl():
    return bool(LocaleController.isRTL)

def tc(*k):
    for x in k:
        try:
            a = getattr(Theme, x, None)
            if a is not None:
                n = int(Theme.getColor(a)) & 0xFFFFFFFF
                v = n - 0x100000000 if n >= 0x80000000 else n
                if v:
                    return v
        except Exception:
            pass
    return 0

def dr(n, col=None):
    try:
        rid = getattr(R.drawable, n, 0)
        if not rid:
            return None
        d = ContextCompat.getDrawable(ApplicationLoader.applicationContext, int(rid))
        if d is not None:
            d = d.mutate()
            if col:
                d.setColorFilter(PorterDuffColorFilter(int(col), PorterDuff.Mode.SRC_IN))
            return d
    except Exception:
        pass
    return None

def pill_dr(color, radius_dp=16):
    g = GradientDrawable()
    g.setShape(0)
    g.setCornerRadius(dp(radius_dp))
    g.setColor(int(color))
    return g

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
                return ld
            except Exception:
                pass
        return bg
    bg.setColor(0)
    g = tc("key_windowBackgroundWhiteGrayText", "key_windowBackgroundWhiteHintText", "key_dialogTextGray")
    if g:
        try:
            bg.setStroke(dp(1.5), int(g))
        except Exception:
            pass
    return bg

def ac(iv_obj, on):
    try:
        iv_obj.animate().cancel()
        iv_obj.setScaleX(0.65)
        iv_obj.setScaleY(0.65)
        d = cl(on)
        try:
            d = d.mutate()
        except Exception:
            pass
        iv_obj.setImageDrawable(d)
        iv_obj.invalidate()
        iv_obj.animate().scaleX(1.0).scaleY(1.0).setDuration(140).start()
    except Exception:
        try:
            iv_obj.setImageDrawable(cl(on))
            iv_obj.invalidate()
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

def make_collapsible_view(ctx, plugin, title, icn, master_key, items, hb=True, default_master=True, default_item=True, on_change_cb=None):
    def _gs(k, d=True):
        try:
            v = plugin.get_setting(k, d)
        except Exception:
            return d
        return parse_bool(v, d)

    def _ss(k, v):
        try:
            plugin.set_setting(k, bool(v))
        except Exception:
            pass
        try:
            plugin.update_settings()
        except Exception:
            pass
        if on_change_cb:
            try:
                on_change_cb()
            except Exception:
                pass
        notify_preview_update()

    m = is_master_enabled(plugin, master_key, default_master)
    st = [_gs(k, default_item) for _, k in items]
    vh = ["%d/%d" % (sum(st), len(items)), None]
    ar = [None]
    ex = [False]

    def om(v):
        _ss(master_key, v)

    def upd():
        if vh[1] is not None:
            try:
                vh[1].setText("%d/%d" % (sum(st), len(items)))
            except Exception:
                pass

    def mc(i, k):
        def _c(v):
            st[i] = v
            _ss(k, v)
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

    v_root = LinearLayout(ctx)
    v_root.setOrientation(1)
    v_root.addView(hdr(ctx, title, icn, vh, m, oe, om, ar), LinearLayout.LayoutParams(MP, WC))
    v_root.addView(sep, sl)
    v_root.addView(box)
    return v_root

def make_mode_picker_and_blocks(plugin, mapping, on_change_global=None):
    def _gs(k, d=0):
        try:
            return int(plugin.get_setting(k, d))
        except Exception:
            return d

    def _ss(k, v):
        try:
            plugin.set_setting(k, int(v))
        except Exception:
            pass
        try:
            plugin.update_settings()
        except Exception:
            pass
        if on_change_global:
            try:
                on_change_global()
            except Exception:
                pass
        notify_preview_update()

    def bp(ctx, root_view):
        root_view.setOrientation(1)
        root_view.removeAllViews()

        title = TextView(ctx)
        title.setText("Режим отображения")
        title.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 16)
        title.setTextColor(tc("key_windowBackgroundWhiteBlackText", "key_dialogTextBlack"))
        try:
            title.setSingleLine(True)
            title.setEllipsize(TextUtils.TruncateAt.END)
        except Exception:
            pass
        title.setPadding(dp(21), dp(12), dp(21), dp(8))
        root_view.addView(title, LinearLayout.LayoutParams(MP, WC))

        scroll = HorizontalScrollView(ctx)
        scroll.setHorizontalScrollBarEnabled(False)
        scroll.setOverScrollMode(2)

        chips_container = LinearLayout(ctx)
        chips_container.setOrientation(0)
        chips_container.setPadding(dp(18), dp(4), dp(18), dp(12))

        blocks_container = LinearLayout(ctx)
        blocks_container.setOrientation(1)

        modes = PICK_MODES
        cur = 0
        try:
            cur = int(_gs("display_mode_pick", 0))
        except Exception:
            cur = 0
        if cur < 0 or cur >= len(modes):
            cur = 0

        chips = []
        sel_bg_col = tc("key_featuredStickers_addButton", "key_switchTrackChecked", "key_windowBackgroundWhiteBlueText2") or 0xFF508DCE
        sel_txt_col = tc("key_featuredStickers_buttonText", "key_windowBackgroundWhite") or 0xFFFFFFFF
        unsel_bg_col = tc("key_windowBackgroundGray", "key_divider") or 0x1A000000
        unsel_txt_col = tc("key_windowBackgroundWhiteBlackText", "key_dialogTextBlack") or 0xFF000000

        def update_chips(selected_idx):
            for idx, chip in enumerate(chips):
                is_sel = (idx == selected_idx)
                chip.setBackground(pill_dr(sel_bg_col if is_sel else unsel_bg_col, 18))
                chip.setTextColor(sel_txt_col if is_sel else unsel_txt_col)

        def render_blocks(mode_idx):
            blocks_container.removeAllViews()

            blocks = get_mode_blocks(mapping, mode_idx)
            for title_text, master_key, items, default_master, default_item in blocks:
                b_view = make_collapsible_view(
                    ctx, plugin, title_text, None, master_key, items, True,
                    default_master=default_master, default_item=default_item,
                    on_change_cb=on_change_global,
                )
                blocks_container.addView(b_view, LinearLayout.LayoutParams(MP, WC))

        for i, mode_data in enumerate(modes):
            chip = TextView(ctx)
            chip.setText(mode_data[0])
            chip.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 14)
            chip.setSingleLine(True)
            chip.setPadding(dp(16), dp(8), dp(16), dp(8))

            lp = LinearLayout.LayoutParams(WC, WC)
            if i > 0:
                lp.leftMargin = dp(8)
            chip.setLayoutParams(lp)

            def _make_click(idx):
                def _click(v):
                    update_chips(idx)
                    _ss("display_mode_pick", idx)
                    render_blocks(idx)
                return _click

            chip.setOnClickListener(OnClickListener(_make_click(i)))
            chips_container.addView(chip)
            chips.append(chip)

        update_chips(cur)
        scroll.addView(chips_container, FrameLayout.LayoutParams(WC, WC))
        root_view.addView(scroll, LinearLayout.LayoutParams(MP, WC))
        root_view.addView(blocks_container, LinearLayout.LayoutParams(MP, WC))
        render_blocks(cur)

    def cr(ctx, lv, acc, guid, rp):
        root = LinearLayout(ctx)
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
