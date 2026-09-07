import json, os, random, sys, time, ctypes
from pathlib import Path
from typing import Any
import psutil
from PySide6.QtCore import QTimer, Qt, QRect, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QCloseEvent, QColor
from PySide6.QtWidgets import (QApplication,QComboBox,QDialog,QDialogButtonBox,QFileDialog,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QMainWindow,QMessageBox,QPushButton,QSpinBox,QTableWidget,QTableWidgetItem,QTabWidget,QVBoxLayout,QWidget,QColorDialog,QGraphicsOpacityEffect,QGroupBox)
from curriculum import available_curricula, filter_questions
from sample_questions import questions as bundled_questions
APP_NAME='StudyLock'; DATA_DIR=Path(os.getenv('APPDATA',str(Path.home())))/APP_NAME; DATA_DIR.mkdir(parents=True,exist_ok=True)
QUESTIONS_FILE=DATA_DIR/'questions.json'; STATS_FILE=DATA_DIR/'stats.json'; SETTINGS_FILE=DATA_DIR/'settings.json'
DEFAULT_TIMER={'size':18,'color':'#ffffff','corner':'top-right','resolution':'1920x1080'}
def norm(v:Any)->str: return ' '.join(str(v).strip().lower().replace('²','2').replace('³','3').replace('−','-').replace('×','x').split())
def atomic_write(p,v):
 t=p.with_name(p.name+'.tmp'); t.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8'); t.replace(p)
def load_json(p,d):
 try:return json.loads(p.read_text(encoding='utf-8')) if p.exists() else d
 except Exception:return d
def validate_questions(data):
 data=data.get('questions') if isinstance(data,dict) else data
 if not isinstance(data,list):raise ValueError('Question data must be a list.')
 cats={c.id:c for c in available_curricula()}; out=[]
 for i,q in enumerate(data,1):
  if not isinstance(q,dict) or not str(q.get('question','')).strip() or not isinstance(q.get('answers'),list) or not q['answers']:raise ValueError(f'Question {i} is invalid.')
  cid=norm(q.get('curriculum','gcse')); sub=str(q.get('subject','Chemistry')); stage=str(q.get('qualification_stage','A Level'))
  if cid not in cats or sub not in cats[cid].subjects or stage not in cats[cid].qualification_stages:raise ValueError(f'Question {i}: course metadata is invalid.')
  out.append({**q,'id':str(q.get('id') or f'q-{i}'),'question':str(q['question']),'choices':[str(x) for x in q.get('choices',[])],'answers':[str(x) for x in q['answers']],'topic':str(q.get('topic') or 'General'),'difficulty':str(q.get('difficulty') or 'Normal'),'curriculum':cid,'subject':sub,'qualification_stage':stage,'numeric_tolerance':max(0,float(q.get('numeric_tolerance',0))),'exam_board':str(q.get('exam_board') or ''),'paper_reference':str(q.get('paper_reference') or '')})
 return out
def ensure_questions():
 seed=bundled_questions(); data=load_json(QUESTIONS_FILE,None)
 if data is None:atomic_write(QUESTIONS_FILE,{'questions':seed});return seed
 try:
  parsed=validate_questions(data)
  if len(parsed)<=8 and parsed and all(str(q.get('id','')).startswith('al-') for q in parsed):atomic_write(QUESTIONS_FILE,{'questions':seed});return seed
  return parsed
 except Exception:return seed
def load_stats():
 s=load_json(STATS_FILE,{'questions':{},'sessions':0,'total_answered':0,'total_correct':0});return s if isinstance(s,dict) else {'questions':{},'sessions':0,'total_answered':0,'total_correct':0}
def save_stats(s):atomic_write(STATS_FILE,s)
def load_settings():
 s=load_json(SETTINGS_FILE,{});s=s if isinstance(s,dict) else {};s.setdefault('game',{});s.setdefault('interval',20);s.setdefault('timer',{});s['timer']={**DEFAULT_TIMER,**s['timer']};return s
def save_settings(s):atomic_write(SETTINGS_FILE,s)
def process_rows():
 out=[];seen=set()
 for p in psutil.process_iter(['pid','name','exe']):
  try:
   n=p.info.get('name') or '';e=Path(p.info.get('exe') or n).name;pid=int(p.info['pid']);k=(norm(n),norm(e))
   if n and pid>0 and k not in seen:seen.add(k);out.append((n,pid,e))
  except (psutil.NoSuchProcess,psutil.AccessDenied,psutil.ZombieProcess,OSError):pass
 return sorted(out,key=lambda x:norm(x[0]))
