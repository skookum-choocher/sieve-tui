"""ScriptPickerScreen — list remote scripts via `sieveman ls`, pick one to edit."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, ListItem, ListView, Static

from .. import sieveman
from ..config import load


class ScriptPickerScreen(Screen[str | None]):
    BINDINGS = [
        ("escape", "cancel", "Back"),
        ("enter", "pick", "Open"),
        ("n", "new", "New script"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("Remote scripts", classes="title")
            yield Static(
                "Pick a script to edit, or start a new one. Active script "
                "is marked with *.",
                classes="hint",
            )
            yield ListView(id="script-list")
            with Horizontal(id="rule-actions"):
                yield Button("Open", id="btn-pick", variant="primary")
                yield Button("New script", id="btn-new")
                yield Button("Back", id="btn-back")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        cfg = load()
        lv = self.query_one("#script-list", ListView)
        lv.clear()
        try:
            scripts = sieveman.ls(cfg.account)
        except sieveman.SieveManError as e:
            self.notify(f"sieveman failed: {e}", severity="error", timeout=10)
            return
        if not scripts:
            lv.append(ListItem(Static("(no scripts on server — press 'n' to create)")))
            return
        for s in scripts:
            marker = "* " if s.active else "  "
            lv.append(ListItem(Static(f"{marker}{s.name}"), id=f"sc-{s.name}"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-pick":
            self.action_pick()
        elif event.button.id == "btn-new":
            self.action_new()
        elif event.button.id == "btn-back":
            self.action_cancel()

    def action_pick(self) -> None:
        lv = self.query_one("#script-list", ListView)
        item = lv.highlighted_child
        if item is None or not item.id or not item.id.startswith("sc-"):
            self.notify("No script selected.", severity="warning")
            return
        name = item.id[len("sc-"):]
        self.dismiss(name)

    def action_new(self) -> None:
        # Dismiss with empty name to signal "open editor with fresh script".
        self.dismiss("")

    def action_cancel(self) -> None:
        self.dismiss(None)
