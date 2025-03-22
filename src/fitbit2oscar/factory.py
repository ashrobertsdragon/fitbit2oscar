import argparse
import importlib
import contextlib
import pkgutil
import sys

import fitbit2oscar.plugins
from fitbit2oscar.config import Config
from fitbit2oscar.exceptions import FitbitConverterValueError
from fitbit2oscar.handlers import DataHandler
from fitbit2oscar._logger import logger

PLUGINS_DIR = fitbit2oscar.plugins

with contextlib.suppress(ModuleNotFoundError):
    plugins = {
        name: importlib.import_module(f"{PLUGINS_DIR.__name__}.{name}.handler")
        for _, name, is_package in pkgutil.walk_packages(
            path=PLUGINS_DIR.__path__
        )
        if is_package
    }


class DataHandlerFactory:
    @staticmethod
    def create_client(
        input_type: str, args: argparse.Namespace
    ) -> DataHandler:
        plugin = plugins[input_type]
        for obj in vars(plugin).values():
            if isinstance(obj, Config):
                config = obj
                break
        else:
            logger.error(f"{input_type} is not a valid plugin")
            raise FitbitConverterValueError(
                f"{input_type} is not a valid plugin"
            )

        try:
            return DataHandler._registry[input_type](args, config)
        except (KeyError, UnboundLocalError):
            logger.error(f"Invalid input type '{input_type}'")
            raise FitbitConverterValueError(
                f"Invalid input type '{input_type}'"
            ) from None
