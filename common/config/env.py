import json
import os
from typing import Any, Dict, Optional

import yaml  # type: ignore

from common.log import get_logger
from common.singleton import Singleton

logger = get_logger(__name__)


class Env(metaclass=Singleton):
    _state: Dict

    def __init__(self, config_path: Optional[str] = None, update_environ: bool = False):
        """Env is a singleton that merge data from config file (json or yaml)
        and os.environ, keys will be upper-cased and values are stringified
        for os.environ consistency.

        Also backward populate config to os.environ for modules relying on it.

        Args:
            config_path (Optional[str, optional): path to json or yaml config.
                Defaults to None.
            mocked_environ (bool): whether to update os.environ with value from Env,
            If set to True, config should be flat (not nested) and all values should
            be convertable to a string. Defaults to False.
        """
        data = {}
        if config_path is not None:
            data = self.to_upper(self.read_from_file(config_path))
        self._state = {**os.environ, **data}
        if update_environ:
            os.environ.update({k: str(v) for k, v in self._state.items()})
        logger.info(f"Instantiating Env with config: {config_path}")

    def read_from_file(self, config_path: str) -> Dict:
        data = None
        with open(config_path, "r") as f:
            ctn = f.read()
            data = self.read_from_json(ctn)
            if data is not None:
                return data

            data = self.read_from_yaml(ctn)
            if data is not None:
                return data
        return {}

    def to_upper(self, data: Dict) -> Dict:
        return {str(k).upper(): str(v) for k, v in data.items()}

    def read_from_json(self, ctn: str) -> Optional[Dict]:
        try:
            return json.loads(ctn)
        except json.JSONDecodeError:
            return None

    def read_from_yaml(self, ctn: str) -> Optional[Dict]:
        # safe load should always return a dict or string
        # so no need to try catch
        rv = yaml.safe_load(ctn)
        if isinstance(rv, dict):
            return rv

        return None

    def __getitem__(self, key: str):
        return self._state[key.upper()]

    def get(self, key: str, default: Any = None):
        return self._state.get(key.upper(), default)
