import concurrent.futures
import os
import threading
import time
from datetime import timedelta
from typing import Dict, List
from unittest import mock

from common.config.constant import Constant


class TestConstantBasicFunctionality:
    def test_basic_get_set_operations(self):
        const = Constant(42, "test_basic")

        assert const.get() == 42

        const.set(100)
        assert const.get() == 100

    def test_property_access(self):
        const = Constant("hello", "test_property")

        assert const.value == "hello"

        const.value = "world"
        assert const.value == "world"

    def test_callable_access(self):
        const = Constant([1, 2, 3], "test_callable")

        assert const() == [1, 2, 3]

        const.set([4, 5, 6])
        assert const() == [4, 5, 6]

    def test_different_data_types(self):
        str_const = Constant("string", "str_test")
        int_const = Constant(123, "int_test")
        list_const = Constant([1, 2, 3], "list_test")
        dict_const = Constant({"key": "value"}, "dict_test")

        assert str_const.value == "string"
        assert int_const.value == 123
        assert list_const.value == [1, 2, 3]
        assert dict_const.value == {"key": "value"}


class TestConstantSingletonBehavior:
    def test_same_identifier_returns_same_instance(self):
        const1 = Constant("first", "singleton_test")
        const2 = Constant("second", "singleton_test")

        assert const1 is const2
        assert const1.value == "first"
        assert const2.value == "first"

    def test_different_identifiers_create_different_instances(self):
        const1 = Constant("value1", "test1")
        const2 = Constant("value2", "test2")

        assert const1 is not const2
        assert const1.value == "value1"
        assert const2.value == "value2"

    def test_singleton_persists_across_modules(self):
        const1 = Constant(100, "module_test")
        const1.set(200)

        const2 = Constant(999, "module_test")

        assert const1 is const2
        assert const2.value == 200

    def test_auto_identifier_with_same_object(self):
        shared_list = [1, 2, 3]
        const1 = Constant(shared_list)
        const2 = Constant(shared_list)

        assert const1 is const2

    def test_auto_identifier_with_different_objects(self):
        const1 = Constant([1, 2, 3])
        const2 = Constant([1, 2, 3])

        assert const1 is not const2


