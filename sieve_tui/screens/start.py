"""StartScreen — first thing the user sees. Three paths: New, Existing, Local-only."""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static


class StartScreen(Screen):
    BINDINGS = [
        ("n", "new", "New"),
        ("e", "existing", "Existing"),
        ("l", "local", "Local-only"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("Sieve TUI", classes="title")
            yield Static(
                "Build sieve mail filters without remembering the syntax.\n"
                "Pick a starting point:",
                classes="hint",
            )
            with Container(id="start-buttons"):
                yield Button("New script (push to server)", id="btn-new",
                             variant="primary")
                yield Button("Edit existing script (download from server)",
                             id="btn-existing")
                yield Button("Local-only (save sieve to a file, no server)",
                             id="btn-local")
                yield Button("Quit", id="btn-quit")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-new":
            self.action_new()
        elif event.button.id == "btn-existing":
            self.action_existing()
        elif event.button.id == "btn-local":
            self.action_local()
        elif event.button.id == "btn-quit":
            self.action_quit()

    def action_new(self) -> None:
        self.app.push_screen("account_setup", self._after_account_new)

    def action_existing(self) -> None:
        self.app.push_screen("account_setup", self._after_account_existing)

    def action_local(self) -> None:
        # Skip account setup entirely. Editor opens with an empty script.
        self.app.start_local_only()

    def action_quit(self) -> None:
        self.app.exit()

    def _after_account_new(self, saved: bool) -> None:
        if saved:
            self.app.start_new_script()

    def _after_account_existing(self, saved: bool) -> None:
        if saved:
            self.app.start_existing()
