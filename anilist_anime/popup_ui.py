from android.util import TypedValue
from android_utils import OnClickListener, OnLongClickListener, run_on_ui_thread
from client_utils import get_last_fragment, run_on_queue
from ui.bulletin import BulletinHelper
from hook_utils import find_class
from org.telegram.messenger import AndroidUtilities
from org.telegram.ui.ActionBar import Theme
from org.telegram.ui.Components import BackupImageView, LayoutHelper
from java import dynamic_proxy
from android.graphics import PorterDuff, PorterDuffColorFilter

L = find_class("android.widget.LinearLayout")
F = find_class("android.widget.FrameLayout")
S = find_class("android.widget.ScrollView")
T = find_class("android.widget.TextView")
V = find_class("android.view.View")
G = find_class("android.graphics.drawable.GradientDrawable")
D = find_class("android.app.Dialog")
C = find_class("android.graphics.drawable.ColorDrawable")
W = find_class("android.view.WindowManager")
Gr = find_class("android.view.Gravity")
AR = find_class("android.R")
OGL = find_class("android.view.ViewTreeObserver$OnGlobalLayoutListener")
IV = find_class("android.widget.ImageView")
CC = find_class("androidx.core.content.ContextCompat")
RD = find_class("org.telegram.messenger.R$drawable")
Ru = find_class("java.lang.Runnable")

DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

def dp(x):
    return AndroidUtilities.dp(x)

def jc(c):
    c = int(c) & 0xFFFFFFFF
    return c - 0x100000000 if c >= 0x80000000 else c

def th(k):
    try:
        return jc(Theme.getColor(k))
    except Exception:
        return 0

def tha(k, a):
    c = th(k)
    return jc((int(c) & 0xFFFFFF) | ((int(a) & 0xFF) << 24))

def rect(f, r=12):
    b = G()
    b.setShape(0)
    b.setCornerRadius(float(dp(r)))
    b.setColor(jc(f))
    return b

def oval(f):
    b = G()
    b.setShape(1)
    b.setColor(jc(f))
    return b

def nclip(v):
    for m in ("setClipChildren", "setClipToPadding", "setClipToOutline"):
        try:
            getattr(v, m)(False)
        except Exception:
            pass
    return v

def lp(w=-1, h=-2, wt=0.0, ml=0, mt=0, mr=0, mb=0):
    p = L.LayoutParams(w, h, wt) if wt else L.LayoutParams(w, h)
    p.setMargins(dp(ml), dp(mt), dp(mr), dp(mb))
    return p

def ico(n):
    try:
        return getattr(RD, n) or 0
    except Exception:
        return 0

def epl(r):
    ea, et = r.get("episodes_aired"), r.get("episodes")
    try:
        if ea is not None and int(ea or 0) > 0:
            return f"{int(ea)}/{int(et)} эп." if et and int(et) > 0 else f"{int(ea)}/? эп."
    except Exception:
        pass
    return f"эп. {r.get('episode')}" if r.get("episode") is not None else ""

_CTRL = None

def show_popup(results, query, use_shiki, is_genre, account, base, on_select, ongoing=False, list_num_mode=0, list_num_custom="•", card_send_mode=0, preview_pos=0, media_pos=0):
    global _CTRL
    ctrl = _SearchUI(results, query, use_shiki, is_genre, account, base, on_select, ongoing, list_num_mode, list_num_custom, card_send_mode, preview_pos, media_pos)
    _CTRL = ctrl
    run_on_ui_thread(ctrl.show)

