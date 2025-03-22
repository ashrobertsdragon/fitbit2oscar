import argparse
import importlib
import contextlib
import pkgutil

import fitbit2oscar.plugins
from fitbit2oscar.exceptions import FitbitConverterValueError
from fitbit2oscar.handlers import DataHandler
from fitbit2oscar._logger import logger


for _, name, is_package in pkgutil.walk_packages(
    path=fitbit2oscar.plugins.__path__,
):
    if is_package:
        with contextlib.suppress(ModuleNotFoundError):
            importlib.import_module(f"fitbit2oscar.plugins.{name}.handler")
            logger.debug(f"Plugin {name} added")


class DataHandlerFactory:
    @staticmethod
    def create_client(
        input_type: str, args: argparse.Namespace
    ) -> DataHandler:
        try:
            return DataHandler._registry[input_type](args)
        except KeyError:
            logger.error(f"Invalid input type '{input_type}'")
            raise FitbitConverterValueError(
                f"Invalid input type '{input_type}'"
            ) from None
