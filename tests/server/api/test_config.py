import json
from datetime import timedelta
from unittest.mock import patch

import pytest

from common.config.constant import Constant
from server.api.config import (
    all_configs,
    edit_config,
    editable_name_to_config_map,
    format_config,
    frozen_config_map,
    validate_config_type,
)
from server.error import MCPError


class TestValidateConfigType:
    """Test suite for validate_config_type function."""

    def test_validate_string_type(self):
        """Test validation of string type constants."""
        constant = Constant("default_string")
        assert validate_config_type(constant, "hello") == "hello"
        assert validate_config_type(constant, 123) == "123"
        assert validate_config_type(constant, True) == "True"

    def test_validate_int_type(self):
        """Test validation of integer type constants."""
        constant = Constant(0)  # int default value
        assert validate_config_type(constant, 42) == 42
        assert validate_config_type(constant, "123") == 123
        assert validate_config_type(constant, 3.14) == 3

    def test_validate_float_type(self):
        """Test validation of float type constants."""
        constant = Constant(0.0)  # float default value
        assert validate_config_type(constant, 3.14) == 3.14
        assert validate_config_type(constant, 42) == 42.0
        assert validate_config_type(constant, "3.14") == 3.14

    def test_validate_bool_type(self):
        """Test validation of boolean type constants."""
        constant = Constant(False)  # bool default value
        assert validate_config_type(constant, True) is True
        assert validate_config_type(constant, False) is False
        assert validate_config_type(constant, "true") is True
        assert validate_config_type(constant, "1") is True
        assert validate_config_type(constant, "yes") is True
        assert validate_config_type(constant, "on") is True
        assert validate_config_type(constant, "false") is False
        assert validate_config_type(constant, "0") is False
        assert validate_config_type(constant, 1) is True
        assert validate_config_type(constant, 0) is False

    def test_validate_timedelta_type(self):
        """Test validation of timedelta type constants."""
        constant = Constant(timedelta(seconds=0))  # timedelta default value
        assert validate_config_type(constant, 60) == timedelta(seconds=60)
        assert validate_config_type(constant, 3.5) == timedelta(seconds=3.5)
        assert validate_config_type(constant, "120") == timedelta(seconds=120)

    def test_validate_list_type(self):
        """Test validation of list type constants."""
        constant = Constant([])  # list default value
        assert validate_config_type(constant, "item1,item2,item3") == ["item1", "item2", "item3"]
        assert validate_config_type(constant, "single") == ["single"]
        assert validate_config_type(constant, "") == []
        assert validate_config_type(constant, "  item1  ,  item2  ") == ["item1", "item2"]

    def test_validate_dict_type(self):
        """Test validation of dict type constants."""
        constant = Constant({})  # dict default value
        test_dict = {"key": "value", "number": 42}
        assert validate_config_type(constant, json.dumps(test_dict)) == test_dict

    def test_validate_config_type_invalid(self):
        """Test validation failures for invalid type conversions."""
        constant = Constant(0)  # int default value
        with pytest.raises(MCPError) as exc_info:
            validate_config_type(constant, "not_a_number")
        assert "Invalid config value or type" in str(exc_info.value)

        constant = Constant({})  # dict default value
        with pytest.raises(MCPError) as exc_info:
            validate_config_type(constant, "invalid json")
        assert "Invalid config value or type" in str(exc_info.value)


class TestFormatConfig:
    """Test suite for format_config function."""

    def test_format_config_basic(self):
        """Test basic config formatting."""
        result = format_config("test_value")
        assert result == {"value": "test_value", "type": "str", "frozen": False}

    def test_format_config_frozen(self):
        """Test formatting with frozen flag."""
        result = format_config(42, is_frozen=True)
        assert result == {"value": 42, "type": "int", "frozen": True}

    def test_format_config_various_types(self):
        """Test formatting with various types."""
        assert format_config(3.14)["type"] == "float"
        assert format_config(True)["type"] == "bool"
        assert format_config([1, 2, 3])["type"] == "list"
        assert format_config({"key": "value"})["type"] == "dict"


