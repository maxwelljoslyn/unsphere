`entitled` is only ever called from `grant_gems`, and tests go through `grant_gems` (never call `entitled` directly). So the blast radius is tiny: the three lambdas in `definitions.py`, the helper signatures, and one line in `grant_gems`. That makes a clean fix easy.

## The taste question, stated precisely

The thing that turns into a rat's nest isn't *sharing* — it's sharing the **wrong thing**. There are two kinds of reuse you could do:

1. **Share rule outputs** — e.g. `cardio_duration` peeks at what `cardio_distance` computed. This is the rat's nest: rules become order-dependent and entangled, and you lose the "each gem is a self-contained `entitled`" property you like.
2. **Share raw inputs** — both rules independently say "I need this user's confirmed cardio exercises," and that *dataset* is loaded once. Rules stay ignorant of each other.

(2) is the tasteful one, and it keeps your mental model intact: a rule is still a pure function from the user's data to a gem count. It just pulls that data from a shared, lazily-loaded cache instead of issuing its own query.

## The shape: a request-scoped lazy context

A small object whose only job is to memoize the *raw queryset materializations*. `cached_property` makes it lazy (a rule that doesn't need cardio never loads it) and load-once (two rules that do, share it):

```python
# gems/context.py
from functools import cached_property


class GemContext:
    """Request-scoped cache of the raw data gem rules read.

    Holds *inputs* (materialized querysets), never rule *outputs*, so rules stay
    independent: two rules that both need the user's cardio exercises trigger one
    DB load and one Python list, but neither knows the other exists. Adding a rule
    that reuses an existing dataset is free; one that needs a new dataset adds a
    new cached_property here.
    """

    def __init__(self, user):
        self.user = user

    @cached_property
    def cardio_exercises(self):
        from workouts.models import CardioExercise

        return list(
            CardioExercise.objects.filter(
                workout__user=self.user, workout__confirmed_at__isnull=False
            )
        )

    @cached_property
    def confirmed_workouts(self):
        from workouts.models import Workout

        return list(
            Workout.objects.filter(user=self.user, confirmed_at__isnull=False)
        )
```

The helpers stop querying and start taking the rows they operate on — which also makes them trivially unit-testable with a plain list:

```python
def _total_cardio_miles(exercises) -> float:
    total_mi = 0.0
    for ex in exercises:
        if ex.distance is None:
            continue
        try:
            total_mi += float(ex.distance.to("mile").magnitude)
        except Exception:
            continue
    return total_mi
```

`entitled` gains a `ctx` parameter (your `Callable[..., int]` annotation already covers it):

```python
GemRuleDef(
    key="cardio_distance",
    ...,
    entitled=lambda user, ctx: int(math.floor(_total_cardio_miles(ctx.cardio_exercises))),
)
GemRuleDef(
    key="cardio_duration",
    ...,
    entitled=lambda user, ctx: int(_total_cardio_minutes(ctx.cardio_exercises) // 10),
)
GemRuleDef(
    key="active_days",
    ...,
    entitled=lambda user, ctx: _active_days(ctx.confirmed_workouts),
)
```

And `grant_gems` builds one context per call:

```python
ctx = GemContext(user)
for key, rule in reg.items():
    delta = rule.entitled(user, ctx) - awarded.get(key, 0)
    ...
```

## Why this stays clean as you grow

- The context only ever grows by *adding lazy properties for new data sources* — it never accumulates cross-rule logic.
- A rule that needs nothing new costs nothing new. A rule needing a new dataset adds exactly one `cached_property`, and every future rule that wants that dataset gets the dedup for free.
- Rules remain order-independent and individually testable — you can still reason about one `entitled` in isolation, which is the property you wanted to protect.
- It naturally extends to achievements later (a shared `Context`) if their threshold queries ever stop being cheap — but I'd leave achievements alone for now since they're `.count()`/`.exists()`, not scans.

The cost is one new parameter on `entitled`. That's the whole price, and it buys you 2 cardio scans → 1, plus a much nicer test surface.

Want me to implement it? It's `definitions.py`, `middleware.py`, a new `context.py`, and a quick test run.
