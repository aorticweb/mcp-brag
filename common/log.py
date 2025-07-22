import logging
import sys


def get_logger(name: str, lvl: int = logging.DEBUG) -> logging.Logger:
    log = logging.getLogger(name)
    log.setLevel(lvl)
    if not log.hasHandlers():
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(name)s %(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        log.addHandler(handler)
    return log
