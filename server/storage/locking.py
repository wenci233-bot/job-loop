from functools import wraps
from threading import RLock
LOCK = RLock()
def locked(fn):
    @wraps(fn)
    def call(*args, **kwargs):
        with LOCK:
            return fn(*args, **kwargs)
    return call
