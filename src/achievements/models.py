from django.db import models
from django.conf import settings


class Achievement(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="achievements"
    )
    achievement_key = models.CharField(max_length=100)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "achievement_key")]

    def __str__(self):
        return f"{self.user} — {self.achievement_key}"
