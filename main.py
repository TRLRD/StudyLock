import json, os, random, sys, time, ctypes
from pathlib import Path
from typing import Any
import psutil
from PySide6.QtCore import QTimer, Qt, QRect, QPropertyAnimation, QEasingCurve, QPointF
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QColorDialog, QGraphicsOpacityEffect, QProgressBar, QFrame
)
from curriculum import available_curricula, filter_questions, subjects_for, stages_for, papers_for
from sample_questions import questions as bundled_questions

APP_NAME='StudyLock'
DATA_DIR=Path(os.getenv('APPDATA',str(Path.home())))/APP_NAME
DATA_DIR.mkdir(parents=True,exist_ok=True)
QUESTIONS_FILE=DATA_DIR/'questions.json'; STATS_FILE=DATA_DIR/'stats.json'; SETTINGS_FILE=DATA_DIR/'settings.json'
DEFAULT_TIMER={'size':18,'color':'#ffffff','corner':'top-right','resolution':'auto'}
DEFAULT_SETTINGS={'game':{},'interval':20,'timer':DEFAULT_TIMER,'reduced_motion':False}

def norm(v:Any)->str:
    return ' '.join(str(v).strip().lower().replace('²','2').replace('³','3').replace('−','-').replace('×','x').split())

def atomic_write(p,v):
    t=p.with_name(p.name+'.tmp'); t.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8'); t.replace(p)

def load_json(p,d):
    try:return json.loads(p.read_text(encoding='utf-8')) if p.exists() else d
    except Exception:return d

def validate_questions(data):
    data=data.get('questions') if isinstance(data,dict) else data
    if not isinstance(data,list): raise ValueError('Question data must be a list.')
    cats={c.id:c for c in available_curricula()}; out=[]; ids=set()
    for i,q in enumerate(data,1):
        if not isinstance(q,dict) or not str(q.get('question','')).strip() or not isinstance(q.get('answers'),list) or not q['answers']:
            raise ValueError(f'Question {i} is invalid.')
        cid=norm(q.get('curriculum','gcse')); sub=str(q.get('subject','Chemistry')); stage=str(q.get('qualification_stage','A Level'))
        if cid not in cats or sub not in cats[cid].subjects or stage not in cats[cid].qualification_stages:
            raise ValueError(f'Question {i}: course metadata is invalid.')
        qid=str(q.get('id') or f'q-{i}')
        if qid in ids: raise ValueError(f'Duplicate question id: {qid}')
        ids.add(qid)
        out.append({**q,'id':qid,'question':str(q['question']),'choices':[str(x) for x in q.get('choices',[])],
            'answers':[str(x) for x in q['answers']],'topic':str(q.get('topic') or 'General'),
            'subtopic':str(q.get('subtopic') or ''),'difficulty':str(q.get('difficulty') or 'Normal'),
            'curriculum':cid,'subject':sub,'qualification_stage':stage,'paper':str(q.get('paper') or 'all'),
            'numeric_tolerance':max(0,float(q.get('numeric_tolerance',0))),
            'exam_board':str(q.get('exam_board') or ''),'paper_reference':str(q.get('paper_reference') or ''),
            'year':str(q.get('year') or ''),'session':str(q.get('session') or ''),'source':str(q.get('source') or 'original')})
    return out

def ensure_questions():
    seed=bundled_questions(); data=load_json(QUESTIONS_FILE,None)
    if data is None:
        atomic_write(QUESTIONS_FILE,{'questions':seed}); return seed
    try:return validate_questions(data)
    except Exception:return seed

def load_stats():
    s=load_json(STATS_FILE,{'questions':{},'sessions':0,'total_answered':0,'total_correct':0})
    return s if isinstance(s,dict) else {'questions':{},'sessions':0,'total_answered':0,'total_correct':0}

def save_stats(s): atomic_write(STATS_FILE,s)

def load_settings():
    s=load_json(SETTINGS_FILE,{}); s=s if isinstance(s,dict) else {}
    for k,v in DEFAULT_SETTINGS.items(): s.setdefault(k,v.copy() if isinstance(v,dict) else v)
    s['timer']={**DEFAULT_TIMER,**(s.get('timer') or {})}; return s

