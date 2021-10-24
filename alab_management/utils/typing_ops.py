def is_typing(cls):
    return hasattr(cls, "__origin__")
