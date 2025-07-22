import json
import os
import threading
from datetime import timedelta
from typing import Dict, Generic, Optional, Type, TypeVar

T = TypeVar("T")


class Constant(Generic[T]):
    _instances: Dict[str, "Constant[T]"] = {}
    _lock = threading.Lock()

    def __new__(cls, default_value: T, identifier: Optional[str] = None, env_var: Optional[str] = None):
        if identifier is None:
            identifier = str(id(default_value))

        with cls._lock:
            if identifier not in cls._instances:
                instance = super().__new__(cls)
                cls._instances[identifier] = instance
                instance._initialized = False  # type: ignore
            return cls._instances[identifier]

    def __init__(self, default_value: T, identifier: Optional[str] = None, env_var: Optional[str] = None):
        if not hasattr(self, "_initialized") or not self._initialized:  # type: ignore
            self._env_var = env_var
            self._default_value = default_value
            self._value = self._get_initial_value()
            self._value_lock = threading.RLock()
            self._initialized = True

    def _get_initial_value(self) -> T:
        """Get the initial value, checking environment variable first if specified."""
        if self._env_var is None:
            return self._default_value

        env_value = os.environ.get(self._env_var)
        if env_value is None:
            return self._default_value

        return self._convert_env_value(env_value, self._default_value)

    @property
    def default_type(self) -> Type[T]:
        return type(self._default_value)

    def _convert_env_value(self, env_value: str, default_value: T) -> T:
        """Convert environment variable string to the appropriate type based on default_value."""
        if default_value is None:
            return env_value  # type: ignore

        default_type = type(default_value)

        try:
            if default_type == str:
                return env_value  # type: ignore
            elif default_type == int:
                return int(env_value)  # type: ignore
            elif default_type == float:
                return float(env_value)  # type: ignore
            elif default_type == bool:
                return env_value.lower() in ("true", "1", "yes", "on")  # type: ignore
            elif default_type == list:
                # Try to parse as comma-separated values
                if not env_value.strip():
                    return []  # type: ignore

                # If it looks like a JSON array, treat it as a single item
                stripped_value = env_value.strip()
                if stripped_value.startswith("[") and stripped_value.endswith("]"):
                    return [env_value]  # type: ignore

                return [item.strip() for item in env_value.split(",")]  # type: ignore
            elif default_type == dict:
                # Try to parse as JSON-like string
                return json.loads(env_value)  # type: ignore
            elif default_type == timedelta:
                return timedelta(seconds=int(env_value))  # type: ignore
            else:
                # For other types, return the string and let the user handle conversion
                return env_value  # type: ignore
        except (ValueError, json.JSONDecodeError):
            # If conversion fails, return the default value
            return default_value

    def get(self) -> T:
        return self._value

    def set(self, new_value: T) -> None:
        with self._value_lock:
            self._value = new_value

    def __call__(self) -> T:
        return self.get()

    @property
    def value(self) -> T:
        return self.get()

    @value.setter
    def value(self, new_value: T) -> None:
        self.set(new_value)
