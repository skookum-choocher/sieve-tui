"""CmdInput — scaffolded command-substitution input.

Renders as:
    $(  [____________________________________]  )

The `$(` and `)` are immutable Static labels. The user types only the inner
command. The wrapped value (`$(cmd)`) is what consumers read. This makes the
shape of the expected input visually explicit — no ambiguity about whether
the wrapper is already present, no chance of double-wrapping.

Reusable: drop this into any TUI that needs a "command that returns a value"
input (passwords, tokens, dynamic config values).
"""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Input, Static


class CmdInput(Horizontal):
    DEFAULT_CSS = ""

    def __init__(self, value: str = "", placeholder: str = "rbw get google",
                 id: str | None = None) -> None:
        super().__init__(id=id)
        self._initial = self._unwrap(value)
        self._placeholder = placeholder

    @staticmethod
    def _unwrap(value: str) -> str:
        v = value.strip()
        if v.startswith("$(") and v.endswith(")"):
            return v[2:-1]
        return v

    def compose(self) -> ComposeResult:
        yield Static("$(", classes="cmdinput-paren")
        yield Input(value=self._initial, placeholder=self._placeholder,
                    id="cmd-inner")
        yield Static(")", classes="cmdinput-paren")

    @property
    def inner(self) -> str:
        return self.query_one("#cmd-inner", Input).value.strip()

    @property
    def wrapped(self) -> str:
        """The value consumers want: `$(<command>)` or empty string."""
        v = self.inner
        return f"$({v})" if v else ""

    def set_value(self, value: str) -> None:
        self.query_one("#cmd-inner", Input).value = self._unwrap(value)
