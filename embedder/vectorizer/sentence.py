from typing import Optional

import mlx.core as mx
import torch
from sentence_transformers import SentenceTransformer

from common import log
from common.device import best_device
from embedder.text import TextBatch
from embedder.vectorizer.interface import Vectorizer
from embedder.constants import EMBEDDING_SIZE

logger = log.get_logger(__name__)


class SentenceTransformerVectorizer(Vectorizer):
    __slots__ = "_model", "_device", "_model_path"

    _model: Optional[SentenceTransformer]
    _device: torch.device
    _model_path: str

    def __init__(self, model_path: str, device: Optional[torch.device] = None):
        """
        Initialize sentence transformer vectorizer

        Args:
            model_path: Path to the sentence transformer model
            device: Torch device to use (default: best available)
        """
        if device is None:
            device = best_device()
        self._device = device
        self._model = None
        self._model_path = model_path

    def _load_model(self):
        """
        Lazy load the sentence transformer model
        """
        if self._model is None:
            logger.debug(f"Loading vectorizermodel {self._model_path} on device {self._device}")
            self._model = SentenceTransformer(
                self._model_path,
                device=self._device,
                tokenizer_kwargs={"use_fast": True, "clean_up_tokenization_spaces": True},
                truncate_dim=EMBEDDING_SIZE.value,
            )
            self._model.eval()  # make sure we're in inference mode, not training

    def free(self):
        """
        Free model resources and clear cache
        """
        if self._model is not None:
            logger.debug(f"Freeing vectorizer model {self._model_path} on device {self._device}")
            if self._device.type == "mps":
                mx.clear_cache()

            del self._model
            self._model = None

    def vectorize(self, batch: TextBatch):
        """
        Convert text batch to embeddings using sentence transformer

        Args:
            batch: TextBatch to vectorize
        """
        self._load_model()
        embeddings = self._model.encode(batch.to_text_array(), batch_size=min(1000, len(batch)), device=self._device)  # type: ignore
        batch.set_vectors(embeddings)
