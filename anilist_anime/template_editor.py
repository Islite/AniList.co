import re
from client_utils import get_last_fragment
from android_utils import run_on_ui_thread, OnClickListener, OnLongClickListener
from ui.bulletin import BulletinHelper
from ui.alert import AlertDialogBuilder
from hook_utils import find_class
from android.util import TypedValue
from org.telegram.messenger import AndroidUtilities
from org.telegram.ui.ActionBar import Theme
from java import dynamic_proxy
from android.graphics import PorterDuff, PorterDuffColorFilter

LinearLayout=find_class("android.widget.LinearLayout")
FrameLayout=find_class("android.widget.FrameLayout")
HorizontalScrollView=find_class("android.widget.HorizontalScrollView")
ScrollView=find_class("android.widget.ScrollView")
TextView=find_class("android.widget.TextView")
EditText=find_class("android.widget.EditText")
Button=find_class("android.widget.Button")
ImageView=find_class("android.widget.ImageView")
ViewGroup=find_class("android.view.ViewGroup")
View=find_class("android.view.View")
GradientDrawable=find_class("android.graphics.drawable.GradientDrawable")
InputType=find_class("android.text.InputType")
Dialog=find_class("android.app.Dialog")
ColorDrawable=find_class("android.graphics.drawable.ColorDrawable")
WindowManager=find_class("android.view.WindowManager")
Gravity=find_class("android.view.Gravity")
Rect=find_class("android.graphics.Rect")
AndroidR=find_class("android.R")
OnGlobalLayoutListener=find_class("android.view.ViewTreeObserver$OnGlobalLayoutListener")
ContextCompat=find_class("androidx.core.content.ContextCompat")
R_drawable=find_class("org.telegram.messenger.R$drawable")
Toast=find_class("android.widget.Toast")
TextWatcher=find_class("android.text.TextWatcher")

NAMES_RU=[("{ru1}","ru1"),("{ru2}","ru2"),("{ru3}","ru3"),("{ru4}","ru4"),("{ru5}","ru5")]
NAMES_EN=[("{en1}","en1"),("{en2}","en2"),("{en3}","en3"),("{en4}","en4"),("{en5}","en5")]
NAMES_ALL=NAMES_RU+NAMES_EN
OTHERS=[("{preview}","preview"),("{a}","a"),("{flag}","flag"),("{country}","country"),("{season}","season"),("{year}","year"),("{format}","format"),("{audience}","audience"),("{genres}","genres"),("{tags}","tags"),("{episodes}","episodes"),("{score}","score"),("{status}","status"),("{duration}","duration"),("{source}","source"),("{studios}","studios"),("{link1}","link1"),("{link2}","link2"),("{description}","description")]
PLACEHOLDERS=NAMES_ALL+OTHERS

DEFAULT_TEMPLATE=("{preview}{a} {ru1}\n| {ru2}\n| {ru3}\n| {ru4}\n| {ru5}\n| {en1}\n| {en2}\n| {en3}\n| {en4}\n| {en5}\n{flag}{country}, {season} {year}\nформат {format}\nцелевая аудитория {audience}\nжанры: {genres}\nтеги: {tags}\n{link1} {link2}\n{description}\nстудии: {studios}\nоригинал: {source}\nпродолжительность серии: {duration}\nстатус: {status}\nрейтинг: {score}\nэпизоды: {episodes}")

PREVIEW_SAMPLES={"preview":"","a":"#аниме","ru1":"Русское название","ru2":"Русское название 2","ru3":"Русское название 3","ru4":"Русское название 4","ru5":"Русское название 5","en1":"English Title","en2":"English Title 2","en3":"English Title 3","en4":"English Title 4","en5":"English Title 5","flag":"🇯🇵","country":"Япония","season":"лето","year":"2018г.","format":"сериал","audience":"сёнэн","genres":"драма экшен","tags":"психология","episodes":"8/18 эп.","score":"8.8/10","status":"выходит","duration":"24 мин.","source":"оригинал","studios":"MAPPA","link1":"AniList","link2":"Shikimori","description":"описание"}

def dp(x):return AndroidUtilities.dp(x)
def to_jcolor(c):
 c=int(c)&0xFFFFFFFF
 if c>=0x80000000:c-=0x100000000
 return c
def th(key):
 try:
  return to_jcolor(Theme.getColor(key))
 except:
  return 0
def th_alpha(key,alpha):
 c=th(key)
 return to_jcolor((int(c)&0x00FFFFFF)|((int(alpha)&0xFF)<<24))
def make_bg(fill,stroke=None,radius=12,stroke_dp=1):
 bg=GradientDrawable()
 bg.setShape(GradientDrawable.RECTANGLE)
 bg.setCornerRadius(float(dp(radius)))
 bg.setColor(to_jcolor(fill))
 if stroke is not None:bg.setStroke(dp(stroke_dp),to_jcolor(stroke))
 return bg
def make_circle_bg(fill,stroke=None,stroke_dp=1):
 bg=GradientDrawable()
 bg.setShape(GradientDrawable.OVAL)
 bg.setColor(to_jcolor(fill))
 if stroke is not None:bg.setStroke(dp(stroke_dp),to_jcolor(stroke))
 return bg
def no_clip(v):
 for m in("setClipChildren","setClipToPadding","setClipToOutline"):
  try:getattr(v,m)(False)
  except:pass
 return v
def lp(w=ViewGroup.LayoutParams.MATCH_PARENT,h=ViewGroup.LayoutParams.WRAP_CONTENT,weight=0.0,ml=0,mt=0,mr=0,mb=0):
 p=LinearLayout.LayoutParams(w,h,weight) if weight else LinearLayout.LayoutParams(w,h)
 p.setMargins(dp(ml),dp(mt),dp(mr),dp(mb))
 return p
