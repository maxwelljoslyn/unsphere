from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordResetConfirmView
from django.shortcuts import redirect, render
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from .auth_emails import EmailSendError, send_confirmation_email
from .forms import RegistrationForm

User = get_user_model()


class ConfirmingPasswordResetConfirmView(PasswordResetConfirmView):
    """Django's reset-confirm view, but it also marks the email confirmed.

    Completing a password reset proves control of the account's email address —
    the same proof account confirmation requires — so anyone who finishes a reset
    should never then be bounced by the unconfirmed-login gate. Without this, a
    user who forgot their password *and* never confirmed would reset it and still
    be unable to log in.
    """

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.user
        if not user.email_confirmed:
            user.email_confirmed = True
            user.save(update_fields=["email_confirmed"])
        return response


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            try:
                send_confirmation_email(user, request)
            except EmailSendError:
                messages.error(
                    request,
                    "Account created, but we couldn't send a confirmation email. "
                    "Use the link below to request another one.",
                )
                return redirect("resend-confirmation")
            if not settings.EMAIL_CONFIRMATION_REQUIRED:
                login(request, user)
                messages.success(request, "Email auto-confirmed in dev.")
                return redirect("workout-list")
            return redirect("register-pending")
    else:
        form = RegistrationForm()
    return render(request, "registration/register.html", {"form": form})


def register_pending(request):
    return render(request, "registration/register_pending.html")


def register_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.email_confirmed = True
        user.save(update_fields=["email_confirmed"])
        login(request, user)
        messages.success(request, "Your email has been confirmed.")
        return redirect("workout-list")
    return render(request, "registration/register_confirm_invalid.html")


def resend_confirmation(request):
    """Public recovery path: re-send the confirmation link.

    Login is blocked until confirmation, so this can't require authentication.
    We always show the same message regardless of whether the username matched,
    to avoid leaking which accounts exist.
    """
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        user = User.objects.filter(username=username, email_confirmed=False).first()
        if user is not None:
            try:
                send_confirmation_email(user, request)
            except EmailSendError:
                pass
        messages.success(
            request,
            "If that account exists and is unconfirmed, a new confirmation "
            "email is on its way.",
        )
        return redirect("login")
    return render(request, "registration/resend_confirmation.html")
