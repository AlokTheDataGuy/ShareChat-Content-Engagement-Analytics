import functools
from typing import Any

_store: dict[str, Any] = {}


def cached(fn):
    """Cache result once for the lifetime of the server process."""
    key = fn.__qualname__

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if key not in _store:
            _store[key] = fn(*args, **kwargs)
        return _store[key]

    return wrapper
