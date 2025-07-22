import numpy as np

from embedder.read_write.bulk_queue import BulkQueueReadWriter
from embedder.text import TextBatch
from tests.conftest import text_input_factory


def test_read_empty_queue():
    """Test reading from an empty queue."""
    reader = BulkQueueReadWriter()
    batch = reader.read()
    assert len(batch) == 0


def test_read_single_item():
    """Test reading a single item from the queue."""
    reader = BulkQueueReadWriter()
    test_input = text_input_factory(1)
    reader._read_queue.put_nowait(test_input)

    batch = reader.read()
    assert len(batch) == 1
    assert batch.inputs[0]._text == test_input._text
    assert batch.inputs[0]._meta == test_input._meta


def test_read_multiple_items():
    """Test reading multiple items from the queue."""
    reader = BulkQueueReadWriter()
    test_inputs = [text_input_factory(i) for i in range(5)]

    reader._read_queue.put_many(test_inputs)

    batch = reader.read()
    assert len(batch) == 5
    for i, input in enumerate(batch.inputs):
        assert input._text == test_inputs[i]._text
        assert input._meta == test_inputs[i]._meta


def test_write_and_read_queue():
    """Test writing to queue and then reading from it."""
    reader_writer = BulkQueueReadWriter()

    # Create a batch with vectors
    test_inputs = [text_input_factory(i, np.array([i] * 10)) for i in range(3)]
    batch = TextBatch(test_inputs)

    # Write the batch
    reader_writer.write(batch)

    # Read items from write queue
    items = reader_writer._write_queue.get_many(3)
    batch = TextBatch(items)

    assert len(batch) == 3

    for i, item in enumerate(batch.inputs):
        assert item._text == test_inputs[i]._text
        assert item._meta == test_inputs[i]._meta
        assert np.array_equal(item._vec, test_inputs[i]._vec)


def test_batch_size_limit():
    """Test that reading respects the batch size limit."""
    reader = BulkQueueReadWriter()
    # making read and write queue identical for testing purposes
    reader._write_queue = reader._read_queue

    # Override batch size for test
    reader._batch_size = 3

    # Add more items than the batch size
    test_inputs = [text_input_factory(i) for i in range(5)]
    reader.write(TextBatch(test_inputs))

    # First read should return batch_size items
    batch1 = reader.read()
    assert len(batch1) == 3

    # Second read should return remaining items
    batch2 = reader.read()
    assert len(batch2) == 2
