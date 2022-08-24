# type: ignore

"""
This file contains the configuration for the alab_management package.
It will read from a yaml file to get all the configurations.

An example of the yaml file is as follows:

.. code-block:: yaml

  [general]
  working_dir = "."
  name = 'default_lab'

  [mongodb]
  host = 'localhost'
  port = 27017
  username = ''
  password = ''

  [rabbitmq]
  host = "localhost"
  port = 5672

"""

import os
from pathlib import Path
from types import MappingProxyType as FrozenDict
from typing import Any, Dict
from monty.design_patterns import singleton
import toml


def froze_config(config_: Dict[str, Any]) -> FrozenDict:
    """
    Convert the config dict to frozen config

    Args:
        config_: the dict of config data

    Returns:
        frozen_config, which is not allowed to modify
    """

    def _froze_collection(collection_or_element):
        """
        Convert a list to tuple, a dict to frozen_dict recursively
        """
        if isinstance(collection_or_element, list):
            return tuple(
                _froze_collection(element) for element in collection_or_element
            )
        if isinstance(collection_or_element, dict):
            return FrozenDict(
                {k: _froze_collection(v) for k, v in collection_or_element.items()}
            )

        return collection_or_element

    return _froze_collection(config_)


@singleton
class AlabConfig:
    """
    Class used for storing all the config data
    """

    def __init__(self):
        """
        Load a immutable toml config file from `config_path`
        """
        config_path = os.getenv("ALAB_CONFIG", None)

        if config_path is None:
            config_path = "config.toml"

        with open(config_path, "r", encoding="utf-8") as f:
            _config = toml.load(f)

        self._path = Path(config_path).absolute()
        self._config = froze_config(_config)

    def __getitem__(self, item):
        return self._config.__getitem__(item)

    def __str__(self):
        return self._config.__repr__()

    def __repr__(self):
        return self.__str__()

    def __hash__(self):  # type: ignore
        return self._config.__hash__()

    @property
    def path(self) -> Path:
        """
        The absolute path to the config file
        """
        return self._path
