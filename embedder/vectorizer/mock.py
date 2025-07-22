from typing import Optional

import numpy as np
import torch

from common.device import best_device
from embedder.text import TextBatch
from embedder.vectorizer.interface import Vectorizer


class MockVectorizer(Vectorizer):
    __slots__ = "_device"
    _device: torch.device

    def __init__(self, device: Optional[torch.device] = None):
        """
        Initialize mock vectorizer for testing

        Args:
            device: Torch device to use (default: best available)
        """
        if device is None:
            device = best_device()

    def vectorize(self, batch: TextBatch):
        """
        Create mock vectors based on text length

        Args:
            batch: TextBatch to vectorize
        """
        batch.set_vectors(np.array([np.array([len(ti._text)] * 10) for ti in batch.inputs]))
