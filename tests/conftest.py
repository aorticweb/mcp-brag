from typing import Optional
from uuid import uuid4

import numpy as np
import pytest

from common.config.env import Env
from embedder.text import TextInput


def text_input_factory(id_value: int, vec: Optional[np.ndarray] = None) -> TextInput:
    ti = TextInput(str(uuid4()), {"id": id_value})
    if vec is not None:
        ti._vec = vec
    return ti


# We have to reset the singleton for each test :'(
@pytest.fixture(autouse=True)
def env_singleton():
    Env._instances[Env] = None
    yield


@pytest.fixture
def anyio_backend():
    return "asyncio"
