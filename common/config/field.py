from dataclasses import MISSING, field
from datetime import timedelta
from typing import Any, Callable

from common.config.env import Env


def mock_validate(v: Any) -> Any:
    return v


def timedelta_validate(v: str) -> timedelta:
    """Convert value read from env (in seconds) to timedelta

    Args:
        v (str): value in seconds

    Returns:
        timedelta: generated timedelta

    Raises:
        ValueError: the data read from env is not an int or float
    """
    return timedelta(seconds=float(v))


def int_validate(v: str) -> int:
    """Convert value read from env to int

    Args:
        v (str): value

    Returns:
        int: generated int

    Raises:
        ValueError: the data read from env is not an int
    """
    return int(v)


def env_field(
    env_name: str,
    default: Any = MISSING,
    required: bool = False,
    validate: Callable[[Any], Any] = mock_validate,
):
    """Read dataclass field form environment.

    Args:
        env_name (str): name of environement variable
            (always upper-cased prior to searching env)
        default (Optional[Any], optional): default value for field.
            Defaults to None.
        required (bool, optional): whether the field should raise if not found.
            Defaults to False.
        validate (Callable[[Any], Any], optional): validate and convert value
            read from env to expected type. Defaults to mock_validate.

    Returns:
        Field: data class field
    """

    def _factory():
        if Env().get(env_name.upper()) is not None:
            return validate(Env()[env_name.upper()])
        if default is not MISSING:
            return default
        if required:
            raise ValueError(f"required field `{env_name.upper()}`not found for in env" " and no default was provided")
        return None

    return field(default_factory=_factory)


def int_env_field(
    env_name: str,
    default: Any = MISSING,
    required: bool = False,
):
    return env_field(env_name, default, required, int_validate)


def timedelta_env_field(
    env_name: str,
    default: Any = MISSING,
    required: bool = False,
):
    """Read value from env if found and convert to timedelta.
    value should be number of seconds

    Args:
        env_name (str): name of environement variable
            (always upper-cased prior to searching env)
        default (Optional[Any], optional): default value for field. Defaults to None.
        required (bool, optional): whether the field should raise if not found.
            Defaults to False.

    Returns:
        Field: field from env that will convert to timedelta
    """
    return env_field(env_name, default, required, timedelta_validate)
