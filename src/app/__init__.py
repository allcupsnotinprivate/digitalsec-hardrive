import pathlib

import nltk

PROJECT_DIR = pathlib.Path(__file__).parent

STATICFILES_DIR = PROJECT_DIR / "staticfiles"

nltk.data.path.append(str(STATICFILES_DIR))
