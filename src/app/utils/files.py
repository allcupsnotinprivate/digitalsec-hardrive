import re
import unicodedata
from pathlib import Path

_INVALID_CHARS_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(candidate: str, extension: str | None = None) -> str:
    if not candidate or not candidate.strip():
        candidate = "document"

    candidate = unicodedata.normalize("NFKD", candidate.strip())

    provided_extension = extension
    if provided_extension:
        provided_extension = provided_extension if provided_extension.startswith(".") else f".{provided_extension}"
        stem = Path(candidate).stem if Path(candidate).stem else candidate
    else:
        path_candidate = Path(candidate)
        provided_extension = path_candidate.suffix
        stem = path_candidate.stem if path_candidate.stem else path_candidate.name

    sanitized_stem = _INVALID_CHARS_PATTERN.sub("_", stem)
    sanitized_stem = sanitized_stem.strip("._") or "document"

    filename = sanitized_stem[:128]
    if provided_extension:
        filename = f"{filename}{provided_extension}"

    return filename
