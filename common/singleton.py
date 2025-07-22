from typing import Dict


class Singleton(type):
    _instances: Dict = {}

    def found(cls) -> bool:
        return cls._instances.get(cls) is not None

    def __call__(cls, *args, **kwargs):
        if not cls.found():
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
