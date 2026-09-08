from __future__ import annotations

import math
from typing import Callable

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QParallelAnimationGroup, QRect, Qt, QTimer, Signal
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
    """StudyLock identity mark: aura rings + protected focus core + lock keyhole."""
    def __init__(self, accent="#8B7CFF", parent=None):
        super().__init__(parent)
        self.accent = QColor(accent)
        self.secondary = QColor("#C77DFF")
        self.phase = 0.0
        self.setFixedSize(64, 64)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(35)

    def set_accent(self, color, secondary=None):
        self.accent = QColor(color)
        if secondary:
            self.secondary = QColor(secondary)
        self.update()

    def _animate(self):
        self.phase = (self.phase + 0.006) % 1.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QPoint(self.width() // 2, self.height() // 2)
        pulse = 1.0 + 0.035 * math.sin(self.phase * math.tau)
        # Radiant aura: focus expanding outward.
        for radius, alpha in ((29 * pulse, 14), (23 * pulse, 25), (18 * pulse, 38)):
            col = QColor(self.accent); col.setAlpha(alpha)
            p.setPen(QPen(col, 1.3)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(c, int(radius), int(radius))
        # Protected focus core.
        core = QPainterPath()
        core.moveTo(c.x(), c.y() - 16)
        core.cubicTo(c.x() + 14, c.y() - 13, c.x() + 15, c.y() - 1, c.x() + 10, c.y() + 11)
        core.cubicTo(c.x() + 5, c.y() + 17, c.x() - 5, c.y() + 17, c.x() - 10, c.y() + 11)
        core.cubicTo(c.x() - 15, c.y() - 1, c.x() - 14, c.y() - 13, c.x(), c.y() - 16)
        p.setPen(QPen(self.accent, 2.4)); p.setBrush(QColor(11, 15, 24, 250)); p.drawPath(core)
        # Keyhole = the lock/protection meaning.
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(245, 247, 255, 235))
        p.drawEllipse(QPoint(c.x(), c.y() - 3), 4.0, 4.0)
        p.drawRoundedRect(c.x() - 2.1, c.y(), 4.2, 9.0, 2, 2)
        # Moving aura spark.
        a = self.phase * math.tau
        sx = c.x() + math.cos(a) * 25
        sy = c.y() + math.sin(a) * 25
        spark = QColor(self.secondary); spark.setAlpha(210)
        p.setBrush(spark); p.drawEllipse(QPoint(int(sx), int(sy)), 2.1, 2.1)


class AuraTitle(QWidget):
    def __init__(self, text="StudyLock", accent="#8B7CFF", secondary="#C77DFF", parent=None):
        super().__init__(parent)
        self.text = text; self.accent = QColor(accent); self.secondary = QColor(secondary); self.phase = 0.0
        self.setMinimumHeight(64); self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._timer = QTimer(self); self._timer.timeout.connect(self._animate); self._timer.start(38)

    def set_colors(self, accent, secondary):
        self.accent = QColor(accent); self.secondary = QColor(secondary); self.update()

    def _animate(self):
        self.phase = (self.phase + 0.007) % 1.0; self.update()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QFont("Segoe UI", 31, QFont.Weight.Bold); p.setFont(font)
        fm = p.fontMetrics(); w = fm.horizontalAdvance(self.text)
        x = (self.width() - w) / 2; y = (self.height() + fm.ascent() - fm.descent()) / 2
        # Moving highlight gives the title a subtle living AURA without shifting its position.
        sweep = (self.phase * 1.6) % 1.0
        grad = QLinearGradient(x, 0, x + w, 0)
        grad.setColorAt(0.0, self.accent); grad.setColorAt(max(0.0, sweep - .16), self.accent)
        grad.setColorAt(sweep, self.secondary); grad.setColorAt(min(1.0, sweep + .16), self.accent)
        grad.setColorAt(1.0, self.accent)
        glow = QColor(self.secondary); glow.setAlpha(24)
        p.setPen(QPen(glow, 7)); p.drawText(int(x), int(y), self.text)
        p.setPen(grad); p.drawText(int(x), int(y), self.text)


class RippleCard(QFrame):
    clicked = Signal()
    def __init__(self, accent="#8B7CFF", parent=None):
        super().__init__(parent); self.accent = accent; self._hover = False
        self._ripple = 0; self._ripple_pos = QPoint()
        self.setObjectName("dashboardCard"); self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True); self.setStyleSheet(self._style())
        shadow = QGraphicsDropShadowEffect(self); shadow.setBlurRadius(0); shadow.setOffset(0, 2); shadow.setColor(QColor(0,0,0,100)); self.setGraphicsEffect(shadow); self.shadow = shadow
    def _style(self):
        border = self.accent if self._hover else "#222D3D"; bg = "#121B28" if self._hover else "#0F1722"
        return f"QFrame#dashboardCard{{background:{bg};border:1px solid {border};border-radius:18px;}}"
    def set_accent(self, accent): self.accent = accent; self.setStyleSheet(self._style())
    def enterEvent(self, event): self._hover=True; self.setStyleSheet(self._style()); self.shadow.setBlurRadius(22); self.shadow.setOffset(0,5); super().enterEvent(event)
    def leaveEvent(self, event): self._hover=False; self.setStyleSheet(self._style()); self.shadow.setBlurRadius(0); self.shadow.setOffset(0,2); super().leaveEvent(event)
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._ripple_pos = event.position().toPoint(); self._ripple = 1; QTimer.singleShot(150, self.clicked.emit); self.update()
        super().mousePressEvent(event)
    def paintEvent(self, event):
        super().paintEvent(event)
        if self._ripple:
            p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); col=QColor(self.accent); col.setAlpha(max(0,80-self._ripple*8)); p.setPen(Qt.PenStyle.NoPen); p.setBrush(col)
            p.drawEllipse(self._ripple_pos,10+self._ripple*3,10+self._ripple*3); self._ripple += 1
            if self._ripple > 10: self._ripple=0
            else: self.update()


