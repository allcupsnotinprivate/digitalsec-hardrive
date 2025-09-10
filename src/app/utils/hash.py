import hashlib
import re
from datetime import datetime

HEX_RUN_RE = re.compile(r"(?:[0-9a-fA-F]{2}\s+){4,}[0-9a-fA-F]{2}")


def create_sha256_hash(input_string: str, as_bytes: bool = True) -> bytes | str:
    sha256_hash = hashlib.sha256(input_string.encode("utf-8"))
    if as_bytes:
        return sha256_hash.digest()
    else:
        return sha256_hash.hexdigest()


def create_md5_hash(input_string: str, as_bytes: bool = True) -> bytes | str:
    md5_hash = hashlib.md5(input_string.encode("utf-8"), usedforsecurity=False)
    if as_bytes:
        return md5_hash.digest()
    else:
        return md5_hash.hexdigest()


def create_document_name() -> str:
    now = datetime.now()

    dt_str = now.strftime("%Y-%m-%d_%H-%M-%S")

    hash_input = dt_str.encode("utf-8")
    hex_str = hashlib.sha256(hash_input).hexdigest()[:10]

    document_name = f"{hex_str}_{dt_str}"
    return document_name


def strip_hashes(text: str) -> str:
    def _is_hash(token: str) -> bool:
        if token.isdigit():
            return False

        if not re.fullmatch(r"[A-Za-z0-9+]+", token):
            return False

        if len(token) < 8:
            return False

        digits = sum(ch.isdigit() for ch in token)
        letters = sum(ch.isalpha() for ch in token)

        if digits > 1 and letters >= 3:
            return True

        return False

    text = HEX_RUN_RE.sub(" ", text)
    tokens = text.split()
    kept = [t for t in tokens if not _is_hash(t)]
    return " ".join(kept)
