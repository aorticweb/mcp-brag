import json
import os
from typing import Optional

import dotenv
import yaml

from common.log import get_logger

logger = get_logger(__name__)


def load_env(file_path: Optional[str] = None):
    if file_path is None:
        return

    if not os.path.exists(file_path):
        logger.warning(f"Env file {file_path} does not exist")
        return

    if os.path.isdir(file_path):
        logger.warning(f"Env file {file_path} is a directory")
        return

    if file_path.endswith(".env"):
        dotenv.load_dotenv(file_path)
        return

    data = {}
    try:
        if file_path.endswith(".json"):
            with open(file_path, "r") as file:
                data = json.load(file)
        elif file_path.endswith(".yaml") or file_path.endswith(".yml"):
            with open(file_path, "r") as file:
                data = yaml.load(file, Loader=yaml.FullLoader)
        else:
            logger.warning(f"Unknown file type for file {file_path}")
            return
    except Exception as e:
        logger.warning(f"Error loading env file {file_path}: {e}")
        return

    for key, value in data.items():
        os.environ[key] = str(value)
