from collections import defaultdict
from typing import Any, DefaultDict, Dict, List, Optional
from uuid import uuid4

import numpy as np


class TextInput:
    __slots__ = "_text", "_meta", "_vec", "_source_id"
    _text: str
    _meta: Dict[str, Any]
    _source_id: Optional[str]
    _vec: Optional[np.ndarray]

    def __init__(self, text: str, metadata: Dict[str, Any], source_id: Optional[str] = None):
        """
        Initialize a text input for embedding

        Args:
            text: The text content to embed
            metadata: Additional metadata associated with the text
            source_id: Optional unique identifier for the source
        """
        self._text = text
        self._meta = metadata
        self._vec = None
        self._source_id = source_id if source_id is not None else str(uuid4())

    def __str__(self) -> str:
        """
        String representation of the text input

        Returns:
            str: The text content
        """
        return self._text


class TextBatch:
    __slots__ = "inputs"
    inputs: List[TextInput]

    def __init__(self, inputs: List[TextInput]):
        """
        Initialize a batch of text inputs

        Args:
            inputs: List of TextInput objects to batch together
        """
        self.inputs = inputs

    def to_text_array(self) -> List[str]:
        """Return text from the inputs, for vectorization.

        Returns:
            List[str]: the text string from the inputs
        """
        return [v._text for v in self.inputs]

    def set_vectors(self, vecs: np.ndarray):
        """Set embeddings for text inputs.

        Args:
            vecs (np.ndarray): vector embeddings for the values
                (output of the vectorizer)
        """
        for input, vec in zip(self.inputs, vecs):
            input._vec = vec

    def count_by_source_id(self) -> DefaultDict[Optional[str], int]:
        """
        Count text inputs grouped by source ID

        Returns:
            DefaultDict[Optional[str], int]: Count of inputs per source ID
        """
        count_by_source_id: DefaultDict[Optional[str], int] = defaultdict(int)
        for input in self.inputs:
            count_by_source_id[input._source_id] += 1
        return count_by_source_id

    def __len__(self):
        """
        Get the number of inputs in the batch

        Returns:
            int: Number of text inputs in the batch
        """
        return len(self.inputs)
