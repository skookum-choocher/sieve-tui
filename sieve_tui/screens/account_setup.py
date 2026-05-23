"""AccountSetupScreen — host/port/username + scaffolded password-cmd input."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static

from ..config import load, save
from ..widgets.cmd_input import CmdInput


class AccountSetupScreen(Screen[bool]):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "save", "Save"),
    ]

    def compose(self) -> ComposeResult:
        cfg = load()
        a = cfg.account

        yield Header()
        with Vertical():
            yield Static("ManageSieve account", classes="title")
            yield Static(
                "Connection details for `sieveman`. Password is a command "
                "that prints the password — never the password itself.",
                classes="hint",
            )

            with Horizontal(classes="field-row"):
                yield Label("Host")
                yield Input(value=a.host, placeholder="imap.example.com",
                            id="in-host")
            with Horizontal(classes="field-row"):
                yield Label("Port")
                yield Input(value=str(a.port), placeholder="4190", id="in-port")
            with Horizontal(classes="field-row"):
                yield Label("Username")
                yield Input(value=a.username, placeholder="user@example.com",
                            id="in-user")
            with Horizontal(classes="field-row"):
                yield Label("Password (cmd)")
                yield CmdInput(value=a.password_cmd,
                               placeholder="rbw get example", id="in-pw")

            with Horizontal(id="rule-actions"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self.action_save()
        elif event.button.id == "btn-cancel":
            self.action_cancel()

    def action_save(self) -> None:
        cfg = load()
        cfg.account.host = self.query_one("#in-host", Input).value.strip()
        try:
            cfg.account.port = int(self.query_one("#in-port", Input).value or "4190")
        except ValueError:
            self.notify("Port must be a number.", severity="error")
            return
        cfg.account.username = self.query_one("#in-user", Input).value.strip()
        cfg.account.password_cmd = self.query_one("#in-pw", CmdInput).wrapped

        missing = [n for n, v in [
            ("host", cfg.account.host),
            ("username", cfg.account.username),
            ("password command", cfg.account.password_cmd),
        ] if not v]
        if missing:
            self.notify(f"Missing: {', '.join(missing)}", severity="error")
            return

        save(cfg)
        self.notify("Account saved.", severity="information")
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
