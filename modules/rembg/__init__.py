import threading
from contextlib import contextmanager


lock = threading.Lock()
scopes = 0 # number of open session_scope() contexts
cached = None # (model, session), kept only while a scope is open


def get_session(model: str):
    """Return a rembg session for model: reused inside session_scope(), otherwise created for this call only"""
    global cached # pylint: disable=global-statement
    import rembg
    with lock:
        if scopes > 0 and cached is not None and cached[0] == model:
            return cached[1]
    session = rembg.new_session(model) # pylint: disable=c-extension-no-member
    with lock:
        if scopes > 0:
            cached = (model, session)
    return session


@contextmanager
def session_scope():
    """Keep one rembg session for all images of a run and release it when the run ends"""
    global scopes, cached # pylint: disable=global-statement
    with lock:
        scopes += 1
    try:
        yield
    finally:
        with lock:
            scopes -= 1
            if scopes == 0:
                cached = None
