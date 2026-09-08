"""Production launcher for the StudyLock desktop build.

The existing main.py remains the application engine. This launcher installs the
new presentation layer before creating MainWindow, so the engine and its tests
remain intact while the packaged EXE gets the new UI.
"""

import main as engine
import ui_overhaul
from ui_overhaul import install_ui

# install_ui builds presentation methods as nested functions. Keep the installer
# isolated from the MainWindow instance, then bind those functions explicitly
# after installation so Python supplies the correct instance at runtime.
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


def _bind_installer_method(method_name):
    """Turn an installer-scope function into a real MainWindow method.

    The functions created by install_ui intentionally close over the module-level
    installer context. Before invoking one, point that context at the actual
    MainWindow instance. This also handles methods whose original signature has
    no explicit ``self`` parameter.
    """
    original = getattr(engine.MainWindow, method_name)

    def bound(self, *args, **kwargs):
        ui_overhaul.self = self
        return original(*args, **kwargs)

    bound.__name__ = getattr(original, "__name__", method_name)
    return bound


# build_ui is called by MainWindow.__init__, so it must accept the instance that
# Python supplies for a class method.
engine.MainWindow.build_ui = _bind_installer_method("build_ui")

# These presentation methods are also installed from nested functions. Bind
# them explicitly so callbacks and Qt signals always operate on the right window.
for _name in (
    "refresh_status",
    "refresh_game_label",
    "pick_game",
    "update_dashboard_labels",
    "refresh_history",
    "save_interval",
    "next_onboarding_account",
    "next_onboarding_theme",
    "finish_onboarding",
    "select_theme",
    "account_info",
    "open_quick_settings",
):
    setattr(engine.MainWindow, _name, _bind_installer_method(_name))


def _go_page(self, widget, direction=1):
    """Navigate using the current MainWindow instance's animated stack."""
    return self.stack.go(widget, direction)


engine.MainWindow.go_page = _go_page


if __name__ == "__main__":
    engine.main()
