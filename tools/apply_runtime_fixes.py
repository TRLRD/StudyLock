from pathlib import Path

p = Path('main.py')
s = p.read_text(encoding='utf-8')

# This workflow used to be a one-shot patcher. The runtime fixes are now part of
# main.py, so make the patcher idempotent: if the first fix is already present,
# leave the working engine untouched and let the workflow continue to validation.
old = '''        save_stats(self.stats); self.current = None; self.refresh_status(); return correct\n'''
if old not in s:
    print('StudyLock runtime fixes already present; nothing to patch')
    raise SystemExit(0)

new = '''        save_stats(self.stats)\n        # Detach the consumed overlay before Qt's WA_DeleteOnClose destroys it.\n        self.current = None\n        self.overlay = None\n        self.refresh_status()\n        return correct\n'''
s = s.replace(old, new, 1)

# Make stopping a hard cancellation point and restore every visual state.
old = '''    def stop(self):\n        self.running = False; self.tick.stop()\n        if hasattr(self, "hud"): self.hud.close()\n        if self.overlay: self.overlay.allow_close = True; self.overlay.close(); self.overlay = None\n        self.current = None; self.status.setText("STOPPED"); self.start_button.setText("START STUDYLOCK")\n'''
new = '''    def stop(self):\n        self.running = False\n        self.tick.stop()\n        self.next_at = 0\n        if hasattr(self, "hud"):\n            self.hud.close()\n            self.hud = None\n        if self.overlay is not None:\n            try:\n                self.overlay.allow_close = True\n                self.overlay.close()\n            except RuntimeError:\n                pass\n            self.overlay = None\n        if self.lock_anim is not None:\n            try:\n                self.lock_anim.timer.stop()\n                self.lock_anim.close()\n            except RuntimeError:\n                pass\n            self.lock_anim = None\n        self.current = None\n        self.status.setText("STOPPED")\n        self.status.setStyleSheet("background:#151d29;color:#aeb9ca;border:1px solid #29364a;border-radius:11px;padding:6px 11px;font-weight:700;")\n        self.start_button.setText("START STUDYLOCK")\n'''
if old in s:
    s = s.replace(old, new, 1)

# Ensure the next-question timer can never fire after an explicit stop.
old = '''    def trigger_with_animation(self):\n        hwnd, _ = self.target(); rect = window_rect(hwnd) if hwnd else None; screen = QApplication.screenAt(rect.center()) if rect else QApplication.primaryScreen(); screen = screen or QApplication.primaryScreen(); geometry = screen.geometry()\n        self.lock_anim = LockChain(geometry, bool(self.settings.get("reduced_motion"))); self.lock_anim.start(); QTimer.singleShot(720 if not self.settings.get("reduced_motion") else 190, self.trigger_question)\n'''
new = '''    def trigger_with_animation(self):\n        if not self.running:\n            return\n        hwnd, _ = self.target()\n        rect = window_rect(hwnd) if hwnd else None\n        screen = QApplication.screenAt(rect.center()) if rect else QApplication.primaryScreen()\n        screen = screen or QApplication.primaryScreen()\n        geometry = screen.geometry()\n        self.lock_anim = LockChain(None, bool(self.settings.get("reduced_motion")))\n        self.lock_anim.setGeometry(geometry)\n        self.lock_anim.start()\n        delay = 720 if not self.settings.get("reduced_motion") else 190\n        QTimer.singleShot(delay, lambda: self.trigger_question() if self.running else None)\n'''
if old in s:
    s = s.replace(old, new, 1)

# Keep the answer lifecycle deterministic: never reuse the same question object/overlay.
old = '''    def trigger_question(self):\n        if not self.running: return\n        question = self.choose_question()\n        if not question: return\n        self.current = question; self.overlay = Overlay(question, self.answer, self.target, self.settings); self.overlay.show()\n'''
new = '''    def trigger_question(self):\n        if not self.running:\n            return\n        if self.overlay is not None:\n            try:\n                self.overlay.allow_close = True\n                self.overlay.close()\n            except RuntimeError:\n                pass\n            self.overlay = None\n        question = self.choose_question()\n        if not question:\n            return\n        self.current = question\n        self.overlay = Overlay(question, self.answer, self.target, self.settings)\n        self.overlay.show()\n'''
if old in s:
    s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('StudyLock runtime fixes applied')
