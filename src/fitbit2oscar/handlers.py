import argparse
import datetime
import importlib
from pathlib import Path

import fitbit2oscar.time_helpers as time_helpers


class DataHandler:
    package = "fitbit2oscar"
    _registry = {}

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        package = cls.package
        if package in cls._registry:
            raise ValueError(f"Data handler '{package}' already exists")
        cls._registry[cls.package] = cls

    def __repr__(cls) -> str:
        return f"{cls.__name__} handler for {cls.package}input type"

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        package = (
            f"{DataHandler.package}.{self.package}"
            if issubclass(self.__class__, DataHandler)
            else self.package
        )
        self.paths_module: importlib.ModuleType = importlib.import_module(
            f"{package}.paths"
        )
        self.extractor_module: importlib.ModuleType = importlib.import_module(
            f"{package}.extract"
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
        sp02_data, bpm_data = self.extractor_module.extract_sleep_health_data(
            self.paths["sp02_paths"],
            self.paths["bpm_paths"],
            self.timezone,
            self.args.start_date,
            self.args.end_date,
        )
        sleep_data = self.extractor_module.extract_sleep_data(
            self.paths["sleep_paths"],
            self.timezone,
            self.args.start_date,
            self.args.end_date,
        )
        return sp02_data, bpm_data, sleep_data


class TakeoutHandler(DataHandler):
    package = "takeout"

    def get_paths_and_timezone(self):
        (
            self.paths["sleep_paths"],
            self.paths["sp02_paths"],
            self.paths["bpm_paths"],
        ) = self.paths_module.get_paths(self.args.fitbit_path)
        self.timezone = time_helpers.get_timezone_from_profile(
            self.args.fitbit_path
        )


class HealthSyncHandler(DataHandler):
    package: str = "health_sync"

    def get_paths_and_timezone(self):
        (
            self.paths["sleep_paths"],
            self.paths["sp02_paths"],
            self.paths["bpm_paths"],
        ) = self.paths_module.get_paths(
            self.args.fitbit_path, self.args.date_format
        )
        self.timezone = time_helpers.get_local_timezone()
