"""Production launcher for the StudyLock desktop build.

The existing main.py remains the application engine. This launcher installs the
presentation layer before creating MainWindow, so the packaged EXE gets the UI
without changing the engine's behavior.
"""

import types

import main as engine
import ui_aura_plus as ui_overhaul
from ui_aura_plus import install_ui

ui_overhaul.self = engine.MainWindow
ui_overhaul.APP_NAME = engine.APP_NAME

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


def _replace_closure_cell(function, predicate, replacement):
    closure = function.__closure__
    if not closure:
        return function
    cells = list(closure)
    for index, cell in enumerate(closure):
        try:
            value = cell.cell_contents
        except ValueError:
            continue
        if predicate(value):
            cells[index] = (lambda value: (lambda: value))(replacement).__closure__[0]
            return types.FunctionType(
                function.__code__,
                function.__globals__,
                function.__name__,
                function.__defaults__,
                tuple(cells),
            )
    return function


_original_build_ui = engine.MainWindow.build_ui


def _bind_installer_method(method_name):
    """Bind an installed zero-argument presentation function to the window."""
    original = _original_build_ui if method_name == "build_ui" else getattr(engine.MainWindow, method_name)

    def bound(self, *args, **kwargs):
        # ui_overhaul's installer functions intentionally use their module-level
        # `self`. Set it to the real instance, then call the function unchanged.
        ui_overhaul.self = self
        return original(*args, **kwargs)

    bound.__name__ = getattr(original, "__name__", method_name)
    bound.__doc__ = getattr(original, "__doc__", None)
    return bound


engine.MainWindow.build_ui = _bind_installer_method("build_ui")

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


if __name__ == "__main__":
    engine.main()