def save_settings(s): atomic_write(SETTINGS_FILE,s)

def process_rows():
    out=[];seen=set()
    for p in psutil.process_iter(['pid','name','exe']):
        try:
            n=p.info.get('name') or ''; e=Path(p.info.get('exe') or n).name; pid=int(p.info['pid']); k=(norm(n),norm(e))
            if n and pid>0 and k not in seen: seen.add(k); out.append((n,pid,e))
        except (psutil.NoSuchProcess,psutil.AccessDenied,psutil.ZombieProcess,OSError): pass
    return sorted(out,key=lambda x:norm(x[0]))

def foreground():
    if sys.platform!='win32': return 0,0
    try:
        h=int(ctypes.windll.user32.GetForegroundWindow()); p=ctypes.c_ulong(0)
        if not h:return 0,0
        ctypes.windll.user32.GetWindowThreadProcessId(h,ctypes.byref(p)); return h,int(p.value)
    except Exception:return 0,0

def window_rect(h):
    try:
        class R(ctypes.Structure): _fields_=[('l',ctypes.c_long),('t',ctypes.c_long),('r',ctypes.c_long),('b',ctypes.c_long)]
        r=R()
        if ctypes.windll.user32.GetWindowRect(h,ctypes.byref(r)): return QRect(r.l,r.t,r.r-r.l,r.b-r.t)
    except Exception: pass
    return None

def topmost(h):
    if sys.platform=='win32' and h:
        try: ctypes.windll.user32.SetWindowPos(h,-1,0,0,0,0,0x0002|0x0001|0x0040)
        except Exception: pass

STYLE='''
QWidget{background:#0b0e14;color:#eef2f7;font-family:"Segoe UI";font-size:14px;}
QMainWindow{background:#080b10;}
QFrame#card{background:#111722;border:1px solid #202a39;border-radius:14px;}
QLabel#title{font-size:30px;font-weight:700;}
QLabel#muted{color:#8d98aa;}
QLineEdit,QComboBox,QSpinBox{background:#0d131d;border:1px solid #273244;border-radius:9px;padding:9px;color:#eef2f7;}
QLineEdit:focus,QComboBox:focus,QSpinBox:focus{border:1px solid #5c7cff;}
QPushButton{background:#182131;border:1px solid #2a374a;border-radius:10px;padding:10px 14px;font-weight:600;}
QPushButton:hover{background:#26334a;border-color:#5c7cff;}
QPushButton:pressed{background:#33445f;padding-top:11px;padding-bottom:9px;}
QPushButton#primary{background:#4f6fff;border-color:#718aff;color:white;}
QPushButton#primary:hover{background:#6683ff;}
QTableWidget{background:#0d131d;border:1px solid #202a39;border-radius:10px;gridline-color:#202a39;}
QHeaderView::section{background:#151d2a;padding:9px;border:0;font-weight:700;}
QProgressBar{background:#0c121b;border:1px solid #263244;border-radius:7px;text-align:center;height:12px;}
QProgressBar::chunk{background:#5c7cff;border-radius:6px;}
'''

