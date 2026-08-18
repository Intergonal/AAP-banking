"""Thread-local user context for agent tools.

Tools run synchronously inside a Flask request (chat endpoint); storing the
authenticated user id in a threading.local keeps the context request-scoped and
thread-safe without coupling the agent engine to Flask.
"""

import threading

_local = threading.local()


def set_user_id(user_id):
    _local.user_id = user_id


def get_user_id():
    return getattr(_local, "user_id", None)
