import os
from dataclasses import dataclass
from datetime import timedelta
from unittest import mock

import pytest

from common.config.field import env_field, int_env_field, timedelta_env_field


class MyConfig:
    name: str = env_field(
        "name",
    )
    location: str = env_field(
        "name",
    )


def test_env_field_found_in_env():
    @dataclass
    class MyConfig:
        name: str = env_field("name")

    with mock.patch.dict(os.environ, {"NAME": "my_value"}):
        assert MyConfig().name == "my_value"


def test_env_field_not_found_in_env():
    @dataclass
    class MyConfig:
        name: str = env_field("name")

    with mock.patch.dict(os.environ, {}):
        assert MyConfig().name is None


def test_env_field_not_found_in_env_with_default():
    @dataclass
    class MyConfig:
        name: str = env_field("name", "long")

    with mock.patch.dict(os.environ, {}):
        assert MyConfig().name == "long"


def test_env_field_not_found_in_env_with_default_none():
    @dataclass
    class MyConfig:
        name: str = env_field("name", None)

    with mock.patch.dict(os.environ, {}):
        assert MyConfig().name is None


def test_env_field_required_not_found_in_env_without_default_raises_error():
    @dataclass
    class MyConfig:
        name: str = int_env_field("name", required=True)

    with mock.patch.dict(os.environ, {}):
        with pytest.raises(ValueError):
            MyConfig()


def test_int_env_field_converts_to_int():
    @dataclass
    class MyConfig:
        name: str = int_env_field("name")

    with mock.patch.dict(os.environ, {"NAME": "0"}):
        assert isinstance(MyConfig().name, int)
        assert MyConfig().name == 0


def test_int_env_field_validates_env_input_and_raises_value_error():
    @dataclass
    class MyConfig:
        name: str = int_env_field("name")

    with mock.patch.dict(os.environ, {"NAME": "fish"}):
        with pytest.raises(ValueError):
            MyConfig()


def test_int_env_field_does_not_validate_default():
    @dataclass
    class MyConfig:
        name: str = int_env_field("name", "fish")

    with mock.patch.dict(os.environ, {}):
        MyConfig().name == "fish"


def test_timedelta_env_field_field_converts_to_timedelta():
    @dataclass
    class MyConfig:
        length: str = timedelta_env_field("length")

    with mock.patch.dict(os.environ, {"LENGTH": "100"}):
        MyConfig().length == timedelta(seconds=100)
