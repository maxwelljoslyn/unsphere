from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="workout-list"), name="home"),
    path("admin/", admin.site.urls),
    # Our auth routes (custom login form, registration) take precedence over
    # Django's built-ins; contrib.auth still supplies logout + password reset.
    path("accounts/", include("users.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("workouts.urls")),
    path("", include("achievements.urls")),
    path("", include("gems.urls")),
    path("", include("stats.urls")),
]
