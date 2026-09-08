from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QSequentialAnimationGroup, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QSpinBox, QStackedWidget, QVBoxLayout, QWidget
)


THEMES = {
    "Aura Purple": {"accent": "#8B7CFF", "secondary": "#C77DFF", "glow": "#6C63FF"},
    "Cyber Blue": {"accent": "#5EA7FF", "secondary": "#72E0FF", "glow": "#3182FF"},
    "Electric Cyan": {"accent": "#42E8D5", "secondary": "#6FB8FF", "glow": "#00BFAE"},
    "Emerald": {"accent": "#58D68D", "secondary": "#9AF0B8", "glow": "#25A865"},
    "Crimson": {"accent": "#FF647C", "secondary": "#FF9A8B", "glow": "#D83A56"},
    "Sunset": {"accent": "#FF9F5A", "secondary": "#FF6FAE", "glow": "#F06A32"},
    "Violet": {"accent": "#B78CFF", "secondary": "#7FD7FF", "glow": "#7B4DFF"},
    "Ocean": {"accent": "#4CC9F0", "secondary": "#4361EE", "glow": "#277DA1"},
    "Rose": {"accent": "#FF77B7", "secondary": "#B388FF", "glow": "#D94F93"},
    "Monochrome": {"accent": "#E8EDF5", "secondary": "#9DA8BA", "glow": "#778195"},
}