def foreground():
 if sys.platform!='win32':return 0,0
 try:
  h=int(ctypes.windll.user32.GetForegroundWindow());p=ctypes.c_ulong(0)
  if not h:return 0,0
  ctypes.windll.user32.GetWindowThreadProcessId(h,ctypes.byref(p));return h,int(p.value)
 except Exception:return 0,0
def window_rect(h):
 try:
  class R(ctypes.Structure):_fields_=[('l',ctypes.c_long),('t',ctypes.c_long),('r',ctypes.c_long),('b',ctypes.c_long)]
  r=R()
  if ctypes.windll.user32.GetWindowRect(h,ctypes.byref(r)):return QRect(r.l,r.t,r.r-r.l,r.b-r.t)
 except Exception:pass
 return None
def active_target(g):
 h,p=foreground()
 if not h:return False
 if g.get('pid') and p==g['pid']:return True
 try:return bool(g.get('exe')) and norm(psutil.Process(p).name())==norm(g['exe'])
 except psutil.Error:return False
def topmost(h):
 if sys.platform=='win32' and h:
  try:ctypes.windll.user32.SetWindowPos(h,-1,0,0,0,0,0x0002|0x0001|0x0040);ctypes.windll.user32.SetForegroundWindow(h)
  except Exception:pass
class GamePicker(QDialog):
 def __init__(self,parent=None,selected=None):
  super().__init__(parent);self.setWindowTitle('Select game');self.resize(760,540);self.selected=None;v=QVBoxLayout(self);v.addWidget(QLabel('Choose the Windows game/app StudyLock should monitor. Other apps remain usable.'));self.search=QLineEdit();self.search.setPlaceholderText('Search…');v.addWidget(self.search);self.table=QTableWidget(0,3);self.table.setHorizontalHeaderLabels(['Application','PID','Executable']);self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);v.addWidget(self.table);r=QHBoxLayout();b=QPushButton('Refresh');b.clicked.connect(self.populate);r.addWidget(b);r.addStretch();box=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);box.accepted.connect(self.accept_choice);box.rejected.connect(self.reject);r.addWidget(box);v.addLayout(r);self.search.textChanged.connect(self.populate);self.populate();self.preselect(selected or {})
 def populate(self):
  q=norm(self.search.text());self.table.setRowCount(0)
  for n,p,e in process_rows():
   if q and q not in norm(n) and q not in norm(e):continue
   r=self.table.rowCount();self.table.insertRow(r);[self.table.setItem(r,c,QTableWidgetItem(str(x))) for c,x in enumerate((n,p,e))]
 def preselect(self,s):
  for r in range(self.table.rowCount()):
   if norm(self.table.item(r,2).text())==norm(s.get('exe','')) and s.get('exe'):self.table.selectRow(r);break
 def accept_choice(self):
  rows=self.table.selectionModel().selectedRows()
  if not rows:return QMessageBox.warning(self,APP_NAME,'Select a game first.')
  r=rows[0].row();self.selected={'name':self.table.item(r,0).text(),'pid':int(self.table.item(r,1).text()),'exe':self.table.item(r,2).text()};self.accept()
class TimerSettings(QDialog):
 def __init__(self,s,parent=None):
  super().__init__(parent);self.setWindowTitle('Timer Settings');self.s=s;v=QVBoxLayout(self);f=QFormLayout();t=s['timer'];self.size=QSpinBox();self.size.setRange(10,72);self.size.setValue(int(t['size']));self.size.setSuffix(' px');f.addRow('Timer size',self.size);self.corner=QComboBox();self.corner.addItems(['top-left','top-right','bottom-left','bottom-right']);self.corner.setCurrentText(t['corner']);f.addRow('Timer position',self.corner);self.res=QComboBox();self.res.addItems(['Auto (display)','1920x1080','1600x900','1366x768','1280x720']);self.res.setCurrentText('Auto (display)' if t['resolution']=='auto' else t['resolution']);f.addRow('Question resolution',self.res);self.color=QPushButton(t['color']);self.color.clicked.connect(self.pick_color);f.addRow('Timer color',self.color);v.addLayout(f);v.addWidget(QLabel('1920×1080 is automatically clamped to your physical display.'));box=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);box.accepted.connect(self.save);box.rejected.connect(self.reject);v.addWidget(box)
 def pick_color(self):
  c=QColorDialog.getColor(QColor(self.color.text()),self)
  if c.isValid():self.color.setText(c.name())
 def save(self):self.s['timer']={'size':self.size.value(),'corner':self.corner.currentText(),'resolution':'auto' if self.res.currentText().startswith('Auto') else self.res.currentText(),'color':self.color.text()};self.accept()
