import argparse
import datetime

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
        self._paths: dict[str, list[Path]] = {}

    def _dirs(self) -> tuple[Path, Path, Path]:
        """The data directories."""

        def _build_path(config_path: str | None) -> Path:
            path = (
                config_path.split(".")
                if isinstance(config_path, str)
                else config_path
            )
            return self.args.fitbit_path.joinpath(*path)

        spo2_dir = _build_path(self.config.vitals["spo2_dir"])
        bpm_dir = _build_path(self.config.vitals["bpm_dir"])
        sleep_dir = _build_path(self.config.sleep.dir)

        return spo2_dir, bpm_dir, sleep_dir

    def _get_paths(self) -> None:
        """
        Get lists of Paths to data files in specified format for SpO2, heart
        rate, and sleep data.
        """
        keys = ["spo2", "bpm", "sleep"]
        data_types = [
            self.config.vitals["spo2_glob"],
            self.config.vitals["bpm_glob"],
            self.config.sleep.glob,
        ]
        filetypes = [
            self.config.vitals["spo2_filetype"],
            self.config.vitals["bpm_filetype"],
            self.config.sleep.filetype,
        ]

        for key, directory, data_type, filetype in zip(
            keys, self._dirs(), data_types, filetypes
        ):
            pattern = self._build_glob_pattern(data_type, filetype)
            self._paths[f"{key}_paths"] = directory.glob(pattern)

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
    def paths(self) -> dict[str, list[str]]:
        if not self._paths:
            self._paths = self._get_paths()
        return self._paths

    def _build_glob_pattern(
        self, data_type: str, filetype: str, **kwargs
    ) -> str:
        """Build glob pattern based on provided arguments"""
        raise NotImplementedError

    def _get_timezone(self) -> str | None:
        """Get the user timezone"""
        raise NotImplementedError
