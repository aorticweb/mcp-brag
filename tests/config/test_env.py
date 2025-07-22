import os
from unittest import mock

import pytest

from common.config.env import Env


@pytest.fixture
def mocked_environ():
    with mock.patch.dict(os.environ, {"MY_VAR": "my_value"}) as environ:
        yield environ


def test_env_reads_from_os_environ(mocked_environ):
    assert Env()["MY_VAR"] == Env()["my_var"] == Env().get("MY_VAR") == Env().get("my_var") == "my_value"
    assert Env().get("NOT_KNOWN") is None
    with pytest.raises(KeyError):
        Env()["NOT_KNOWN"]


def test_env_reads_yaml_format_with_os_environ_backpopulate(mocked_environ):
    mock_file_content = "\n".join(["redis_host: localhost", "redis_port: 6379", 'redis_db: "0"'])
    file_mock = mock.mock_open(read_data=mock_file_content)
    with mock.patch("builtins.open", file_mock):
        assert Env("mock_path", True).get("REDIS_HOST") == "localhost"
        # test singleton characteristic
        assert Env().get("REDIS_PORT") == "6379"
        assert Env().get("REDIS_DB") == "0"

    assert os.environ.get("REDIS_HOST") == "localhost"
    assert os.environ.get("REDIS_PORT") == "6379"


def test_env_reads_invalid_yaml_format_no_error():
    mock_file_content = "NOT_YAML_"
    file_mock = mock.mock_open(read_data=mock_file_content)
    with mock.patch("builtins.open", file_mock):
        assert Env("mock_path").get("REDIS_HOST") is None
        # test singleton characteristic
        assert Env().get("REDIS_PORT") is None

    assert os.environ.get("REDIS_HOST") is None


def test_env_reads_json_format():
    mock_file_content = '{"redis_host": "localhost", "redis_port": 6379, "redis_db": "0"}'
    file_mock = mock.mock_open(read_data=mock_file_content)
    with mock.patch("builtins.open", file_mock):
        assert Env("mock_path").get("REDIS_HOST") == "localhost"
        # test singleton characteristic
        assert Env().get("REDIS_PORT") == "6379"
        assert Env().get("REDIS_DB") == "0"


def test_env_reads_invalid_json_format_no_error():
    mock_file_content = "NOT_JSON"
    file_mock = mock.mock_open(read_data=mock_file_content)
    with mock.patch("builtins.open", file_mock):
        assert Env("mock_path").get("REDIS_HOST") is None
        # test singleton characteristic
        assert Env().get("REDIS_PORT") is None

    assert os.environ.get("REDIS_HOST") is None