class TimerHUD(QWidget):
 def __init__(self,s):
  super().__init__();self.s=s;self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.Tool);self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground);v=QVBoxLayout(self);v.setContentsMargins(7,4,7,4);self.label=QLabel('00:00');self.label.setAlignment(Qt.AlignmentFlag.AlignCenter);v.addWidget(self.label);self.anim=QPropertyAnimation(self.label,b'windowOpacity',self);self.anim.setDuration(430);self.anim.setStartValue(1);self.anim.setEndValue(.35);self.anim.setEasingCurve(QEasingCurve.Type.InOutSine);self.anim.setLoopCount(2);self.last=None;self.apply()
 def apply(self):
  t=self.s['timer'];self.label.setFont(QFont('Segoe UI',int(t['size']),QFont.Weight.Bold));self.normal=f"color:{t['color']};background:rgba(10,12,18,220);border:1px solid rgba(255,255,255,40);border-radius:9px;padding:5px 9px;";self.label.setStyleSheet(self.normal)
 def update(self,sec,screen):
  sec=max(0,int(sec));self.label.setText(f'{sec//60:02d}:{sec%60:02d}');self.adjustSize();g=screen.geometry();m=18;c=self.s['timer']['corner'];x=g.left()+m if 'left' in c else g.right()-self.width()-m+1;y=g.top()+m if 'top' in c else g.bottom()-self.height()-m+1;self.move(x,y)
  if 0<sec<=5:
   self.label.setStyleSheet('color:#ff3b3b;background:rgba(10,12,18,225);border:1px solid rgba(255,60,60,100);border-radius:9px;padding:5px 9px;')
   if self.last!=sec:self.last=sec;self.anim.stop();self.anim.start()
  else:self.last=None;self.anim.stop();self.label.setWindowOpacity(1);self.label.setStyleSheet(self.normal)