class GamePicker(QDialog):
    def __init__(self,parent=None,selected=None):
        super().__init__(parent); self.setWindowTitle('Select game'); self.resize(760,540); self.selected=None
        v=QVBoxLayout(self); v.addWidget(QLabel('Select the Windows game/app StudyLock should monitor. Other apps remain usable.'))
        self.search=QLineEdit(); self.search.setPlaceholderText('Search application…'); v.addWidget(self.search)
        self.table=QTableWidget(0,3); self.table.setHorizontalHeaderLabels(['Application','PID','Executable']); self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers); v.addWidget(self.table)
        r=QHBoxLayout(); refresh=QPushButton('Refresh'); refresh.clicked.connect(self.populate); r.addWidget(refresh); r.addStretch(); box=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel); box.accepted.connect(self.accept_choice); box.rejected.connect(self.reject); r.addWidget(box); v.addLayout(r)
        self.search.textChanged.connect(self.populate); self.populate(); self.preselect(selected or {})
    def populate(self):
        q=norm(self.search.text()); self.table.setRowCount(0)
        for n,p,e in process_rows():
            if q and q not in norm(n) and q not in norm(e): continue
            row=self.table.rowCount(); self.table.insertRow(row)
            for c,x in enumerate((n,p,e)): self.table.setItem(row,c,QTableWidgetItem(str(x)))
    def preselect(self,s):
        for r in range(self.table.rowCount()):
            if s.get('exe') and norm(self.table.item(r,2).text())==norm(s['exe']): self.table.selectRow(r); break
    def accept_choice(self):
        rows=self.table.selectionModel().selectedRows()
        if not rows:return QMessageBox.warning(self,APP_NAME,'Select a game first.')
        r=rows[0].row(); self.selected={'name':self.table.item(r,0).text(),'pid':int(self.table.item(r,1).text()),'exe':self.table.item(r,2).text()}; self.accept()

class TimerSettings(QDialog):
    def __init__(self,s,parent=None):
        super().__init__(parent); self.setWindowTitle('Timer Settings'); self.s=s
        v=QVBoxLayout(self); f=QFormLayout(); t=s['timer']
        self.size=QSpinBox(); self.size.setRange(10,72); self.size.setValue(int(t['size'])); self.size.setSuffix(' px'); f.addRow('Timer size',self.size)
        self.corner=QComboBox(); self.corner.addItems(['top-left','top-right','bottom-left','bottom-right']); self.corner.setCurrentText(t['corner']); f.addRow('Timer position',self.corner)
        self.res=QComboBox(); self.res.addItems(['Auto (display)','1920x1080','1600x900','1366x768','1280x720']); self.res.setCurrentText('Auto (display)' if t['resolution']=='auto' else t['resolution']); f.addRow('Question resolution',self.res)
        self.color=QPushButton(t['color']); self.color.clicked.connect(self.pick_color); f.addRow('Timer color',self.color); v.addLayout(f)
        v.addWidget(QLabel('The question overlay is clamped to the physical display so it cannot extend off-screen.'))
        box=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel); box.accepted.connect(self.save); box.rejected.connect(self.reject); v.addWidget(box)
    def pick_color(self):
        c=QColorDialog.getColor(QColor(self.color.text()),self)
        if c.isValid(): self.color.setText(c.name())
    def save(self):
        self.s['timer']={'size':self.size.value(),'corner':self.corner.currentText(),'resolution':'auto' if self.res.currentText().startswith('Auto') else self.res.currentText(),'color':self.color.text()}; self.accept()

class TimerHUD(QWidget):
    def __init__(self,s):
        super().__init__(); self.s=s; self.last=None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.Tool); self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        v=QVBoxLayout(self); v.setContentsMargins(7,4,7,4); self.label=QLabel('00:00'); self.label.setAlignment(Qt.AlignmentFlag.AlignCenter); v.addWidget(self.label)
        self.anim=QPropertyAnimation(self.label,b'windowOpacity',self); self.anim.setDuration(430); self.anim.setStartValue(1); self.anim.setEndValue(.35); self.anim.setEasingCurve(QEasingCurve.Type.InOutSine); self.anim.setLoopCount(2); self.apply()
    def apply(self):
        t=self.s['timer']; self.label.setFont(QFont('Segoe UI',int(t['size']),QFont.Weight.Bold)); self.normal=f"color:{t['color']};background:rgba(10,12,18,220);border:1px solid rgba(255,255,255,40);border-radius:9px;padding:5px 9px;"; self.label.setStyleSheet(self.normal)
    def update_time(self,sec,screen):
        sec=max(0,int(sec)); self.label.setText(f'{sec//60:02d}:{sec%60:02d}'); self.adjustSize(); g=screen.geometry(); m=18; c=self.s['timer']['corner']; x=g.left()+m if 'left' in c else g.right()-self.width()-m+1; y=g.top()+m if 'top' in c else g.bottom()-self.height()-m+1; self.move(x,y)
        if 0<sec<=5:
            self.label.setStyleSheet('color:#ff4d5e;background:rgba(10,12,18,225);border:1px solid rgba(255,77,94,120);border-radius:9px;padding:5px 9px;')
            if self.last!=sec: self.last=sec; self.anim.stop(); self.anim.start()
        else: self.last=None; self.anim.stop(); self.label.setWindowOpacity(1); self.label.setStyleSheet(self.normal)

