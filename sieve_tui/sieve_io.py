"""Sieve script <-> in-memory rule list.

Read path: use sievelib's Parser (mature, handles RFC 5228 well) to walk an
existing script's AST and extract rules. Write path: emit sieve text directly
from our Rule dataclasses — small, predictable, no dependence on sievelib's
factory tuple-shape quirks.

Rule model is intentionally narrow for v1:
    - 1+ conditions (any|all)
    - 1 action

That covers ~95% of personal spam-filter use cases. Multi-action and nested
rules can come later.

Canonical write order: rules are grouped by primary condition kind first,
then alphabetized by the rule's name within each group. The on-disk file
reads in canonical order regardless of how rules were added in the UI.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


# Predicates: (label, sieve emitter callable, requires-extension)
# Each emitter receives the value and returns the sieve test string.
PREDICATE_KINDS = [
    ("From (sender address)", "from"),
    ("From domain", "from_domain"),
    ("To (recipient)", "to"),
    ("Subject contains", "subject_contains"),
    ("Subject is", "subject_is"),
    ("List-Id contains", "listid_contains"),
    ("Any header contains", "header_contains"),
    ("Body contains", "body_contains"),
]
PREDICATE_KEYS = {key: label for label, key in PREDICATE_KINDS}

ACTION_KINDS = [
    ("Move to folder", "fileinto"),
    ("Mark as read", "markread"),
    ("Delete (discard)", "discard"),
    ("Redirect to address", "redirect"),
    ("Keep (do nothing)", "keep"),
]
ACTION_KEYS = {key: label for label, key in ACTION_KINDS}


@dataclass
class Condition:
    kind: str           # one of PREDICATE_KINDS keys
    value: str = ""     # the user input (sender address, domain, substring, etc.)
    extra: str = ""     # for "header contains": the header field name

    def to_sieve(self) -> str:
        v = _q(self.value)
        if self.kind == "from":
            return f'address :is "From" {v}'
        if self.kind == "from_domain":
            return f'address :contains "From" {v}'
        if self.kind == "to":
            return f'address :is "To" {v}'
        if self.kind == "subject_contains":
            return f'header :contains "Subject" {v}'
        if self.kind == "subject_is":
            return f'header :is "Subject" {v}'
        if self.kind == "listid_contains":
            return f'header :contains "List-Id" {v}'
        if self.kind == "header_contains":
            field = _q(self.extra or "X-Header")
            return f'header :contains {field} {v}'
        if self.kind == "body_contains":
            return f'body :contains {v}'
        return f'# unknown condition: {self.kind}'


@dataclass
class Action:
    kind: str           # one of ACTION_KINDS keys
    arg: str = ""       # folder name for fileinto, address for redirect

    def to_sieve(self) -> str:
        if self.kind == "fileinto":
            return f'fileinto {_q(self.arg)};'
        if self.kind == "markread":
            return f'setflag "\\\\Seen";'
        if self.kind == "discard":
            return "discard;"
        if self.kind == "redirect":
            return f'redirect {_q(self.arg)};'
        if self.kind == "keep":
            return "keep;"
        return f'# unknown action: {self.kind}'

    def required_extensions(self) -> list[str]:
        if self.kind == "fileinto":
            return ["fileinto"]
        if self.kind == "markread":
            return ["imap4flags"]
        return []


@dataclass
class Rule:
    name: str
    match: Literal["any", "all"] = "any"
    conditions: list[Condition] = field(default_factory=list)
    action: Action = field(default_factory=lambda: Action(kind="keep"))

    @property
    def primary_kind(self) -> str:
        """Sort key for grouping in canonical output."""
        return self.conditions[0].kind if self.conditions else "zzz"


def _q(s: str) -> str:
    """Sieve-quote a string value."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def emit(rules: list[Rule]) -> str:
    """Build a sieve script string from a list of rules, in canonical order."""
    # Group + sort: by primary condition kind, then by rule name.
    sorted_rules = sorted(rules, key=lambda r: (r.primary_kind, r.name.lower()))

    extensions: set[str] = set()
    for r in sorted_rules:
        extensions.update(r.action.required_extensions())

    lines = []
    if extensions:
        ext_list = ", ".join(f'"{e}"' for e in sorted(extensions))
        lines.append(f"require [{ext_list}];")
        lines.append("")

    for r in sorted_rules:
        lines.append(f"# Rule: {r.name}")
        if len(r.conditions) == 1:
            test = r.conditions[0].to_sieve()
            lines.append(f"if {test} {{")
        else:
            joiner = "anyof" if r.match == "any" else "allof"
            tests = ", ".join(c.to_sieve() for c in r.conditions)
            lines.append(f"if {joiner} ({tests}) {{")
        lines.append(f"    {r.action.to_sieve()}")
        lines.append("}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def parse(text: str) -> list[Rule]:
    """Parse an existing sieve script into Rules. Falls back to a single
    'imported' rule whose action is a no-op if the parse can't decompose
    into our v1 rule model."""
    try:
        from sievelib.parser import Parser
    except ImportError:
        return []

    p = Parser()
    if not p.parse(text):
        return []

    rules: list[Rule] = []
    for cmd in p.result:
        if cmd.name != "if":
            continue
        rule = _command_to_rule(cmd, len(rules) + 1)
        if rule is not None:
            rules.append(rule)
    return rules


def _command_to_rule(cmd, idx: int) -> Rule | None:
    """Best-effort: convert a sievelib 'if' command into our Rule model.
    On unfamiliar shapes, returns a Rule with a placeholder condition so
    the user can see it in the tree and decide what to do."""
    name = f"imported_{idx}"
    # cmd.arguments['test'] is the test expression (single or any/allof block)
    test = cmd.arguments.get("test")
    conds: list[Condition] = []
    match: Literal["any", "all"] = "any"

    if test is None:
        return None

    test_name = getattr(test, "name", "") or ""
    if test_name in ("anyof", "allof"):
        match = "any" if test_name == "anyof" else "all"
        for sub in test.arguments.get("tests", []):
            conds.append(_test_to_condition(sub))
    else:
        conds.append(_test_to_condition(test))

    # Take first action only (v1 limitation).
    action = Action(kind="keep")
    for child in cmd.children:
        action = _command_to_action(child)
        break

    return Rule(name=name, match=match, conditions=conds, action=action)


def _test_to_condition(test) -> Condition:
    nm = getattr(test, "name", "") or "unknown"
    args = getattr(test, "arguments", {}) or {}
    if nm == "address":
        match_type = args.get("match-type", ":is")
        headers = args.get("header-list", '""').strip('"')
        keys = args.get("key-list", '""').strip('"')
        if headers.lower() == "from" and match_type == ":is":
            return Condition(kind="from", value=keys)
        if headers.lower() == "from" and match_type == ":contains":
            return Condition(kind="from_domain", value=keys)
        if headers.lower() == "to":
            return Condition(kind="to", value=keys)
        return Condition(kind="header_contains", value=keys, extra=headers)
    if nm == "header":
        headers = args.get("header-list", '""').strip('"')
        keys = args.get("key-list", '""').strip('"')
        match_type = args.get("match-type", ":contains")
        if headers.lower() == "subject":
            return Condition(kind="subject_contains" if match_type == ":contains"
                             else "subject_is", value=keys)
        if headers.lower() == "list-id":
            return Condition(kind="listid_contains", value=keys)
        return Condition(kind="header_contains", value=keys, extra=headers)
    if nm == "body":
        keys = args.get("key-list", '""').strip('"')
        return Condition(kind="body_contains", value=keys)
    return Condition(kind="header_contains", value=f"<unparsed: {nm}>", extra="?")


def _command_to_action(cmd) -> Action:
    nm = getattr(cmd, "name", "")
    args = getattr(cmd, "arguments", {}) or {}
    if nm == "fileinto":
        folder = args.get("mailbox", '""').strip('"')
        return Action(kind="fileinto", arg=folder)
    if nm == "discard":
        return Action(kind="discard")
    if nm == "redirect":
        addr = args.get("address", '""').strip('"')
        return Action(kind="redirect", arg=addr)
    if nm == "setflag":
        return Action(kind="markread")
    if nm == "keep":
        return Action(kind="keep")
    return Action(kind="keep")
