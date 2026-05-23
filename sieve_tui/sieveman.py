"""Thin subprocess wrapper around the system `sieveman` CLI.

We don't speak ManageSieve ourselves — sieveman already does it well and is
installed on the box. We just shell out, parse stdout, surface errors as
exceptions, and let the TUI render them as toasts/dialogs.

Password handling: the account's `password_cmd` is a literal $(rbw get ...)
string. We pass it to sieveman via the shell so substitution happens at
invocation time, never persisted in env or argv visible to other users.
"""

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import Account


class SieveManError(RuntimeError):
    pass


@dataclass
class RemoteScript:
    name: str
    active: bool


def _common_args(acct: Account) -> list[str]:
    return [
        "-H", acct.host,
        "-P", str(acct.port),
        "-u", acct.username,
        "-p", acct.password_cmd,
    ]


def _run(acct: Account, *cmd: str, input_text: str | None = None) -> str:
    """Run `sieveman <flags> <cmd...>` via shell so $() in password_cmd expands."""
    full = ["sieveman", *_common_args(acct), *cmd]
    # Build a single shell line; shlex.quote everything EXCEPT the password
    # argument, which we want the shell to interpret for $() substitution.
    parts = []
    for i, arg in enumerate(full):
        if i > 0 and full[i - 1] == "-p":
            parts.append(f'"{arg}"')  # let shell interpret $()
        else:
            parts.append(shlex.quote(arg))
    line = " ".join(parts)
    proc = subprocess.run(
        line, shell=True, input=input_text, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise SieveManError(proc.stderr.strip() or proc.stdout.strip() or
                            f"sieveman exited {proc.returncode}")
    return proc.stdout


def ls(acct: Account) -> list[RemoteScript]:
    """List scripts on the server. Active script is marked with *."""
    out = _run(acct, "ls")
    scripts = []
    for line in out.splitlines():
        s = line.strip()
        if not s:
            continue
        active = s.startswith("*")
        name = s.lstrip("*").strip()
        scripts.append(RemoteScript(name=name, active=active))
    return scripts


def get(acct: Account, name: str) -> str:
    """Download a script by name, return its sieve text."""
    tmp = Path("/tmp") / f"sieve-tui-{name}.sieve"
    _run(acct, "get", name, str(tmp))
    text = tmp.read_text()
    tmp.unlink(missing_ok=True)
    return text


def put(acct: Account, name: str, text: str) -> None:
    """Upload a script by name. Overwrites if it exists."""
    tmp = Path("/tmp") / f"sieve-tui-put-{name}.sieve"
    tmp.write_text(text)
    try:
        _run(acct, "put", name, str(tmp))
    finally:
        tmp.unlink(missing_ok=True)


def activate(acct: Account, name: str) -> None:
    _run(acct, "activate", name)