class TestConstantThreadSafety:
    def test_concurrent_reads(self):
        const = Constant(0, "concurrent_read_test")
        const.set(42)
        results = []

        def read_worker():
            for _ in range(10):
                value = const.get()
                results.append(value)
                time.sleep(0.001)

        threads = []
        for _ in range(5):
            thread = threading.Thread(target=read_worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert all(value == 42 for value in results)
        assert len(results) == 50

    def test_concurrent_writes(self):
        const = Constant(0, "concurrent_write_test")

        def write_worker(worker_id: int):
            for i in range(5):
                const.set(worker_id * 100 + i)
                time.sleep(0.001)

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(write_worker, i) for i in range(3)]
            concurrent.futures.wait(futures)

        final_value = const.get()
        assert isinstance(final_value, int)

    def test_singleton_access_across_threads(self):
        results = []

        def thread_worker(worker_id: int):
            local_const = Constant(f"initial_{worker_id}", "thread_singleton_test")
            results.append((worker_id, id(local_const), local_const.value))

        threads = []
        for i in range(5):
            thread = threading.Thread(target=thread_worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        instance_ids = [result[1] for result in results]
        values = [result[2] for result in results]

        assert len(set(instance_ids)) == 1
        assert all(value == "initial_0" for value in values)


class TestConstantAtomicOperations:
    def test_atomic_increment(self):
        counter = Constant(0, "atomic_counter")

        def increment_worker():
            for _ in range(100):
                current = counter.get()
                counter.set(current + 1)

        threads = []
        for _ in range(3):
            thread = threading.Thread(target=increment_worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert counter.get() == 300

    def test_atomic_list_operations(self):
        list_const = Constant([], "atomic_list")

        def append_worker(worker_id: int):
            for i in range(10):
                current_list = list_const.get().copy()
                current_list.append(f"worker_{worker_id}_item_{i}")
                list_const.set(current_list)

        threads = []
        for i in range(3):
            thread = threading.Thread(target=append_worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        final_list = list_const.get()
        assert len(final_list) == 30

    def test_property_setter_atomicity(self):
        const = Constant("initial", "property_atomic")

        def property_worker(worker_id: int):
            for i in range(50):
                const.value = f"worker_{worker_id}_value_{i}"

        threads = []
        for i in range(2):
            thread = threading.Thread(target=property_worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        final_value = const.value
        assert isinstance(final_value, str)
        assert final_value.startswith("worker_")


class TestConstantTypeHints:
    def test_string_type_hint(self):
        const: Constant[str] = Constant("test", "type_str")

        assert const.get() == "test"
        const.set("updated")
        assert const.value == "updated"

    def test_list_type_hint(self):
        const: Constant[List[int]] = Constant([1, 2, 3], "type_list")

        assert const.get() == [1, 2, 3]
        const.set([4, 5, 6])
        assert const.value == [4, 5, 6]

    def test_dict_type_hint(self):
        const: Constant[Dict[str, int]] = Constant({"a": 1}, "type_dict")

        assert const.get() == {"a": 1}
        const.set({"b": 2, "c": 3})
        assert const.value == {"b": 2, "c": 3}


class TestConstantEdgeCases:
    def test_none_default_value(self):
        const = Constant(None, "none_test")

        assert const.get() is None
        const.set("not_none")
        assert const.value == "not_none"

    def test_empty_string_identifier(self):
        const1 = Constant("value1", "")
        const2 = Constant("value2", "")

        assert const1 is const2
        assert const1.value == "value1"

    def test_numeric_identifier_as_string(self):
        const1 = Constant("value1", "123")
        const2 = Constant("value2", "123")

        assert const1 is const2
        assert const1.value == "value1"

    def test_complex_nested_data(self):
        complex_data = {
            "users": [
                {"id": 1, "name": "Alice", "settings": {"theme": "dark"}},
                {"id": 2, "name": "Bob", "settings": {"theme": "light"}},
            ],
            "config": {"version": "1.0", "features": ["auth", "notifications"]},
        }

        const = Constant(complex_data, "complex_test")

        assert const.get() == complex_data

        updated_data = complex_data.copy()
        updated_data["config"]["version"] = "1.1"
        const.set(updated_data)

        assert const.value["config"]["version"] == "1.1"

    def test_mutable_default_isolation(self):
        default_list = [1, 2, 3]
        const1 = Constant(default_list, "mutable_test1")
        const2 = Constant(default_list, "mutable_test2")

        assert const1 is not const2

        const1.set([4, 5, 6])

        assert const1.value == [4, 5, 6]
        assert const2.value == [1, 2, 3]


class TestConstantEnvironmentVariables:
    def test_string_from_environment(self):
        with mock.patch.dict(os.environ, {"TEST_STRING": "from_env"}):
            const = Constant("default", "env_str_test", env_var="TEST_STRING")
            assert const.value == "from_env"

    def test_string_fallback_to_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            const = Constant("default_value", "env_str_fallback", env_var="MISSING_VAR")
            assert const.value == "default_value"

    def test_integer_from_environment(self):
        with mock.patch.dict(os.environ, {"TEST_INT": "42"}):
            const = Constant(0, "env_int_test", env_var="TEST_INT")
            assert const.value == 42
            assert isinstance(const.value, int)

    def test_integer_fallback_to_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            const = Constant(100, "env_int_fallback", env_var="MISSING_INT")
            assert const.value == 100

    def test_integer_invalid_conversion_fallback(self):
        with mock.patch.dict(os.environ, {"TEST_INT": "not_a_number"}):
            const = Constant(999, "env_int_invalid", env_var="TEST_INT")
            assert const.value == 999

    def test_float_from_environment(self):
        with mock.patch.dict(os.environ, {"TEST_FLOAT": "3.14159"}):
            const = Constant(0.0, "env_float_test", env_var="TEST_FLOAT")
            assert const.value == 3.14159
            assert isinstance(const.value, float)

    def test_boolean_true_values_from_environment(self):
        true_values = ["true", "True", "TRUE", "1", "yes", "Yes", "on", "On"]
        for i, true_val in enumerate(true_values):
            with mock.patch.dict(os.environ, {"TEST_BOOL": true_val}):
                const = Constant(False, f"env_bool_true_{i}", env_var="TEST_BOOL")
                assert const.value is True

    def test_boolean_false_values_from_environment(self):
        false_values = ["false", "False", "FALSE", "0", "no", "No", "off", "Off", "anything_else"]
        for i, false_val in enumerate(false_values):
            with mock.patch.dict(os.environ, {"TEST_BOOL": false_val}):
                const = Constant(True, f"env_bool_false_{i}", env_var="TEST_BOOL")
                assert const.value is False

    def test_list_from_environment_comma_separated(self):
        with mock.patch.dict(os.environ, {"TEST_LIST": "item1, item2, item3"}):
            const = Constant([], "env_list_test", env_var="TEST_LIST")
            assert const.value == ["item1", "item2", "item3"]

    def test_list_from_environment_empty_string(self):
        with mock.patch.dict(os.environ, {"TEST_LIST": ""}):
            const = Constant(["default"], "env_list_empty", env_var="TEST_LIST")
            assert const.value == []

    def test_list_from_environment_single_item(self):
        with mock.patch.dict(os.environ, {"TEST_LIST": "single_item"}):
            const = Constant([], "env_list_single", env_var="TEST_LIST")
            assert const.value == ["single_item"]

    def test_dict_from_environment_json(self):
        with mock.patch.dict(os.environ, {"TEST_DICT": '{"key": "value", "number": 42}'}):
            const = Constant({}, "env_dict_test", env_var="TEST_DICT")
            assert const.value == {"key": "value", "number": 42}

    def test_dict_from_environment_invalid_json_fallback(self):
        with mock.patch.dict(os.environ, {"TEST_DICT": "not_valid_json"}):
            default_dict = {"default": "value"}
            const = Constant(default_dict, "env_dict_invalid", env_var="TEST_DICT")
            assert const.value == default_dict

    def test_none_default_with_environment(self):
        with mock.patch.dict(os.environ, {"TEST_NONE": "some_value"}):
            const = Constant(None, "env_none_test", env_var="TEST_NONE")
            assert const.value == "some_value"

    def test_none_default_without_environment(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            const = Constant(None, "env_none_fallback", env_var="MISSING_VAR")
            assert const.value is None

    def test_environment_variable_singleton_behavior(self):
        with mock.patch.dict(os.environ, {"SINGLETON_TEST": "env_value"}):
            const1 = Constant("default", "env_singleton", env_var="SINGLETON_TEST")
            const2 = Constant("different_default", "env_singleton", env_var="SINGLETON_TEST")

            assert const1 is const2
            assert const1.value == "env_value"
            assert const2.value == "env_value"

    def test_environment_variable_with_manual_override(self):
        with mock.patch.dict(os.environ, {"OVERRIDE_TEST": "from_env"}):
            const = Constant("default", "env_override", env_var="OVERRIDE_TEST")
            assert const.value == "from_env"

            # Manual override should work
            const.set("manually_set")
            assert const.value == "manually_set"

    def test_custom_type_from_environment(self):
        # For unsupported types, should return the string value
        class CustomType:
            def __init__(self, value):
                self.value = value

        custom_default = CustomType("default")
        with mock.patch.dict(os.environ, {"CUSTOM_TEST": "string_value"}):
            const = Constant(custom_default, "env_custom", env_var="CUSTOM_TEST")
            assert const.value == "string_value"  # Should be the string, not CustomType

    def test_environment_variable_type_consistency(self):
        # Test that the same env var consistently converts to the expected type
        with mock.patch.dict(os.environ, {"CONSISTENT_TEST": "123"}):
            int_const = Constant(0, "env_int_consistent", env_var="CONSISTENT_TEST")
            str_const = Constant("", "env_str_consistent", env_var="CONSISTENT_TEST")
            float_const = Constant(0.0, "env_float_consistent", env_var="CONSISTENT_TEST")

            assert int_const.value == 123
            assert isinstance(int_const.value, int)

            assert str_const.value == "123"
            assert isinstance(str_const.value, str)

            assert float_const.value == 123.0
            assert isinstance(float_const.value, float)

    def test_timedelta_from_environment(self):
        with mock.patch.dict(os.environ, {"TEST_TIMEDELTA": "3600"}):
            const = Constant(timedelta(seconds=0), "env_timedelta_test", env_var="TEST_TIMEDELTA")
            assert const.value == timedelta(seconds=3600)
            assert isinstance(const.value, timedelta)

    def test_timedelta_invalid_conversion_fallback(self):
        with mock.patch.dict(os.environ, {"TEST_TIMEDELTA": "not_a_number"}):
            default_td = timedelta(minutes=5)
            const = Constant(default_td, "env_timedelta_invalid", env_var="TEST_TIMEDELTA")
            assert const.value == default_td

    def test_multiple_environment_variable_instances(self):
        # Test that different instances with same env var but different identifiers
        # still read from the environment
        with mock.patch.dict(os.environ, {"SHARED_ENV": "shared_value"}):
            const1 = Constant("default1", "instance1", env_var="SHARED_ENV")
            const2 = Constant("default2", "instance2", env_var="SHARED_ENV")

            assert const1.value == "shared_value"
            assert const2.value == "shared_value"
            assert const1 is not const2  # Different instances

    def test_environment_variable_with_spaces(self):
        with mock.patch.dict(os.environ, {"TEST_SPACES": "  value with spaces  "}):
            const = Constant("", "env_spaces", env_var="TEST_SPACES")
            assert const.value == "  value with spaces  "  # Preserves spaces for strings

    def test_list_with_spaces_in_items(self):
        with mock.patch.dict(os.environ, {"TEST_LIST_SPACES": "item 1, item 2, item 3"}):
            const = Constant([], "env_list_spaces", env_var="TEST_LIST_SPACES")
            assert const.value == ["item 1", "item 2", "item 3"]

    def test_empty_environment_variable(self):
        with mock.patch.dict(os.environ, {"TEST_EMPTY": ""}):
            # String should return empty string
            str_const = Constant("default", "env_empty_str", env_var="TEST_EMPTY")
            assert str_const.value == ""

            # List should return empty list
            list_const = Constant(["default"], "env_empty_list", env_var="TEST_EMPTY")
            assert list_const.value == []

    def test_environment_variable_thread_safety(self):
        results = []

        def create_const_worker(worker_id: int):
            with mock.patch.dict(os.environ, {"THREAD_TEST": f"value_{worker_id}"}):
                # Each thread sets a different env value
                const = Constant("default", f"thread_env_{worker_id}", env_var="THREAD_TEST")
                results.append((worker_id, const.value))

        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_const_worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Each thread should get its own value
        for worker_id, value in results:
            assert value == f"value_{worker_id}"

    def test_complex_json_from_environment(self):
        complex_json = {"nested": {"array": [1, 2, 3], "string": "value", "bool": True}, "list": ["a", "b", "c"]}
        json_str = '{"nested": {"array": [1, 2, 3], "string": "value", "bool": true}, "list": ["a", "b", "c"]}'

        with mock.patch.dict(os.environ, {"TEST_COMPLEX_JSON": json_str}):
            const = Constant({}, "env_complex_json", env_var="TEST_COMPLEX_JSON")
            assert const.value == complex_json

    def test_unicode_from_environment(self):
        with mock.patch.dict(os.environ, {"TEST_UNICODE": "Hello 世界 🌍"}):
            const = Constant("", "env_unicode", env_var="TEST_UNICODE")
            assert const.value == "Hello 世界 🌍"

    def test_numeric_string_not_converted_for_string_type(self):
        with mock.patch.dict(os.environ, {"TEST_NUMERIC_STR": "123"}):
            const = Constant("", "env_numeric_str", env_var="TEST_NUMERIC_STR")
            assert const.value == "123"
            assert isinstance(const.value, str)

    def test_boolean_edge_cases(self):
        # Test empty string for boolean
        with mock.patch.dict(os.environ, {"TEST_BOOL_EMPTY": ""}):
            const = Constant(True, "env_bool_empty", env_var="TEST_BOOL_EMPTY")
            assert const.value is False  # Empty string should be False

        # Test numeric strings other than "1" for boolean
        with mock.patch.dict(os.environ, {"TEST_BOOL_NUM": "123"}):
            const = Constant(True, "env_bool_num", env_var="TEST_BOOL_NUM")
            assert const.value is False  # Only "1" should be True

    def test_dict_with_single_quotes_fallback(self):
        # JSON requires double quotes, single quotes should fail
        with mock.patch.dict(os.environ, {"TEST_DICT_SINGLE": "{'key': 'value'}"}):
            default = {"default": "dict"}
            const = Constant(default, "env_dict_single", env_var="TEST_DICT_SINGLE")
            assert const.value == default  # Should fallback due to invalid JSON

    def test_list_with_json_array_format(self):
        # List type should parse comma-separated, not JSON arrays
        with mock.patch.dict(os.environ, {"TEST_LIST_JSON": '["a", "b", "c"]'}):
            const = Constant([], "env_list_json", env_var="TEST_LIST_JSON")
            # Should treat the whole thing as one item since it's not comma-separated
            assert const.value == ['["a", "b", "c"]']

    def test_whitespace_only_environment_variable(self):
        with mock.patch.dict(os.environ, {"TEST_WHITESPACE": "   \t\n   "}):
            # String should preserve whitespace
            str_const = Constant("default", "env_whitespace_str", env_var="TEST_WHITESPACE")
            assert str_const.value == "   \t\n   "

            # List should return empty list
            list_const = Constant(["default"], "env_whitespace_list", env_var="TEST_WHITESPACE")
            assert list_const.value == []


class TestConstantIntegration:
    def test_singleton_with_env_var_consistency(self):
        # Create multiple constants with same identifier but different env vars
        with mock.patch.dict(os.environ, {"ENV1": "value1", "ENV2": "value2"}):
            const1 = Constant("default", "shared_id", env_var="ENV1")
            const2 = Constant("default", "shared_id", env_var="ENV2")

            # Should be same instance, first env var wins
            assert const1 is const2
            assert const1.value == "value1"
            assert const2.value == "value1"

    def test_env_var_change_after_initialization(self):
        # Environment variable changes after initialization should not affect value
        with mock.patch.dict(os.environ, {"CHANGE_TEST": "initial"}):
            const = Constant("default", "change_test", env_var="CHANGE_TEST")
            assert const.value == "initial"

            # Change environment variable
            os.environ["CHANGE_TEST"] = "changed"

            # Value should remain the same (captured at initialization)
            assert const.value == "initial"

    def test_concurrent_initialization_with_env_vars(self):
        results = []
        barrier = threading.Barrier(3)

        def init_worker(worker_id: int):
            barrier.wait()  # Ensure all threads start at same time
            with mock.patch.dict(os.environ, {"CONCURRENT_TEST": f"worker_{worker_id}"}):
                const = Constant("default", "concurrent_init", env_var="CONCURRENT_TEST")
                results.append((worker_id, const.value))

        threads = []
        for i in range(3):
            thread = threading.Thread(target=init_worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All should have the same value (from whichever thread won the race)
        values = [r[1] for r in results]
        assert len(set(values)) == 1
        assert values[0].startswith("worker_")

    def test_env_var_with_type_hint_mismatch(self):
        # Type hint doesn't affect runtime behavior
        with mock.patch.dict(os.environ, {"TYPE_HINT_TEST": "string_value"}):
            # Declare as int but env var is string
            const: Constant[int] = Constant(0, "type_hint_test", env_var="TYPE_HINT_TEST")
            # Should fall back to default since conversion fails
            assert const.value == 0

    def test_special_characters_in_env_var_name(self):
        # Test with valid env var names containing underscores, numbers
        with mock.patch.dict(os.environ, {"TEST_VAR_123": "special_value"}):
            const = Constant("default", "special_env", env_var="TEST_VAR_123")
            assert const.value == "special_value"

    def test_very_long_environment_value(self):
        long_value = "x" * 10000
        with mock.patch.dict(os.environ, {"LONG_TEST": long_value}):
            const = Constant("", "long_env", env_var="LONG_TEST")
            assert const.value == long_value
            assert len(const.value) == 10000

    def test_mixed_type_operations_with_env_vars(self):
        with mock.patch.dict(os.environ, {"MIXED_INT": "42", "MIXED_STR": "hello"}):
            int_const = Constant(0, "mixed_int", env_var="MIXED_INT")
            str_const = Constant("", "mixed_str", env_var="MIXED_STR")

            # Update int constant
            int_const.set(100)
            assert int_const.value == 100

            # String constant remains unchanged
            assert str_const.value == "hello"

    def test_float_precision_from_environment(self):
        with mock.patch.dict(os.environ, {"FLOAT_PRECISION": "3.141592653589793"}):
            const = Constant(0.0, "float_precision", env_var="FLOAT_PRECISION")
            assert const.value == 3.141592653589793
            assert str(const.value) == "3.141592653589793"

    def test_negative_numbers_from_environment(self):
        with mock.patch.dict(os.environ, {"NEGATIVE_INT": "-42", "NEGATIVE_FLOAT": "-3.14"}):
            int_const = Constant(0, "negative_int", env_var="NEGATIVE_INT")
            float_const = Constant(0.0, "negative_float", env_var="NEGATIVE_FLOAT")

            assert int_const.value == -42
            assert float_const.value == -3.14

    def test_list_with_empty_items(self):
        with mock.patch.dict(os.environ, {"LIST_EMPTY_ITEMS": "a,,b,,c"}):
            const = Constant([], "list_empty_items", env_var="LIST_EMPTY_ITEMS")
            assert const.value == ["a", "", "b", "", "c"]

    def test_zero_values_from_environment(self):
        with mock.patch.dict(os.environ, {"ZERO_INT": "0", "ZERO_FLOAT": "0.0"}):
            int_const = Constant(99, "zero_int", env_var="ZERO_INT")
            float_const = Constant(99.9, "zero_float", env_var="ZERO_FLOAT")

            assert int_const.value == 0
            assert float_const.value == 0.0
