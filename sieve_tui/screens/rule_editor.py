"""RuleEditorScreen — the main editing surface.

Owns the in-memory rule list. Renders it via RuleTreeView. Add/Edit/Delete
buttons mutate the list and re-render. Save opens a Save dialog (local file
or push to server, depending on mode).
"""

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from .. import sieveman, sieve_io
from ..config import load
from ..widgets.rule_tree import RuleTreeView
from .rule_form import RuleFormScreen


class RuleEditorScreen(Screen):
    BINDINGS = [
        ("a", "add", "Add"),
        ("e", "edit", "Edit"),
        ("d", "delete", "Delete"),
        ("s", "save", "Save"),
        ("escape", "back", "Back"),
        # vim navigation — drives the Tree cursor directly so j/k beat the
        # app-level focus-next/prev bindings when the editor is the active screen.
        Binding("j", "tree_down", "Down", show=False),
        Binding("k", "tree_up", "Up", show=False),
        Binding("h", "tree_collapse", "Collapse", show=False),
        Binding("l", "tree_expand", "Expand/Select", show=False),
    ]

    def __init__(self, script_name: str, rules: list[sieve_io.Rule],
                 mode: str) -> None:
        super().__init__()
        self.script_name = script_name or "untitled"
        self.rules: list[sieve_io.Rule] = rules
        # mode: "local" (save to file only) | "remote" (push via sieveman)
        self.mode = mode
        self._selected_idx: int | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static(f"Editing: {self.script_name}  [{self.mode}]",
                         id="script-title", classes="title")
            yield Static(self._mode_hint(), classes="hint")
            yield RuleTreeView(id="rule-tree")
            with Horizontal(id="rule-actions"):
                yield Button("Add (a)", id="btn-add", variant="primary")
                yield Button("Edit (e)", id="btn-edit")
                yield Button("Delete (d)", id="btn-delete")
                yield Button("Save (s)", id="btn-save")
                yield Button("Back (esc)", id="btn-back")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(RuleTreeView).load_rules(self.rules)

    def _mode_hint(self) -> str:
        if self.mode == "local":
            return ("Local-only mode. Save writes the sieve script to "
                    f"{load().local_dir_path}. No server push.")
        return ("Remote mode. Save writes locally AND pushes to the server "
                "via sieveman. The active script is the one applied to inbound mail.")

    def on_rule_tree_view_rule_selected(self,
                                        event: RuleTreeView.RuleSelected) -> None:
        self._selected_idx = event.index

    def on_button_pressed(self, event: Button.Pressed) -> None:
        getattr(self, f"action_{event.button.id[4:]}")()

    # ── Actions ─────────────────────────────────────────────────────────────

    def action_add(self) -> None:
        def after(rule: sieve_io.Rule | None) -> None:
            if rule is not None:
                self.rules.append(rule)
                self.query_one(RuleTreeView).load_rules(self.rules)
                self.notify(f"Added: {rule.name}")
        self.app.push_screen(RuleFormScreen(), after)

    def action_edit(self) -> None:
        if self._selected_idx is None:
            self.notify("Select a rule first.", severity="warning")
            return
        existing = self.rules[self._selected_idx]
        idx = self._selected_idx

        def after(rule: sieve_io.Rule | None) -> None:
            if rule is not None:
                self.rules[idx] = rule
                self.query_one(RuleTreeView).load_rules(self.rules)
                self.notify(f"Updated: {rule.name}")
        self.app.push_screen(RuleFormScreen(existing), after)

    def action_delete(self) -> None:
        if self._selected_idx is None:
            self.notify("Select a rule first.", severity="warning")
            return
        rule = self.rules.pop(self._selected_idx)
        self._selected_idx = None
        self.query_one(RuleTreeView).load_rules(self.rules)
        self.notify(f"Deleted: {rule.name}")

    def action_save(self) -> None:
        cfg = load()
        text = sieve_io.emit(self.rules)

        # Always save locally.
        cfg.local_dir_path.mkdir(parents=True, exist_ok=True)
        local_path = cfg.local_dir_path / f"{self.script_name}.sieve"
        local_path.write_text(text)
        msg = f"Saved → {local_path}"

        if self.mode == "remote":
            try:
                sieveman.put(cfg.account, self.script_name, text)
                msg += f"\nPushed to {cfg.account.host} as '{self.script_name}'"
            except sieveman.SieveManError as e:
                self.notify(f"Local saved, but push failed: {e}",
                            severity="error", timeout=10)
                return

        self.notify(msg, severity="information", timeout=8)

    def action_back(self) -> None:
        self.app.pop_screen()

    # ── Vim navigation actions (drive the tree cursor directly) ─────────────

    def action_tree_down(self) -> None:
        self.query_one(RuleTreeView).action_cursor_down()

    def action_tree_up(self) -> None:
        self.query_one(RuleTreeView).action_cursor_up()

    def action_tree_expand(self) -> None:
        tree = self.query_one(RuleTreeView)
        node = tree.cursor_node
        if node is None:
            return
        if node.allow_expand and not node.is_expanded:
            node.expand()
        else:
            tree.action_select_cursor()

    def action_tree_collapse(self) -> None:
        tree = self.query_one(RuleTreeView)
        node = tree.cursor_node
        if node is None:
            return
        if node.is_expanded:
            node.collapse()
        elif node.parent is not None and node.parent is not tree.root:
            tree.select_node(node.parent)