def get_drawable(name):
 try:
  r=getattr(R_drawable,name)
  if r:return r
 except:pass
 return 0

class TemplateEditor:
 def __init__(self, host):
  self._host = host
  self.editor=self.current_dialog=self._activity=self._root=self._content=self._listener=None
  self._last_kb=0
  self._base_inset=-1
  self._panel=self._active=self._btn_names=self._btn_places=self._btn_mode=self._btn_preview=None
  self._btn_clear=self._btn_send=self._btn_back=self._btn_undo=self._btn_redo=self._oval_group=None
  self._head_bar=self._bottom_bar=self._head_blur=self._bottom_blur=None
  self._bottom_spacer=None
  self._history=[]
  self._hist_idx=-1
  self._pre_sel=0
  self._pre_text=""
  self._ignore_change=False
  self._watcher=None

 def get_setting(self, key, default=None):
  return self._host.get_setting(key, default)
 def set_setting(self, key, value, reload_settings=False):
  try:
   return self._host.set_setting(key, value, reload_settings=reload_settings)
  except TypeError:
   return self._host.set_setting(key, value)

 
 def _is_vertical(self):
  v=self.get_setting("layout_mode",0)
  if v is True or v=="true" or v=="vertical":return True
  if v is False or v=="false" or v=="horizontal":return False
  try:return int(v)==1
  except:return False

 
 def _enabled(self,key):
  v=self.get_setting("ph_"+key,True)
  return not(v is False or v=="false" or v==0)

 def _render_preview(self,tpl=None):
  try:
   self._host.update_settings()
   if tpl is None:
    tpl=self._get_text() or str(self.get_setting("card_template",DEFAULT_TEMPLATE) or DEFAULT_TEMPLATE)
   prev=getattr(self._host,"card_template",None)
   self._host.card_template=str(tpl)
   try:
    from settings_ui import build_preview
    mapping=getattr(self._host,"mapping",None)
    if mapping is None:
     from mapping import MappingState
     mapping=MappingState(self._host)
    return build_preview(self._host, mapping)
   finally:
    if prev is not None:
     self._host.card_template=prev
  except Exception as e:
   mv=dict(PREVIEW_SAMPLES)
   for t,k in PLACEHOLDERS:
    if not self._enabled(k):mv[k]=""
   try:
    return str(tpl or DEFAULT_TEMPLATE).format(**mv)
   except Exception:
    return "Ошибка шаблона: "+str(e)

 def _preview_plain(self,text):
  if not text:return "(пусто)"
  s=str(text)
  s=re.sub(r"(?is)<br\s*/?>","\n",s)
  s=re.sub(r"(?is)<a\s+[^>]*>(.*?)</a>",r"\1",s)
  s=re.sub(r"(?is)</?(?:b|i|em|strong|code|blockquote|p|span)[^>]*>","",s)
  s=re.sub(r"(?is)<[^>]+>","",s)
  s=re.sub(r"\[([^\]]+)\]\(([^)]+)\)",r"\1",s)
  s=re.sub(r"`([^`]+)`",r"\1",s)
  s=re.sub(r"\*\*\*([^*]+)\*\*\*",r"\1",s)
  s=re.sub(r"\*\*([^*]+)\*\*",r"\1",s)
  s=re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)",r"\1",s)
  s=re.sub(r"\[\]\([^)]*\)","",s)
  s=re.sub(r"[ \t]+\n","\n",s)
  s=re.sub(r"\n{3,}","\n\n",s)
  return s.strip() or "(пусто)"

 def _show_preview(self,from_editor=False):
  try:
   tpl=self._get_text() if from_editor else str(self.get_setting("card_template",DEFAULT_TEMPLATE) or DEFAULT_TEMPLATE)
   text=self._render_preview(tpl)
   frag=get_last_fragment()
   if not frag or not frag.getParentActivity():return
   act=frag.getParentActivity()
   b=AlertDialogBuilder(act)
   b.set_title("Превью")
   plain=self._preview_plain(text)
   try:
    from android.widget import ScrollView as _SV
    sv=_SV(act)
    tv=TextView(act)
    tv.setText(plain)
    tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP,15)
    tv.setTextColor(th(Theme.key_dialogTextBlack))
    tv.setPadding(dp(18),dp(8),dp(18),dp(8))
    try:tv.setTextIsSelectable(True)
    except:pass
    sv.addView(tv)
    b.set_view(sv)
   except Exception:
    b.set_message(plain)
   b.set_positive_button("Закрыть",lambda d,w:d.dismiss())
   b.show()
  except Exception as e:BulletinHelper.show_error(str(e))

 def _open_ph_switches(self,token,key):
  try:
   act=get_last_fragment().getParentActivity()
   if not act:return
   b=AlertDialogBuilder(act)
   b.set_title(str(key))
   wrap=LinearLayout(act)
   wrap.setOrientation(LinearLayout.VERTICAL)
   wrap.setPadding(dp(12),dp(8),dp(12),dp(8))
   wrap.setBackgroundColor(th(Theme.key_dialogBackground))
   row=LinearLayout(act)
   row.setOrientation(LinearLayout.HORIZONTAL)
   row.setPadding(dp(4),dp(8),dp(4),dp(8))
   tv=TextView(act)
   tv.setText("В шаблоне")
   tv.setTextSize(TypedValue.COMPLEX_UNIT_DIP,14)
   tv.setTextColor(th(Theme.key_dialogTextBlack))
   tv.setLayoutParams(lp(0,ViewGroup.LayoutParams.WRAP_CONTENT,1.0))
   row.addView(tv)
   st=TextView(act)
   on=self._enabled(key)
   st.setText("вкл" if on else "выкл")
   st.setTextColor(th(Theme.key_windowBackgroundWhiteBlueText) if on else th(Theme.key_windowBackgroundWhiteGrayText))
   st.setTextSize(TypedValue.COMPLEX_UNIT_DIP,13)
   row.addView(st)
   def toggle(v,sk="ph_"+key,s=st,k=key):
    newv=not self._enabled(k)
    self.set_setting(sk,newv)
    s.setText("вкл" if newv else "выкл")
    s.setTextColor(th(Theme.key_windowBackgroundWhiteBlueText) if newv else th(Theme.key_windowBackgroundWhiteGrayText))
   row.setOnClickListener(OnClickListener(toggle))
   wrap.addView(row)
   b.set_view(wrap)
   b.set_positive_button("Закрыть",lambda d,w:d.dismiss())
   b.show()
  except Exception as e:BulletinHelper.show_error(str(e))

 def _get_text(self):
  try:return str(self.editor.getText().toString()) if self.editor else ""
  except:return ""

 def _set_text(self,value,pos=None,push=True):
  try:
   if not self.editor:return
   value=str(value)
   if push:
    try:
     old=self._get_text()
     old_sel=int(self.editor.getSelectionStart() or 0)
     if old!=value:self._push_history(old,old_sel)
    except:pass
    self._push_history(value,pos if pos is not None else len(value))
   self._ignore_change=True
   self.editor.setText(value)
   sel=len(value) if pos is None else max(0,min(int(pos),len(value)))
   try:self.editor.setSelection(sel)
   except:pass
   self._ignore_change=False
  except:self._ignore_change=False

 def _append_text(self,text):
  try:
   if not self.editor:return
   old=self._get_text()
   start=max(0,int(self.editor.getSelectionStart() or 0))
   end=int(self.editor.getSelectionEnd() or start)
   new_text=old[:start]+str(text)+old[end:]
   self._set_text(new_text,start+len(text))
  except:pass

 def _push_history(self,text=None,sel=None):
  try:
   if text is None:text=self._get_text()
   if sel is None and self.editor is not None:
    try:sel=int(self.editor.getSelectionStart() or 0)
    except:sel=len(text)
   if self._hist_idx>=0 and self._hist_idx<len(self._history):
    if self._history[self._hist_idx][0]==text:
     if sel is not None:self._history[self._hist_idx]=(text,sel)
     return
   if self._hist_idx<len(self._history)-1:self._history=self._history[:self._hist_idx+1]
   self._history.append((text,sel if sel is not None else len(text)))
   if len(self._history)>20:self._history=self._history[-20:]
   self._hist_idx=len(self._history)-1
   try:self._update_bottom_style()
   except:pass
  except:pass

 def _undo(self):
  try:
   if self._hist_idx<=0 or not self.editor:return
   self._hist_idx-=1
   text,sel=self._history[self._hist_idx]
   if sel is None:sel=0
   pos=max(0,min(int(sel),len(text)))
   self._ignore_change=True
   self.editor.setText(text)
   try:self.editor.setSelection(pos,pos)
   except:
    try:self.editor.setSelection(pos)
    except:pass
   self._ignore_change=False
   try:self._update_bottom_style()
   except:pass
  except:self._ignore_change=False

 def _redo(self):
  try:
   if self._hist_idx>=len(self._history)-1 or not self.editor:return
   self._hist_idx+=1
   text,sel=self._history[self._hist_idx]
   if sel is None:sel=0
   pos=max(0,min(int(sel),len(text)))
   self._ignore_change=True
   self.editor.setText(text)
   try:self.editor.setSelection(pos,pos)
   except:
    try:self.editor.setSelection(pos)
    except:pass
   self._ignore_change=False
   try:self._update_bottom_style()
   except:pass
  except:self._ignore_change=False

 def _delete_word(self):
  try:
   if not self.editor:return
   text=self._get_text()
   pos=max(0,int(self.editor.getSelectionStart() or 0))
   if pos<=0:return
   i=pos-1
   if text[i].isspace():
    self._set_text(text[:i]+text[pos:],i)
    return
   while i>=0 and not text[i].isspace():i-=1
   start=i+1
   self._set_text(text[:start]+text[pos:],start)
  except:pass

 def _show_tip(self,text):
  try:
   act=self._activity
   if act is None:return
   Toast.makeText(act,str(text),Toast.LENGTH_SHORT).show()
  except:
   try:BulletinHelper.show_info(str(text))
   except:pass

 def _load_icon(self,act,name,color=None):
  try:
   res_id=get_drawable(name)
   if not res_id:return None
   d=ContextCompat.getDrawable(act,res_id)
   if d is not None and color is not None:
    d=d.mutate()
    d.setColorFilter(PorterDuffColorFilter(to_jcolor(color),PorterDuff.Mode.SRC_IN))
   return d
  except:return None

 def _icon_btn(self,act,icon_name,click,size=42,bg_fill=None,bg_stroke=None,icon_color=None,circle=True,tip=None):
  iv=ImageView(act)
  s=dp(size)
  iv.setLayoutParams(lp(s,s))
  try:iv.setScaleType(ImageView.ScaleType.CENTER_INSIDE)
  except:pass
  pad=dp(10)
  iv.setPadding(pad,pad,pad,pad)
  white=th(Theme.key_windowBackgroundWhite)
  fill=bg_fill if bg_fill is not None else white
  iv.setBackground(make_circle_bg(fill) if circle else make_bg(fill,None,10,0))
  try:
   sel=Theme.createSelectorDrawable(0x18000000,1)
   if sel is not None:
    try:iv.setForeground(sel)
    except:pass
  except:pass
  try:
   iv.setClickable(True)
   iv.setFocusable(True)
  except:pass
  d=self._load_icon(act,icon_name,icon_color)
  if d is not None:iv.setImageDrawable(d)
  iv.setOnClickListener(OnClickListener(lambda v,c=click:c() if callable(c) else None))
  if tip:
   try:iv.setOnLongClickListener(OnLongClickListener(lambda v,t=tip:(self._show_tip(t),True)[1]))
   except:pass
  return iv

 def _oval_icon(self,act,icon_name,click,active=False,tip=None):
  iv=ImageView(act)
  s=dp(40)
  iv.setLayoutParams(lp(s,s,0,4,2,4,2))
  try:iv.setScaleType(ImageView.ScaleType.CENTER_INSIDE)
  except:pass
  pad=dp(8)
  iv.setPadding(pad,pad,pad,pad)
  try:
   sel=Theme.createSelectorDrawable(0x21000000,1)
   if sel is not None:
    try:iv.setBackground(sel)
    except:pass
  except:pass
  try:
   iv.setClickable(True)
   iv.setFocusable(True)
  except:pass
  accent=th(Theme.key_windowBackgroundWhiteBlueText)
  text_c=th(Theme.key_windowBackgroundWhiteBlackText)
  ic=accent if active else text_c
  d=self._load_icon(act,icon_name,ic)
  if d is not None:
   try:iv.setImageDrawable(d)
   except:pass
  iv.setOnClickListener(OnClickListener(lambda v:click()))
  if tip:
   try:iv.setOnLongClickListener(OnLongClickListener(lambda v,t=tip:(self._show_tip(t),True)[1]))
   except:pass
  return iv

 def _ph_btn(self,act,sym,key,label=None):
  b=Button(act)
  b.setAllCaps(False)
  show=str(key or "").replace("{","").replace("}","")
  if not show:show=str(sym or "").replace("{","").replace("}","")
  b.setText(show)
  text_c=th(Theme.key_windowBackgroundWhiteBlackText)
  card=th(Theme.key_windowBackgroundWhite)
  b.setTextColor(int(text_c))
  b.setTextSize(TypedValue.COMPLEX_UNIT_DIP,15)
  try:b.setBackground(make_bg(th_alpha(Theme.key_windowBackgroundWhite,0xE6),None,12,0))
  except:b.setBackgroundColor(int(card))
  try:
   b.setElevation(0.0)
   b.setStateListAnimator(None)
  except:pass
  b.setPadding(dp(8),dp(8),dp(8),dp(8))
  b.setMinHeight(0)
  b.setMinimumHeight(0)
  try:
   b.setIncludeFontPadding(False)
   b.setHeight(dp(42))
  except:pass
  b.setOnClickListener(OnClickListener(lambda v,s=sym:self._append_text(s)))
  try:b.setOnLongClickListener(OnLongClickListener(lambda v,s=sym,k=key:(self._open_ph_switches(s,k),True)[1]))
  except:pass
  return b

 def _h_row(self,act,items):
  row=LinearLayout(act)
  no_clip(row)
  row.setOrientation(LinearLayout.HORIZONTAL)
  try:row.setGravity(Gravity.CENTER_VERTICAL)
  except:pass
  row.setLayoutParams(lp())
  for it in items:
   sym,key=it[0],it[1]
   if not self._enabled(key):continue
   b=self._ph_btn(act,sym,key)
   p=lp(0,dp(42),1.0,2,2,2,2)
   try:p.gravity=Gravity.CENTER_VERTICAL
   except:pass
   b.setLayoutParams(p)
   row.addView(b)
  return row

 def _single_carousel(self,act,items):
  row=LinearLayout(act)
  row.setOrientation(LinearLayout.HORIZONTAL)
  try:row.setGravity(Gravity.CENTER_VERTICAL)
  except:pass
  row.setLayoutParams(lp(ViewGroup.LayoutParams.WRAP_CONTENT,dp(46)))
  for it in items:
   sym,key=it[0],it[1]
   if not self._enabled(key):continue
   b=self._ph_btn(act,sym,key)
   p=lp(ViewGroup.LayoutParams.WRAP_CONTENT,dp(42),0,2,2,2,2)
   try:p.gravity=Gravity.CENTER_VERTICAL
   except:pass
   b.setLayoutParams(p)
   row.addView(b)
  hsv=HorizontalScrollView(act)
  hsv.setHorizontalScrollBarEnabled(False)
  try:hsv.setOverScrollMode(View.OVER_SCROLL_IF_CONTENT_SCROLLS)
  except:pass
  try:hsv.setFillViewport(False)
  except:pass
  hsv.addView(row)
  hsv.setLayoutParams(lp(ViewGroup.LayoutParams.MATCH_PARENT,dp(46)))
  return hsv

 def _vertical_block(self,act,lines):
  box=LinearLayout(act)
  box.setOrientation(LinearLayout.VERTICAL)
  box.setLayoutParams(lp())
  for line in lines:
   if not line:continue
   box.addView(self._h_row(act,line))
  try:
   for i in range(box.getChildCount()):
    ch=box.getChildAt(i)
    try:
     ch.setClipChildren(True)
     ch.setClipToPadding(True)
    except:pass
  except:pass
  row_h=dp(46)
  sv=ScrollView(act)
  sv.setVerticalScrollBarEnabled(True)
  try:sv.setOverScrollMode(View.OVER_SCROLL_IF_CONTENT_SCROLLS)
  except:pass
  try:sv.setFillViewport(False)
  except:pass
  try:
   sv.setClipChildren(True)
   sv.setClipToPadding(True)
  except:pass
  try:
   box.setClipChildren(True)
   box.setClipToPadding(True)
  except:pass
  sv.addView(box)
  sv.setLayoutParams(lp(ViewGroup.LayoutParams.MATCH_PARENT,row_h))
  try:
   class _TopClip(dynamic_proxy(OnGlobalLayoutListener)):
    def onGlobalLayout(self):
     try:
      w=int(sv.getWidth() or 0)
      h=int(sv.getHeight() or 0)
      if w>0 and h>0:
       r=Rect(0,0,w,h+dp(50))
       sv.setClipBounds(r)
       try:sv.getViewTreeObserver().removeOnGlobalLayoutListener(self)
       except:pass
     except:pass
   sv.getViewTreeObserver().addOnGlobalLayoutListener(_TopClip())
  except:pass
  return sv

 def _chunk(self,items,n):return [items[i:i+n] for i in range(0,len(items),n)]

 def _build_names_panel(self,act):
  if self._is_vertical():return self._vertical_block(act,[NAMES_RU,NAMES_EN])
  return self._single_carousel(act,NAMES_ALL)

 def _build_places_panel(self,act):
  items=[it for it in OTHERS if self._enabled(it[1])]
  if self._is_vertical():
   lines=self._chunk(items,4) or [[]]
   return self._vertical_block(act,lines)
  return self._single_carousel(act,items)

 def _set_active(self,which):
  self._active=None if self._active==which else which
  self._refresh_panel()
  self._update_bottom_style()

 def _update_spacer_for_panel(self):
  try:
   if self._bottom_spacer is None:return
   base=dp(40)+dp(24)
   extra=dp(30) if self._active=="places" else 0
   lp_s=self._bottom_spacer.getLayoutParams()
   if lp_s is not None:
    lp_s.height=base+extra
    self._bottom_spacer.setLayoutParams(lp_s)
    try:self._bottom_spacer.requestLayout()
    except:pass
  except:pass

 def _refresh_panel(self):
  try:
   if self._panel is None or self._activity is None:return
   self._panel.removeAllViews()
   if self._active=="names":self._panel.addView(self._build_names_panel(self._activity))
   elif self._active=="places":self._panel.addView(self._build_places_panel(self._activity))
   self._panel.setVisibility(View.VISIBLE if self._active else View.GONE)
   try:self._panel.setElevation(0.0)
   except:pass
   try:
    if self._bottom_blur is not None:
     self._bottom_blur.bringToFront()
     self._bottom_blur.setElevation(float(dp(4)))
   except:pass
   try:
    if self._bottom_bar is not None:
     self._bottom_bar.bringToFront()
     self._bottom_bar.setElevation(float(dp(6)))
   except:pass
   self._update_spacer_for_panel()
  except Exception as e:pass

 def _update_bottom_style(self):
  try:
   act=self._activity
   if act is None:return
   accent=th(Theme.key_windowBackgroundWhiteBlueText)
   text_c=th(Theme.key_windowBackgroundWhiteBlackText)
   gray_c=th(Theme.key_windowBackgroundWhiteGrayText)
   white=th(Theme.key_windowBackgroundWhite)
   if self._btn_mode is not None:
    icon="msg_go_down" if self._is_vertical() else "msg_arrowright"
    d=self._load_icon(act,icon,text_c)
    if d is not None:self._btn_mode.setImageDrawable(d)
   if self._btn_preview is not None:
    d=self._load_icon(act,"msg_view_file",text_c)
    if d is not None:self._btn_preview.setImageDrawable(d)
   if self._btn_names is not None:
    ic=accent if self._active=="names" else text_c
    d=self._load_icon(act,"menu_tag_rename",ic)
    if d is not None:self._btn_names.setImageDrawable(d)
   if self._btn_places is not None:
    ic=accent if self._active=="places" else text_c
    d=self._load_icon(act,"menu_tag_edit",ic)
    if d is not None:self._btn_places.setImageDrawable(d)
   can_undo=self._hist_idx>0
   can_redo=self._hist_idx<len(self._history)-1
   if self._btn_undo is not None:
    ic=text_c if can_undo else gray_c
    d=self._load_icon(act,"iv_undo",ic)
    if d is not None:self._btn_undo.setImageDrawable(d)
   if self._btn_redo is not None:
    ic=text_c if can_redo else gray_c
    d=self._load_icon(act,"iv_redo",ic)
    if d is not None:self._btn_redo.setImageDrawable(d)
   fill=th_alpha(Theme.key_windowBackgroundWhite,0xE6)
   for b in(self._btn_mode,self._btn_undo,self._btn_redo,self._btn_back,self._btn_clear,self._btn_send):
    if b is None:continue
    try:
     b.setBackground(make_circle_bg(fill))
     b.setElevation(0.0)
    except:pass
   if self._oval_group is not None:
    try:
     self._oval_group.setBackground(make_bg(fill,None,22,0))
     self._oval_group.setElevation(0.0)
    except:pass
  except:pass

 def _toggle_layout_mode(self):
  self._set_layout_mode(not self._is_vertical())

 def _set_layout_mode(self,vertical):
  self.set_setting("layout_mode",1 if vertical else 0)
  self._refresh_panel()
  self._update_bottom_style()

 def _remove_kb_listener(self):
  try:
   if self._listener is not None:
    for view in(self._root,self._activity.getWindow().getDecorView() if self._activity else None):
     if view is None:continue
     try:
      obs=view.getViewTreeObserver()
      if obs is not None and obs.isAlive():obs.removeOnGlobalLayoutListener(self._listener)
     except:pass
  except:pass
  self._listener=None
  self._last_kb=0
  self._base_inset=-1
  try:
   if self._content is not None:self._content.setTranslationY(0.0)
   if self._root is not None:self._root.setPadding(0,0,0,0)
  except:pass

 def _attach_kb_listener(self,root,act):
  self._remove_kb_listener()
  self._root=root
  self._last_kb=0
  def on_layout():
   try:
    if act is None:return
    r=Rect()
    decor=act.getWindow().getDecorView()
    decor.getWindowVisibleDisplayFrame(r)
    screen_h=int(decor.getRootView().getHeight() or decor.getHeight() or 0)
    if screen_h<=0:return
    visible=int(r.bottom)-int(r.top)
    inset=max(0,screen_h-visible)
    if inset<dp(120):self._base_inset=inset
    base=self._base_inset if self._base_inset>=0 else 0
    kb=inset-base
    if kb<dp(60):kb=0
    if kb==self._last_kb:return
    self._last_kb=kb
    try:
     if self._content is not None:self._content.setTranslationY(0.0)
     root.setPadding(0,0,0,int(kb))
     root.requestLayout()
    except:pass
   except Exception as e:pass
  class LayoutListener(dynamic_proxy(OnGlobalLayoutListener)):
   def onGlobalLayout(self):on_layout()
  listener=LayoutListener()
  self._listener=listener
  attached=False
  try:
   obs=act.getWindow().getDecorView().getViewTreeObserver()
   if obs is not None:
    obs.addOnGlobalLayoutListener(listener)
    attached=True
  except:pass
  if not attached:
   try:
    obs=root.getViewTreeObserver()
    if obs is not None:obs.addOnGlobalLayoutListener(listener)
   except:pass

 def _attach_watcher(self):
  try:
   if self.editor is None:return
   if self._watcher is not None:
    try:self.editor.removeTextChangedListener(self._watcher)
    except:pass
   plugin=self
   class Watcher(dynamic_proxy(TextWatcher)):
    def beforeTextChanged(self,s,start,count,after):
     if plugin._ignore_change:return
     try:
      if plugin.editor is not None:
       plugin._pre_sel=int(plugin.editor.getSelectionStart() or 0)
       plugin._pre_text=plugin._get_text()
     except:
      plugin._pre_sel=0
      plugin._pre_text=""
    def onTextChanged(self,s,start,before,count):pass
    def afterTextChanged(self,s):
     if plugin._ignore_change:return
     try:
      text=str(s.toString()) if s is not None else ""
      pre_t=getattr(plugin,"_pre_text",None)
      pre_s=getattr(plugin,"_pre_sel",None)
      if pre_t is not None and pre_t!=text:plugin._push_history(pre_t,pre_s if pre_s is not None else 0)
      try:cur=int(plugin.editor.getSelectionStart() or 0) if plugin.editor is not None else len(text)
      except:cur=len(text)
      plugin._push_history(text,cur)
     except:pass
   self._watcher=Watcher()
   self.editor.addTextChangedListener(self._watcher)
  except Exception as e:pass

 def open_keyboard(self):
  try:
   act=get_last_fragment().getParentActivity()
   if not act:return BulletinHelper.show_error("Activity not found")
   if self.current_dialog is not None:
    try:
     self._remove_kb_listener()
     self.current_dialog.dismiss()
    except:pass
    self.current_dialog=None
   self._activity=act
   self._active=None
   self._history=[]
   self._hist_idx=-1
   self._ignore_change=False
   bg=th(Theme.key_windowBackgroundWhite)
   text_c=th(Theme.key_windowBackgroundWhiteBlackText)
   hint_c=th(Theme.key_windowBackgroundWhiteGrayText)
   card=th(Theme.key_windowBackgroundWhite)
   border=th(Theme.key_divider)
   accent=th(Theme.key_windowBackgroundWhiteBlueText)
   white=th(Theme.key_windowBackgroundWhite)
   try:theme=AndroidR.style.Theme_Black_NoTitleBar_Fullscreen
   except:
    try:theme=AndroidR.style.Theme_DeviceDefault_NoActionBar
    except:theme=16973834
   dialog=Dialog(act,theme)
   root=LinearLayout(act)
   root.setOrientation(LinearLayout.VERTICAL)
   root.setBackgroundColor(int(bg))
   root.setLayoutParams(lp(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.MATCH_PARENT))
   content=LinearLayout(act)
   content.setOrientation(LinearLayout.VERTICAL)
   content.setPadding(dp(8),dp(2),dp(8),dp(0))
   content.setBackgroundColor(int(bg))
   content.setLayoutParams(lp(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.MATCH_PARENT))
   self._content=content
   sb_height=getattr(AndroidUtilities,"statusBarHeight",dp(24)) or dp(24)
   extra=40
   head_h=int(sb_height)+dp(extra)
   frame=FrameLayout(act)
   frame.setLayoutParams(lp(ViewGroup.LayoutParams.MATCH_PARENT,0,1.0))
   try:
    frame.setClipChildren(False)
    frame.setClipToPadding(False)
    try:frame.setClipToOutline(False)
    except:pass
    no_clip(frame)
   except:pass
   sv=ScrollView(act)
   sv.setVerticalScrollBarEnabled(True)
   try:sv.setFillViewport(True)
   except:pass
   sv.setLayoutParams(FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.MATCH_PARENT))
   editor_container=LinearLayout(act)
   editor_container.setOrientation(LinearLayout.VERTICAL)
   editor_container.setLayoutParams(lp())
   editor_container.setPadding(0,head_h,0,0)
   self.editor=EditText(act)
   self.editor.setHint("Шаблон карточки AniList")
   self.editor.setMinLines(6)
   self.editor.setTextSize(TypedValue.COMPLEX_UNIT_DIP,22)
   self.editor.setTextColor(int(text_c))
   try:self.editor.setHintTextColor(int(hint_c))
   except:pass
   self.editor.setBackground(make_bg(th_alpha(Theme.key_windowBackgroundWhite,0xE6),None,12,0))
   self.editor.setPadding(dp(10),dp(10),dp(10),dp(10))
   self.editor.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_MULTI_LINE)
   try:
    self.editor.setHorizontallyScrolling(False)
    self.editor.setGravity(Gravity.TOP|Gravity.START)
   except:pass
   try:
    tpl=str(self.get_setting("card_template",DEFAULT_TEMPLATE) or DEFAULT_TEMPLATE)
    self.editor.setText(tpl)
    self._push_history(tpl,None)
   except:pass
   ed_lp=lp()
   self.editor.setLayoutParams(ed_lp)
   editor_container.addView(self.editor)
   bottom_spacer=View(act)
   bottom_spacer.setLayoutParams(lp(ViewGroup.LayoutParams.MATCH_PARENT,dp(40)+dp(24)))
   editor_container.addView(bottom_spacer)
   self._bottom_spacer=bottom_spacer
   sv.addView(editor_container)
   frame.addView(sv)
   top_bar_h=dp(40)
   head_blur=View(act)
   head_blur_lp=FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,max(int(sb_height)+top_bar_h,head_h))
   try:head_blur_lp.gravity=Gravity.TOP
   except:pass
   head_blur_lp.setMargins(0,0,0,0)
   head_blur.setLayoutParams(head_blur_lp)
   try:
    Orientation=getattr(GradientDrawable,"Orientation")
    colors=[th_alpha(Theme.key_windowBackgroundWhite,0xE6),th_alpha(Theme.key_windowBackgroundWhite,0xCC),th_alpha(Theme.key_windowBackgroundWhite,0x00)]
    g=GradientDrawable(Orientation.TOP_BOTTOM,colors)
    g.setShape(GradientDrawable.RECTANGLE)
    head_blur.setBackground(g)
   except:
    try:head_blur.setBackgroundColor(to_jcolor(white))
    except:head_blur.setBackgroundColor(to_jcolor(white))
   self._head_blur=head_blur
   frame.addView(head_blur)
   head=LinearLayout(act)
   no_clip(head)
   head.setOrientation(LinearLayout.HORIZONTAL)
   try:head.setGravity(Gravity.CENTER_VERTICAL)
   except:pass
   head.setPadding(dp(2),int(sb_height),dp(2),dp(2))
   head_lp=FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT)
   try:head_lp.gravity=Gravity.TOP
   except:pass
   head.setLayoutParams(head_lp)
   try:head.setBackground(ColorDrawable(0))
   except:pass
   try:head.setWillNotDraw(True)
   except:pass
   self._head_bar=head
   def do_close():
    self._remove_kb_listener()
    dialog.dismiss()
   self._btn_back=self._icon_btn(act,"ic_ab_back",do_close,42,None,border,text_c,True,"Выход")
   back_lp=lp(dp(42),dp(42),0,0,0,4,0)
   self._btn_back.setLayoutParams(back_lp)
   head.addView(self._btn_back)
   spacer_head=View(act)
   spacer_head.setLayoutParams(lp(0,1,1.0))
   head.addView(spacer_head)
   self._btn_undo=self._icon_btn(act,"iv_undo",self._undo,42,None,border,text_c,True,"Отменить")
   undo_lp=lp(dp(42),dp(42),0,0,0,4,0)
   self._btn_undo.setLayoutParams(undo_lp)
   head.addView(self._btn_undo)
   self._btn_redo=self._icon_btn(act,"iv_redo",self._redo,42,None,border,text_c,True,"Повторить")
   redo_lp=lp(dp(42),dp(42))
   self._btn_redo.setLayoutParams(redo_lp)
   head.addView(self._btn_redo)
   frame.addView(head)
   try:
    def sync_head(v=None):
     try:
      h=head.getHeight()
      if h>0 and self._head_blur is not None:
       lp_b=self._head_blur.getLayoutParams()
       want=max(h,int(sb_height)+top_bar_h,head_h)
       lp_b.height=want
       self._head_blur.setLayoutParams(lp_b)
     except:pass
    class HeadLayout(dynamic_proxy(OnGlobalLayoutListener)):
     def onGlobalLayout(self):sync_head()
    head.getViewTreeObserver().addOnGlobalLayoutListener(HeadLayout())
   except:pass
   self._attach_watcher()
   panel=LinearLayout(act)
   panel.setOrientation(LinearLayout.VERTICAL)
   panel.setVisibility(View.GONE)
   try:panel.setElevation(float(dp(0)))
   except:pass
   self._panel=panel
   no_clip(panel)
   panel_lp=FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT)
   try:panel_lp.gravity=Gravity.BOTTOM
   except:pass
   panel_lp.setMargins(0,0,0,dp(40)+dp(0)+dp(2))
   panel.setLayoutParams(panel_lp)
   frame.addView(panel)
   bottom_bar_h=dp(40)
   bottom_blur=View(act)
   bottom_blur_lp=FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,bottom_bar_h+dp(0))
   try:bottom_blur_lp.gravity=Gravity.BOTTOM
   except:pass
   bottom_blur_lp.setMargins(0,0,0,0)
   bottom_blur.setLayoutParams(bottom_blur_lp)
   try:
    Orientation=getattr(GradientDrawable,"Orientation")
    colors=[th_alpha(Theme.key_windowBackgroundWhite,0x00),th_alpha(Theme.key_windowBackgroundWhite,0xCC),th_alpha(Theme.key_windowBackgroundWhite,0xE6)]
    g=GradientDrawable(Orientation.TOP_BOTTOM,colors)
    g.setShape(GradientDrawable.RECTANGLE)
    bottom_blur.setBackground(g)
   except:
    try:bottom_blur.setBackgroundColor(to_jcolor(white))
    except:bottom_blur.setBackgroundColor(to_jcolor(white))
   self._bottom_blur=bottom_blur
   frame.addView(bottom_blur)
   bottom=LinearLayout(act)
   no_clip(bottom)
   bottom.setOrientation(LinearLayout.HORIZONTAL)
   try:bottom.setGravity(Gravity.CENTER_VERTICAL)
   except:pass
   bottom.setPadding(dp(4),dp(4),dp(4),dp(6))
   try:bottom.setBackground(ColorDrawable(0))
   except:pass
   try:bottom.setWillNotDraw(True)
   except:pass
   bottom_lp=FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT)
   try:bottom_lp.gravity=Gravity.BOTTOM
   except:pass
   bottom_lp.setMargins(0,0,0,dp(0))
   bottom.setLayoutParams(bottom_lp)
   self._bottom_bar=bottom
   def do_save():
    text=self._get_text()
    try:
     self.set_setting("card_template",text,reload_settings=True)
    except TypeError:
     self.set_setting("card_template",text)
    try:
     self._host.update_settings()
    except Exception:
     pass
    try:
     self._host.set_setting("__preview_tick",str(hash(text)&0xFFFFFFFF),reload_settings=True)
    except Exception:
     pass
    try:
     self._remove_kb_listener()
     dialog.dismiss()
    except Exception:
     pass
   orient_icon="msg_go_down" if self._is_vertical() else "msg_arrowright"
   self._btn_mode=self._icon_btn(act,orient_icon,self._toggle_layout_mode,42,None,border,text_c,True,"Раскладка")
   mode_lp=lp(dp(42),dp(42),0,4,0,8,0)
   self._btn_mode.setLayoutParams(mode_lp)
   bottom.addView(self._btn_mode)
   oval=LinearLayout(act)
   no_clip(oval)
   oval.setOrientation(LinearLayout.HORIZONTAL)
   try:oval.setGravity(Gravity.CENTER_VERTICAL)
   except:pass
   oval.setBackground(make_bg(white,None,22,0))
   try:oval.setElevation(0.0)
   except:pass
   oval.setPadding(dp(6),dp(2),dp(6),dp(2))
   oval_lp=lp(ViewGroup.LayoutParams.WRAP_CONTENT,dp(44),0,0,0,8,0)
   oval.setLayoutParams(oval_lp)
   self._oval_group=oval
   self._btn_preview=self._oval_icon(act,"msg_view_file",lambda:self._show_preview(True),False,"Превью")
   oval.addView(self._btn_preview)
   self._btn_names=self._oval_icon(act,"menu_tag_rename",lambda:self._set_active("names"),False,"Названия")
   oval.addView(self._btn_names)
   self._btn_places=self._oval_icon(act,"menu_tag_edit",lambda:self._set_active("places"),False,"Плейсы")
   oval.addView(self._btn_places)
   bottom.addView(oval)
   spacer=View(act)
   spacer.setLayoutParams(lp(0,1,1.0))
   bottom.addView(spacer)
   self._btn_clear=self._icon_btn(act,"msg_clear_input",self._delete_word,42,None,border,text_c,True,"Удалить слово")
   clear_lp=lp(dp(42),dp(42),0,0,0,8,0)
   self._btn_clear.setLayoutParams(clear_lp)
   bottom.addView(self._btn_clear)
   self._btn_send=self._icon_btn(act,"msg_filled_sdcard",do_save,42,None,border,text_c,True,"Сохранить")
   send_lp=lp(dp(42),dp(42),0,0,0,4,0)
   self._btn_send.setLayoutParams(send_lp)
   bottom.addView(self._btn_send)
   frame.addView(bottom)
   try:
    def sync_bot(v=None):
     try:
      h=bottom.getHeight()
      if h>0 and self._bottom_blur is not None:
       lp_b=self._bottom_blur.getLayoutParams()
       lp_b.height=max(h,bottom_bar_h)+dp(0)
       try:lp_b.setMargins(0,0,0,0)
       except:pass
       self._bottom_blur.setLayoutParams(lp_b)
      if self._panel is not None:
       lp_p=self._panel.getLayoutParams()
       gap=dp(2)
       want=int(h)+gap if h>0 else dp(40)+dp(0)+gap
       try:lp_p.setMargins(0,0,0,want)
       except:pass
       self._panel.setLayoutParams(lp_p)
      self._update_spacer_for_panel()
     except:pass
    class BotLayout(dynamic_proxy(OnGlobalLayoutListener)):
     def onGlobalLayout(self):sync_bot()
    bottom.getViewTreeObserver().addOnGlobalLayoutListener(BotLayout())
   except:pass
   content.addView(frame)
   self._update_bottom_style()
   root.addView(content)
   dialog.setContentView(root)
   dialog.setCancelable(True)
   dialog.setCanceledOnTouchOutside(True)
   try:dialog.setOnDismissListener(lambda d:self._remove_kb_listener())
   except:pass
   window=dialog.getWindow()
   if window is not None:
    try:
     decor=window.getDecorView()
     if decor is not None:decor.setSystemUiVisibility(View.SYSTEM_UI_FLAG_LAYOUT_STABLE|View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN)
     window.setBackgroundDrawable(ColorDrawable(int(bg)))
     window.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_NOTHING|WindowManager.LayoutParams.SOFT_INPUT_STATE_HIDDEN)
     window.clearFlags(0x04000000|0x08000000)
     window.addFlags(0x80000000)
     try:
      window.setStatusBarColor(int(bg))
      window.setNavigationBarColor(int(bg))
     except:pass
     try:window.setDimAmount(0.0)
     except:pass
     wlp=window.getAttributes()
     wlp.width=ViewGroup.LayoutParams.MATCH_PARENT
     wlp.height=ViewGroup.LayoutParams.MATCH_PARENT
     try:
      wlp.gravity=Gravity.TOP
      wlp.y=0
     except:pass
     window.setAttributes(wlp)
     window.setLayout(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.MATCH_PARENT)
    except:pass
   self.current_dialog=dialog
   dialog.show()
   self._attach_kb_listener(root,act)
  except Exception as e:
   BulletinHelper.show_error(str(e))
