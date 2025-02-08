import argparse
import datetime
import importlib
from pathlib import Path


class DataHandler:
    package = "fitbit2oscar"
    _registry = {}

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._registry[cls.package] = cls

    @classmethod
    def create_client(
        cls, input_type: str, args: argparse.Namespace
    ) -> "DataHandler":
        try:
            return cls._registry[input_type](args)
        except KeyError:
            raise ValueError(f"Invalid input type '{input_type}'")

    def __repr__(cls) -> str:
        return cls.__name__

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        package = (
            f"{DataHandler.package}.{self.package}"
            if issubclass(self.__class__, DataHandler)
            else self.package
        )
        self.helpers: importlib.ModuleType = importlib.import_module(
            f"{package}.helpers"
        )
        self.parser: importlib.ModuleType = importlib.import_module(
            f"{package}.parser"
        )

        self.paths: dict[str, list[Path]] = {
            "sleep_paths": [],
            "sp02_paths": [],
            "bpm_paths": [],
        }
        self.timezone: datetime.timezone | None = None

    def get_paths_and_timezone(self) -> None:
        """Get paths and timezone."""
        raise NotImplementedError

    def parse_data(
        self,
    ) -> tuple[list[dict[str, datetime.datetime | int]], list]:
        viatom_data = self.parser.get_sleep_health_data(
            self.paths["sp02_paths"],
            self.paths["bpm_paths"],
            self.timezone,
            self.args.start_date,
            self.args.end_date,
        )
        dreem_data = self.parser.get_sleep_data(
            self.paths["sleep_paths"],
            self.timezone,
            self.args.start_date,
            self.args.end_date,
        )
        return viatom_data, dreem_data


class TakeoutHandler(DataHandler):
    package = "takeout"

    def get_paths_and_timezone(self):
        (
            self.paths["sleep_paths"],
            self.paths["sp02_paths"],
            self.paths["bpm_paths"],
        ) = self.helpers.get_paths(self.args.fitbit_path)
        self.timezone = self.helpers.get_timezone(self.args.fitbit_path)


class HealthSyncHandler(DataHandler):
    package: str = "health_sync"

    def get_paths_and_timezone(self):
        (
            self.paths["sleep_paths"],
            self.paths["sp02_paths"],
            self.paths["bpm_paths"],
        ) = self.helpers.get_paths(
            self.args.fitbit_path, self.args.date_format
        )
        self.timezone = self.helpers.get_timezone()