class LockChain(QWidget):
    def __init__(self,parent=None,reduced=False):
        super().__init__(parent); self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground); self.reduced=reduced; self.progress=0.0; self.fade=1.0; self.timer=QTimer(self); self.timer.timeout.connect(self.step)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.Tool)
    def start(self):
        self.progress=0; self.fade=1; self.show(); self.raise_()
        if self.reduced: self.progress=1; self.update(); QTimer.singleShot(220,self.finish)
        else:self.timer.start(16)
    def step(self):
        self.progress=min(1,self.progress+0.035); self.fade=max(0,self.fade-0.008); self.update()
        if self.progress>=1: self.timer.stop(); QTimer.singleShot(180,self.finish)
    def finish(self): self.hide(); self.deleteLater()
    def paintEvent(self,e):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); w,h=self.width(),self.height(); c=QPointF(w/2,h/2); reach=min(w,h)*.39
        p.setPen(QPen(QColor(92,124,255,170),3));
        for dx,dy in [(-1,-1),(1,-1),(-1,1),(1,1)]:
            end=QPointF(c.x()+dx*reach,c.y()+dy*reach); mid=QPointF(c.x()+(end.x()-c.x())*min(1,self.progress*1.25),c.y()+(end.y()-c.y())*min(1,self.progress*1.25)); p.drawLine(c,mid)
            if self.progress>.2:
                r=22; p.setBrush(QBrush(QColor(17,23,34,230))); p.setPen(QPen(QColor(113,138,255,220),2)); p.drawRoundedRect(int(mid.x()-r),int(mid.y()-r),r*2,r*2,8,8); p.setPen(QPen(QColor(230,235,245,220),3)); p.drawArc(int(mid.x()-7),int(mid.y()-12),14,18,0,180*16); p.drawRect(int(mid.x()-8),int(mid.y()-3),16,12)
        p.setPen(QPen(QColor(255,255,255,80),1)); p.drawEllipse(int(c.x()-30),int(c.y()-30),60,60)

class AnswerButton(QPushButton):
    def __init__(self,text,parent=None):
        super().__init__(text,parent); self.setMinimumHeight(58); self.setCursor(Qt.CursorShape.PointingHandCursor); self.setFocusPolicy(Qt.FocusPolicy.StrongFocus); self.setStyleSheet(self.idle())
    def idle(self):return 'QPushButton{background:rgba(22,30,44,235);border:1px solid rgba(117,137,170,70);border-radius:13px;padding:10px 18px;text-align:left;font-size:16px;} QPushButton:hover{background:rgba(75,96,145,245);border:1px solid rgba(140,160,255,220);} QPushButton:pressed{background:rgba(92,124,255,255);padding-left:22px;}'

