from django.urls import path

from . import views

urlpatterns = [
    path("gems/", views.gem_list, name="gem-list"),
]
