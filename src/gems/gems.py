from __future__ import annotations

from typing import Callable, Dict, Optional

import attr

registry: Dict[str, GemRuleDef] = {}


@attr.s(auto_attribs=True)
class GemRuleDef:
    """A repeatable gem source.

    Unlike an achievement (a one-time boolean), a gem rule grants a *count* that
    grows with activity. `entitled(user)` returns the cumulative number of gems
    the user should have earned from this rule so far; the grant step credits the
    difference between that and what the rule has already awarded. Framing every
    rule as a cumulative high-water mark — rather than a per-event trigger — keeps
    crediting idempotent and retroactive, exactly like the achievement checks.

    `category` is a coarse grouping ("cardio", "consistency", ...) stamped onto
    each credit so balances can later be sliced per category (e.g. a future
    "earn 50 cardio gems" achievement).
    """

    key: str
    name: str
    category: str
    entitled: Callable[..., int]
    _registry: Optional[Dict[str, GemRuleDef]] = attr.field(
        default=None, repr=False, eq=False, hash=False
    )

    def __attrs_post_init__(self) -> None:
        reg = self._registry if self._registry is not None else registry
        if self.key in reg:
            raise ValueError(f"{self.key!r} is already registered")
        reg[self.key] = self
