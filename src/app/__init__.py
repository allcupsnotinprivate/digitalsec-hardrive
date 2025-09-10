import pathlib

import nltk

PROJECT_DIR = pathlib.Path(__file__).parent

STATICFILES_DIR = PROJECT_DIR / "staticfiles"

LOGS_DIR = PROJECT_DIR / "logs"

try:  # pragma: no cover - optional dependency
    import nltk

    nltk.data.path.append(str(STATICFILES_DIR))
except (Exception,):
    nltk = None
