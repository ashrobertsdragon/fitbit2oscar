import argparse
import importlib
import inspect
import pkgutil
from pathlib import Path
from collections.abc import Generator

from fitbit2oscar.config import Config
from fitbit2oscar.exceptions import FitbitConverterDataError
from fitbit2oscar._types import VitalsData, SleepEntry
from fitbit2oscar._logger import logger


for _, name, is_package in pkgutil.walk_packages(
    path=["fitbit2oscar.plugins"],
):
    if is_package:
        try:
            module = importlib.import_module(
                f"fitbit2oscar.plugins.{name}.handler"
            )
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, "DataHandler"):
                    globals()[name] = obj

            logger.debug(f"Plugin {name} added")
        except ModuleNotFoundError:
            pass


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

    def _profile_info(self) -> Path:
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

    def _dirs(self) -> tuple[Path, Path, Path]:
        """The data directories."""

        def _build_path(config_path: str | None) -> Path:
            if config_path:
                return self.args.fitbit_path / self._parse_dict_notation(
                    config_path
                )
            return self.args.fitbit_path

        spo2_dir = _build_path(self.config.vitals.spo2_dir)
        bpm_dir = _build_path(self.config.vitals.bpm_dir)
        sleep_dir = _build_path(self.config.sleep.dir)

        return spo2_dir, bpm_dir, sleep_dir

    def _get_paths(self) -> None:
        """
        Get lists of Paths to data files in specified format for SpO2, heart
        rate, and sleep data.
        """
        keys = ["spo2", "bpm", "sleep"]
        data_types = [
            self.config.vitals.spo2_glob,
            self.config.vitals.bpm_glob,
            self.config.sleep.glob,
        ]
        filetypes = [
            self.config.vitals.spo2_filetype,
            self.config.vitals.bpm_filetype,
            self.config.sleep.filetype,
        ]

        for key, directory, data_type, filetype in zip(
            keys, self._dirs(), data_types, filetypes
        ):
            pattern = self._build_glob_pattern(data_type, filetype)
            self.paths[f"{key}_paths"] = directory.glob(pattern)

    @property
    def timezone(self) -> str | None:
        """The user timezone if one exists or None"""
        if not self._timezone:
            self._timezone = self._get_timezone()
        return self._timezone

    @property
    def paths(self) -> dict[str, list[str]]:
        if not self._paths:
            self._paths = self._get_paths()
        return self._paths

    def parse_data(
        self,
    ) -> tuple[
        Generator[VitalsData, None, None],
        Generator[VitalsData, None, None],
        Generator[SleepEntry, None, None],
    ]:
        return self.extractor_module.extract_data(
            self.paths, self.args.start_date, self.args.end_date, self.timezone
        )

    def _build_glob_pattern(
        self, data_type: str, filetype: str, **kwargs
    ) -> str:
        """Build glob pattern based on provided arguments"""
        raise NotImplementedError

    def _get_timezone(self) -> str | None:
        """Get the user timezone"""
        raise NotImplementedError