class Overlay(QWidget):
 def __init__(self,q,answer,target,s):
  super().__init__();self.q=q;self.answer=answer;self.target=target;self.s=s;self.allow=False;self.started=time.monotonic();self.hwnd=0;self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.Tool);self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose);self.setStyleSheet('background:#0d1017;color:#f5f7fb;');v=QVBoxLayout(self);v.setContentsMargins(50,35,50,35);v.setSpacing(14);title=QLabel('STUDYLOCK  •  ANSWER TO CONTINUE');title.setAlignment(Qt.AlignmentFlag.AlignCenter);title.setFont(QFont('Segoe UI',22,QFont.Weight.Bold));v.addWidget(title);meta=QLabel(f"{q.get('topic','General')}  •  {q.get('difficulty','Normal')}");meta.setAlignment(Qt.AlignmentFlag.AlignCenter);meta.setStyleSheet('color:#8f98aa;');v.addWidget(meta);lab=QLabel(q['question']);lab.setWordWrap(True);lab.setAlignment(Qt.AlignmentFlag.AlignCenter);lab.setFont(QFont('Segoe UI',24,QFont.Weight.DemiBold));v.addWidget(lab,1);choices=q.get('choices',[])
  if choices:
   for i,c in enumerate(choices):b=QPushButton(f'{chr(65+i)}   {c}');b.setMinimumHeight(52);b.clicked.connect(lambda _,x=c:self.submit(x));v.addWidget(b)
  else:
   self.input=QLineEdit();self.input.setPlaceholderText('Type your answer…');self.input.setMinimumHeight(52);self.input.returnPressed.connect(lambda:self.submit(self.input.text()));v.addWidget(self.input);b=QPushButton('CHECK ANSWER');b.clicked.connect(lambda:self.submit(self.input.text()));v.addWidget(b)
  self.fade=QGraphicsOpacityEffect(self);self.setGraphicsEffect(self.fade);self.fade_anim=QPropertyAnimation(self.fade,b'opacity',self);self.fade_anim.setDuration(280);self.fade_anim.setStartValue(0);self.fade_anim.setEndValue(1);self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic);self.watchdog=QTimer(self);self.watchdog.timeout.connect(self.watch);self.watchdog.start(120)
 def showEvent(self,e):super().showEvent(e);self.hwnd=int(self.winId());self.place();self.fade_anim.start();self.watch()
 def place(self):
  h,p=self.target();r=window_rect(h) if h else None;screen=QApplication.screenAt(r.center()) if r else QApplication.primaryScreen();screen=screen or QApplication.primaryScreen();g=screen.geometry();choice=self.s['timer']['resolution']
  if choice!='auto':
   try:w,hh=map(int,choice.split('x'));w=min(w,g.width());hh=min(hh,g.height());self.setGeometry(g.x()+(g.width()-w)//2,g.y()+(g.height()-hh)//2,w,hh);return
   except Exception:pass
  self.setGeometry(g)
 def watch(self):
  h,p=self.target();fh,fp=foreground()
  if self.hwnd and fh==self.hwnd:return
  if h and fp==p:self.place();topmost(self.hwnd)
  elif self.isVisible():self.hide()
 def submit(self,val):
  elapsed=max(.05,time.monotonic()-self.started);ok=self.answer(val,elapsed)
  if ok:self.allow=True;self.close()
  else:self.allow=True;self.close()
 def closeEvent(self,e):e.accept() if self.allow else e.ignore()
class PerformanceDialog(QDialog):
 def __init__(self,stats,parent=None):
  super().__init__(parent);self.setWindowTitle('Topic Performance');self.resize(900,540);v=QVBoxLayout(self);v.addWidget(QLabel('Accuracy is the main factor; speed helps, but fast wrong answers never make a topic strong.'));t=QTableWidget(0,6);t.setHorizontalHeaderLabels(['Topic','Accuracy','Avg time','Wrong attempts','Mastery','Recommendation']);t.horizontalHeader().setStretchLastSection(True);v.addWidget(t);topics={}
  for x in stats.get('questions',{}).values():
   a=topics.setdefault(x.get('topic','General'),{'a':0,'c':0,'w':0,'times':[]});a['a']+=int(x.get('attempts',0));a['c']+=int(x.get('correct',0));a['w']+=int(x.get('wrong',0));a['times']+=list(x.get('times',[]))
  for topic,x in sorted(topics.items()):
   acc=x['c']/x['a']*100 if x['a'] else 0;avg=sum(x['times'])/len(x['times']) if x['times'] else 0;mastery=round(acc*.8+max(0,min(100,100-avg*3))*.2);rec='Strong' if mastery>=85 else 'Maintain' if mastery>=70 else 'Practice soon' if mastery>=55 else 'Weak point — prioritize practice';vals=[topic,f'{acc:.0f}%',f'{avg:.1f}s',str(x['w']),f'{mastery}/100',rec];r=t.rowCount();t.insertRow(r);[t.setItem(r,c,QTableWidgetItem(str(val))) for c,val in enumerate(vals)]
  b=QPushButton('Close');b.clicked.connect(self.accept);v.addWidget(b)
class MainWindow(QMainWindow):
 def __init__(self):
  super().__init__();self.setWindowTitle(APP_NAME);self.resize(920,700);self.questions=ensure_questions();self.stats=load_stats();self.settings=load_settings();self.session=False;self.overlay=None;self.current=None;self.pool=[];self.last_ids=[];self.remaining=0;self.last_tick=time.monotonic();self.hud=TimerHUD(self.settings);self.build_ui();self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(250);self.recovery=QTimer(self);self.recovery.timeout.connect(self.recover);self.recovery.start(100)
 def build_ui(self):
  self.setStyleSheet("QMainWindow{background:#0b0d12;} QWidget{font-family:'Segoe UI';font-size:14px;} QTabWidget::pane{border:1px solid #252a35;border-radius:12px;} QPushButton{background:#1b2230;border:1px solid #343d4e;border-radius:9px;padding:10px 14px;} QPushButton:hover{background:#283346;} QComboBox,QSpinBox,QLineEdit{background:#151a23;border:1px solid #303848;border-radius:8px;padding:8px;} QTableWidget{background:#11151d;border:1px solid #252a35;} QLabel{color:#eef1f7;} QGroupBox{border:1px solid #252a35;border-radius:10px;margin-top:10px;padding:12px;}");tabs=QTabWidget();self.setCentralWidget(tabs);home=QWidget();tabs.addTab(home,'Session');v=QVBoxLayout(home);title=QLabel('StudyLock');title.setFont(QFont('Segoe UI',32,QFont.Weight.Bold));v.addWidget(title);sub=QLabel('Focus on the question. Only your selected game is interrupted.');sub.setStyleSheet('color:#8f98aa;');v.addWidget(sub);f=QFormLayout();self.curr=QComboBox();self.curr.addItems([c.name for c in available_curricula()]);self.curr.currentIndexChanged.connect(self.course_changed);f.addRow('Curriculum',self.curr);self.subject=QComboBox();f.addRow('Subject',self.subject);self.stage=QComboBox();f.addRow('Qualification',self.stage);self.interval=QSpinBox();self.interval.setRange(1,240);self.interval.setValue(int(self.settings['interval']));self.interval.setSuffix(' min');f.addRow('Question interval',self.interval);v.addLayout(f);g=QGroupBox('Game');gr=QHBoxLayout(g);self.game_label=QLabel('No game selected');b=QPushButton('Select Game');b.clicked.connect(self.pick_game);gr.addWidget(self.game_label,1);gr.addWidget(b);v.addWidget(g);r=QHBoxLayout();self.start=QPushButton('▶  START SESSION');self.start.clicked.connect(self.toggle);r.addWidget(self.start);b=QPushButton('⏱  Timer Settings');b.clicked.connect(self.timer_settings);r.addWidget(b);b=QPushButton('📊  Topic Performance');b.clicked.connect(lambda:PerformanceDialog(self.stats,self).exec());r.addWidget(b);v.addLayout(r);self.status=QLabel('Ready. Select your course and game.');self.status.setStyleSheet('color:#8f98aa;');v.addWidget(self.status);v.addStretch();bank=QWidget();tabs.addTab(bank,'Question Bank');bv=QVBoxLayout(bank);self.qtable=QTableWidget(0,6);self.qtable.setHorizontalHeaderLabels(['Question','Topic','Curriculum','Subject','Qualification','Answers']);self.qtable.horizontalHeader().setStretchLastSection(True);bv.addWidget(self.qtable);r=QHBoxLayout();b=QPushButton('Import JSON');b.clicked.connect(self.import_questions);r.addWidget(b);b=QPushButton('Export JSON');b.clicked.connect(self.export_questions);r.addWidget(b);r.addStretch();bv.addLayout(r);self.course_changed(0);self.refresh();self.restore_game()
 def course_changed(self,i):c=available_curricula()[i];self.subject.clear();self.subject.addItems(c.subjects);self.stage.clear();self.stage.addItems(c.qualification_stages)
 def restore_game(self):
  g=self.settings['game'];
  if g.get('exe'):self.game_label.setText(f"{g.get('name',g['exe'])}  ({g['exe']})")
 def pick_game(self):
  d=GamePicker(self,self.settings['game']);
  if d.exec() and d.selected:self.settings['game']=d.selected;save_settings(self.settings);self.restore_game()
 def timer_settings(self):
  d=TimerSettings(self.settings,self)
  if d.exec():self.hud.apply();save_settings(self.settings)
 def course(self):c=available_curricula()[self.curr.currentIndex()];return c.id,self.subject.currentText(),self.stage.currentText()
 def target(self):
  g=self.settings['game'];h,p=foreground()
  if h and ((g.get('pid') and p==g['pid']) or (g.get('exe') and norm(psutil.Process(p).name())==norm(g['exe']))):return h,p
  return 0,0
 def toggle(self):
  if self.session:return self.stop('Session stopped.')
  g=self.settings['game'];
  if not g.get('exe'):return QMessageBox.warning(self,APP_NAME,'Select the game you want StudyLock to monitor first.')
  cid,sub,stage=self.course();self.pool=filter_questions(self.questions,curriculum_id=cid,subject=sub,qualification_stage=stage)
  if not self.pool:return QMessageBox.warning(self,APP_NAME,'There are no questions for this course yet.')
  self.settings['interval']=self.interval.value();save_settings(self.settings);self.session=True;self.stats['sessions']+=1;self.remaining=self.interval.value()*60;self.last_tick=time.monotonic();self.last_ids=[];self.start.setText('■  STOP SESSION');self.status.setText('Session running — leaving the game pauses the timer.')
 def stop(self,msg):
  self.session=False;self.current=None;self.remaining=0;self.hud.hide();self.start.setText('▶  START SESSION');self.status.setText(msg);save_stats(self.stats)
  if self.overlay:self.overlay.allow=True;self.overlay.close();self.overlay=None
 def tick(self):
  now=time.monotonic();dt=min(1,now-self.last_tick);self.last_tick=now
  if not self.session:return
  if self.overlay:self.hud.hide();self.overlay.watch();return
  g=self.settings['game']
  if active_target(g):
   self.remaining-=dt;fh,_=foreground();rr=window_rect(fh) if fh else None;screen=QApplication.screenAt(rr.center()) if rr else None;screen=screen or QApplication.primaryScreen();self.hud.update(self.remaining,screen);self.hud.show()
   if self.remaining<=0:self.hud.hide();self.trigger()
  else:self.hud.hide()
  self.status.setText(f"Session running • next question in {max(0,self.remaining)/60:.1f} min • {self.stage.currentText()} {self.subject.currentText()}")
 def trigger(self):
  pool=[q for q in self.pool if q['id'] not in self.last_ids] or self.pool;self.current=random.choice(pool);self.last_ids=(self.last_ids+[self.current['id']])[-12:];self.overlay=Overlay(self.current,self.answer,self.target,self.settings);self.hud.hide();self.overlay.show();self.status.setText('Question active — answer correctly to continue.')
 def answer(self,val,elapsed):
  q=self.current;ok=any(norm(val)==norm(a) for a in q['answers'])
  if not ok:
   try:ok=any(float(q.get('numeric_tolerance',0))>0 and abs(float(val)-float(a))<=float(q.get('numeric_tolerance',0)) for a in q['answers'])
   except (ValueError,TypeError):pass
  s=self.stats['questions'].setdefault(q['id'],{'topic':q.get('topic','General'),'attempts':0,'correct':0,'wrong':0,'times':[]});s['attempts']+=1;s['topic']=q.get('topic','General');self.stats['total_answered']+=1
  if ok:s['correct']+=1;s['times'].append(round(elapsed,3));self.stats['total_correct']+=1
  else:s['wrong']+=1
  save_stats(self.stats);old=self.overlay;self.overlay=None;self.current=None
  if ok:self.remaining=self.interval.value()*60;self.last_tick=time.monotonic();self.status.setText('✓ Correct — gameplay unlocked.');return True
  if old:old.allow=True;old.close()
  self.status.setText('✕ Incorrect — loading a different question.');QTimer.singleShot(120,self.trigger);return False
 def recover(self):
  if not self.session or sys.platform!='win32':return
  try:
   u=ctypes.windll.user32;down=all(u.GetAsyncKeyState(k)&0x8000 for k in (0x11,0x10,0x7B))
   if down:
    if not hasattr(self,'recover_at'):self.recover_at=time.monotonic()
    if time.monotonic()-self.recover_at>=5:self.stop('Emergency recovery used.');del self.recover_at
   else:self.recover_at=None
  except Exception:pass
 def import_questions(self):
  p,_=QFileDialog.getOpenFileName(self,'Import questions','','JSON files (*.json)');
  if not p:return
  try:
   incoming=validate_questions(json.loads(Path(p).read_text(encoding='utf-8')));d={q['id']:q for q in self.questions};d.update({q['id']:q for q in incoming});self.questions=list(d.values());atomic_write(QUESTIONS_FILE,{'questions':self.questions});self.refresh();QMessageBox.information(self,APP_NAME,f'Imported {len(incoming)} questions.')
  except Exception as e:QMessageBox.critical(self,APP_NAME,f'Import failed:\n{e}')
 def export_questions(self):
  p,_=QFileDialog.getSaveFileName(self,'Export questions','studylock_questions.json','JSON files (*.json)');
  if p:atomic_write(Path(p),{'questions':self.questions})
 def refresh(self):
  if not hasattr(self,'qtable'):return
  self.qtable.setRowCount(0)
  for q in self.questions:
   r=self.qtable.rowCount();self.qtable.insertRow(r);vals=[q['question'],q['topic'],q['curriculum'],q['subject'],q['qualification_stage'],', '.join(q['answers'])];[self.qtable.setItem(r,c,QTableWidgetItem(str(x))) for c,x in enumerate(vals)]
 def closeEvent(self,e):
  if self.session:self.stop('Application closed; session stopped safely.')
  e.accept()
def main():
 app=QApplication(sys.argv);app.setApplicationName(APP_NAME);w=MainWindow();w.show();sys.exit(app.exec())
if __name__=='__main__':main()
