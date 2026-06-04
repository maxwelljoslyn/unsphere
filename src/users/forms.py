from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class ConfirmedAuthenticationForm(AuthenticationForm):
    """Login form that refuses unconfirmed accounts.

    Superusers (e.g. the admin created via createsuperuser) bypass the check so
    they're never locked out, and the gate only applies when confirmation is
    actually required (i.e. not in dev).
    """

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if (
            settings.EMAIL_CONFIRMATION_REQUIRED
            and not user.email_confirmed
            and not user.is_superuser
        ):
            raise forms.ValidationError(
                "Please confirm your email address before logging in. "
                "Check your inbox, or request a new confirmation link.",
                code="unconfirmed",
            )
