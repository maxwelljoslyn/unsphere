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
]
