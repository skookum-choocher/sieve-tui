"""SieveTUIApp — top-level Textual application + screen routing."""

from pathlib import Path

from textual.app import App
from textual.binding import Binding

from . import sieveman, sieve_io
from .config import load
from .screens.account_setup import AccountSetupScreen
from .screens.rule_editor import RuleEditorScreen
from .screens.script_picker import ScriptPickerScreen
from .screens.start import StartScreen


THEME_PATH = Path(__file__).parent / "theme.tcss"


class SieveTUIApp(App):
    CSS_PATH = str(THEME_PATH)
    SCREENS = {
        "start": StartScreen,
        "account_setup": AccountSetupScreen,
    }
    # vim-style focus navigation across widgets (j/k as Tab/Shift-Tab aliases).
    # Hidden from footer to avoid clutter. Input widgets consume character keys
    # before bindings fire, so typing 'j' in a text field still works as expected.
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        Binding("j", "focus_next", "Down", show=False),
        Binding("k", "focus_previous", "Up", show=False),
    ]

    def on_mount(self) -> None:
        self.push_screen("start")

    # ── Entry points called from StartScreen ────────────────────────────────

    def start_local_only(self) -> None:
        """No server. Open editor with an empty script."""
        self.push_screen(RuleEditorScreen(
            script_name="untitled", rules=[], mode="local",
        ))

    def start_new_script(self) -> None:
        """Account is configured. Open editor with empty script, remote save."""
        self.push_screen(RuleEditorScreen(
            script_name="new_script", rules=[], mode="remote",
        ))

    def start_existing(self) -> None:
        """Account is configured. Pick a remote script, parse, edit."""
        self.push_screen(ScriptPickerScreen(), self._after_pick)

    def _after_pick(self, script_name: str | None) -> None:
        if script_name is None:
            return  # user cancelled
        if script_name == "":
            # User chose "new script" from picker
            self.push_screen(RuleEditorScreen(
                script_name="new_script", rules=[], mode="remote",
            ))
            return
        cfg = load()
        try:
            text = sieveman.get(cfg.account, script_name)
        except sieveman.SieveManError as e:
            self.notify(f"Could not download {script_name}: {e}",
                        severity="error", timeout=10)
            return
        rules = sieve_io.parse(text)
        self.push_screen(RuleEditorScreen(
            script_name=script_name, rules=rules, mode="remote",
        ))
