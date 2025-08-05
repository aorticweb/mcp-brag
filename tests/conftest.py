from typing import Optional
from uuid import uuid4

import numpy as np
import pytest

from embedder.text import TextInput


def text_input_factory(id_value: int, vec: Optional[np.ndarray] = None) -> TextInput:
    ti = TextInput(str(uuid4()), {"id": id_value})
    if vec is not None:
        ti._vec = vec
    return ti


@pytest.fixture
def anyio_backend():
    return "asyncio"
