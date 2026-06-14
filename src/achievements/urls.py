from django.urls import path

from . import views

urlpatterns = [
    path("achievements/", views.achievement_list, name="achievement-list"),
    path("achievements/ack/", views.acknowledge, name="achievement-ack"),
]