class AnimatedStack(QStackedWidget):
    """Safe fade transitions: never alter the stack child's geometry."""
    def __init__(self, parent=None): super().__init__(parent); self._busy=False; self._anim=None
    def go(self, widget, direction=1):
        if self._busy or self.currentWidget() is widget: return
        self._busy=True; self.setCurrentWidget(widget)
        effect=QGraphicsOpacityEffect(widget); widget.setGraphicsEffect(effect); effect.setOpacity(0.0)
        fade=QPropertyAnimation(effect,b"opacity",self); fade.setDuration(220); fade.setStartValue(0.0); fade.setEndValue(1.0); fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim=fade
        fade.finished.connect(lambda: self._finish(widget))
        fade.start()
    def _finish(self, widget):
        if widget.graphicsEffect() is not None: widget.setGraphicsEffect(None)
        self._busy=False; self._anim=None


class SelectionPage(QWidget):
    def __init__(self,title,subtitle,accent,parent=None):
        super().__init__(parent); self.accent=accent
        outer=QVBoxLayout(self); outer.setContentsMargins(30,24,30,30); outer.setSpacing(18)
        head=QHBoxLayout(); self.back=QPushButton("←  Back"); self.back.setObjectName("ghost"); head.addWidget(self.back); head.addStretch(); outer.addLayout(head)
        self.heading=QLabel(title); self.heading.setObjectName("pageHeading"); outer.addWidget(self.heading)
        sub=QLabel(subtitle); sub.setObjectName("pageSubtitle"); sub.setWordWrap(True); outer.addWidget(sub)
        self.body=QVBoxLayout(); self.body.setSpacing(14); outer.addLayout(self.body); outer.addStretch()


class ThemeCard(RippleCard):
    def __init__(self,name,theme,parent=None):
        super().__init__(theme["accent"],parent); self.name=name; self.theme=theme; self.setMinimumHeight(110)
        layout=QVBoxLayout(self); layout.setContentsMargins(18,16,18,16); layout.setSpacing(8)
        sw=QHBoxLayout(); sw.setSpacing(5)
        for c in (theme["accent"],theme["secondary"],theme["glow"]):
            dot=QLabel(); dot.setFixedSize(18,18); dot.setStyleSheet(f"background:{c};border-radius:9px;"); sw.addWidget(dot)
        sw.addStretch(); layout.addLayout(sw); label=QLabel(name); label.setStyleSheet("font-size:16px;font-weight:700;"); layout.addWidget(label)
        self.selected=QLabel("SELECTED"); self.selected.setStyleSheet(f"color:{theme['accent']};font-size:10px;font-weight:800;letter-spacing:1px;"); self.selected.hide(); layout.addWidget(self.selected)
    def set_selected(self,selected): self.selected.setVisible(selected); self.setStyleSheet(self._style()+(f"QFrame#dashboardCard{{border:2px solid {self.accent};}}" if selected else ""))


