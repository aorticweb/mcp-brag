from embedder.text import TextBatch


class Vectorizer:
    def vectorize(self, batch: TextBatch):
        """Vectorize a batch of text and set embedding vectors in place.

        Args:
            batch (TextBatch): batch of text input to vectorize
        """
        raise NotImplementedError()

    def free(self):
        """
        Free the vectorizer resources
        """
        pass
