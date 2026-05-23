"""RuleTreeView — Tree widget showing rules grouped by their primary condition kind.

Each top-level node is a condition-kind group (e.g. "From sender", "List-Id
contains"). Children are rule names. Selecting a rule leaf surfaces its index
via the `rule-selected` message so the editor screen can open the form.
"""

from textual.message import Message
from textual.widgets import Tree

from ..sieve_io import Rule, PREDICATE_KEYS


class RuleTreeView(Tree[int]):
    """Tree of rules. Data on each leaf node is the rule's index in the parent list."""

    class RuleSelected(Message):
        def __init__(self, index: int) -> None:
            super().__init__()
            self.index = index

    def __init__(self, **kwargs) -> None:
        super().__init__("Rules", **kwargs)
        self.show_root = True
        self.guide_depth = 3

    def load_rules(self, rules: list[Rule]) -> None:
        self.clear()
        # Bucket by primary condition kind.
        buckets: dict[str, list[tuple[int, Rule]]] = {}
        for i, r in enumerate(rules):
            buckets.setdefault(r.primary_kind, []).append((i, r))

        # Sort buckets by their friendly label, rules within bucket by name.
        for kind in sorted(buckets, key=lambda k: PREDICATE_KEYS.get(k, k)):
            label = PREDICATE_KEYS.get(kind, kind)
            group_node = self.root.add(f"[b]{label}[/b]  ({len(buckets[kind])})",
                                       expand=True)
            for idx, rule in sorted(buckets[kind], key=lambda t: t[1].name.lower()):
                cond_summary = _summary(rule)
                rule_node = group_node.add(
                    f"{rule.name}  ─  {cond_summary}",
                    data=idx, expand=False, allow_expand=False,
                )
        self.root.expand()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if event.node.data is not None:
            self.post_message(self.RuleSelected(event.node.data))


def _summary(rule: Rule) -> str:
    """One-line preview of a rule's body for the tree leaf label."""
    if not rule.conditions:
        return f"(no condition) → {rule.action.kind}"
    c = rule.conditions[0]
    cond_str = f'{PREDICATE_KEYS.get(c.kind, c.kind)}: "{c.value}"'
    if len(rule.conditions) > 1:
        cond_str += f" + {len(rule.conditions) - 1} more"
    act = rule.action
    if act.kind in ("fileinto", "redirect") and act.arg:
        act_str = f"{act.kind} → {act.arg}"
    else:
        act_str = act.kind
    return f"{cond_str}  →  {act_str}"
