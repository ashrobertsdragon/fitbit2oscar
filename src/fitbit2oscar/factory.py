import argparse

from fitbit2oscar.handlers import DataHandler


class DataHandlerFactory:
    @staticmethod
    def create_client(
        input_type: str, args: argparse.Namespace
    ) -> DataHandler:
        try:
            return DataHandler._registry[input_type](args)
        except KeyError:
            raise ValueError(f"Invalid input type '{input_type}'")
