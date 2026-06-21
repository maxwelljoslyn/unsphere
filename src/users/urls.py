from django.contrib.auth.views import LoginView
from django.urls import path

from . import views
from .forms import ConfirmedAuthenticationForm

urlpatterns = [
    path(
        "login/",
        LoginView.as_view(authentication_form=ConfirmedAuthenticationForm),
        name="login",
    ),
    path("register/", views.register, name="register"),
    path("register/pending/", views.register_pending, name="register-pending"),
    path(
        "register/confirm/<uidb64>/<token>/",
        views.register_confirm,
        name="register-confirm",
    ),
    path(
        "email-confirmation/resend/",
        views.resend_confirmation,
        name="resend-confirmation",
    ),
    # Override Django's reset-confirm view (its other reset views, included via
    # django.contrib.auth.urls, are used as-is) so a completed reset also marks
    # the email confirmed. This is matched before contrib.auth.urls; it produces
    # the identical path, so the reset link in the email routes here regardless
    # of which pattern reverse() picks for the shared name.
    path(
        "reset/<uidb64>/<token>/",
        views.ConfirmingPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
]