class TestEditConfig:
    """Test suite for edit_config function."""

    @patch.dict(editable_name_to_config_map, clear=True)
    def test_edit_config_success(self):
        """Test successful config editing."""
        test_constant = Constant(10)  # int default value
        editable_name_to_config_map["TEST_VALUE"] = test_constant

        result = edit_config("test_value", "20")
        assert result == {"TEST_VALUE": {"value": 20, "type": "int", "frozen": False}}
        assert test_constant.value == 20

    @patch.dict(editable_name_to_config_map, clear=True)
    def test_edit_config_case_insensitive(self):
        """Test that config name is case-insensitive."""
        test_constant = Constant("default_value")  # str default value
        editable_name_to_config_map["TEST_VALUE"] = test_constant

        result = edit_config("TeSt_VaLuE", "new_value")
        assert result == {"TEST_VALUE": {"value": "new_value", "type": "str", "frozen": False}}

    def test_edit_config_invalid_name(self):
        """Test editing with invalid config name."""
        with pytest.raises(MCPError) as exc_info:
            edit_config("INVALID_CONFIG", "value")
        assert "Invalid config name: INVALID_CONFIG" in str(exc_info.value)

    @patch.dict(editable_name_to_config_map, clear=True)
    def test_edit_config_type_validation_failure(self):
        """Test that type validation errors are propagated."""
        test_constant = Constant(0)  # int default value
        editable_name_to_config_map["TEST_VALUE"] = test_constant

        with pytest.raises(MCPError) as exc_info:
            edit_config("TEST_VALUE", "not_a_number")
        assert "Invalid config value or type" in str(exc_info.value)


class TestAllConfigs:
    """Test suite for all_configs function."""

    @patch.dict(editable_name_to_config_map, clear=True)
    @patch.dict(frozen_config_map, clear=True)
    def test_all_configs_empty(self):
        """Test all_configs with no configurations."""
        result = all_configs()
        assert result == {}

    @patch.dict(editable_name_to_config_map, clear=True)
    @patch.dict(frozen_config_map, clear=True)
    def test_all_configs_mixed(self):
        """Test all_configs with both editable and frozen configs."""
        # Add editable configs
        editable_const = Constant("default")  # str default value
        editable_const.set("editable")
        editable_name_to_config_map["EDITABLE_VALUE"] = editable_const

        # Add frozen configs
        frozen_const = Constant(0)  # int default value
        frozen_const.set(42)
        frozen_config_map["FROZEN_VALUE"] = frozen_const

        result = all_configs()

        assert "EDITABLE_VALUE" in result
        assert result["EDITABLE_VALUE"] == {"value": "editable", "type": "str", "frozen": False}

        assert "FROZEN_VALUE" in result
        assert result["FROZEN_VALUE"] == {"value": 42, "type": "int", "frozen": True}

    @patch.dict(editable_name_to_config_map, clear=True)
    def test_all_configs_multiple_editable(self):
        """Test all_configs with multiple editable configurations."""
        constants = {
            "CONFIG1": Constant("default"),  # str default value
            "CONFIG2": Constant(0),  # int default value
            "CONFIG3": Constant(False),  # bool default value
        }

        constants["CONFIG1"].set("value1")
        constants["CONFIG2"].set(123)
        constants["CONFIG3"].set(True)

        for name, const in constants.items():
            editable_name_to_config_map[name] = const

        result = all_configs()

        assert len(result) >= 3
        assert result["CONFIG1"]["value"] == "value1"
        assert result["CONFIG2"]["value"] == 123
        assert result["CONFIG3"]["value"] is True


class TestIntegration:
    """Integration tests for config module."""

    def test_real_config_maps_populated(self):
        """Test that the real config maps are populated with expected configs."""
        # Check some expected editable configs exist
        assert "INGESTION_PROCESS_MAX_FILE_PATHS" in editable_name_to_config_map
        assert "CHUNK_CHARACTER_LIMIT" in editable_name_to_config_map
        assert "SEARCH_RESULT_LIMIT" in editable_name_to_config_map

        # Check some expected frozen configs exist
        assert "AUDIO_TRANSCRIPTION_DIR" in frozen_config_map
        assert "EMBEDDER_IDLE_TIMEOUT" in frozen_config_map
        assert "SQLITE_DB_LOCATION" in frozen_config_map

    def test_config_type_consistency(self):
        """Test that config types match their constant types."""
        for name, constant in editable_name_to_config_map.items():
            assert isinstance(
                constant.value, constant.default_type
            ), f"Config {name} value type doesn't match its default_type"

        for name, constant in frozen_config_map.items():
            assert isinstance(
                constant.value, constant.default_type
            ), f"Config {name} value type doesn't match its default_type"
