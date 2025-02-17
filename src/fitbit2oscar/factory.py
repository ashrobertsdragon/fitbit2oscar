import argparse
import logging

from fitbit2oscar.exceptions import FItbitConverterValueError
from fitbit2oscar.handlers import DataHandler

logger = logging.getLogger("fitbit2oscar")


class DataHandlerFactory:
    @staticmethod
    def create_client(
        input_type: str, args: argparse.Namespace
    ) -> DataHandler:
        try:
            return DataHandler._registry[input_type](args)
        except KeyError:
            logging.error(f"Invalid input type '{input_type}'")
            raise FItbitConverterValueError(
                f"Invalid input type '{input_type}'"
            )
