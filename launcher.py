"""Production launcher for the StudyLock desktop build.

The existing main.py remains the application engine. This launcher installs the
new presentation layer before creating MainWindow, so the engine and its tests
remain intact while the packaged EXE gets the new UI.
"""

import types

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


def _replace_closure_cell(function, predicate, replacement):
    """Return a function with one matching closure cell replaced.

    A few legacy installer helpers are local functions. If one was declared with
    a ``self`` parameter but is called as a local helper, Python reports a
    missing-self TypeError. Rebuilding the function with a corrected closure is
    safer than mutating the original function object or changing the engine.
    """
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


# Current ui_overhaul.py defines make_header(self) but build_ui calls the local
# helper as make_header(). Normalize that helper to a zero-argument closure while
# retaining the existing installer-scope ``self`` behavior.
_original_build_ui = engine.MainWindow.build_ui
for _cell in _original_build_ui.__closure__ or ():
    try:
        _value = _cell.cell_contents
    except ValueError:
        continue
    if getattr(_value, "__name__", None) == "make_header":
        def _make_header_without_argument(_helper):
            def _make_header():
                return _helper(ui_overhaul.self)
            return _make_header
        _fixed = _make_header_without_argument(_value)
        _original_build_ui = _replace_closure_cell(
            _original_build_ui,
            lambda value, target=_value: value is target,
            _fixed,
        )
        break


def _bind_installer_method(method_name):
    """Turn an installer-scope function into a real MainWindow method.

    The functions created by install_ui intentionally use the module-level
    installer context. Before invoking one, point that context at the actual
    MainWindow instance. The wrapper itself owns the Python instance binding, so
    the installer function never receives an unexpected implicit ``self``.
    """
    original = getattr(engine.MainWindow, method_name)
    if method_name == "build_ui":
        original = _original_build_ui

    def bound(self, *args, **kwargs):
        ui_overhaul.self = self
        return original(*args, **kwargs)

    bound.__name__ = getattr(original, "__name__", method_name)
    bound.__doc__ = getattr(original, "__doc__", None)
    return bound


# build_ui is called by MainWindow.__init__, so it must accept the instance that
# Python supplies for a class method.
engine.MainWindow.build_ui = _bind_installer_method("build_ui")

# These presentation methods are also installed from nested functions. Bind
# them explicitly so callbacks and Qt signals always operate on the right window.
for _name in (
    "apply_theme",
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
