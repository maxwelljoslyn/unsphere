from django.db import migrations

INITIAL_MOVEMENTS = [
    ("rowing", "cardio"),
    ("running", "cardio"),
]


def add_movements(apps, schema_editor):
    Movement = apps.get_model("workouts", "Movement")
    for name, kind in INITIAL_MOVEMENTS:
        Movement.objects.get_or_create(name=name, defaults={"kind": kind})


def remove_movements(apps, schema_editor):
    Movement = apps.get_model("workouts", "Movement")
    Movement.objects.filter(name__in=[name for name, _ in INITIAL_MOVEMENTS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("workouts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_movements, remove_movements),
    ]
