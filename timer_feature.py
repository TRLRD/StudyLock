import time
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QLabel, QDialog, QFormLayout, QSpinBox, QComboBox,
    QPushButton, QHBoxLayout, QVBoxLayout, QColorDialog,
    QGraphicsOpacityEffect, QApplication
)

DEFAULT_TIMER = {
    "color": "#FFFFFF",
    "size": 18,
    "position": "Top Right",
}


def timer_settings(settings):
    t = settings.setdefault("timer", {})
    for key, value in DEFAULT_TIMER.items():
        t.setdefault(key, value)
    return t


class TimerSettingsDialog(QDialog):
    def __init__(self, settings, on_save, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Timer Settings")
        self.resize(420, 230)
        self.settings = settings
        self.on_save = on_save
        t = timer_settings(settings)

        v = QVBoxLayout(self)
        form = QFormLayout()

        self.size = QSpinBox()
        self.size.setRange(10, 48)
        self.size.setValue(int(t["size"]))
        self.size.setSuffix(" px")
        form.addRow("Timer size", self.size)

        self.position = QComboBox()
        self.position.addItems(["Top Left", "Top Right", "Bottom Left", "Bottom Right"])
        self.position.setCurrentText(t["position"])
        form.addRow("Corner", self.position)

        color_row = QHBoxLayout()
        self.color = t["color"]
        self.color_button = QPushButton(self.color)
        self.color_button.clicked.connect(self.choose_color)
        color_row.addWidget(self.color_button)
        color_row.addStretch()
        form.addRow("Timer color", color_row)
        v.addLayout(form)

        v.addWidget(QLabel("The timer turns red and smoothly blinks during the final 5 seconds."))
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.clicked.connect(self.save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        v.addLayout(buttons)

    def choose_color(self):
        chosen = QColorDialog.getColor(QColor(self.color), self, "Choose timer color")
        if chosen.isValid():
            self.color = chosen.name().upper()
            self.color_button.setText(self.color)

    def save(self):
        t = timer_settings(self.settings)
        t["color"] = self.color
        t["size"] = self.size.value()
        t["position"] = self.position.currentText()
        self.on_save()
        self.accept()


class TimerOverlay(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.last_second = None
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.label = QLabel("20:00", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.effect = QGraphicsOpacityEffect(self)
        self.effect.setOpacity(1.0)
        self.label.setGraphicsEffect(self.effect)
        self.animation = QPropertyAnimation(self.effect, b"opacity", self)
        self.animation.setDuration(650)
        self.animation.setStartValue(1.0)
        self.animation.setKeyValueAt(0.5, 0.25)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.update_style()
        self.poll = QTimer(self)
        self.poll.timeout.connect(self.update_timer)
        self.poll.start(100)
        self.hide()

    def update_style(self, warning=False):
        t = timer_settings(self.main_window.settings)
        color = "#FF3B3B" if warning else t["color"]
        self.label.setFont(QFont("Segoe UI", int(t["size"]), QFont.Weight.Bold))
        self.label.setStyleSheet(
            f"color: {color}; background: rgba(17,19,24,210);"
            "border-radius: 8px; padding: 4px 9px;"
        )
        self.adjustSize()

    def screen_geometry(self):
        target_hwnd, _ = self.main_window.target_info()
        if target_hwnd:
            rect = main_window_rect(target_hwnd)
            if rect:
                screen = QApplication.screenAt(rect.center())
                if screen:
                    return screen.geometry()
        return QApplication.primaryScreen().geometry()

    def place(self):
        screen = self.screen_geometry()
        margin = 16
        size = self.sizeHint()
        pos = timer_settings(self.main_window.settings)["position"]
        if pos == "Top Left":
            x, y = screen.left() + margin, screen.top() + margin
        elif pos == "Bottom Left":
            x, y = screen.left() + margin, screen.bottom() - size.height() - margin + 1
        elif pos == "Bottom Right":
            x, y = screen.right() - size.width() - margin + 1, screen.bottom() - size.height() - margin + 1
        else:
            x, y = screen.right() - size.width() - margin + 1, screen.top() + margin
        self.move(x, y)

    def update_timer(self):
        if not self.main_window.session or self.main_window.overlay:
            if self.isVisible():
                self.hide()
            return
        if not self.main_window.target_active():
            if self.isVisible():
                self.hide()
            return

        remaining = max(0.0, float(self.main_window.remaining))
        seconds = int(remaining + 0.999)
        minutes, secs = divmod(seconds, 60)
        self.label.setText(f"{minutes:02d}:{secs:02d}")
        warning = 0 < remaining <= 5.0
        self.update_style(warning)
        if warning:
            if seconds != self.last_second:
                self.last_second = seconds
                self.animation.stop()
                self.animation.start()
        else:
            self.last_second = None
            self.animation.stop()
            self.effect.setOpacity(1.0)

        self.place()
        if not self.isVisible():
            self.show()

    def reset_after_question(self):
        self.last_second = None
        self.animation.stop()
        self.effect.setOpacity(1.0)
        self.update_style(False)
        self.update_timer()

    def hide_timer(self):
        self.animation.stop()
        self.effect.setOpacity(1.0)
        self.hide()


def main_window_rect(hwnd):
    try:
        import ctypes
        from PySide6.QtCore import QRect
        class RECT_STRUCT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
        r = RECT_STRUCT()
        if not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r)):
            return None
        if r.right <= r.left or r.bottom <= r.top:
            return None
        return QRect(r.left, r.top, r.right - r.left, r.bottom - r.top)
    except Exception:
        return None


def aligned_overlay_watch(original_watch):
    def watch(self):
        target_hwnd, target_pid = self.target_info()
        app_main = __import__("main")
        f_hwnd, f_pid = app_main.foreground()
        if self.overlay_hwnd and f_hwnd == self.overlay_hwnd:
            return
        if target_hwnd and f_pid == target_pid:
            rect = main_window_rect(target_hwnd)
            if rect:
                screen = QApplication.screenAt(rect.center()) or QApplication.primaryScreen()
                self.setGeometry(screen.geometry())
            if not self.isVisible():
                self.show()
            app_main.make_topmost(self.overlay_hwnd or int(self.winId()))
        elif self.isVisible():
            self.hide()
    return watch


def install(main):
    original_load_settings = main.load_settings

    def load_settings_with_timer():
        settings = original_load_settings()
        timer_settings(settings)
        return settings

    main.load_settings = load_settings_with_timer
    main.Overlay.watch = aligned_overlay_watch(main.Overlay.watch)

    original_toggle = main.MainWindow.toggle_session
    original_stop = main.MainWindow.stop_session
    original_trigger = main.MainWindow.trigger_question
    original_answer = main.MainWindow.answer_question

    def toggle(self):
        original_toggle(self)
        if not self.session:
            if hasattr(self, "study_timer_overlay"):
                self.study_timer_overlay.hide_timer()
        else:
            self.study_timer_overlay.update_timer()

    def stop(self, message):
        if hasattr(self, "study_timer_overlay"):
            self.study_timer_overlay.hide_timer()
        original_stop(self, message)

    def trigger(self):
        self.study_timer_overlay.hide_timer()
        original_trigger(self)

    def answer(self, value, elapsed, wrong_before):
        result = original_answer(self, value, elapsed, wrong_before)
        if result and hasattr(self, "study_timer_overlay"):
            self.study_timer_overlay.reset_after_question()
        return result

    main.MainWindow.toggle_session = toggle
    main.MainWindow.stop_session = stop
    main.MainWindow.trigger_question = trigger
    main.MainWindow.answer_question = answer

    window = main.MainWindow()
    window.study_timer_overlay = TimerOverlay(window)

    def save_timer_settings():
        main.save_settings(window.settings)
        window.study_timer_overlay.update_style(False)
        window.study_timer_overlay.update_timer()

    def open_timer_settings():
        TimerSettingsDialog(window.settings, save_timer_settings, window).exec()

    button = QPushButton("⏱ Timer Settings")
    button.clicked.connect(open_timer_settings)
    central = window.centralWidget()
    if central and central.layout() and central.layout().count() > 0:
        session_page = central.widget(0)
        if session_page and session_page.layout():
            session_page.layout().addWidget(button)

    return window
