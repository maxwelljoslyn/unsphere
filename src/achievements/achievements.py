from __future__ import annotations

from typing import Callable, Dict, List, Optional

import attr

registry: Dict[str, AchievementDef] = {}


@attr.s(auto_attribs=True)
class AchievementDef:
    key: str
    name: str
    description: str
    threshold: Callable[..., bool]
    category: Optional[List[str]] = None
    _registry: Optional[Dict[str, AchievementDef]] = attr.field(
        default=None, repr=False, eq=False, hash=False
    )

    def __attrs_post_init__(self) -> None:
        reg = self._registry if self._registry is not None else registry
        if self.key in reg:
            raise ValueError(f"{self.key!r} is already registered")
        reg[self.key] = self
