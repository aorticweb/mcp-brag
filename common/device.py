from common.log import get_logger

logger = get_logger(__name__)


def best_device():
    """In the following order mps (m1 macs), cuda, cpu (default)
    return the first available device detected

    Returns:
        torch.device: the detected torch device
    """
    import torch

    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    logger.warning("Using torch cpu device, performance might be impacted")
    return torch.device("cpu")
