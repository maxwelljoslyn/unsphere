"""Delete all workouts, exercises, and achievements for QA.

Users and movements are intentionally kept, so you can repeatedly re-test
achievement unlocks from a clean slate without recreating accounts or the
movement catalog.

    uv run python manage.py reset_qa_data            # prompts for confirmation
    uv run python manage.py reset_qa_data --noinput  # skip the prompt
"""

from django.core.management.base import BaseCommand

from achievements.models import Achievement
from workouts.models import CardioExercise, StrengthExercise, Workout


class Command(BaseCommand):
    help = (
        "Delete all workouts, exercises, and achievements (keeps users and movements)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_true",
            dest="noinput",
            help="Skip the confirmation prompt.",
        )

    def handle(self, *args, **options):
        if not options["noinput"]:
            answer = input(
                "Delete ALL workouts, exercises, and achievements? "
                "(users and movements are kept) [y/N]: "
            )
            if answer.strip().lower() not in {"y", "yes"}:
                self.stdout.write(self.style.WARNING("Aborted; nothing deleted."))
                return

        # Delete exercises and achievements before workouts. (Exercises would
        # cascade when workouts are deleted, but doing them first yields honest
        # per-model counts. Achievements aren't tied to workouts.)
        for model in (CardioExercise, StrengthExercise, Achievement, Workout):
            count, _ = model.objects.all().delete()
            self.stdout.write(f"  {model.__name__}: {count} deleted")

        self.stdout.write(self.style.SUCCESS("Done. Users and movements untouched."))
