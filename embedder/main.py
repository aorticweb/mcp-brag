import asyncio
import os

from common.config.env import Env
from common.log import get_logger
from embedder.embed import get_embedder

logger = get_logger(__name__)


async def main():
    """
    Main entry point for the embedder service
    """
    # init env
    Env(os.environ.get("EMBEDDER_CONFIG_PATH"), True)
    embedder = get_embedder()
    logger.debug("Generated embedder")
    while True:
        embedder.iter()


if __name__ == "__main__":
    asyncio.run(main())
