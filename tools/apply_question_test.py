from pathlib import Path

p = Path('main.py')
s = p.read_text(encoding='utf-8')

s = s.replace(
'''class Overlay(QWidget):\n    def __init__(self, question, answer_callback, target_callback, settings):\n        super().__init__()\n        self.question = question; self.answer_callback = answer_callback; self.target_callback = target_callback; self.settings = settings\n''',
'''class Overlay(QWidget):\n    def __init__(self, question, answer_callback, target_callback, settings, test_mode=False):\n        super().__init__()\n        self.question = question; self.answer_callback = answer_callback; self.target_callback = target_callback; self.settings = settings; self.test_mode = test_mode\n''', 1)

s = s.replace(
'''    def watch_target(self):\n        hwnd, pid = self.target_callback(); foreground_hwnd, foreground_pid = foreground()\n''',
'''    def watch_target(self):\n        if self.test_mode:\n            if not self.isVisible():\n                self.show()\n            return\n        hwnd, pid = self.target_callback(); foreground_hwnd, foreground_pid = foreground()\n''', 1)

needle = '''    def trigger_question(self):\n        if not self.running:\n            return\n'''
if needle not in s:
    raise SystemExit('trigger_question not found')

insert = '''    def trigger_test_question(self):\n        if self.overlay is not None:\n            try:\n                self.overlay.allow_close = True\n                self.overlay.close()\n            except RuntimeError:\n                pass\n            self.overlay = None\n        question = self.choose_question()\n        if not question:\n            QMessageBox.warning(self, APP_NAME, "No questions match the current selection.")\n            return\n        self.current = question\n        self.overlay = Overlay(question, self.answer, self.target, self.settings, test_mode=True)\n        self.overlay.show()\n\n'''
s = s.replace(needle, insert + needle, 1)

old = '''        actions = QHBoxLayout(); self.start_button = QPushButton("START STUDYLOCK"); self.start_button.setObjectName("primary"); self.start_button.setMinimumWidth(190); self.start_button.clicked.connect(self.toggle); actions.addWidget(self.start_button); stop_button = QPushButton("STOP"); stop_button.setMinimumWidth(90); stop_button.clicked.connect(self.stop); actions.addWidget(stop_button); actions.addStretch(); imp = QPushButton("Import question bank"); imp.clicked.connect(self.import_questions); actions.addWidget(imp); exp = QPushButton("Export question bank"); exp.clicked.connect(self.export_questions); actions.addWidget(exp); outer.addLayout(actions)\n'''
new = '''        actions = QHBoxLayout(); self.start_button = QPushButton("START STUDYLOCK"); self.start_button.setObjectName("primary"); self.start_button.setMinimumWidth(190); self.start_button.clicked.connect(self.toggle); actions.addWidget(self.start_button); stop_button = QPushButton("STOP"); stop_button.setMinimumWidth(90); stop_button.clicked.connect(self.stop); actions.addWidget(stop_button); test_button = QPushButton("TEST QUESTION"); test_button.setToolTip("Show one question now without requiring the selected game to be running."); test_button.clicked.connect(self.trigger_test_question); actions.addWidget(test_button); actions.addStretch(); imp = QPushButton("Import question bank"); imp.clicked.connect(self.import_questions); actions.addWidget(imp); exp = QPushButton("Export question bank"); exp.clicked.connect(self.export_questions); actions.addWidget(exp); outer.addLayout(actions)\n'''
if old not in s:
    raise SystemExit('actions block not found')
s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('Standalone question test path applied')
