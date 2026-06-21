import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

User = get_user_model()

REQUIRED = override_settings(EMAIL_CONFIRMATION_REQUIRED=True)
NOT_REQUIRED = override_settings(EMAIL_CONFIRMATION_REQUIRED=False)


def _confirm_url(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return reverse("register-confirm", kwargs={"uidb64": uid, "token": token})


# --- Registration -----------------------------------------------------------


@pytest.mark.django_db
@REQUIRED
def test_register_creates_unconfirmed_user_and_sends_email(client):
    resp = client.post(
        reverse("register"),
        {
            "username": "newbie",
            "email": "newbie@example.com",
            "password1": "testpass123!",
            "password2": "testpass123!",
        },
    )
    assert resp.status_code == 302
    assert resp.url == reverse("register-pending")
    user = User.objects.get(username="newbie")
    assert user.email_confirmed is False
    assert len(mail.outbox) == 1
    assert "newbie@example.com" in mail.outbox[0].to


@pytest.mark.django_db
@NOT_REQUIRED
def test_register_autoconfirms_and_logs_in_when_not_required(client):
    resp = client.post(
        reverse("register"),
        {
            "username": "devuser",
            "email": "dev@example.com",
            "password1": "testpass123!",
            "password2": "testpass123!",
        },
    )
    assert resp.status_code == 302
    assert resp.url == reverse("workout-list")
    user = User.objects.get(username="devuser")
    assert user.email_confirmed is True
    assert len(mail.outbox) == 0
    # logged in
    assert resp.wsgi_request.user.is_authenticated


# --- Confirmation -----------------------------------------------------------


@pytest.mark.django_db
@REQUIRED
def test_confirm_link_confirms_and_logs_in(client):
    user = User.objects.create_user(
        username="pending", email="p@example.com", password="x"
    )
    resp = client.get(_confirm_url(user))
    assert resp.status_code == 302
    assert resp.url == reverse("workout-list")
    user.refresh_from_db()
    assert user.email_confirmed is True


@pytest.mark.django_db
@REQUIRED
def test_confirm_link_invalid_token(client):
    user = User.objects.create_user(
        username="pending2", email="p2@example.com", password="x"
    )
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    resp = client.get(
        reverse("register-confirm", kwargs={"uidb64": uid, "token": "bad-token"})
    )
    assert resp.status_code == 200
    assert b"invalid or has expired" in resp.content.lower()
    user.refresh_from_db()
    assert user.email_confirmed is False


# --- Login gating -----------------------------------------------------------


@pytest.mark.django_db
@REQUIRED
def test_unconfirmed_login_blocked(client):
    User.objects.create_user(
        username="blocked", email="b@example.com", password="testpass123!"
    )
    resp = client.post(
        reverse("login"), {"username": "blocked", "password": "testpass123!"}
    )
    assert resp.status_code == 200  # re-rendered form, not a redirect
    assert b"confirm your email" in resp.content.lower()
    assert not resp.wsgi_request.user.is_authenticated


@pytest.mark.django_db
@REQUIRED
def test_confirmed_login_succeeds(client):
    user = User.objects.create_user(
        username="ok", email="ok@example.com", password="testpass123!"
    )
    user.email_confirmed = True
    user.save(update_fields=["email_confirmed"])
    resp = client.post(reverse("login"), {"username": "ok", "password": "testpass123!"})
    assert resp.status_code == 302


@pytest.mark.django_db
@REQUIRED
def test_superuser_bypasses_confirmation(client):
    User.objects.create_superuser(
        username="maxwell", email="m@example.com", password="testpass123!"
    )
    resp = client.post(
        reverse("login"), {"username": "maxwell", "password": "testpass123!"}
    )
    assert resp.status_code == 302


# --- Resend -----------------------------------------------------------------


@pytest.mark.django_db
@REQUIRED
def test_resend_confirmation_sends_for_unconfirmed(client):
    User.objects.create_user(username="lost", email="lost@example.com", password="x")
    resp = client.post(reverse("resend-confirmation"), {"username": "lost"})
    assert resp.status_code == 302
    assert resp.url == reverse("login")
    assert len(mail.outbox) == 1


@pytest.mark.django_db
@REQUIRED
def test_resend_confirmation_unknown_user_is_silent(client):
    resp = client.post(reverse("resend-confirmation"), {"username": "ghost"})
    assert resp.status_code == 302
    assert len(mail.outbox) == 0


# --- Password reset ---------------------------------------------------------


@pytest.mark.django_db
def test_password_reset_sends_email(client):
    User.objects.create_user(
        username="forgot", email="forgot@example.com", password="oldpass123!"
    )
    resp = client.post(reverse("password_reset"), {"email": "forgot@example.com"})
    assert resp.status_code == 302
    assert resp.url == reverse("password_reset_done")
    assert len(mail.outbox) == 1
    assert "forgot@example.com" in mail.outbox[0].to


@pytest.mark.django_db
def test_password_reset_unknown_email_is_silent(client):
    resp = client.post(reverse("password_reset"), {"email": "nobody@example.com"})
    assert resp.status_code == 302
    assert resp.url == reverse("password_reset_done")
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_password_reset_confirm_sets_password_and_confirms_email(client):
    user = User.objects.create_user(
        username="resetme", email="reset@example.com", password="oldpass123!"
    )
    assert user.email_confirmed is False
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    # The first GET stores the token in the session and redirects to the
    # set-password URL (the token in the URL becomes a fixed sentinel).
    resp = client.get(
        reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": token})
    )
    assert resp.status_code == 302

    resp = client.post(
        resp.url,
        {"new_password1": "brandnew456!", "new_password2": "brandnew456!"},
    )
    assert resp.status_code == 302
    assert resp.url == reverse("password_reset_complete")

    user.refresh_from_db()
    assert user.check_password("brandnew456!")
    # Completing the reset proves email control, so the account is confirmed too.
    assert user.email_confirmed is True


@pytest.mark.django_db
def test_password_reset_confirm_invalid_link(client):
    user = User.objects.create_user(
        username="resetbad", email="resetbad@example.com", password="oldpass123!"
    )
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    resp = client.get(
        reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": "bad-token"})
    )
    assert resp.status_code == 200
    assert b"invalid or has expired" in resp.content.lower()
