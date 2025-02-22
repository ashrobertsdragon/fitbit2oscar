import argparse
import importlib
from pathlib import Path
from collections.abc import Generator

from fitbit2oscar.config import Config
from fitbit2oscar.exceptions import FitbitConverterDataError
from fitbit2oscar._types import VitalsData, SleepEntry


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
        return f"{cls.__name__} handler for {cls.package} input type"

    def __init__(self, args: argparse.Namespace, config: Config) -> None:
        self.args = args
        self.config = config
        package = (
            f"{DataHandler.package}.{self.package}"
            if issubclass(self.__class__, DataHandler)
            else self.package
        )
        self.extractor_module: importlib.ModuleType = importlib.import_module(
            f"{package}.extract"
        )

        self.paths: dict[str, list[Path]] = {
            "sleep_paths": [],
            "sp02_paths": [],
            "bpm_paths": [],
        }

    @property
    def profile_path(self) -> Path:
        if self.config.profile_path is None:
            raise FitbitConverterDataError(
                f"There is no profile path utilized in "
                f"{self.package} input type"
            )
        return self.args.fitbit_path / self._walk_paths(
            self.config.profile_path
        )

    @staticmethod
    def _walk_paths(paths: list[str] | str):
        return paths if isinstance(paths, str) else "/".join(paths)

    def _build_glob_pattern(self, **kwargs) -> str:
        """Build glob pattern based on provided arguments"""
        raise NotImplementedError

    def _dirs(self) -> tuple[Path, Path, Path]:
        """Get paths and timezone."""
        spo2_dir = self.args.fitbit_path / self._parse_dict_notation(
            self.config.vitals.spo2_dir
        )
        bpm_dir = self.args.fitbit_path / self._parse_dict_notation(
            self.config.vitals.bpm_dir
        )
        sleep_dir = self.args.fitbit_path / self._parse_dict_notation(
            self.config.sleep.dir
        )
        return spo2_dir, bpm_dir, sleep_dir

    def get_paths(self) -> None:
        """Get list of paths for files for SpO2, heart rate, and sleep data"""
        raise NotImplementedError

    def parse_data(
        self,
    ) -> tuple[
        Generator[VitalsData, None, None],
        Generator[VitalsData, None, None],
        Generator[SleepEntry, None, None],
    ]:
        return self.extractor_module.extract_data(
            self.paths,
            self.args.start_date,
            self.args.end_date,
        )