class _SearchUI:
    def __init__(self, results, query, use_shiki, is_genre, account, base, on_select, ongoing=False, list_num_mode=0, list_num_custom="•", card_send_mode=0, preview_pos=0, media_pos=0):
        self._res = list(results or [])
        self._q = query or ""
        self._src = "Shikimori" if use_shiki else "AniList"
        self._genre = bool(is_genre)
        self._ong = bool(ongoing)
        self._account = account
        self._base = base
        self._on_select = on_select
        self._list_num_mode = int(list_num_mode or 0)
        self._list_num_custom = str(list_num_custom or "•")
        self._plugin_card_mode = int(card_send_mode or 0)
        self._plugin_preview_pos = int(preview_pos or 0)
        self._plugin_media_pos = int(media_pos or 0)
        self._a = None
        self.current_dialog = None
        self._items = []
        self._sel = set()
        self._a1 = self._a2 = None
        self._multi = False
        self._bar = self._blur = self._cf = None
        self._bc = self._bl = self._bcl = self._ball = self._bb = self._bx = None
        self._temp_pos = None
        self._force_mode = None
        self._force_nolink = False
        self._rows = {}
        self._sw = False
        self._build()

    def _build(self):
        self._items = []
        if self._ong:
            last = None
            for i, r in enumerate(self._res):
                d = r.get("day")
                if d is not None and d != last:
                    self._items.append({"t": "h", "d": d, "x": DAYS[d] if 0 <= d < 7 else ""})
                    last = d
                self._items.append({"t": "i", "i": i, "r": r})
            return
        has_id = any(r.get("_section") == "id" for r in self._res)
        has_name = any(r.get("_section") == "name" for r in self._res)
        if has_id and has_name:
            last_sec = None
            for i, r in enumerate(self._res):
                sec = r.get("_section")
                if sec and sec != last_sec:
                    label = "По ID" if sec == "id" else "Совпадения по названию"
                    self._items.append({"t": "h", "x": label})
                    last_sec = sec
                self._items.append({"t": "i", "i": i, "r": r})
            return
        if has_id and not has_name:
            self._items.append({"t": "h", "x": "По ID"})
        self._items += [{"t": "i", "i": i, "r": r} for i, r in enumerate(self._res)]

    def _lic(self, a, n, c=None):
        try:
            rid = ico(n)
            if not rid:
                return None
            d = CC.getDrawable(a, rid)
            if d is not None and c is not None:
                d = d.mutate()
                d.setColorFilter(PorterDuffColorFilter(jc(c), PorterDuff.Mode.SRC_IN))
            return d
        except Exception:
            return None

    def _ib(self, a, icon, click, sz=44, fill=None, ic=None, tip=None):
        iv = IV(a)
        s = dp(sz)
        iv.setLayoutParams(lp(s, s))
        try:
            iv.setScaleType(IV.ScaleType.CENTER_INSIDE)
        except Exception:
            pass
        iv.setPadding(dp(10), dp(10), dp(10), dp(10))
        iv.setBackground(oval(fill if fill is not None else tha(Theme.key_windowBackgroundWhite, 0xE6)))
        try:
            sel = Theme.createSelectorDrawable(0x18000000, 1)
            if sel is not None:
                try:
                    iv.setForeground(sel)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            iv.setClickable(True)
            iv.setFocusable(True)
            iv.setLongClickable(False)
        except Exception:
            pass
        d = self._lic(a, icon, ic if ic is not None else th(Theme.key_windowBackgroundWhiteBlackText))
        if d is not None:
            iv.setImageDrawable(d)
        iv.setOnClickListener(OnClickListener(lambda v, c=click: c() if callable(c) else None))
        return iv

    def _ob(self, a, icon, click, tip=None):
        iv = IV(a)
        iv.setLayoutParams(lp(dp(40), dp(40), 0, 4, 2, 4, 2))
        try:
            iv.setScaleType(IV.ScaleType.CENTER_INSIDE)
        except Exception:
            pass
        iv.setPadding(dp(8), dp(8), dp(8), dp(8))
        iv.setBackground(oval(tha(Theme.key_windowBackgroundWhite, 0xE6)))
        try:
            sel = Theme.createSelectorDrawable(0x21000000, 1)
            if sel is not None:
                try:
                    iv.setForeground(sel)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            iv.setClickable(True)
            iv.setFocusable(True)
            iv.setLongClickable(False)
        except Exception:
            pass
        d = self._lic(a, icon, th(Theme.key_windowBackgroundWhiteBlackText))
        if d is not None:
            iv.setImageDrawable(d)
        iv.setOnClickListener(OnClickListener(lambda v: click()))
        return iv

    def _tip(self, t):
        try:
            BulletinHelper.show_info(str(t))
        except Exception:
            pass

    def _rbg(self, row, idx):
        try:
            sel = idx in self._sel
            bg = tha(Theme.key_dialogBackground, 0xFF) if not sel else tha(Theme.key_chat_messagePanelSend, 0x33)
            row.setBackground(Theme.createSimpleSelectorRoundRectDrawable(dp(12), bg, tha(Theme.key_listSelector, 0x40)))
        except Exception:
            try:
                row.setBackground(rect(tha(Theme.key_dialogBackground, 0xFF), 12))
            except Exception:
                pass

    def _row(self, a, res, idx):
        row = L(a)
        row.setOrientation(0)
        row.setPadding(dp(12), dp(12), dp(12), dp(12))
        self._rbg(row, idx)
        row.setClickable(True)
        try:
            row.setLongClickable(True)
        except Exception:
            pass
        img = BackupImageView(a)
        img.setRoundRadius(dp(8))
        ph = C(th(Theme.key_windowBackgroundGray))
        c = res.get("cover_url")
        if c:
            try:
                img.setImage(c, None, ph)
            except Exception:
                img.setImageDrawable(ph)
        else:
            img.setImageDrawable(ph)
        row.addView(img, LayoutHelper.createLinear(64, 90, Gr.CENTER_VERTICAL, 0, 0, dp(12), 0))
        col = L(a)
        col.setOrientation(1)
        g = th(Theme.key_windowBackgroundWhiteGrayText)

        def tv(x, sz=14, cr=None):
            v = T(a)
            v.setText(x)
            v.setTextSize(TypedValue.COMPLEX_UNIT_DIP, sz)
            v.setTextColor(cr if cr is not None else g)
            return v

        col.addView(tv(res.get("title") or "—", 16, th(Theme.key_windowBackgroundWhiteBlackText)))
        col.addView(tv(f"{res.get('type_ru', '')}, {res.get('score', '?')}/10"))
        if res.get("country_line"):
            col.addView(tv(res["country_line"]))
        gens = res.get("genres") or []
        if gens:
            col.addView(tv(", ".join(gens[:4])))
        e = epl(res)
        if e:
            col.addView(tv(e, 13))
        row.addView(col, LayoutHelper.createLinear(0, -2, 1.0))
        row.setOnClickListener(OnClickListener(lambda v, i=idx: self._clk(i)))
        row.setOnLongClickListener(OnLongClickListener(lambda v, i=idx: (self._lng(i), True)[1]))
        self._rows[idx] = row
        return row

    def _hdr(self, a, text):
        t = T(a)
        t.setText(text)
        try:
            t.setTypeface(AndroidUtilities.getTypeface("fonts/rmedium.ttf"))
        except Exception:
            pass
        t.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 15)
        t.setTextColor(th(Theme.key_windowBackgroundWhiteBlueText))
        t.setPadding(dp(4), dp(14), dp(4), dp(6))
        return t

    def _clk(self, i):
        if not self._multi:
            self._one(i)
            return
        if i in self._sel:
            self._sel.discard(i)
            if self._a1 == i:
                self._a1 = None
            if self._a2 == i:
                self._a2 = None
        else:
            self._sel.add(i)
            if self._a1 is None:
                self._a1 = i
            elif self._a2 is None:
                self._a2 = i
            else:
                self._a1 = self._a2
                self._a2 = i
        if not self._sel and self._multi:
            self._rev()
        self._rs()
        self._ui2()
        self._ord()

    def _lng(self, i):
        self._a1 = i
        self._sel.add(i)
        if not self._multi:
            self._multi = True
            self._uni()
        self._rs()
        self._ui2()
        self._ord()

    def _one(self, i):
        try:
            if i < 0 or i >= len(self._res):
                return
            res = self._res[i]
            self._cl()
            run_on_queue(lambda r=res: self._on_select(r, self._account, self._base, self._send_opts()))
        except Exception as e:
            BulletinHelper.show_error(str(e))

    def _rs(self):
        try:
            for i, r in list(self._rows.items()):
                self._rbg(r, i)
        except Exception:
            pass

    def _clr(self):
        self._sel = set()
        self._a1 = self._a2 = None
        self._rs()
        self._ui2()
        self._rev()

    def _all(self):
        if not self._res:
            return
        self._sel = set(range(len(self._res)))
        self._a1 = 0
        self._a2 = len(self._res) - 1
        if not self._multi:
            self._multi = True
            self._uni()
        self._rs()
        self._ui2()
        self._ord()

    def _bet(self):
        if self._a1 is None or self._a2 is None:
            return
        for i in range(min(self._a1, self._a2), max(self._a1, self._a2) + 1):
            self._sel.add(i)
        self._rs()
        self._ui2()
        self._ord()

    def _scf(self, a):
        fr = F(a)
        try:
            fr.setBackground(Theme.createSimpleSelectorRoundRectDrawable(
                dp(24), tha(Theme.key_chat_messagePanelSend, 0xE6),
                Theme.getColor(Theme.key_featuredStickers_addButtonPressed)))
        except Exception:
            fr.setBackground(rect(tha(Theme.key_chat_messagePanelSend, 0xE6), 24))
        fr.setPadding(dp(24), dp(12), dp(24), dp(12))
        t = T(a)
        t.setText("Закрыть")
        t.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 17)
        try:
            t.setTypeface(AndroidUtilities.getTypeface("fonts/rmedium.ttf"))
        except Exception:
            pass
        t.setGravity(Gr.CENTER)
        t.setTextColor(th(Theme.key_featuredStickers_buttonText))
        fr.addView(t, LayoutHelper.createFrame(-1, -2, Gr.CENTER))
        fr.setOnClickListener(OnClickListener(lambda v: self._cl()))
        return fr

    def _run(self, fn):
        class R(dynamic_proxy(Ru)):
            def run(self):
                try:
                    if fn:
                        fn()
                except Exception:
                    pass
        return R()

    def _ao(self, v, end=None):
        try:
            try:
                v.animate().cancel()
            except Exception:
                pass
            a = v.animate()
            a.alpha(0.)
            a.scaleX(.85)
            a.scaleY(.85)
            a.setDuration(160)
            if end:
                try:
                    a.withEndAction(self._run(end))
                except Exception:
                    try:
                        v.postDelayed(self._run(end), 170)
                    except Exception:
                        try:
                            end()
                        except Exception:
                            pass
            a.start()
        except Exception:
            try:
                v.setAlpha(0.)
            except Exception:
                pass
            if end:
                try:
                    end()
                except Exception:
                    pass

    def _ai(self, v):
        try:
            try:
                v.animate().cancel()
            except Exception:
                pass
            v.setAlpha(0.)
            v.setScaleX(.85)
            v.setScaleY(.85)
            a = v.animate()
            a.alpha(1.)
            a.scaleX(1.)
            a.scaleY(1.)
            a.setDuration(180)
            a.start()
        except Exception:
            try:
                v.setAlpha(1.)
                v.setScaleX(1.)
                v.setScaleY(1.)
            except Exception:
                pass

    def _kids(self):
        o = []
        if self._bar:
            for i in range(self._bar.getChildCount()):
                try:
                    o.append(self._bar.getChildAt(i))
                except Exception:
                    pass
        return o

    def _uni(self):
        try:
            if not self._bar or not self._a:
                return
            act = self._a
            close = self._cf

            def build():
                try:
                    self._bar.removeAllViews()
                    try:
                        self._bar.setGravity(Gr.CENTER_VERTICAL)
                    except Exception:
                        pass
                    self._bar.setPadding(dp(8), dp(10), dp(8), dp(14))
                    nf = tha(Theme.key_windowBackgroundWhite, 0xE6)
                    ni = th(Theme.key_windowBackgroundWhiteBlackText)
                    self._bx = self._ib(act, "msg_close", self._cl, 44, nf, ni, "Закрыть")
                    self._bx.setLayoutParams(lp(dp(44), dp(44), 0, 4, 0, 8, 0))
                    self._bar.addView(self._bx)
                    ov = L(act)
                    nclip(ov)
                    ov.setOrientation(0)
                    try:
                        ov.setGravity(Gr.CENTER_VERTICAL)
                    except Exception:
                        pass
                    ov.setBackground(rect(nf, 22))
                    ov.setPadding(dp(6), dp(4), dp(6), dp(4))
                    ov.setLayoutParams(lp(-2, dp(48), 0, 0, 0, 8, 0))
                    self._bcl = self._ob(act, "msg_clear", self._clr, "очистить")
                    ov.addView(self._bcl)
                    self._ball = self._ob(act, "msg_list", self._all, "Выбрать всё")
                    ov.addView(self._ball)
                    self._bb = self._ob(act, "select_between", self._bet, "Выбрать между")
                    ov.addView(self._bb)
                    self._bar.addView(ov)
                    sp = V(act)
                    sp.setLayoutParams(lp(0, 1, 1.))
                    self._bar.addView(sp)
                    self._bl = self._ib(act, "msg_filled_data_messages", lambda: self._req("list"), 44, nf, ni, "Список")
                    self._bl.setLayoutParams(lp(dp(44), dp(44), 0, 0, 0, 6, 0))
                    self._bc = self._ib(act, "send_extera_24", lambda: self._req("card"), 44, nf, ni)
                    self._bc.setLayoutParams(lp(dp(44), dp(44), 0, 0, 0, 4, 0))
                    try:
                        self._bc.setLongClickable(True)
                        self._bc.setOnLongClickListener(OnLongClickListener(lambda v: (self._show_card_menu(self._bc), True)[1]))
                    except Exception:
                        pass
                    if len(self._sel) >= 3:
                        self._bar.addView(self._bc)
                        self._bar.addView(self._bl)
                    else:
                        self._bar.addView(self._bl)
                        self._bar.addView(self._bc)
                    for v in (self._bx, ov, self._bl, self._bc):
                        try:
                            v.setAlpha(0.)
                        except Exception:
                            pass
                        self._ai(v)
                    self._ui2()
                    self._rm()
                except Exception as e:
                    try:
                        BulletinHelper.show_error(str(e))
                    except Exception:
                        pass

            if close is not None:
                self._ao(close, build)
            else:
                build()
        except Exception:
            pass

    def _rev(self):
        try:
            if not self._bar or not self._a:
                return
            self._multi = False
            views = self._kids()

            def done():
                try:
                    self._bar.removeAllViews()
                    try:
                        self._bar.setGravity(Gr.CENTER)
                    except Exception:
                        pass
                    self._bar.setPadding(dp(20), dp(10), dp(20), dp(18))
                    self._cf = self._scf(self._a)
                    self._bar.addView(self._cf, lp(-1, -2))
                    self._ai(self._cf)
                except Exception:
                    pass

            if views:
                c = [0]
                t = len(views)

                def one():
                    c[0] += 1
                    if c[0] >= t:
                        done()

                for v in views:
                    self._ao(v, one)
            else:
                done()
        except Exception:
            pass

    def _rm(self):
        try:
            if not self._multi or not self._bar or not self._bl or not self._bc or not self._a:
                return
            nf = tha(Theme.key_windowBackgroundWhite, 0xE6)
            ni = th(Theme.key_windowBackgroundWhiteBlackText)
            sf = tha(Theme.key_chat_messagePanelSend, 0xE6)
            si = th(Theme.key_featuredStickers_buttonText)
            gy = th(Theme.key_windowBackgroundWhiteGrayText)
            n = len(self._sel)
            ch = self._kids()
            if self._bl not in ch or self._bc not in ch:
                return
            if ch.index(self._bc) > ch.index(self._bl):
                rm, ot, ri, oi = self._bc, self._bl, "send_extera_24", "msg_filled_data_messages"
            else:
                rm, ot, ri, oi = self._bl, self._bc, "msg_filled_data_messages", "send_extera_24"
            ot.setBackground(oval(nf))
            d = self._lic(self._a, oi, ni if n > 0 else gy)
            if d is not None:
                ot.setImageDrawable(d)
            rm.setBackground(oval(sf))
            d = self._lic(self._a, ri, si if n > 0 else gy)
            if d is not None:
                rm.setImageDrawable(d)
        except Exception:
            pass

    def _ord(self):
        try:
            if not self._multi or not self._bar or not self._bl or not self._bc or self._sw:
                return
            want = len(self._sel) >= 3
            ch = self._kids()
            if self._bl not in ch or self._bc not in ch:
                return
            if (ch.index(self._bc) < ch.index(self._bl)) == want:
                self._rm()
                return
            lb, cb = self._bl, self._bc
            self._sw = True
            done = [0]

            def fin():
                done[0] += 1
                if done[0] < 2:
                    return
                try:
                    try:
                        self._bar.removeView(lb)
                    except Exception:
                        pass
                    try:
                        self._bar.removeView(cb)
                    except Exception:
                        pass
                    if want:
                        self._bar.addView(cb)
                        self._bar.addView(lb)
                    else:
                        self._bar.addView(lb)
                        self._bar.addView(cb)
                    for v in (lb, cb):
                        try:
                            v.setAlpha(0.)
                            v.setScaleX(.85)
                            v.setScaleY(.85)
                        except Exception:
                            pass
                    self._rm()
                    self._ai(lb)
                    self._ai(cb)
                except Exception:
                    pass
                self._sw = False

            self._ao(lb, fin)
            self._ao(cb, fin)
        except Exception:
            self._sw = False

    def _ui2(self):
        try:
            if not self._a or not self._multi:
                return
            tc = th(Theme.key_windowBackgroundWhiteBlackText)
            gy = th(Theme.key_windowBackgroundWhiteGrayText)
            ac = th(Theme.key_windowBackgroundWhiteBlueText)
            n = len(self._sel)
            for b in (self._bc, self._bl):
                if b is not None:
                    try:
                        b.setEnabled(n > 0)
                    except Exception:
                        pass
            if self._ball is not None:
                d = self._lic(self._a, "msg_list", tc)
                if d is not None:
                    self._ball.setImageDrawable(d)
            if self._bb is not None:
                hr = self._a1 is not None and self._a2 is not None and self._a1 != self._a2
                d = self._lic(self._a, "select_between", ac if hr else gy)
                if d is not None:
                    self._bb.setImageDrawable(d)
                try:
                    self._bb.setEnabled(hr)
                except Exception:
                    pass
            if self._bcl is not None:
                d = self._lic(self._a, "msg_clear", tc if n > 0 else gy)
                if d is not None:
                    self._bcl.setImageDrawable(d)
            self._rm()
        except Exception:
            pass

    def _cl(self):
        try:
            if self.current_dialog:
                self.current_dialog.dismiss()
        except Exception:
            pass
        self.current_dialog = None
        self._rst()

    def _rst(self):
        self._sel = set()
        self._a1 = self._a2 = None
        self._multi = False
        self._bar = self._blur = self._cf = None
        self._bx = self._bcl = self._ball = self._bb = self._bc = self._bl = None
        self._rows = {}
        self._sw = False

    def _mode(self):
        try:
            return int(getattr(self, "_plugin_card_mode", 0) or 0)
        except Exception:
            return 0

    def _pos_label(self):
        if self._temp_pos is None:
            return "По умолчанию"
        return "Снизу" if self._temp_pos == 1 else "Сверху"

    def _cycle_pos(self):
        # По умолчанию → Снизу → Сверху → По умолчанию
        if self._temp_pos is None:
            self._temp_pos = 1
        elif self._temp_pos == 1:
            self._temp_pos = 0
        else:
            self._temp_pos = None

    def _pos(self, media=0):
        if self._temp_pos is not None:
            return self._temp_pos
        try:
            if media:
                return int(getattr(self, "_plugin_media_pos", 0) or 0)
            return int(getattr(self, "_plugin_preview_pos", 0) or 0)
        except Exception:
            return 0

    def _inv(self, media=0):
        # temp: 0=Сверху, 1=Снизу (лейблы меню общие)
        # у media и preview разная полярность invert относительно лейбла
        if self._temp_pos is not None:
            if media:
                # media: Сверху→False, Снизу→True
                return self._temp_pos == 1
            # preview: Сверху→True, Снизу→False
            return self._temp_pos == 0
        p = self._pos(media)
        if media:
            # media items=["Сверху","Снизу"]: 0→False, 1→True
            return p == 1
        # preview items=["Снизу","Сверху"]: 0→False, 1→True
        return p == 1

    def _req(self, mode):
        n = len(self._sel)
        if n <= 0:
            BulletinHelper.show_info("Ничего не выбрано")
            return
        if mode == "card" and n >= 2:
            self._conf()
            return
        if mode == "list":
            self._slist()
            return
        if mode == "preview":
            self._force_mode = 0
            self._force_nolink = False
            self._scards()
            return
        if mode == "media":
            self._force_mode = 1
            self._force_nolink = False
            self._scards()
            return
        if mode == "nolink":
            self._force_nolink = True
            self._force_mode = 1
            self._scards()
            return
        self._scards()

    def _conf(self):
        try:
            from ui.alert import AlertDialogBuilder
            act = self._a or ((get_last_fragment().getParentActivity()) if get_last_fragment() else None)
            if not act:
                BulletinHelper.show_error("Activity not found")
                return
            b = AlertDialogBuilder(act)
            b.set_title("Подтверждение")
            b.set_message("Отправка нескольких карточек может занять много времени")

            def ok(bld, w):
                try:
                    bld.dismiss()
                except Exception:
                    pass
                self._scards()

            def cancel(bld, w):
                try:
                    bld.dismiss()
                except Exception:
                    pass

            b.set_positive_button("Отправить", ok)
            b.set_negative_button("Закрыть", cancel)
            b.set_cancelable(True)
            b.show()
        except Exception as e:
            BulletinHelper.show_error(str(e))

    def _send_opts(self):
        mode = getattr(self, "_force_mode", None)
        if mode is None:
            mode = self._mode()
        media = 1 if int(mode) == 1 else 0
        return {
            "card_send_mode": int(mode),
            "invert": bool(self._inv(media)),
            "no_link": bool(getattr(self, "_force_nolink", False)),
            "temp_pos": self._temp_pos,
        }

    def _scards(self):
        try:
            idxs = sorted(self._sel)
            items = [self._res[i] for i in idxs if 0 <= i < len(self._res)]
            opts = self._send_opts()
            self._force_mode = None
            self._force_nolink = False
            self._temp_pos = None
            self._cl()
            for res in items:
                run_on_queue(lambda r=res, o=opts: self._on_select(r, self._account, self._base, o))
        except Exception as e:
            BulletinHelper.show_error(str(e))












    def _show_card_menu(self, anchor):
        try:
            frag = get_last_fragment()
            if not frag or not self.current_dialog:
                return
            ItemOptions = find_class("org.telegram.ui.Components.ItemOptions")
            if not ItemOptions:
                return
            class R(dynamic_proxy(Ru)):
                def __init__(self, fn):
                    super().__init__()
                    self.fn = fn
                def run(self):
                    try:
                        if self.fn:
                            self.fn()
                    except Exception:
                        pass
            container = None
            try:
                container = self.current_dialog.getWindow().getDecorView()
            except Exception:
                pass
            if container is None:
                try:
                    container = anchor.getRootView()
                except Exception:
                    pass
            if container is None:
                return
            options = ItemOptions.makeOptions(container, frag.getResourceProvider(), anchor)
            try:
                options.setOnTopOfScrim()
            except Exception:
                pass
            mode = self._mode()
            if self._temp_pos is None:
                irpos = ico("msg_reorder") or ico("msg_media") or 0
            else:
                irpos = ico("menu_link_below" if self._temp_pos == 1 else "menu_link_above") or ico("msg_reorder") or 0
            irm = ico("iv_media") or ico("msg_photo") or ico("msg_media") or 0
            irp = ico("media_link_24") or ico("msg_link") or ico("msg_openin") or 0
            irn = ico("menu_link_revoke") or ico("msg_delete") or ico("msg_clear") or 0
            def do_cycle():
                self._cycle_pos()
                try:
                    options.dismiss()
                except Exception:
                    pass
                try:
                    BulletinHelper.show_info("Обложка: " + self._pos_label())
                except Exception:
                    pass
                def reopen():
                    try:
                        self._show_card_menu(anchor)
                    except Exception:
                        pass
                try:
                    anchor.postDelayed(self._run(reopen), 80)
                except Exception:
                    run_on_ui_thread(reopen)
            def do_send(m):
                try:
                    options.dismiss()
                except Exception:
                    pass
                self._req(m)
            options.add(int(irpos), "Обложка: " + self._pos_label(), R(do_cycle))
            if mode == 0:
                options.add(int(irm), "Медиа", R(lambda: do_send("media")))
            else:
                options.add(int(irp), "Превью", R(lambda: do_send("preview")))
            options.add(int(irn), "Без ссылки", R(lambda: do_send("nolink")))
            options.show()
        except Exception as e:
            BulletinHelper.show_error(str(e))


    def _slist(self):
        try:
            from client_utils import send_text
            o = sorted(self._sel)
            if not o:
                BulletinHelper.show_error("Пусто")
                return
            src_label = "Shikimori" if "Shikimori" in str(self._src) else "AniList"
            if self._ong:
                header = "%s поиск: онгоинги <code>%s</code>" % (src_label, self._q) if self._q else "%s поиск: онгоинги" % src_label
            else:
                header = "%s поиск: <code>%s</code>" % (src_label, self._q) if self._q else "%s поиск" % src_label
            def _num(i, t):
                try:
                    mode = int(getattr(self, "_list_num_mode", 0) or 0)
                except Exception:
                    mode = 0
                custom = getattr(self, "_list_num_custom", "•") or "•"
                if mode == 2:
                    return t
                if mode == 1:
                    return "%s %s" % (custom, t)
                return "%d. %s" % (i + 1, t)
            parts = [header]
            counter = [0]
            def add_title(title):
                n = counter[0]
                counter[0] = n + 1
                try:
                    mode = int(getattr(self, "_list_num_mode", 0) or 0)
                except Exception:
                    mode = 0
                custom = getattr(self, "_list_num_custom", "•") or "•"
                if mode == 2:
                    return "<code>%s</code>" % title
                if mode == 1:
                    return "%s <code>%s</code>" % (custom, title)
                return "%d. <code>%s</code>" % (n + 1, title)
            if self._ong:
                by = {}
                for i in o:
                    if 0 <= i < len(self._res):
                        r = self._res[i]
                        d = r.get("day")
                        key = d if d is not None else -1
                        by.setdefault(key, []).append(r.get("title") or "—")
                for d in sorted(by.keys(), key=lambda x: 9 if x < 0 else x):
                    titles = by[d]
                    mono = "\n".join(add_title(tt) for tt in titles)
                    if d >= 0 and d < 7:
                        parts.append(DAYS[d])
                        parts.append("<blockquote expandable>%s</blockquote>" % mono)
                    else:
                        parts.append("<blockquote expandable>%s</blockquote>" % mono)
            else:
                has_id = any(self._res[i].get("_section") == "id" for i in o if 0 <= i < len(self._res))
                has_name = any(self._res[i].get("_section") == "name" for i in o if 0 <= i < len(self._res))
                if has_id and has_name:
                    id_titles = [self._res[i].get("title") or "—" for i in o if 0 <= i < len(self._res) and self._res[i].get("_section") == "id"]
                    name_titles = [self._res[i].get("title") or "—" for i in o if 0 <= i < len(self._res) and self._res[i].get("_section") == "name"]
                    if id_titles:
                        parts.append("По ID")
                        parts.append("<blockquote expandable>%s</blockquote>" % ("\n".join(add_title(tt) for tt in id_titles)))
                    if name_titles:
                        parts.append("Совпадения по названию")
                        parts.append("<blockquote expandable>%s</blockquote>" % ("\n".join(add_title(tt) for tt in name_titles)))
                else:
                    titles = [self._res[i].get("title") or "—" for i in o if 0 <= i < len(self._res)]
                    parts.append("<blockquote expandable>%s</blockquote>" % ("\n".join(add_title(tt) for tt in titles)))
            LIMIT = 3500
            chunks = []
            cur = []
            cur_len = 0
            for part in parts:
                pl = len(part) + 1
                if cur and cur_len + pl > LIMIT:
                    chunks.append("\n".join(cur))
                    cur = [part]
                    cur_len = pl
                else:
                    cur.append(part)
                    cur_len += pl
            if cur:
                chunks.append("\n".join(cur))
            if not chunks or not any(c.strip() for c in chunks):
                BulletinHelper.show_error("Пусто")
                return
            self._cl()
            try:
                from search import build_send_params
                base = self._base if isinstance(self._base, dict) else {}
                for body in chunks:
                    p = build_send_params(self._account, base, body, "HTML")
                    send_text(account=self._account, **p)
            except Exception:
                try:
                    for body in chunks:
                        send_text(body)
                except Exception:
                    pass
            BulletinHelper.show_success("Отправлено текстом")
        except Exception as e:
            BulletinHelper.show_error(str(e))

    def _grad(self, top):
        try:
            Ori = getattr(G, "Orientation")
            c = Theme.key_windowBackgroundGray
            cols = [tha(c, 0xE6), tha(c, 0xCC), tha(c, 0x00)] if top else [tha(c, 0x00), tha(c, 0xCC), tha(c, 0xE6)]
            g = G(Ori.TOP_BOTTOM, cols)
            g.setShape(0)
            return g
        except Exception:
            return None

    def show(self):
        try:
            frag = get_last_fragment()
            act = frag.getParentActivity() if frag else None
            if not act:
                return
            if self.current_dialog:
                try:
                    self.current_dialog.dismiss()
                except Exception:
                    pass
                self.current_dialog = None
            self._a = act
            self._sel = set()
            self._a1 = self._a2 = None
            self._multi = False
            self._rows = {}
            bg = th(Theme.key_windowBackgroundGray)
            tc = th(Theme.key_windowBackgroundWhiteBlackText)
            hc = th(Theme.key_windowBackgroundWhiteGrayText)
            try:
                theme = AR.style.Theme_Black_NoTitleBar_Fullscreen
            except Exception:
                try:
                    theme = AR.style.Theme_DeviceDefault_NoActionBar
                except Exception:
                    theme = 16973834
            dialog = D(act, theme)
            root = L(act)
            root.setOrientation(1)
            root.setBackgroundColor(int(bg))
            root.setLayoutParams(lp(-1, -1))
            content = L(act)
            content.setOrientation(1)
            content.setBackgroundColor(int(bg))
            content.setLayoutParams(lp(-1, -1))
            sb = getattr(AndroidUtilities, "statusBarHeight", dp(24)) or dp(24)
            hh = int(sb) + dp(48)
            frame = F(act)
            frame.setLayoutParams(lp(-1, 0, 1.))
            nclip(frame)
            try:
                frame.setClipChildren(False)
                frame.setClipToPadding(False)
            except Exception:
                pass
            sv = S(act)
            sv.setVerticalScrollBarEnabled(True)
            try:
                sv.setFillViewport(True)
            except Exception:
                pass
            sv.setLayoutParams(F.LayoutParams(-1, -1))
            lc = L(act)
            lc.setOrientation(1)
            lc.setLayoutParams(lp())
            lc.setBackgroundColor(int(bg))
            lc.setPadding(dp(12), hh, dp(12), dp(80))
            for it in self._items:
                if it["t"] == "h":
                    lc.addView(self._hdr(act, it["x"]), lp())
                else:
                    lc.addView(self._row(act, it["r"], it["i"]), lp(-1, -2, 0, 0, 4, 0, 4))
            sv.addView(lc)
            frame.addView(sv)
            hb = V(act)
            hlp = F.LayoutParams(-1, max(int(sb) + dp(48), hh))
            try:
                hlp.gravity = Gr.TOP
            except Exception:
                pass
            hb.setLayoutParams(hlp)
            g = self._grad(True)
            if g is not None:
                hb.setBackground(g)
            else:
                hb.setBackgroundColor(int(bg))
            frame.addView(hb)
            head = L(act)
            nclip(head)
            head.setOrientation(1)
            try:
                head.setGravity(Gr.CENTER_HORIZONTAL)
            except Exception:
                pass
            head.setPadding(dp(12), int(sb) + dp(4), dp(12), dp(6))
            hpl = F.LayoutParams(-1, -2)
            try:
                hpl.gravity = Gr.TOP
            except Exception:
                pass
            head.setLayoutParams(hpl)
            title = T(act)
            src_l = "Shikimori" if "Shikimori" in str(self._src) else "AniList"
            qtxt = str(self._q or "")
            if self._ong:
                title.setText("%s поиск: онгоинги %s" % (src_l, qtxt) if qtxt else "%s поиск: онгоинги" % src_l)
            else:
                title.setText("%s поиск: %s" % (src_l, qtxt) if qtxt else "%s поиск" % src_l)
            try:
                title.setTypeface(AndroidUtilities.getTypeface("fonts/rmedium.ttf"))
            except Exception:
                pass
            title.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 17)
            title.setGravity(Gr.CENTER)
            title.setTextColor(int(tc))
            try:
                title.setSingleLine(True)
            except Exception:
                pass
            head.addView(title, lp(-1, -2, 0, 0, 0, 0, 2))
            frame.addView(head)
            try:
                def sh(v=None):
                    try:
                        h = head.getHeight()
                        if h > 0:
                            p = hb.getLayoutParams()
                            p.height = max(h, int(sb) + dp(48), hh)
                            hb.setLayoutParams(p)
                    except Exception:
                        pass

                class HL(dynamic_proxy(OGL)):
                    def onGlobalLayout(self):
                        sh()

                head.getViewTreeObserver().addOnGlobalLayoutListener(HL())
            except Exception:
                pass
            bb = V(act)
            blp = F.LayoutParams(-1, dp(80))
            try:
                blp.gravity = Gr.BOTTOM
            except Exception:
                pass
            bb.setLayoutParams(blp)
            g = self._grad(False)
            if g is not None:
                bb.setBackground(g)
            else:
                bb.setBackgroundColor(int(bg))
            self._blur = bb
            frame.addView(bb)
            bot = L(act)
            nclip(bot)
            bot.setOrientation(0)
            try:
                bot.setGravity(Gr.CENTER)
            except Exception:
                pass
            bot.setPadding(dp(20), dp(10), dp(20), dp(18))
            bpl = F.LayoutParams(-1, -2)
            try:
                bpl.gravity = Gr.BOTTOM
            except Exception:
                pass
            bot.setLayoutParams(bpl)
            self._bar = bot
            self._cf = self._scf(act)
            bot.addView(self._cf, lp(-1, -2))
            frame.addView(bot)
            try:
                def sb2(v=None):
                    try:
                        h = bot.getHeight()
                        if h > 0 and self._blur is not None:
                            p = self._blur.getLayoutParams()
                            p.height = max(h, dp(60)) + dp(10)
                            self._blur.setLayoutParams(p)
                    except Exception:
                        pass

                class BL(dynamic_proxy(OGL)):
                    def onGlobalLayout(self):
                        sb2()

                bot.getViewTreeObserver().addOnGlobalLayoutListener(BL())
            except Exception:
                pass
            content.addView(frame)
            root.addView(content)
            dialog.setContentView(root)
            dialog.setCancelable(True)
            dialog.setCanceledOnTouchOutside(True)
            w = dialog.getWindow()
            if w is not None:
                try:
                    d = w.getDecorView()
                    if d is not None:
                        d.setSystemUiVisibility(V.SYSTEM_UI_FLAG_LAYOUT_STABLE | V.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN)
                    w.setBackgroundDrawable(C(int(bg)))
                    w.setSoftInputMode(W.LayoutParams.SOFT_INPUT_ADJUST_NOTHING | W.LayoutParams.SOFT_INPUT_STATE_HIDDEN)
                    w.clearFlags(0x04000000 | 0x08000000)
                    w.addFlags(0x80000000)
                    try:
                        w.setStatusBarColor(int(bg))
                        w.setNavigationBarColor(int(bg))
                    except Exception:
                        pass
                    try:
                        w.setDimAmount(0.)
                    except Exception:
                        pass
                    a = w.getAttributes()
                    a.width = -1
                    a.height = -1
                    try:
                        a.gravity = Gr.TOP
                        a.y = 0
                    except Exception:
                        pass
                    w.setAttributes(a)
                    w.setLayout(-1, -1)
                except Exception:
                    pass
            self.current_dialog = dialog
            dialog.show()
        except Exception as e:
            BulletinHelper.show_error(str(e))
