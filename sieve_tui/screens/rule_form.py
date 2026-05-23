"""RuleFormScreen — modal for editing a single rule (one condition for v1)."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

from ..sieve_io import (
    Rule, Condition, Action, PREDICATE_KINDS, ACTION_KINDS,
)


class RuleFormScreen(ModalScreen[Rule | None]):
    """Returns the edited/new Rule on save, or None on cancel."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "save", "Save"),
    ]

    def __init__(self, rule: Rule | None = None) -> None:
        super().__init__()
        self._editing = rule
        if rule is None:
            self._initial = Rule(
                name="",
                match="any",
                conditions=[Condition(kind="from", value="")],
                action=Action(kind="fileinto", arg=""),
            )
        else:
            self._initial = rule

    def compose(self) -> ComposeResult:
        r = self._initial
        c = r.conditions[0] if r.conditions else Condition(kind="from")
        a = r.action

        with VerticalScroll(id="rule-form"):
            yield Static(
                "Edit rule" if self._editing else "New rule",
                classes="title",
            )
            with Horizontal(classes="field-row"):
                yield Label("Rule name")
                yield Input(value=r.name, placeholder="e.g. github-notifications",
                            id="in-name")

            with Horizontal(classes="field-row"):
                yield Label("Condition")
                yield Select(
                    [(label, key) for label, key in PREDICATE_KINDS],
                    value=c.kind,
                    allow_blank=False,
                    id="in-cond-kind",
                )

            with Horizontal(classes="field-row"):
                yield Label("Header name")
                yield Input(value=c.extra, placeholder="X-GitHub-Reason",
                            id="in-cond-extra")

            with Horizontal(classes="field-row"):
                yield Label("Match value")
                yield Input(value=c.value,
                            placeholder="substring / address / domain",
                            id="in-cond-value")

            with Horizontal(classes="field-row"):
                yield Label("Action")
                yield Select(
                    [(label, key) for label, key in ACTION_KINDS],
                    value=a.kind,
                    allow_blank=False,
                    id="in-action-kind",
                )

            with Horizontal(classes="field-row"):
                yield Label("Action arg")
                yield Input(value=a.arg,
                            placeholder="folder name / redirect address",
                            id="in-action-arg")

            with Horizontal(id="rule-actions"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")

    def on_mount(self) -> None:
        self._toggle_extra_visibility(self._initial.conditions[0].kind
                                      if self._initial.conditions else "from")
        self._toggle_arg_visibility(self._initial.action.kind)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "in-cond-kind":
            self._toggle_extra_visibility(event.value)
        elif event.select.id == "in-action-kind":
            self._toggle_arg_visibility(event.value)

    def _toggle_extra_visibility(self, cond_kind: str) -> None:
        extra_row = self.query_one("#in-cond-extra", Input).parent
        extra_row.display = cond_kind == "header_contains"

    def _toggle_arg_visibility(self, action_kind: str) -> None:
        arg_row = self.query_one("#in-action-arg", Input).parent
        arg_row.display = action_kind in ("fileinto", "redirect")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self.action_save()
        elif event.button.id == "btn-cancel":
            self.action_cancel()

    def action_save(self) -> None:
        name = self.query_one("#in-name", Input).value.strip()
        cond_kind = self.query_one("#in-cond-kind", Select).value
        cond_extra = self.query_one("#in-cond-extra", Input).value.strip()
        cond_value = self.query_one("#in-cond-value", Input).value.strip()
        action_kind = self.query_one("#in-action-kind", Select).value
        action_arg = self.query_one("#in-action-arg", Input).value.strip()

        if not name:
            self.notify("Rule name is required.", severity="error")
            return
        if not cond_value and cond_kind != "keep":
            self.notify("Condition value is required.", severity="error")
            return
        if action_kind in ("fileinto", "redirect") and not action_arg:
            self.notify(f"{action_kind} requires an argument.", severity="error")
            return

        rule = Rule(
            name=name,
            match=self._initial.match,
            conditions=[Condition(kind=cond_kind, value=cond_value,
                                  extra=cond_extra)],
            action=Action(kind=action_kind, arg=action_arg),
        )
        self.dismiss(rule)

    def action_cancel(self) -> None:
        self.dismiss(None)
