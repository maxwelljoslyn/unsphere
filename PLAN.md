# Fitness Tracker — Session Plan

## What this is
Private fitness tracking app for two users (Maxwell + Ryan). Django + HTMX.
"parrot" is a placeholder project name, will be renamed later.

## Architecture decisions (don't relitigate these)

**Exercise catalog in DB** — `Movement` table (name, kind) rather than enums in code.
Kind choices: `cardio` / `strength`. First two movements: rowing, running (cardio).

**Two exercise tables, not one sparse table** — `CardioExercise` and `StrengthExercise`
both inherit from abstract `Exercise`. DB-level constraints enforced per table.
`CardioExercise` has a `CheckConstraint` requiring at least one of distance or duration.
`StrengthExercise` requires sets + reps; weight is optional (bodyweight/PT use case).

**Pint for all unit math** — singleton `u = UnitRegistry()` in `src/parrot/units.py`.
`PintField` (model field) stores quantities as strings in DB.
`PintFormField` (form field, MultiValueField) renders two inputs: [magnitude, unit text].
`PintTimeFormField` renders two number inputs: [minutes, seconds], no unit text entry.
Store American units canonically (miles, lbs). Pint handles conversion at input boundary.

**Achievements** — `AchievementDef` (attrs class) defined in code, registered in a
module-level dict `registry: Dict[str, AchievementDef]`. DB table `Achievement` stores
only earned rows (user, achievement_key, earned_at). No dormant/false rows.
Middleware `AchievementMiddleware` runs `check_achievements(user, reg)` after every
request, stores newly earned keys in `request.session["pending_achievements"]`.
`check_achievements` accepts a registry parameter for test isolation.
`AchievementDef.__init__` auto-registers into the passed registry (default: global).

**No JSON fields** — wherever JSON would be tempting, use multiple FK'd tables instead.

**SQLite** with WAL, busy_timeout=5000, foreign_keys=ON, synchronous=NORMAL,
cache_size=-64000, temp_store=MEMORY, mmap_size=134217728.
Configured via `connection_created` signal in `ParrotConfig.ready()`.

## Key files

| File | Purpose |
|---|---|
| `src/parrot/settings.py` | Django config, SQLite, AUTH_USER_MODEL, login redirects |
| `src/parrot/apps.py` | ParrotConfig — wires SQLite pragmas on connection_created |
| `src/parrot/units.py` | `u = UnitRegistry()` singleton — import from here everywhere |
| `src/parrot/urls.py` | Root URLs: admin, accounts/, workouts app |
| `src/users/models.py` | `User(AbstractUser)` + `email_confirmed` flag |
| `src/users/forms.py` | RegistrationForm, ConfirmedAuthenticationForm (blocks unconfirmed login) |
| `src/users/auth_emails.py` | `send_confirmation_email` (token + Mailgun SMTP), `EmailSendError` |
| `src/users/views.py` | register, register_pending, register_confirm, resend_confirmation |
| `src/users/urls.py` | Auth routes incl. custom LoginView; mounted at `accounts/` before contrib.auth |
| `src/users/admin.py` | Custom UserAdmin exposing `email_confirmed` |
| `src/workouts/models.py` | Movement, Workout, abstract Exercise, CardioExercise, StrengthExercise |
| `src/workouts/fields.py` | PintField (model), PintWidget, PintTimeWidget, PintFormField, PintTimeFormField |
| `src/workouts/forms.py` | WorkoutForm, MovementForm, CardioExerciseForm, StrengthExerciseForm |
| `src/workouts/views.py` | All workout/exercise/movement views (function-based) |
| `src/workouts/urls.py` | Routes for workouts/ and movements/ |
| `src/achievements/achievements.py` | AchievementDef class, global registry dict |
| `src/achievements/models.py` | Achievement (earned rows only) |
| `src/achievements/middleware.py` | check_achievements(), AchievementMiddleware |
| `tests/test_achievements.py` | Registration, duplicate key, checker tests |
| `conftest.py` | achievement_registry fixture (empty dict, for test isolation) |
| `templates/base.html` | Base layout + HTMX CDN script tag |
| `templates/workouts/workout_detail.html` | HTMX exercise-add interaction hub |
| `templates/workouts/_exercise_added.html` | Success partial: restores buttons + OOB appends exercise row |
| `templates/workouts/_cardio_form.html` | Cardio exercise form partial |
| `templates/workouts/_strength_form.html` | Strength exercise form partial |

## HTMX interaction pattern (exercise add)

Workout detail page has `<ul id="exercise-list">` and `<div id="add-exercise-area">`.

1. "Add Cardio" button: `hx-get` → fetches `_cardio_form.html` → replaces `#add-exercise-area`
2. Form submits: `hx-post` with `hx-target="#add-exercise-area" hx-swap="outerHTML"`
3. **Valid POST** → `_exercise_added.html`:
   - Main content: restores the two add-buttons into `#add-exercise-area`
   - OOB: `<li hx-swap-oob="beforeend:#exercise-list">` appends new exercise row
4. **Invalid POST** → re-renders `_cardio_form.html` with errors back into `#add-exercise-area`

## What still needs doing

### Blocking usability
- [x] **Achievements defined** — `src/achievements/definitions.py` registers
      first_workout / ten_workouts / fifty_workouts / first_cardio / first_strength.
      Imported from `AchievementsConfig.ready()`.