class Overlay(QWidget):
    def __init__(self,q,answer,target,s):
        super().__init__(); self.q=q; self.answer=answer; self.target=target; self.s=s; self.allow=False; self.started=time.monotonic(); self.hwnd=0; self.buttons=[]
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.Tool); self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose); self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet('color:#f5f7fb;')
        v=QVBoxLayout(self); v.setContentsMargins(70,55,70,55); v.setSpacing(16)
        title=QLabel('STUDYLOCK  •  ANSWER TO CONTINUE'); title.setAlignment(Qt.AlignmentFlag.AlignCenter); title.setFont(QFont('Segoe UI',22,QFont.Weight.Bold)); v.addWidget(title)
        meta=QLabel(f"{q.get('topic','General')}  •  {q.get('difficulty','Normal')}" + (f"  •  {q.get('paper')}" if q.get('paper') not in ('','all',None) else '')); meta.setAlignment(Qt.AlignmentFlag.AlignCenter); meta.setObjectName('muted'); v.addWidget(meta)
        lab=QLabel(q['question']); lab.setWordWrap(True); lab.setAlignment(Qt.AlignmentFlag.AlignCenter); lab.setFont(QFont('Segoe UI',25,QFont.Weight.DemiBold)); v.addWidget(lab,1)
        choices=q.get('choices',[])
        if choices:
            for i,c in enumerate(choices):
                b=AnswerButton(f'{chr(65+i)}   {c}'); b.clicked.connect(lambda _,x=c:self.submit(x)); self.buttons.append(b); v.addWidget(b)
        else:
            self.input=QLineEdit(); self.input.setPlaceholderText('Type your answer…'); self.input.setMinimumHeight(56); self.input.returnPressed.connect(lambda:self.submit(self.input.text())); v.addWidget(self.input); b=AnswerButton('CHECK ANSWER'); b.setObjectName('primary'); b.clicked.connect(lambda:self.submit(self.input.text())); v.addWidget(b)
        self.fade=QGraphicsOpacityEffect(self); self.setGraphicsEffect(self.fade); self.fade_anim=QPropertyAnimation(self.fade,b'opacity',self); self.fade_anim.setDuration(280); self.fade_anim.setStartValue(0); self.fade_anim.setEndValue(1); self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.watchdog=QTimer(self); self.watchdog.timeout.connect(self.watch); self.watchdog.start(120)
    def paintEvent(self,e):
        p=QPainter(self); p.fillRect(self.rect(),QColor(9,12,18,190))
        # central card is intentionally much more opaque than the backdrop for readability.
        card=self.rect().adjusted(35,35,-35,-35); p.setBrush(QBrush(QColor(15,21,31,242))); p.setPen(QPen(QColor(103,125,170,90),1)); p.drawRoundedRect(card,20,20)
    def showEvent(self,e): super().showEvent(e); self.hwnd=int(self.winId()); self.place(); self.fade_anim.start(); self.watch()
    def place(self):
        h,p=self.target(); r=window_rect(h) if h else None; screen=QApplication.screenAt(r.center()) if r else QApplication.primaryScreen(); screen=screen or QApplication.primaryScreen(); g=screen.geometry(); choice=self.s['timer']['resolution']
        if choice!='auto':
            try:w,hh=map(int,choice.split('x')); w=min(w,g.width()); hh=min(hh,g.height()); self.setGeometry(g.x()+(g.width()-w)//2,g.y()+(g.height()-hh)//2,w,hh); return
            except Exception:pass
        self.setGeometry(g)
    def watch(self):
        h,p=self.target(); fh,fp=foreground()
        if self.hwnd and fh==self.hwnd:return
        if h and fp==p: self.place(); topmost(self.hwnd); self.show()
        elif self.isVisible(): self.hide()
    def submit(self,val):
        elapsed=max(.05,time.monotonic()-self.started); self.allow=True; self.answer(val,elapsed); self.close()
    def closeEvent(self,e): e.accept() if self.allow else e.ignore()

class PerformanceDialog(QDialog):
    def __init__(self,stats,weak_only=False,parent=None):
        super().__init__(parent); self.setWindowTitle('StudyLock Performance'); self.resize(980,620); v=QVBoxLayout(self)
        title=QLabel('Topic performance'); title.setFont(QFont('Segoe UI',24,QFont.Weight.Bold)); v.addWidget(title)
        v.addWidget(QLabel('Accuracy is primary. Speed is secondary, so fast wrong answers do not inflate mastery.'))
        topics={}
        for x in stats.get('questions',{}).values():
            topic=x.get('topic','General'); a=topics.setdefault(topic,{'a':0,'c':0,'w':0,'times':[]}); a['a']+=int(x.get('attempts',0)); a['c']+=int(x.get('correct',0)); a['w']+=int(x.get('wrong',0)); a['times'] += list(x.get('times',[]))
        t=QTableWidget(0,6); t.setHorizontalHeaderLabels(['Topic','Accuracy','Avg time','Wrong','Mastery','Recommendation']); t.horizontalHeader().setStretchLastSection(True); v.addWidget(t)
        for topic,x in sorted(topics.items()):
            acc=x['c']/x['a']*100 if x['a'] else 0; avg=sum(x['times'])/len(x['times']) if x['times'] else 0; mastery=round(acc*.8+max(0,min(100,100-avg*3))*.2); rec='Strong' if mastery>=85 else 'Maintain' if mastery>=70 else 'Practice soon' if mastery>=55 else 'Weak point — prioritize practice'
            if weak_only and mastery>=70: continue
            vals=[topic,f'{acc:.0f}%',f'{avg:.1f}s',str(x['w']),f'{mastery}/100',rec]; r=t.rowCount(); t.insertRow(r)
            for c,val in enumerate(vals): t.setItem(r,c,QTableWidgetItem(str(val)))
        b=QPushButton('Close'); b.clicked.connect(self.accept); v.addWidget(b)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle(APP_NAME); self.resize(980,720); self.setStyleSheet(STYLE)
        self.questions=ensure_questions(); self.stats=load_stats(); self.settings=load_settings(); self.recent=[]; self.current=None; self.overlay=None; self.lock_anim=None; self.running=False; self.next_at=0; self.seconds_left=0
        self.tick=QTimer(self); self.tick.setInterval(250); self.tick.timeout.connect(self.loop)
        self.build_ui(); self.refresh_course(); self.refresh_status()
    def card(self):
        w=QFrame(); w.setObjectName('card'); return w
    def build_ui(self):
        root=QWidget(); outer=QVBoxLayout(root); outer.setContentsMargins(30,26,30,26); outer.setSpacing(18)
        head=QHBoxLayout(); title=QLabel(APP_NAME); title.setObjectName('title'); head.addWidget(title); head.addStretch(); self.status=QLabel('Stopped'); self.status.setObjectName('muted'); head.addWidget(self.status); outer.addLayout(head)
        course=self.card(); g=QGridLayout(course); g.setContentsMargins(20,20,20,20); g.setHorizontalSpacing(12); g.setVerticalSpacing(12)
        self.curr=QComboBox(); self.curr.addItems([c.name for c in available_curricula()]); self.curr.currentIndexChanged.connect(self.refresh_course); self.subj=QComboBox(); self.subj.currentIndexChanged.connect(self.refresh_qualification); self.qual=QComboBox(); self.qual.currentIndexChanged.connect(self.refresh_papers); self.paper=QComboBox()
        for col,label,w in [(0,'Curriculum',self.curr),(1,'Subject',self.subj),(2,'Qualification',self.qual),(3,'Paper',self.paper)]: g.addWidget(QLabel(label),0,col); g.addWidget(w,1,col)
        outer.addWidget(course)
        game=self.card(); gv=QHBoxLayout(game); gv.setContentsMargins(20,18,20,18); self.game_label=QLabel('No game selected'); self.game_label.setObjectName('muted'); gv.addWidget(self.game_label,1); pick=QPushButton('Select game'); pick.clicked.connect(self.pick_game); gv.addWidget(pick); outer.addWidget(game)
        controls=self.card(); cv=QHBoxLayout(controls); cv.setContentsMargins(20,18,20,18); self.interval=QSpinBox(); self.interval.setRange(5,3600); self.interval.setValue(int(self.settings.get('interval',20))); self.interval.setSuffix(' sec'); cv.addWidget(QLabel('Question every')); cv.addWidget(self.interval); cv.addStretch(); timerb=QPushButton('Timer settings'); timerb.clicked.connect(self.timer_settings); cv.addWidget(timerb); perf=QPushButton('Performance'); perf.clicked.connect(lambda:self.show_perf(False)); cv.addWidget(perf); weak=QPushButton('Practice weak areas'); weak.clicked.connect(lambda:self.show_perf(True)); cv.addWidget(weak); outer.addWidget(controls)
        actions=QHBoxLayout(); self.start=QPushButton('START STUDYLOCK'); self.start.setObjectName('primary'); self.start.clicked.connect(self.toggle); actions.addWidget(self.start); stop=QPushButton('Stop'); stop.clicked.connect(self.stop); actions.addWidget(stop); actions.addStretch(); imp=QPushButton('Import question bank'); imp.clicked.connect(self.import_questions); exp=QPushButton('Export question bank'); exp.clicked.connect(self.export_questions); actions.addWidget(imp); actions.addWidget(exp); outer.addLayout(actions)
        note=self.card(); nv=QVBoxLayout(note); nv.setContentsMargins(20,18,20,18); n=QLabel('Only the selected game is interrupted. If you switch to another app, the StudyLock overlay hides; when you return to the selected game, it appears again.'); n.setWordWrap(True); nv.addWidget(n); self.bank_label=QLabel(); self.bank_label.setObjectName('muted'); nv.addWidget(self.bank_label); outer.addWidget(note); outer.addStretch(); self.setCentralWidget(root)
    def refresh_course(self):
        c=available_curricula()[self.curr.currentIndex()]; old=self.subj.currentText(); self.subj.blockSignals(True); self.subj.clear(); self.subj.addItems(subjects_for(c.id)); self.subj.setCurrentText(old if old in subjects_for(c.id) else (subjects_for(c.id)[0] if subjects_for(c.id) else '')); self.subj.blockSignals(False); self.refresh_qualification()
    def refresh_qualification(self):
        c=available_curricula()[self.curr.currentIndex()]; old=self.qual.currentText(); self.qual.blockSignals(True); self.qual.clear(); self.qual.addItems(stages_for(c.id)); self.qual.setCurrentText(old if old in stages_for(c.id) else (stages_for(c.id)[0] if stages_for(c.id) else '')); self.qual.blockSignals(False); self.refresh_papers()
    def refresh_papers(self):
        c=available_curricula()[self.curr.currentIndex()]; ps=papers_for(c.id,self.subj.currentText(),self.qual.currentText()); self.paper.clear(); self.paper.addItem('All papers','all');
        for p in ps:self.paper.addItem(f'{p.name} — {p.description}',p.id)
        self.refresh_status()
    def selected_filter(self): return available_curricula()[self.curr.currentIndex()].id,self.subj.currentText(),self.qual.currentText(),self.paper.currentData() or 'all'
    def refresh_status(self):
        if not hasattr(self,'bank_label'): return
        cid,sub,stage,pid=self.selected_filter(); qs=filter_questions(self.questions,curriculum_id=cid,subject=sub,qualification_stage=stage,paper_id=pid); self.bank_label.setText(f'{len(qs)} questions available for this selection  •  {self.stats.get("total_answered",0)} answers recorded')
    def pick_game(self):
        d=GamePicker(self,self.settings.get('game',{}));
        if d.exec(): self.settings['game']=d.selected; save_settings(self.settings); self.game_label.setText(f"{d.selected['name']}  •  PID {d.selected['pid']}")
    def timer_settings(self):
        d=TimerSettings(self.settings,self)
        if d.exec(): save_settings(self.settings); self.settings=load_settings()
    def show_perf(self,weak): PerformanceDialog(self.stats,weak,self).exec()
    def choose_question(self):
        cid,sub,stage,pid=self.selected_filter(); qs=filter_questions(self.questions,curriculum_id=cid,subject=sub,qualification_stage=stage,paper_id=pid)
        if not qs:return None
        pool=[q for q in qs if q.get('id') not in self.recent]
        if not pool: pool=qs[:]
        # Weak-topic weighting: topics with lower observed accuracy get picked more often.
        def weight(q):
            x=self.stats.get('questions',{}).get(q.get('id'),{}); a=int(x.get('attempts',0)); acc=(int(x.get('correct',0))/a) if a else .5; return 1.8-acc
        q=random.choices(pool,weights=[weight(x) for x in pool],k=1)[0]; self.recent.append(q.get('id')); self.recent=self.recent[-12:]; return q
    def answer(self,val,elapsed):
        q=self.current; ifok=False; target=norm(val)
        for a in q.get('answers',[]):
            if target==norm(a): ifok=True; break
            try:
                if q.get('numeric_tolerance',0)>0 and abs(float(target)-float(a))<=q['numeric_tolerance']: ifok=True; break
            except Exception: pass
        st=self.stats.setdefault('questions',{}).setdefault(q['id'],{'attempts':0,'correct':0,'wrong':0,'times':[],'topic':q.get('topic','General')}); st['attempts']+=1; st['times'].append(round(elapsed,2)); self.stats['total_answered']=self.stats.get('total_answered',0)+1
        if ifok: st['correct']+=1; self.stats['total_correct']=self.stats.get('total_correct',0)+1
        else: st['wrong']+=1
        save_stats(self.stats); self.current=None
        return ifok
    def trigger_question(self):
        q=self.choose_question()
        if not q:return
        self.current=q; self.overlay=Overlay(q,self.answer,self.target,self.settings); self.overlay.show()
    def target(self):
        g=self.settings.get('game') or {}; h,p=foreground();
        if not h:return 0,0
        if g.get('pid') and p==g['pid']:return h,p
        try:
            if g.get('exe') and norm(psutil.Process(p).name())==norm(g['exe']):return h,p
        except psutil.Error:pass
        return 0,0
    def start_run(self):
        if not self.settings.get('game',{}): QMessageBox.warning(self,APP_NAME,'Select a game first.'); return
        self.running=True; self.next_at=time.monotonic()+self.interval.value(); self.seconds_left=self.interval.value(); self.start.setText('RUNNING'); self.status.setText('Running');
        self.hud=TimerHUD(self.settings); self.hud.show(); self.tick.start()
    def toggle(self): self.stop() if self.running else self.start_run()
    def stop(self):
        self.running=False; self.tick.stop();
        if hasattr(self,'hud'): self.hud.close()
        if self.overlay: self.overlay.allow=True; self.overlay.close(); self.overlay=None
        self.status.setText('Stopped'); self.start.setText('START STUDYLOCK')
    def loop(self):
        if not self.running:return
        target=self.settings.get('game',{}); h,p=foreground();
        if not h or not target:return
        screen=QApplication.screenAt(QPointF(0,0).toPoint()) or QApplication.primaryScreen();
        if hasattr(self,'hud'): self.hud.update_time(max(0,self.next_at-time.monotonic()),screen)
        if time.monotonic()>=self.next_at:
            self.next_at=time.monotonic()+self.interval.value(); self.seconds_left=self.interval.value();
            if self.overlay is None or not self.overlay.isVisible(): self.trigger_with_animation()
    def trigger_with_animation(self):
        h,p=self.target(); r=window_rect(h) if h else None; screen=QApplication.screenAt(r.center()) if r else QApplication.primaryScreen(); screen=screen or QApplication.primaryScreen(); g=screen.geometry()
        self.lock_anim=LockChain(); self.lock_anim.setGeometry(g); self.lock_anim.start(); QTimer.singleShot(700 if not self.settings.get('reduced_motion') else 240,self.trigger_question)
    def import_questions(self):
        path,_=QFileDialog.getOpenFileName(self,'Import question bank','','JSON files (*.json)')
        if not path:return
        try:
            data=json.loads(Path(path).read_text(encoding='utf-8')); parsed=validate_questions(data); self.questions=parsed; atomic_write(QUESTIONS_FILE,{'questions':parsed}); self.refresh_status(); QMessageBox.information(self,APP_NAME,f'Imported {len(parsed)} questions.')
        except Exception as e: QMessageBox.critical(self,APP_NAME,f'Import failed:\n{e}')
    def export_questions(self):
        path,_=QFileDialog.getSaveFileName(self,'Export question bank','studylock_questions.json','JSON files (*.json)')
        if path: Path(path).write_text(json.dumps({'questions':self.questions},indent=2,ensure_ascii=False),encoding='utf-8')
    def closeEvent(self,e): self.stop(); e.accept()

def main():
    app=QApplication(sys.argv); app.setApplicationName(APP_NAME); w=MainWindow(); w.show(); sys.exit(app.exec())

if __name__=='__main__': main()
