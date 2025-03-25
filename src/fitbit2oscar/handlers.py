import argparse
import datetime

from collections.abc import Generator
from pathlib import Path
from typing import ClassVar

from fitbit2oscar.config import Config
from fitbit2oscar.exceptions import FitbitConverterDataError


class DataHandler:
    package = "fitbit2oscar"
    _registry: ClassVar[dict[str, type["DataHandler"]]] = {}

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        _package = cls.__module__.split(".")[-2]
        if _package in cls._registry:
            raise ValueError(f"Data handler '{_package}' already exists")
        cls.package = _package
        cls._registry[_package] = cls

    def __repr__(self) -> str:
        return f"{self.__name__} handler for {self.package} input type"

    def __init__(self, args: argparse.Namespace, config: Config) -> None:
        self.args = args
        self.config = config

        self._profile_path: Path | None = None
        self._timezone: datetime.timezone | None = None
        self._paths: dict[str, Generator[Path, None, None]] = {}

    def _dirs(self) -> tuple[Path, Path, Path]:
        """The data directories."""

        def _build_path(config_path: str | None) -> Path:
            path = (
                config_path.split(".")
                if isinstance(config_path, str)
                else config_path
            )
            return self.args.fitbit_path.joinpath(*path)

        spo2_dir = _build_path(self.config.vitals["spo2"]["dir"])
        bpm_dir = _build_path(self.config.vitals["bpm"]["dir"])
        sleep_dir = _build_path(self.config.sleep.dir)

        return sleep_dir, bpm_dir, spo2_dir

    def _generate_paths(
        self, directory: Path, data_type: str, filetype: str
    ) -> Generator[Path, None, None]:
        return (
            file
            for pattern in self._build_glob_pattern(
                data_type,
                filetype,
                self.args.start_date,
                self.args.end_date,
            )
            for file in directory.glob(pattern)
        )

    def _get_paths(self) -> dict[str, Generator[Path, None, None]]:
        """
        Get lists of Paths to data files in specified format for SpO2, heart
        rate, and sleep data.
        """
        keys = [
            "sleep",
            "bpm",
            "spo2",
        ]
        data_types = [
            self.config.sleep.glob,
            self.config.vitals["bpm"]["glob"],
            self.config.vitals["spo2"]["glob"],
        ]
        filetypes = [
            self.config.sleep.filetype,
            self.config.vitals["bpm"]["filetype"],
            self.config.vitals["spo2"]["filetype"],
        ]

        for key, directory, data_type, filetype in zip(
            keys, self._dirs(), data_types, filetypes
        ):
            self._paths[f"{key}_paths"] = self._generate_paths(
                directory, data_type, filetype
            )
        return self._paths

    def _build_profile_path(self) -> Path:
        if self.config.profile_path is None:
            raise FitbitConverterDataError(
                f"There is no profile path utilized in "
                f"{self.package} input type"
            )
        return self.args.fitbit_path.joinpath(*self.config.profile_path)

    @property
    def profile_path(self) -> Path:
        if not self._profile_path:
            self._profile_path = self._build_profile_path()
        return self._profile_path

    @property
    def timezone(self) -> datetime.timezone | None:
        """The user timezone if one exists or None"""
        if not self._timezone:
            self._timezone = self._get_timezone()
        return self._timezone

    @property
    def paths(self) -> dict[str, Generator[Path, None, None]]:
        if not self._paths:
            self._paths = self._get_paths()
        if not self._paths:
            raise FitbitConverterDataError(
                f"There are no paths for {self.package} plugin"
            )
        return self._paths

    def _build_glob_pattern(
        self,
        data_type: str,
        filetype: str,
        start_date: datetime.date,
        end_date: datetime.date,
        **kwargs,
    ) -> Generator[str, None, None]:
        """Build glob patterns based on provided arguments for date range"""
        raise NotImplementedError

    def _get_timezone(self) -> str | None:
        """Get the user timezone"""
        raise NotImplementedError
