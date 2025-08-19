import hashlib
from datetime import datetime


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
