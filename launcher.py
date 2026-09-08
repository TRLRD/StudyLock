"""Production launcher for the StudyLock desktop build.

The existing main.py remains the application engine. This launcher installs the
new presentation layer before creating MainWindow, so the engine and its tests
remain intact while the packaged EXE gets the new UI.
"""

import main as engine
import ui_overhaul
from ui_overhaul import install_ui

# ui_overhaul.install_ui currently contains a small installer-scope reference
# to ``self``. During installation there is no instance yet, so provide the
# intended class context here. The instance-level navigation method is restored
# immediately after installation below.
ui_overhaul.self = engine.MainWindow

install_ui(
    engine.MainWindow,
    engine.GamePicker,
    engine.TimerSettings,
    engine.PerformanceDialog,
    engine.available_curricula,
    engine.subjects_for,
    engine.stages_for,
    engine.papers_for,
    engine.filter_questions,
    engine.save_settings,
)


def _go_page(self, widget, direction=1):
    """Navigate using the current MainWindow instance's animated stack."""
    return self.stack.go(widget, direction)


# The installer-scope lambda is not instance-bound correctly when placed on the
# class. Replace it with a normal instance method before MainWindow is created.
engine.MainWindow.go_page = _go_page


if __name__ == "__main__":
    engine.main()
