from __future__ import annotations
import math, types
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QBrush, QRadialGradient
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget
import ui_overhaul as base
self=None
APP_NAME="StudyLock"
class AuraLogo(base.AuraLogo):
    def __init__(self,accent="#8B7CFF",parent=None):
        super().__init__(accent,parent); self.setFixedSize(86,86); self.phase=0.0; self.setToolTip("AURA — protected focus"); self.setAccessibleName("AURA protected focus logo")
    def _animate(self): self.phase=(self.phase+0.014)%1.0; self.update()
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); cx,cy=self.width()/2,self.height()/2; c=QPointF(cx,cy); t=self.phase*math.tau; pulse=1+0.035*math.sin(t*1.7)
        aura=QRadialGradient(c,39); z=QColor(self.accent); z.setAlpha(0); m=QColor(self.accent); m.setAlpha(42); h=QColor(self.accent); h.setAlpha(105); aura.setColorAt(0,h); aura.setColorAt(.35,m); aura.setColorAt(1,z); p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(aura)); p.drawEllipse(c,38*pulse,38*pulse)
        for radius,speed,sweep,alpha,width in ((31,2,92,235,2.6),(25,-1.25,118,205,2.2),(20,.72,150,175,1.7)):
            col=QColor(self.accent); col.setAlpha(alpha); p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(QPen(col,width,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap)); start=(t*speed*180/math.pi+radius*3)%360; p.drawArc(int(cx-radius),int(cy-radius),int(radius*2),int(radius*2),int(-start*16),int(-sweep*16)); p.drawArc(int(cx-radius),int(cy-radius),int(radius*2),int(radius*2),int((180-start)*16),int(sweep*.45*16))
        for i,(angle,radius,size) in enumerate(((18,31,2.3),(142,25,2),(255,29,1.8),(326,21,2.1))):
            a=math.radians(angle)+t*(.22+i*.07); r=radius+math.sin(t*(1.2+i*.17)+i)*1.5; x,y=cx+math.cos(a)*r,cy+math.sin(a)*r; col=QColor(self.accent); col.setAlpha(170+int(65*(.5+.5*math.sin(t*2+i)))); p.setBrush(col); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(QPointF(x,y),size,size)
        core=QPainterPath(); core.moveTo(cx,cy-19); core.cubicTo(cx+14,cy-16,cx+17,cy-5,cx+13,cy+9); core.cubicTo(cx+9,cy+20,cx+3,cy+23,cx,cy+24); core.cubicTo(cx-3,cy+23,cx-9,cy+20,cx-13,cy+9); core.cubicTo(cx-17,cy-5,cx-14,cy-16,cx,cy-19); p.setBrush(QColor(8,13,22,246)); p.setPen(QPen(self.accent,2.5,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin)); p.drawPath(core)
        inner=QColor(self.accent); inner.setAlpha(42); p.setBrush(inner); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(c,12,12); p.setBrush(QColor(245,247,255,242)); p.drawEllipse(QPointF(cx,cy-4),4.3,4.3); p.drawRoundedRect(int(cx-2.2),int(cy-1),4.4,11,2.2,2.2); p.setPen(QPen(self.accent,1.8,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
        for dx,dy in ((0,-35),(35,0),(0,35),(-35,0)): p.drawLine(QPointF(cx+dx*.72,cy+dy*.72),QPointF(cx+dx*.86,cy+dy*.86))
def _cell(value): return (lambda v:(lambda:v))(value).__closure__[0]
def _rebind_tree(function,instance,seen=None):
    if not isinstance(function,types.FunctionType): return function
    seen=set() if seen is None else seen
    if id(function) in seen: return function
    seen.add(id(function)); closure=function.__closure__
    if not closure: return function
    cells=list(closure); changed=False
    for i,c in enumerate(closure):
        try: value=c.cell_contents
        except ValueError: continue
        if value is base.MainWindow if hasattr(base,"MainWindow") else False:
            cells[i]=_cell(instance); changed=True
        elif isinstance(value,type) and value.__name__=="MainWindow" and value.__module__=="main":
            cells[i]=_cell(instance); changed=True
        elif isinstance(value,types.FunctionType):
            rebound=_rebind_tree(value,instance,seen)
            if rebound is not value: cells[i]=_cell(rebound); changed=True
    if not changed: return function
    return types.FunctionType(function.__code__,function.__globals__,function.__name__,function.__defaults__,tuple(cells))
def _replace_cell(fn,predicate,replacement):
    cells=list(fn.__closure__ or ())
    for i,cell in enumerate(cells):
        try: value=cell.cell_contents
        except ValueError: continue
        if predicate(value): cells[i]=_cell(replacement); return types.FunctionType(fn.__code__,fn.__globals__,fn.__name__,fn.__defaults__,tuple(cells))
    return fn
def _normalize_build(fn):
    runtime=base.self
    fn=_rebind_tree(fn,runtime)
    for cell in fn.__closure__ or ():
        try: value=cell.cell_contents
        except ValueError: continue
        if getattr(value,"__name__",None)=="make_header":
            def factory(helper):
                def fixed(): return helper(base.self)
                return fixed
            fn=_replace_cell(fn,lambda current,target=value:current is target,factory(value)); break
    return fn
def _settings_page(TimerSettings,save_settings,w):
    page=QWidget(); outer=QVBoxLayout(page); outer.setContentsMargins(38,26,38,36); outer.setSpacing(16); top=QHBoxLayout(); back=QPushButton("←  Back"); back.setObjectName("ghost"); back.clicked.connect(lambda:w.go_page(w.home_page,-1)); top.addWidget(back); top.addStretch(); outer.addLayout(top); title=QLabel("Settings"); title.setObjectName("pageHeading"); outer.addWidget(title); sub=QLabel("Everything that controls your StudyLock experience, in one place."); sub.setObjectName("pageSubtitle"); outer.addWidget(sub)
    account=base.RippleCard(base.THEMES[w.settings.get("theme","Aura Purple")]["accent"]); account.setObjectName("panel"); al=QVBoxLayout(account); al.setContentsMargins(22,20,22,20); e=QLabel("ACCOUNT"); e.setObjectName("eyebrow"); al.addWidget(e); ar=QHBoxLayout(); txt=QVBoxLayout(); n=QLabel("Local StudyLock account"); n.setStyleSheet("font-size:18px;font-weight:750;"); txt.addWidget(n); st=QLabel("Not connected • sign-in is a placeholder for now"); st.setObjectName("muted"); txt.addWidget(st); ar.addLayout(txt,1); login=QPushButton("SIGN IN"); login.setObjectName("primary"); login.clicked.connect(lambda:QMessageBox.information(w,"Account","Account login is a placeholder. No online account service is connected yet.")); ar.addWidget(login); al.addLayout(ar); outer.addWidget(account)
    timer=base.RippleCard(base.THEMES[w.settings.get("theme","Aura Purple")]["accent"]); timer.setObjectName("panel"); tl=QVBoxLayout(timer); tl.setContentsMargins(22,20,22,20); e=QLabel("TIMER & QUESTION CONTROL"); e.setObjectName("eyebrow"); tl.addWidget(e); row=QHBoxLayout(); info=QVBoxLayout(); info.addWidget(QLabel("Question interval")); h=QLabel("How often StudyLock pauses the game for a question."); h.setObjectName("muted"); info.addWidget(h); row.addLayout(info,1); interval=QSpinBox(); interval.setRange(1,3600); interval.setValue(int(w.settings.get("interval",20))); interval.setSuffix(" sec"); interval.setFixedWidth(130); row.addWidget(interval); tl.addLayout(row); actions=QHBoxLayout(); actions.addStretch(); advanced=QPushButton("ADVANCED TIMER APPEARANCE")
    def adv():
        d=TimerSettings(w.settings,w)
        if d.exec(): save_settings(w.settings); w.refresh_status()
    advanced.clicked.connect(adv); save=QPushButton("SAVE TIMER SETTINGS"); save.setObjectName("primary")
    def save_timer(): w.settings["interval"]=interval.value(); save_settings(w.settings); w.refresh_status(); w.update_dashboard_labels()
    save.clicked.connect(save_timer); actions.addWidget(advanced); actions.addWidget(save); tl.addLayout(actions); outer.addWidget(timer)
    appearance=QWidget(); av=QVBoxLayout(appearance); av.setContentsMargins(0,0,0,0); e=QLabel("APPEARANCE"); e.setObjectName("eyebrow"); av.addWidget(e); h=QLabel("Choose the AURA color language for the entire app."); h.setObjectName("muted"); av.addWidget(h); grid=QGridLayout(); w.settings_theme_cards=[]
    for i,(name,data) in enumerate(base.THEMES.items()):
        card=base.ThemeCard(name,data); card.clicked.connect(lambda name=name:w.select_theme(name)); w.settings_theme_cards.append(card); grid.addWidget(card,i//2,i%2)
    av.addLayout(grid); outer.addWidget(appearance); more=base.RippleCard(base.THEMES[w.settings.get("theme","Aura Purple")]["accent"]); more.setObjectName("panel"); ml=QVBoxLayout(more); e=QLabel("MORE SETTINGS"); e.setObjectName("eyebrow"); ml.addWidget(e); f=QLabel("Reserved for future StudyLock options — notifications, accessibility, behavior and more."); f.setObjectName("muted"); f.setWordWrap(True); ml.addWidget(f); outer.addWidget(more); outer.addStretch(); return page
def install_ui(*args,**kwargs):
    global self,APP_NAME
    MainWindow,GamePicker,TimerSettings,PerformanceDialog=args[:4]; self=MainWindow; APP_NAME=getattr(base,"APP_NAME","StudyLock"); base.self=MainWindow; base.APP_NAME=APP_NAME; base.AuraLogo=AuraLogo; base.install_ui(*args,**kwargs); stable_build_source=MainWindow.build_ui; save_settings=args[-1]
    def build_ui_plus():
        w=base.self; base.self=w; stable_build=_normalize_build(stable_build_source); stable_build.__globals__["self"]=w; stable_build(); w.settings_page=_settings_page(TimerSettings,save_settings,w); w.stack.addWidget(w.settings_page); root=w.home_page.widget()
        for card in root.findChildren(base.RippleCard):
            for label in [x for x in card.findChildren(QLabel) if x.text().strip().lower().startswith("change")]:
                button=QPushButton("CHANGE"); button.setObjectName("cardAction"); card.layout().replaceWidget(label,button); label.deleteLater(); button.clicked.connect(card.clicked.emit)
        for card in root.findChildren(base.RippleCard):
            text=" ".join(x.text() for x in card.findChildren(QLabel))
            if "Question Interval" in text:
                try: card.clicked.disconnect()
                except (TypeError,RuntimeError): pass
                card.clicked.connect(lambda:w.go_page(w.settings_page,1))
        w.apply_theme()
    def open_settings(): base.self.go_page(base.self.settings_page,1)
    MainWindow.build_ui=build_ui_plus; MainWindow.open_quick_settings=open_settings; original_apply=MainWindow.apply_theme
    def apply_theme_plus(self):
        w=self
        # MainWindow.apply_theme is a method on the class, but original_apply is
        # captured as the raw function object. Call it with the instance explicitly
        # so Python does not leave the nested ui_overhaul.apply_theme(self) unbound.
        original_apply(w)
        for card in getattr(w,"settings_theme_cards",[]):
            card.set_selected(card.name==w.settings.get("theme"))
    MainWindow.apply_theme=apply_theme_plus
