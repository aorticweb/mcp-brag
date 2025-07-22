import numpy as np
import pytest

from embedder.embed import get_embedder
from embedder.read_write.bulk_queue import BulkQueueReadWriter
from embedder.text import TextInput
from embedder.vectorizer.mock import MockVectorizer
from tests.conftest import text_input_factory

pytestmark = pytest.mark.anyio


async def test_async_pool_embedder_mock_vectorizer():
    # type checks
    e = get_embedder(transport=BulkQueueReadWriter(), vectorizer=MockVectorizer())
    assert isinstance(e._transport, BulkQueueReadWriter)
    assert isinstance(e._vectorizer, MockVectorizer)

    # write input to queue
    text_input = text_input_factory(0)
    e._transport._read_queue.put_nowait(text_input)

    # run one iteration of the embedder
    e.iter()

    # check what was written to the write queue
    received: TextInput = e._transport._write_queue.get_many(1)[0]
    assert received is not None
    assert received._text == text_input._text
    assert received._meta["id"] == text_input._meta["id"]
    assert np.all(received._vec == np.array([len(text_input._text)] * 10))