- [x] **Celebration display** — modal `<dialog id="achievement-dialog">` in
      `base.html`. Two delivery paths:
      - **HTMX (immediate):** `AchievementMiddleware` appends an OOB swap
        (`_celebration_oob.html`) filling `#achievement-dialog-content` and sets
        `HX-Trigger: achievements:earned`; a JS listener calls `showModal()`. Shows
        on the same interaction that earned it.
      - **Full page (e.g. after a create→redirect):** middleware stashes keys in
        `session["pending_achievements"]`; `context_processors.pending_achievements`
        pops them on the next non-HTMX render and the inline script opens the dialog.
      Trophy lives in `_celebration_content.html` (not the shell) so an empty dialog
      has no 🏆. Animation: dialog scales/fades in (200ms), trophy grows to 2× over
      1s then back over 3s (CSS `@keyframes`, in `base.html`).
      Note: a count-of-achievements achievement is fine here — the checker is
      eventually-consistent, so earning your 50th on one interaction awards the
      "have 50" achievement on the next interaction.
- [x] **Registration / login / confirmation** — full self-serve auth in the `users`
      app, modeled on the zingor project: `RegistrationForm`, email confirmation via
      `default_token_generator` + Mailgun SMTP (env-configured), register → pending →
      confirm-link → login. `email_confirmed` lives on the custom `User`.
      **Unconfirmed login is blocked** via `ConfirmedAuthenticationForm`
      (`confirm_login_allowed`); superusers bypass it so Maxwell (createsuperuser)
      is never locked out. Resend is a public recovery page (login is blocked, so it
      can't be authenticated). Gate respects `EMAIL_CONFIRMATION_REQUIRED`
      (off in DEBUG). Ryan = regular user, Maxwell = superuser.

### Achievements page
- [x] `/achievements` (`achievements/views.py`, `urls.py`, `achievement_list.html`):
      lists every defined achievement. Locked = "?" (identity hidden). If other
      users earned one you haven't, their usernames + earn times show anyway
      (competition). If you've earned it: 🏆 + name + description + your earn time,
      plus any other earners. Nav link added to `base.html`.
      **Sort order** = definition order in `definitions.py`. The view iterates
      `registry.items()` and `registry` is a plain dict, so list order is just the
      order the `AchievementDef(...)` calls run at import. No explicit sort anywhere.
      `AchievementDef` has an unused `category` field; if a deliberate, source-position-
      independent ordering is ever wanted, add an explicit sort key there.

### Missing CRUD
- [x] Edit and delete for Workout (full-page forms + confirm page)
- [x] Edit and delete for CardioExercise and StrengthExercise (HTMX, on detail page)
- [x] Edit and delete for Movement (full-page + confirm page)

### Admin
- [x] Registered Movement, Workout, CardioExercise, StrengthExercise (workouts/admin.py),
      Achievement (achievements/admin.py), and a custom User admin (users/admin.py).

### Seed data
- [x] `workouts/migrations/0002_seed_movements.py` seeds rowing + running (cardio).

### Testing
- [x] PintFormField / PintTimeFormField (compress, decompress, error messages) — test_fields.py
- [x] CardioExercise at-least-one validation (model + form) — test_workouts_models.py
- [x] View tests (workout CRUD, exercise add/edit/delete happy + validation) — test_views.py
- [x] Auth flow (register, confirm, blocked/allowed login, resend) — test_auth.py

### Bugs fixed this session
- `PintField` inherited CharField's MaxLengthValidator, which called `len()` on a
  pint Quantity and crashed on save. Now validates the stored string form.
- `PintTimeWidget.render()` was missing the `renderer` kwarg Django passes.
- `CheckConstraint(check=...)` → `condition=...` (Django 6.0 deprecation).

### Smaller / deferred
- [ ] `wsgi.py` / `asgi.py` don't add `src/` to sys.path — fine for `uv run` dev,
      will need fixing before any deployment.
- [x] `AchievementMiddleware` now short-circuits when the registry is empty.
- [ ] No cancel button on exercise add/edit forms (deliberate for now).
- [x] HTMX celebration — shows on the same interaction via OOB swap + HX-Trigger,
      in a modal `<dialog>` with a scale-in + trophy pop animation.
- [ ] CSS — still deferred; only the celebration animation has styling so far.
- [x] **One celebration at a time** — each newly earned achievement now gets its
      own dialog, shown one after another (the client loops with no extra round
      trips). Middleware/context processor render each into an inert `<template>`
      inside `<div id="achievement-queue">` (via `_celebration_queue.html`, one
      card per achievement from `_celebration_content.html`, now singular). The
      base.html script drains the queue: `showNext()` moves the next card into the
      dialog and `showModal()`s; on dismiss it reopens for the next after a short
      gap (so it visibly closes/reanimates). HTMX path refills the queue
      out-of-band (`_celebration_oob.html`); full-page path fills it from
      `pending_achievements`. The dialog is modal while open, so no further htmx
      request can clobber an undrained queue.
- [ ] Templates feature, unlockable. Unlock criteria not yet decided. Implementation:
      hidden <span id="nav-templates-link"> plus a _nav_templates_oob.html appended by whatever unlocks it.
- [ ] **Scrub "Parrot" from user-facing strings** (do as part of the app rename):
      email subject (`src/users/auth_emails.py:41`), email body
      (`templates/registration/confirmation_email.txt:3`), and the `DEFAULT_FROM_EMAIL`
      fallback default (`src/parrot/settings.py:148`, `no-reply@parrot.local`). The
      admin fieldset label (`src/users/admin.py:12`) is superuser-only. Package/import
      paths, the db filename, and host defaults are internal — not user-facing.


## Running the app

```
uv run python manage.py runserver
uv run python manage.py createsuperuser
uv run pytest
```

Migrations are already generated. If models change: `uv run python manage.py makemigrations`.
