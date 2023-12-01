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
from typing import Any, Dict, Optional

import toml


def freeze_config(config_: Dict[str, Any]) -> FrozenDict:
    """
    Convert the config dict to frozen config.

    Args:
        config_: the dict of config data

    Returns
    -------
        frozen_config, which can not be modified
    """

    def _frozen_collection(collection_or_element):
        """Convert a list to tuple, a dict to frozen_dict recursively."""
        if isinstance(collection_or_element, list):
            return tuple(_frozen_collection(element) for element in collection_or_element)
        if isinstance(collection_or_element, dict):
            return FrozenDict({k: _frozen_collection(v) for k, v in collection_or_element.items()})

        return collection_or_element

    return _frozen_collection(config_)


# @singleton
class AlabConfig:
    """Class used for storing all the config data."""

    def __init__(self, sim_mode: Optional[bool] = None):
        """Load a immutable toml config file from `config_path`."""
        config_path = os.getenv("ALAB_CONFIG", None)

        if config_path is None:
            config_path = "config.toml"
        try:
            with open(config_path, encoding="utf-8") as f:
                _config = toml.load(f)
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"Config file was not found at {config_path}."
                "Please set your computer's environment variable 'ALAB_CONFIG' to the path to the config file. In "
                "absence of this environment variable, we assume there is a file named config.toml in the current "
                "directory."
            ) from exc

        self._path = Path(config_path).absolute()
        # self._config = freeze_config(_config)
        self._config = _config

        # Define the key and nested_key for the 'general' section
        key = "general"
        nested_key = "simulation"

        # Update the 'general' section with the new value for 'simulation' if sim_mode is provided
        if sim_mode is not None and key in self._config:
            general_section = self._config[key]
            general_section[nested_key] = sim_mode
            self.set_item(key, general_section)

            # Save the modified configuration back to the file 'config.toml'
            with open(config_path, "w", encoding="utf-8") as f:
                toml.dump(self._config, f)

            # Define the key and nested_key for the 'alarm' section
            key = "alarm"
            nested_key = ["email_password", "email_receivers", "email_sender", "slack_bot_token", "slack_channel"]

            # Open the file 'config.toml' again to read the modified configuration
            with open(config_path, encoding="utf-8") as f:
                _config = toml.load(f)

            # Update the 'alarm' section with the new value for 'email_password', 'email_receivers',
            # 'email_sender', 'slack_bot_token', 'slack_channel' if sim_mode is provided
            if sim_mode:
                email_password = ""
                email_receivers = [""]
                email_sender = ""
                slack_bot_token = ""
                slack_channel = ""
            else:
                email_password = "rjuttalfbnvquyek"
                email_receivers = [
                    "bernardus_rendy@berkeley.edu",
                ]
                email_sender = "alabmanagement@gmail.com"
                slack_bot_token = "xoxb-53032848964-4821073683568-Ccm2VwTJLbhU0reM8XENw2wr"
                slack_channel = "C04PF6C68MR"
            alarm_section = self._config[key]
            alarm_section[nested_key[0]] = email_password
            alarm_section[nested_key[1]] = email_receivers
            alarm_section[nested_key[2]] = email_sender
            alarm_section[nested_key[3]] = slack_bot_token
            alarm_section[nested_key[4]] = slack_channel
            self.set_item(key, alarm_section)
            with open(config_path, "w", encoding="utf-8") as f:
                toml.dump(self._config, f)

    def __getitem__(self, item):
        """Get the config item."""
        return self._config.__getitem__(item)

    def __str__(self):
        """Get the string representation of the config."""
        return self._config.__repr__()

    def __repr__(self):
        """Get the string representation of the config."""
        return self.__str__()

    def __hash__(self):  # type: ignore
        """Get the hash of the config."""
        return self._config.__hash__()

    def get(self, item, default=None):
        """Get the config item."""
        return self._config.get(item, default)

    def set_item(self, key, value):
        """Set a specific config item."""
        self._config[key] = value

    def __contains__(self, item):
        """Check if the config contains the item."""
        return self._config.__contains__(item)

    @property
    def path(self) -> Path:
        """The absolute path to the config file."""
        return self._path