class AuraLogo(QWidget):
    def __init__(self, accent="#8B7CFF", parent=None):
        super().__init__(parent)
        self.accent = QColor(accent)
        self.phase = 0.0
        self.setFixedSize(52, 52)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(42)

    def set_accent(self, color):
        self.accent = QColor(color)
        self.update()

    def _animate(self):
        self.phase = (self.phase + 0.012) % 1.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QPoint(self.width() // 2, self.height() // 2)
        pulse = 1.0 + 0.035 * __import__('math').sin(self.phase * 6.283)
        for radius, alpha in ((22 * pulse, 22), (17 * pulse, 34), (12, 55)):
            col = QColor(self.accent); col.setAlpha(alpha)
            p.setPen(QPen(col, 1.4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(c, int(radius), int(radius))
        path = QPainterPath()
        path.moveTo(c.x(), c.y() - 13)
        path.cubicTo(c.x() + 11, c.y() - 11, c.x() + 13, c.y() - 1, c.x() + 9, c.y() + 10)
        path.cubicTo(c.x() + 4, c.y() + 15, c.x() - 4, c.y() + 15, c.x() - 9, c.y() + 10)
        path.cubicTo(c.x() - 13, c.y() - 1, c.x() - 11, c.y() - 11, c.x(), c.y() - 13)
        p.setPen(QPen(self.accent, 2.2)); p.setBrush(QColor(14, 18, 29, 245)); p.drawPath(path)
        p.setPen(QPen(QColor(245, 247, 255, 235), 2.0)); p.drawLine(c.x() - 5, c.y() + 1, c.x() + 5, c.y() + 1)
        p.drawLine(c.x(), c.y() - 4, c.x(), c.y() + 7)
        dot = 2.2 + 0.7 * __import__('math').sin(self.phase * 6.283)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(self.accent); p.drawEllipse(c, dot, dot)


class AuraTitle(QWidget):
    def __init__(self, text="StudyLock", accent="#8B7CFF", secondary="#C77DFF", parent=None):
        super().__init__(parent)
        self.text = text; self.accent = QColor(accent); self.secondary = QColor(secondary); self.phase = 0.0
        self.setMinimumHeight(54); self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._timer = QTimer(self); self._timer.timeout.connect(self._animate); self._timer.start(45)

    def set_colors(self, accent, secondary):
        self.accent = QColor(accent); self.secondary = QColor(secondary); self.update()

    def _animate(self):
        self.phase = (self.phase + 0.008) % 1.0; self.update()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QFont("Segoe UI", 30, QFont.Weight.Bold); p.setFont(font)
        fm = p.fontMetrics(); w = fm.horizontalAdvance(self.text); x = (self.width() - w) / 2; y = (self.height() + fm.ascent() - fm.descent()) / 2
        grad = QLinearGradient(x, 0, x + w, 0)
        shift = (self.phase * 2.0) - 0.5
        grad.setColorAt(max(0.0, min(1.0, 0.0 + shift)), self.secondary)
        grad.setColorAt(0.48, self.accent); grad.setColorAt(max(0.0, min(1.0, 0.8 + shift)), self.secondary)
        p.setPen(grad); p.drawText(int(x), int(y), self.text)
        glow = QColor(self.accent); glow.setAlpha(22)
        p.setPen(QPen(glow, 7)); p.drawText(int(x), int(y), self.text)


class RippleCard(QFrame):
    clicked = Signal()

    def __init__(self, accent="#8B7CFF", parent=None):
        super().__init__(parent)
        self.accent = accent; self._hover = False; self._ripple = 0; self._ripple_pos = QPoint()
        self.setObjectName("dashboardCard"); self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(self._style())
        shadow = QGraphicsDropShadowEffect(self); shadow.setBlurRadius(0); shadow.setOffset(0, 2); shadow.setColor(QColor(0, 0, 0, 100)); self.setGraphicsEffect(shadow); self.shadow = shadow

    def _style(self):
        border = self.accent if self._hover else "#222D3D"
        bg = "#121B28" if self._hover else "#0F1722"
        return f"QFrame#dashboardCard{{background:{bg};border:1px solid {border};border-radius:18px;}}"

    def set_accent(self, accent): self.accent = accent; self.setStyleSheet(self._style())

    def enterEvent(self, event):
        self._hover = True; self.setStyleSheet(self._style()); self.shadow.setBlurRadius(22); self.shadow.setOffset(0, 5); super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False; self.setStyleSheet(self._style()); self.shadow.setBlurRadius(0); self.shadow.setOffset(0, 2); super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._ripple_pos = event.position().toPoint(); self._ripple = 1
            QTimer.singleShot(175, self.clicked.emit); self.update()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._ripple:
            p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
            col = QColor(self.accent); col.setAlpha(max(0, 80 - self._ripple * 8))
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(col); p.drawEllipse(self._ripple_pos, 10 + self._ripple * 3, 10 + self._ripple * 3)
            self._ripple += 1
            if self._ripple > 10: self._ripple = 0
            else: self.update()


class AnimatedStack(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self._busy = False

    def go(self, widget, direction=1):
        if self._busy or self.currentWidget() is widget: return
        self._busy = True
        old = self.currentWidget(); self.setCurrentWidget(widget)
        effect = QGraphicsOpacityEffect(widget); widget.setGraphicsEffect(effect); effect.setOpacity(0.0)
        fade = QPropertyAnimation(effect, b"opacity", self); fade.setDuration(310); fade.setStartValue(0.0); fade.setEndValue(1.0); fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        geo = widget.geometry(); start = QRect(geo.x() + 26 * direction, geo.y(), geo.width(), geo.height())
        widget.setGeometry(start)
        slide = QPropertyAnimation(widget, b"geometry", self); slide.setDuration(310); slide.setStartValue(start); slide.setEndValue(geo); slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        group = QSequentialAnimationGroup(self); group.addAnimation(fade); group.finished.connect(lambda: self._finish(widget, effect)); group.start(); self._slide = slide; slide.start()

    def _finish(self, widget, effect):
        widget.setGraphicsEffect(None); self._busy = False


class SelectionPage(QWidget):
    def __init__(self, title, subtitle, accent, parent=None):
        super().__init__(parent); self.accent = accent
        outer = QVBoxLayout(self); outer.setContentsMargins(30, 24, 30, 30); outer.setSpacing(18)
        head = QHBoxLayout(); self.back = QPushButton("←  Back"); self.back.setObjectName("ghost"); head.addWidget(self.back); head.addStretch(); outer.addLayout(head)
        self.heading = QLabel(title); self.heading.setObjectName("pageHeading"); outer.addWidget(self.heading)
        sub = QLabel(subtitle); sub.setObjectName("pageSubtitle"); sub.setWordWrap(True); outer.addWidget(sub)
        self.body = QVBoxLayout(); self.body.setSpacing(14); outer.addLayout(self.body); outer.addStretch()


class ThemeCard(RippleCard):
    def __init__(self, name, theme, parent=None):
        super().__init__(theme["accent"], parent); self.name = name; self.theme = theme; self.setMinimumHeight(110)
        layout = QVBoxLayout(self); layout.setContentsMargins(18, 16, 18, 16); layout.setSpacing(8)
        swatches = QHBoxLayout(); swatches.setSpacing(5)
        for c in (theme["accent"], theme["secondary"], theme["glow"]):
            dot = QLabel(); dot.setFixedSize(18, 18); dot.setStyleSheet(f"background:{c};border-radius:9px;"); swatches.addWidget(dot)
        swatches.addStretch(); layout.addLayout(swatches)
        label = QLabel(name); label.setStyleSheet("font-size:16px;font-weight:700;"); layout.addWidget(label)
        self.selected = QLabel("SELECTED"); self.selected.setStyleSheet(f"color:{theme['accent']};font-size:10px;font-weight:800;letter-spacing:1px;"); self.selected.hide(); layout.addWidget(self.selected)

    def set_selected(self, selected): self.selected.setVisible(selected); self.setStyleSheet(self._style() + (f"QFrame#dashboardCard{{border:2px solid {self.accent};}}" if selected else ""))


def install_ui(MainWindow, GamePicker, TimerSettings, PerformanceDialog, available_curricula, subjects_for, stages_for, papers_for, filter_questions, save_settings):
    """Install the visual overhaul while keeping MainWindow's existing engine methods intact."""

    def theme(self):
        name = self.settings.get("theme", "Aura Purple")
        return THEMES.get(name, THEMES["Aura Purple"])

    def apply_theme(self):
        t = theme(self); a, s, g = t["accent"], t["secondary"], t["glow"]
        self.setStyleSheet(f"""
        QWidget{{background:#080B11;color:#EEF2F7;font-family:'Segoe UI';font-size:14px;}}
        QMainWindow{{background:#080B11;}}
        QLabel{{background:transparent;}}
        QLabel#pageHeading{{font-size:27px;font-weight:750;}}
        QLabel#pageSubtitle{{color:#8995A8;font-size:13px;}}
        QLabel#muted{{color:#8995A8;}}
        QLabel#eyebrow{{color:{a};font-size:11px;font-weight:800;letter-spacing:1.4px;}}
        QLabel#statusPill{{background:#151D29;border:1px solid #29364A;border-radius:10px;padding:7px 12px;font-weight:700;}}
        QFrame#panel{{background:#0C131E;border:1px solid #1D2938;border-radius:20px;}}
        QFrame#miniPanel{{background:#0F1722;border:1px solid #202C3D;border-radius:14px;}}
        QPushButton{{background:#121C2A;border:1px solid #29384D;border-radius:11px;padding:10px 15px;font-weight:650;min-height:18px;}}
        QPushButton:hover{{background:#1A2738;border-color:{a};}}
        QPushButton:pressed{{background:#243552;}}
        QPushButton#primary{{background:{g};border-color:{a};color:white;}}
        QPushButton#primary:hover{{background:{a};}}
        QPushButton#ghost{{background:transparent;border-color:#263448;color:#AEB9CA;}}
        QPushButton#danger{{background:#22161B;border-color:#56303A;color:#FFB6C0;}}
        QLineEdit,QComboBox,QSpinBox{{background:#0A111A;border:1px solid #273448;border-radius:11px;padding:11px;color:#EEF2F7;min-height:20px;}}
        QLineEdit:focus,QComboBox:focus,QSpinBox:focus{{border:1px solid {a};}}
        QComboBox::drop-down{{border:0;width:28px;}}
        QScrollArea{{border:0;background:transparent;}}
        QProgressBar{{background:#0B111A;border:1px solid #263347;border-radius:7px;text-align:center;height:12px;}}
        QProgressBar::chunk{{background:{a};border-radius:6px;}}
        """)
        if hasattr(self, "logo"): self.logo.set_accent(a)
        if hasattr(self, "title_widget"): self.title_widget.set_colors(a, s)
        for card in getattr(self, "dashboard_cards", []): card.set_accent(a)
        if hasattr(self, "theme_cards"):
            for c in self.theme_cards: c.set_selected(c.name == self.settings.get("theme"))

    def make_header(self):
        header = QHBoxLayout(); header.setContentsMargins(8, 2, 8, 0)
        self.logo = AuraLogo(theme(self)["accent"]); header.addWidget(self.logo)
        header.addStretch(1)
        self.title_widget = AuraTitle(APP_NAME, theme(self)["accent"], theme(self)["secondary"]); header.addWidget(self.title_widget, 2)
        header.addStretch(1)
        settings_btn = QPushButton("⚙"); settings_btn.setToolTip("Settings"); settings_btn.setFixedSize(42, 42); settings_btn.clicked.connect(self.open_quick_settings); header.addWidget(settings_btn)
        return header

    def wrap(page):
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); scroll.setWidget(page); return scroll

    def dashboard():
        page = QWidget(); root = QVBoxLayout(page); root.setContentsMargins(46, 18, 46, 34); root.setSpacing(15)
        greeting = QLabel(); greeting.setObjectName("pageHeading"); self.greeting = greeting; root.addWidget(greeting)
        desc = QLabel("Configure your study environment, then let StudyLock handle the interruptions."); desc.setObjectName("pageSubtitle"); root.addWidget(desc)
        root.addSpacing(8)
        grid = QGridLayout(); grid.setHorizontalSpacing(14); grid.setVerticalSpacing(14)
        cards = []
        def add_card(row, col, icon, title, subtitle, key, handler):
            card = RippleCard(theme(self)["accent"]); card.setMinimumHeight(126); lay = QHBoxLayout(card); lay.setContentsMargins(20, 18, 18, 18); lay.setSpacing(15)
            icon_label = QLabel(icon); icon_label.setFixedWidth(42); icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter); icon_label.setStyleSheet(f"font-size:26px;color:{theme(self)['accent']};")
            lay.addWidget(icon_label)
            text = QVBoxLayout(); text.setSpacing(4); t = QLabel(title); t.setStyleSheet("font-size:17px;font-weight:750;"); text.addWidget(t); s = QLabel(subtitle); s.setObjectName("muted"); s.setWordWrap(True); text.addWidget(s); lay.addLayout(text, 1)
            arrow = QLabel("Change  →"); arrow.setStyleSheet(f"color:{theme(self)['accent']};font-weight:700;"); lay.addWidget(arrow, 0, Qt.AlignmentFlag.AlignVCenter)
            card.clicked.connect(handler); grid.addWidget(card, row, col); cards.append(card); setattr(self, key + "_card", card)
        add_card(0, 0, "◈", "Select Your Curriculum", "Choose curriculum, subject, qualification and paper", "curriculum", lambda: self.go_page(self.curriculum_page, 1))
        add_card(0, 1, "◉", "Select A Game", "Choose the Windows game StudyLock should monitor", "game", lambda: self.go_page(self.game_page, 1))
        add_card(1, 0, "◷", "Choose Your Question Interval", "Set how often StudyLock asks a question", "interval", lambda: self.go_page(self.interval_page, 1))
        add_card(1, 1, "▥", "History", "Review accuracy, speed and topic performance", "history", lambda: self.go_page(self.history_page, 1))
        self.dashboard_cards = cards; root.addLayout(grid)
        status = QFrame(); status.setObjectName("panel"); sl = QHBoxLayout(status); sl.setContentsMargins(18, 14, 18, 14)
        self.status = QLabel("STOPPED"); self.status.setObjectName("statusPill"); sl.addWidget(self.status); self.dashboard_summary = QLabel(); self.dashboard_summary.setObjectName("muted"); sl.addWidget(self.dashboard_summary, 1); root.addWidget(status)
        actions = QHBoxLayout(); actions.setSpacing(10)
        self.start_button = QPushButton("START STUDYLOCK"); self.start_button.setObjectName("primary"); self.start_button.setMinimumHeight(44); self.start_button.clicked.connect(self.toggle); actions.addWidget(self.start_button)
        stop = QPushButton("STOP"); stop.setMinimumHeight(44); stop.clicked.connect(self.stop); actions.addWidget(stop)
        test = QPushButton("TEST QUESTION"); test.setMinimumHeight(44); test.clicked.connect(self.trigger_test_question); actions.addWidget(test)
        actions.addStretch()
        performance = QPushButton("Performance"); performance.clicked.connect(lambda: self.show_perf(False)); actions.addWidget(performance)
        weak = QPushButton("Practice Weak Areas"); weak.clicked.connect(lambda: self.show_perf(True)); actions.addWidget(weak)
        root.addLayout(actions)
        note = QLabel("StudyLock only interrupts the selected target window. Switching to another app hides the question and keeps the rest of your desktop usable."); note.setObjectName("muted"); note.setWordWrap(True); root.addWidget(note)
        self.bank_label = QLabel(); self.bank_label.setObjectName("muted"); root.addWidget(self.bank_label)
        return page

    def selection_header(page):
        page.back.clicked.connect(lambda: self.go_page(self.home_page, -1))

    def curriculum_page():
        page = SelectionPage("Study Configuration", "Set the curriculum path StudyLock will use for questions. Your choices are saved and previewed on the home screen.", theme(self)["accent"])
        self.curriculum_page = page; selection_header(page)
        fields = QGridLayout(); fields.setHorizontalSpacing(14); fields.setVerticalSpacing(10)
        labels = ["Curriculum", "Subject", "Qualification", "Paper"]
        combos = []
        for i, label in enumerate(labels):
            lab = QLabel(label); lab.setObjectName("eyebrow"); fields.addWidget(lab, 0, i)
            cb = QComboBox(); fields.addWidget(cb, 1, i); combos.append(cb)
        self.curr, self.subj, self.qual, self.paper = combos
        self.curr.addItems([c.name for c in available_curricula()]); self.curr.currentIndexChanged.connect(self.refresh_course); self.subj.currentIndexChanged.connect(self.refresh_qualification); self.qual.currentIndexChanged.connect(self.refresh_papers); self.paper.currentIndexChanged.connect(self.refresh_status)
        page.body.addLayout(fields)
        preview = QFrame(); preview.setObjectName("miniPanel"); pv = QVBoxLayout(preview); pv.setContentsMargins(16, 14, 16, 14); self.course_preview = QLabel(); self.course_preview.setWordWrap(True); pv.addWidget(self.course_preview); page.body.addWidget(preview)
        save = QPushButton("Save Configuration  →"); save.setObjectName("primary"); save.clicked.connect(lambda: self.go_page(self.home_page, -1)); page.body.addWidget(save)
        return page

    def game_page():
        page = SelectionPage("Select A Game", "StudyLock monitors only the target window. Other applications remain usable.", theme(self)["accent"]); self.game_page = page; selection_header(page)
        panel = QFrame(); panel.setObjectName("panel"); lay = QVBoxLayout(panel); lay.setContentsMargins(22, 22, 22, 22); lay.setSpacing(12)
        self.game_page_label = QLabel(); self.game_page_label.setStyleSheet("font-size:18px;font-weight:750;"); lay.addWidget(self.game_page_label)
        hint = QLabel("Use the selector to choose a running Windows application. You can change it at any time."); hint.setObjectName("muted"); hint.setWordWrap(True); lay.addWidget(hint)
        choose = QPushButton("Choose Running Application"); choose.setObjectName("primary"); choose.clicked.connect(self.pick_game); lay.addWidget(choose, 0, Qt.AlignmentFlag.AlignLeft)
        page.body.addWidget(panel); return page

    def interval_page():
        page = SelectionPage("Choose Your Question Interval", "Choose how frequently StudyLock should interrupt the selected game. The existing timer engine remains in control of the countdown.", theme(self)["accent"]); self.interval_page = page; selection_header(page)
        panel = QFrame(); panel.setObjectName("panel"); lay = QVBoxLayout(panel); lay.setContentsMargins(22, 22, 22, 22); lay.setSpacing(14)
        self.interval = QSpinBox(); self.interval.setRange(5, 3600); self.interval.setValue(int(self.settings.get("interval", 20))); self.interval.setSuffix(" seconds"); self.interval.setMinimumHeight(44); lay.addWidget(self.interval)
        quick = QHBoxLayout()
        for seconds in (300, 600, 900, 1200, 1800):
            b = QPushButton(f"{seconds//60} min"); b.clicked.connect(lambda _, s=seconds: self.interval.setValue(s)); quick.addWidget(b)
        lay.addLayout(quick)
        save = QPushButton("Save Interval  →"); save.setObjectName("primary"); save.clicked.connect(self.save_interval); lay.addWidget(save, 0, Qt.AlignmentFlag.AlignLeft)
        page.body.addWidget(panel); return page

    def history_page():
        page = SelectionPage("History", "A quick view of your study performance. Accuracy is the primary signal; response speed is secondary.", theme(self)["accent"]); self.history_page = page; page.back.clicked.connect(lambda: self.go_page(self.home_page, -1))
        self.history_content = QVBoxLayout(); page.body.addLayout(self.history_content)
        refresh = QPushButton("Refresh History"); refresh.clicked.connect(self.refresh_history); page.body.addWidget(refresh, 0, Qt.AlignmentFlag.AlignLeft)
        return page

    def onboarding():
        page = QWidget(); root = QVBoxLayout(page); root.setContentsMargins(80, 45, 80, 45); root.setSpacing(18); root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top = QHBoxLayout(); top.addWidget(AuraLogo(theme(self)["accent"])); top.addStretch(); step = QLabel("WELCOME  •  1 / 3"); step.setObjectName("eyebrow"); top.addWidget(step); root.addLayout(top)
        self.onboard_stack = AnimatedStack(); self.onboard_stack.setMinimumHeight(360); root.addWidget(self.onboard_stack, 1)
        def step_page(title, subtitle):
            w = QWidget(); l = QVBoxLayout(w); l.setAlignment(Qt.AlignmentFlag.AlignCenter); l.setContentsMargins(50, 20, 50, 20); h = QLabel(title); h.setAlignment(Qt.AlignmentFlag.AlignCenter); h.setObjectName("pageHeading"); l.addWidget(h); s = QLabel(subtitle); s.setAlignment(Qt.AlignmentFlag.AlignCenter); s.setWordWrap(True); s.setObjectName("pageSubtitle"); l.addWidget(s); return w, l
        p1, l1 = step_page("Hey! What Should We Call You?", "Choose a name you'd like StudyLock to use. This is stored locally on this device.")
        self.name_edit = QLineEdit(); self.name_edit.setPlaceholderText("Enter your name…"); self.name_edit.setMaximumWidth(420); self.name_edit.setMinimumHeight(46); l1.addWidget(self.name_edit, 0, Qt.AlignmentFlag.AlignHCenter)
        b1 = QPushButton("Continue  →"); b1.setObjectName("primary"); b1.setMinimumWidth(180); b1.clicked.connect(self.next_onboarding_account); l1.addWidget(b1, 0, Qt.AlignmentFlag.AlignHCenter); self.onboard_stack.addWidget(p1)
        p2, l2 = step_page("Want to Connect an Account?", "We suggest you connect an account so settings and progress can be associated with you. Data is not shared with anyone else.")
        b2 = QPushButton("Connect Account"); b2.clicked.connect(self.account_info); l2.addWidget(b2, 0, Qt.AlignmentFlag.AlignHCenter); skip = QPushButton("Skip for now"); skip.setObjectName("ghost"); skip.clicked.connect(self.next_onboarding_theme); l2.addWidget(skip, 0, Qt.AlignmentFlag.AlignHCenter); self.onboard_stack.addWidget(p2)
        p3, l3 = step_page("Select a Theme", "Choose the Aura that fits you. You can change this later from settings.")
        wrap = QWidget(); grid = QGridLayout(wrap); grid.setHorizontalSpacing(12); grid.setVerticalSpacing(12); self.theme_cards = []
        for i, (name, data) in enumerate(THEMES.items()):
            card = ThemeCard(name, data); card.clicked.connect(lambda n=name: self.select_theme(n)); self.theme_cards.append(card); grid.addWidget(card, i // 2, i % 2)
        l3.addWidget(wrap, 0, Qt.AlignmentFlag.AlignHCenter)
        finish = QPushButton("Enter StudyLock  →"); finish.setObjectName("primary"); finish.setMinimumWidth(220); finish.clicked.connect(self.finish_onboarding); l3.addWidget(finish, 0, Qt.AlignmentFlag.AlignHCenter); self.onboard_stack.addWidget(p3)
        return page

    self.theme = theme
    self.apply_theme = apply_theme
    self.go_page = lambda widget, direction=1: self.stack.go(widget, direction)

    def build_ui():
        self.settings.setdefault("theme", "Aura Purple"); self.settings.setdefault("onboarding_complete", False); self.settings.setdefault("profile_name", ""); save_settings(self.settings)
        root = QWidget(); outer = QVBoxLayout(root); outer.setContentsMargins(18, 12, 18, 12); outer.setSpacing(4); outer.addLayout(make_header())
        self.stack = AnimatedStack(); outer.addWidget(self.stack, 1)
        self.home_page = wrap(dashboard()); self.curriculum_page = None; self.game_page = None; self.interval_page = None; self.history_page = None
        self.stack.addWidget(self.home_page)
        # Build configuration pages after dashboard so all existing MainWindow engine methods can keep their expected widgets.
        cpage = curriculum_page(); gpage = game_page(); ipage = interval_page(); hpage = history_page()
        self.stack.addWidget(cpage); self.stack.addWidget(gpage); self.stack.addWidget(ipage); self.stack.addWidget(hpage)
        onboarding_page = onboarding(); self.onboarding_page = onboarding_page; self.stack.addWidget(onboarding_page)
        if self.settings.get("onboarding_complete"):
            self.stack.setCurrentWidget(self.home_page)
        else:
            self.stack.setCurrentWidget(onboarding_page)
        self.apply_theme(); self.update_dashboard_labels(); self.refresh_history()
        self.setCentralWidget(root)

    def next_onboarding_account():
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setFocus(); return
        self.settings["profile_name"] = name; save_settings(self.settings); self.onboard_stack.setCurrentIndex(1)

    def next_onboarding_theme(): self.onboard_stack.setCurrentIndex(2)

    def finish_onboarding():
        self.settings["onboarding_complete"] = True; save_settings(self.settings); self.stack.go(self.home_page, 1); self.update_dashboard_labels()

    def select_theme(name):
        self.settings["theme"] = name; save_settings(self.settings); apply_theme(self)

    def account_info():
        QMessageBox.information(self, APP_NAME, "Account connection is prepared in the onboarding flow, but no online account service is currently configured. You can safely skip it and use StudyLock locally.")

    def save_interval():
        self.settings["interval"] = int(self.interval.value()); save_settings(self.settings); self.update_dashboard_labels(); self.go_page(self.home_page, -1)

    def open_quick_settings():
        dialog = TimerSettings(self.settings, self)
        if dialog.exec(): save_settings(self.settings); self.settings = __import__('main').load_settings()
        self.apply_theme()

    def refresh_status_new():
        if not hasattr(self, "bank_label") or not hasattr(self, "curr"): return
        try:
            cid, subject, stage, paper = self.selected_filter(); qs = filter_questions(self.questions, curriculum_id=cid, subject=subject, qualification_stage=stage, paper_id=paper)
            self.bank_label.setText(f"{len(qs)} questions available  •  {self.stats.get('total_answered', 0)} answers recorded")
            if hasattr(self, "course_preview"): self.course_preview.setText(f"{self.curr.currentText()}  •  {self.subj.currentText()}  •  {self.qual.currentText()}  •  {self.paper.currentText()}")
        except Exception: pass
        self.update_dashboard_labels()

    def update_dashboard_labels():
        if not hasattr(self, "curr") or not hasattr(self, "greeting"): return
        name = self.settings.get("profile_name", "").strip(); self.greeting.setText(f"Welcome back, {name}." if name else "Welcome to StudyLock.")
        course = f"{self.curr.currentText()} • {self.subj.currentText()} • {self.qual.currentText()} • {self.paper.currentText()}"
        game = self.settings.get("game") or {}; game_text = game.get("name", "No game selected")
        interval_text = f"{int(self.interval.value())} seconds" if hasattr(self, "interval") else f"{int(self.settings.get('interval',20))} seconds"
        for card, text in ((getattr(self,'curriculum_card',None), course), (getattr(self,'game_card',None), game_text), (getattr(self,'interval_card',None), interval_text), (getattr(self,'history_card',None), f"{self.stats.get('total_answered',0)} answers recorded")):
            if card:
                labels = card.findChildren(QLabel); [lab.setText(text) for lab in labels if lab.objectName() == "muted"]
        if hasattr(self, "dashboard_summary"):
            self.dashboard_summary.setText(f"{course}   •   Target: {game_text}   •   Interval: {interval_text}")
        if hasattr(self, "game_page_label"): self.game_page_label.setText(game_text)

    def refresh_game_label_new(): update_dashboard_labels()

    def pick_game_new():
        dialog = GamePicker(self, self.settings.get("game", {}))
        if dialog.exec(): self.settings["game"] = dialog.selected; save_settings(self.settings); update_dashboard_labels()

    def refresh_history():
        if not hasattr(self, "history_content"): return
        while self.history_content.count():
            item = self.history_content.takeAt(0); w = item.widget();
            if w: w.deleteLater()
        answered = int(self.stats.get("total_answered", 0)); correct = int(self.stats.get("total_correct", 0)); accuracy = (correct / answered * 100) if answered else 0
        summary = QFrame(); summary.setObjectName("panel"); sl = QHBoxLayout(summary); sl.setContentsMargins(18, 16, 18, 16)
        for value, label in ((str(answered), "Answered"), (str(correct), "Correct"), (f"{accuracy:.0f}%", "Accuracy"), (str(self.stats.get("sessions",0)), "Sessions")):
            box = QVBoxLayout(); v = QLabel(value); v.setStyleSheet(f"font-size:23px;font-weight:800;color:{theme(self)['accent']};"); box.addWidget(v); l = QLabel(label); l.setObjectName("muted"); box.addWidget(l); sl.addLayout(box, 1)
        self.history_content.addWidget(summary)
        perf = QPushButton("Open Detailed Performance"); perf.clicked.connect(lambda: self.show_perf(False)); self.history_content.addWidget(perf, 0, Qt.AlignmentFlag.AlignLeft)

    def open_quick_settings_wrapper(): open_quick_settings()

    # Preserve the engine and replace only the presentation-facing methods.
    MainWindow.build_ui = build_ui
    MainWindow.refresh_status = refresh_status_new
    MainWindow.refresh_game_label = refresh_game_label_new
    MainWindow.pick_game = pick_game_new
    MainWindow.update_dashboard_labels = update_dashboard_labels
    MainWindow.refresh_history = refresh_history
    MainWindow.save_interval = save_interval
    MainWindow.next_onboarding_account = next_onboarding_account
    MainWindow.next_onboarding_theme = next_onboarding_theme
    MainWindow.finish_onboarding = finish_onboarding
    MainWindow.select_theme = select_theme
    MainWindow.account_info = account_info
    MainWindow.open_quick_settings = open_quick_settings_wrapper
