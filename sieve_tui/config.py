"""Config load/save for sieve-tui.

Schema (single account v1):
    [account]
    host = "imap.example.com"
    port = 4190
    username = "user@example.com"
    password_cmd = "rbw get example"

    [output]
    local_dir = "~/.local/share/sieve-tui/scripts"

Reads use stdlib tomllib. Writes hand-emit our known schema — keeps the
project zero-deps for TOML, no fight with pip on externally-managed Python.
"""

import tomllib
from dataclasses import dataclass, field, asdict
from pathlib import Path


CONFIG_DIR = Path.home() / ".config" / "sieve-tui"
CONFIG_FILE = CONFIG_DIR / "config.toml"
DEFAULT_LOCAL_DIR = Path.home() / ".local" / "share" / "sieve-tui" / "scripts"


@dataclass
class Account:
    host: str = ""
    port: int = 4190
    username: str = ""
    # The literal command string (already wrapped, e.g. "$(rbw get google)").
    # Resolved at use-time by passing through the shell.
    password_cmd: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.host and self.username and self.password_cmd)


@dataclass
class Output:
    local_dir: str = str(DEFAULT_LOCAL_DIR)


@dataclass
class Config:
    account: Account = field(default_factory=Account)
    output: Output = field(default_factory=Output)

    @property
    def local_dir_path(self) -> Path:
        return Path(self.output.local_dir).expanduser()


def load() -> Config:
    if not CONFIG_FILE.exists():
        return Config()
    with CONFIG_FILE.open("rb") as f:
        data = tomllib.load(f)
    acct = Account(**data.get("account", {}))
    out = Output(**data.get("output", {}))
    return Config(account=acct, output=out)


def _escape(s: str) -> str:
    """Minimal TOML string escape for our values (host, username, cmd, path)."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def save(cfg: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = []
    if cfg.account.configured or cfg.account.host or cfg.account.username:
        lines.append("[account]")
        lines.append(f'host = "{_escape(cfg.account.host)}"')
        lines.append(f"port = {cfg.account.port}")
        lines.append(f'username = "{_escape(cfg.account.username)}"')
        lines.append(f'password_cmd = "{_escape(cfg.account.password_cmd)}"')
        lines.append("")
    lines.append("[output]")
    lines.append(f'local_dir = "{_escape(cfg.output.local_dir)}"')
    CONFIG_FILE.write_text("\n".join(lines) + "\n")