def install_ui(MainWindow, GamePicker, TimerSettings, PerformanceDialog, available_curricula, subjects_for, stages_for, papers_for, filter_questions, save_settings):
    def theme(self): return THEMES.get(self.settings.get("theme","Aura Purple"),THEMES["Aura Purple"])
    def apply_theme(self):
        t=theme(self); a,s,g=t["accent"],t["secondary"],t["glow"]
        self.setStyleSheet(f"""
        QWidget{{background:#080B11;color:#EEF2F7;font-family:'Segoe UI';font-size:14px;}}
        QMainWindow{{background:#080B11;}}
        QLabel{{background:transparent;}}
        QLabel#pageHeading{{font-size:27px;font-weight:750;}}
        QLabel#pageSubtitle{{color:#8995A8;font-size:13px;}}
        QLabel#muted{{color:#8995A8;}}
        QLabel#eyebrow{{color:{a};font-size:11px;font-weight:800;letter-spacing:1.4px;}}
        QFrame#panel{{background:#0C131E;border:1px solid #1D2938;border-radius:20px;}}
        QPushButton{{background:#121C2A;border:1px solid #29384D;border-radius:11px;padding:10px 15px;font-weight:650;min-height:18px;}}
        QPushButton:hover{{background:#1A2738;border-color:{a};}} QPushButton:pressed{{background:#243552;}}
        QPushButton#primary{{background:{g};border-color:{a};color:white;}} QPushButton#primary:hover{{background:{a};}}
        QPushButton#ghost{{background:transparent;border-color:#263448;color:#AEB9CA;}}
        QLineEdit,QComboBox,QSpinBox{{background:#0A111A;border:1px solid #273448;border-radius:11px;padding:11px;color:#EEF2F7;min-height:20px;}}
        QLineEdit:focus,QComboBox:focus,QSpinBox:focus{{border:1px solid {a};}}
        QScrollArea{{border:0;background:transparent;}}
        """)
        if hasattr(self,"logo"): self.logo.set_accent(a,s)
        if hasattr(self,"title_widget"): self.title_widget.set_colors(a,s)
        for card in getattr(self,"dashboard_cards",[]): card.set_accent(a)
        for c in getattr(self,"theme_cards",[]): c.set_selected(c.name==self.settings.get("theme"))

    def make_header(self):
        header=QHBoxLayout(); header.setContentsMargins(12,4,12,2); header.setSpacing(12)
        left=QHBoxLayout(); left.setSpacing(9); self.logo=AuraLogo(theme(self)["accent"]); left.addWidget(self.logo)
        identity=QVBoxLayout(); identity.setSpacing(0)
        tag=QLabel("AURA FOCUS"); tag.setObjectName("eyebrow"); identity.addWidget(tag)
        meaning=QLabel("Protected study state"); meaning.setObjectName("muted"); meaning.setStyleSheet("font-size:10px;"); identity.addWidget(meaning)
        left.addLayout(identity); header.addLayout(left,1)
        self.title_widget=AuraTitle(APP_NAME,theme(self)["accent"],theme(self)["secondary"]); header.addWidget(self.title_widget,0,Qt.AlignmentFlag.AlignCenter)
        right=QHBoxLayout(); right.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter); settings_btn=QPushButton("⚙"); settings_btn.setToolTip("Settings"); settings_btn.setFixedSize(42,42); settings_btn.clicked.connect(self.open_quick_settings); right.addWidget(settings_btn); header.addLayout(right,1)
        return header

    def wrap(page):
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); scroll.setWidget(page); return scroll

    # Preserve the remainder of the established dashboard/page implementation.
    # The installer below is populated by the original project methods at runtime.
    # Header/theme/transition primitives above are the only presentation changes.
    old_build=getattr(MainWindow,"build_ui",None)
    if old_build:
        MainWindow.build_ui=old_build
    MainWindow.theme=theme
    MainWindow.apply_theme=apply_theme
    MainWindow.make_header=make_header
    MainWindow.wrap=wrap
    MainWindow.AuraLogo=AuraLogo
    MainWindow.AuraTitle=AuraTitle
    MainWindow.AnimatedStack=AnimatedStack
    MainWindow.RippleCard=RippleCard
