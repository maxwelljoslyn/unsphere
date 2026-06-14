from django.db import migrations, models
from django.db.models import F


def backfill_acknowledged(apps, schema_editor):
    """Treat every pre-existing achievement as already acknowledged.

    Without this, deploying the column would leave all historical rows with
    acknowledged_at=NULL, so every user would be re-celebrated for achievements
    they earned (and dismissed) long ago on their next page load. Stamping the
    earn time as the acknowledgment time suppresses that.
    """
    Achievement = apps.get_model("achievements", "Achievement")
    Achievement.objects.filter(acknowledged_at__isnull=True).update(
        acknowledged_at=F("earned_at")
    )


class Migration(migrations.Migration):
    dependencies = [
        ("achievements", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="achievement",
            name="acknowledged_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_acknowledged, migrations.RunPython.noop),
    ]
