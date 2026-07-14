# Unsphere

A fitness tracker I built and run for myself and some friends. You
log workouts, earn gems and achievements for staying consistent, and watch your
lifetime stats add up. The user base is small, but it's deployed and live at [unsphere.maxwelljoslyn.com](https://unsphere.maxwelljoslyn.com)
(note: most features require login).

**Stack**: Django, SQLite, and [HTMX](https://htmx.org/) (for interactivity with minimal JavaScript.) Sits behind a Caddy reverse proxy which I use for several sites. Deployed via GitHub Actions.

## Features

- **Workout logging**: Build a workout from individual exercises. Workouts are drafts until confirmed, so you can keep adding to a workout while you're still exercising, then confirm it at the end.
- **Cardio and strength exercises**: Cardio tracks distance and/or duration; strength tracks sets, reps, and weight. Quantities are unit-aware (powered by [Pint](https://pint.readthedocs.io/)) and currently support miles/kilometers and pounds/kilograms.
- **Custom movements**: Unsphere calls each type of exercise a "movement". The initial set consists of `rowing` and `running`, but all users can add their own cardio or strength movements.
- **Timezone-aware**: Each workout stores a UTC instant plus the IANA zone it was logged in, so it's always displayed in, and labeled with, the timezone where it actually happened.
- **Achievements and celebrations**: Users earn achievements for milestones, such as total lifetime workouts. A "celebration" modal popup appears after a user earns an achievement. Each achievement can be earned once.
- **Gems**: Users earn gems, a playful in-app currency, for consistent activity. Gem criteria can be satisfied repeatedly, e.g. each mile of cardio distance earns a user one gem. Gem gains are "celebrated" more subtly than achievements, with a small popup in the corner and a consistent navbar element.
- **Stats**: The stats page shows each user their lifetime totals for workouts, exercises, cardio distance and time, plus their current workout streak and a heatmap of workout frequency over time.
- **In-app feedback**: Users can notify a developer/admin of bugs or feature requests with a feedback form that files GitHub issues.

## Setup

```sh
git clone https://github.com/maxwelljoslyn/unsphere.git
uv sync
uv run python manage.py migrate
```

The initial migration seeds the cardio movements `rowing` and `running`.

### Accounts

If you're the admin, create a superuser account (needed to reach `/admin/` routes) with:

```sh
uv run python manage.py createsuperuser
```

Users self-register at `/accounts/register/`. Registration creates a regular
(non-staff) account and sends a confirmation email; the account cannot log in
until the email link is clicked.

### Email

In development (`DEBUG=True`) email confirmation is disabled by default, so
registration auto-confirms and logs you straight in. Confirmation emails are
printed to the console (the default `EMAIL_BACKEND`).

Production email is sent over SMTP and configured through environment variables. Here's an example for using Mailgun as an email provider:

```sh
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.mailgun.org
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=postmaster@mg.yourdomain.com
EMAIL_HOST_PASSWORD=<mailgun smtp password>
DEFAULT_FROM_EMAIL=Unsphere <no-reply@mg.yourdomain.com>
EMAIL_CONFIRMATION_REQUIRED=true
```

`EMAIL_CONFIRMATION_REQUIRED` defaults to `false` when `DEBUG` is on and `true` otherwise.

### Feedback

Logged-in users can submit feedback (a title and description) at `/feedback/`.
Each submission is filed as a GitHub issue, labeled `user-feedback`, in a repo
you designate. The submitter's username is appended to the issue body.

This is configured through two environment variables:

```sh
GITHUB_FEEDBACK_REPO=owner/name          # repo that receives the issues
GITHUB_FEEDBACK_TOKEN=<github pat>       # personal access token, issue-write scope
```

If either of those variables is not set, the feedback page is still reachable, but it will display a message indicating it's not configured.

The token must be a **personal access token** with permission to create issues in the target repo (fine-grained: `Issues - Read` and `Issues - Write`; classic: `repo`). A deploy key won't work; it can push, but can't call the GitHub REST API. Issues are filed as whoever owns the token, so use a GitHub account you're comfortable having appear as the issue author.

## Running

If database models have changed, migrate them with:

```sh
uv run python manage.py makemigrations
uv run python manage.py migrate
```

Assuming no errors during migration, start up the server:

```sh
uv run python manage.py runserver
```

## Development

Run tests with `uv run pytest`. `pytest-xdist` is a developer dependency, so you can speed up test runs by distributing tests over multiple workers with `uv run pytest -n X` (where X is a number or `auto`).

This project uses `ruff` for formatting. Before committing, run `uv run ruff check --fix && uv run ruff format` to standardize code style.
