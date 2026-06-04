import os
import sys
from pathlib import Path

# The apps (users, workouts, achievements) live under src/, which manage.py
# adds to sys.path. Gunicorn imports this module directly, so add it here too.
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from django.core.wsgi import get_wsgi_application  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "unsphere.settings")
application = get_wsgi_application()
