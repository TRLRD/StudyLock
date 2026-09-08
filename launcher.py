"""Production launcher for the StudyLock desktop build.

The existing main.py remains the application engine. This launcher installs the
new presentation layer before creating MainWindow, so the engine and its tests
remain intact while the packaged EXE gets the new UI.
"""

import main as engine
from ui_overhaul import install_ui


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


if __name__ == "__main__":
    engine.main()
