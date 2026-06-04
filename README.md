# unsphere

Private fitness tracking app for two users (Maxwell + Ryan). Django + HTMX.

## Setup

```sh
uv run python manage.py migrate
```

The initial migration seeds the cardio movements `rowing` and `running`.

### Accounts

Users self-register at `/accounts/register/`. Registration creates a regular
(non-staff) account and sends a confirmation email; the account cannot log in
until the email link is clicked. Superusers bypass the confirmation gate.

Make Maxwell a superuser (Ryan stays a regular user):

```sh
uv run python manage.py createsuperuser   # for Maxwell
```

Then either register Ryan through the web flow, or create him from the admin at
`/admin/`.

In development (`DEBUG=True`) email confirmation is disabled by default, so
registration auto-confirms and logs you straight in. Confirmation emails are
printed to the console (the default `EMAIL_BACKEND`).

### Email (Mailgun in production)

Email is sent over SMTP and configured entirely through the environment. For
Mailgun:

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

`EMAIL_CONFIRMATION_REQUIRED` defaults to `false` when `DEBUG` is on and `true`
otherwise.

## Running

```sh
uv run python manage.py runserver
uv run pytest
```

If models change: `uv run python manage.py makemigrations`.

See `PLAN.md` for architecture decisions and remaining work.
