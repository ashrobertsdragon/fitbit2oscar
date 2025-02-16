from pathlib import Path

from fitbit2oscar._enums import DateFormat
from fitbit2oscar.exceptions import (
    FitbitConverterDataError,
    FitbitConverterValueError,
)


def generate_filename(
    data_type: str,
    date_type: str,
    suffix: str = "Fitbit",
    filetype: str = "csv",
) -> str:
    """
    Generate filename from data type, date string format.

    Used to create glob patterns for Health Sync data files using one of the
    date formats defined in DateFormat.

    Args:
        data_type (str): Type of data.
        date_type (str): Type of date format.
        suffix (str, optional): Suffix for filename. Defaults to "Fitbit".
        filetype (str, optional): File type. Defaults to "csv".

    Returns:
        str: Generated filename in format:
            "{data_type} {date_format} {suffix}.{filetype}"

    Raises:
        FitbitConverterValueError: If date_type is not a valid DateFormat.
    """
    try:
        date_format = DateFormat[date_type]
        return (
            f"Sleep {DateFormat["DAILY"]} ?? ?? ?? {suffix}.{filetype}"
            if data_type == "Sleep"
            else f"{data_type} {date_format} {suffix}.{filetype}"
        )
    except KeyError:
        raise FitbitConverterValueError(f"Invalid date format '{date_type}'")


def get_health_sync_fitbit_path(input_path: str) -> Path:
    """Get path to Fitbit directory."""
    fitbit = Path(input_path)
    if not (fitbit.exists() and fitbit.is_dir()):
        raise FitbitConverterDataError(f"{input_path} is not a valid path")
    return fitbit


def get_sleep_paths(fitbit_path: Path, fmt: str) -> list[Path]:
    """Get paths to sleep data JSON files."""
    sleep = fitbit_path / "Health Sync Sleep"
    pattern = generate_filename("Sleep", "DAILY")
    return list(sleep.glob(pattern))


def get_sp02_paths(fitbit_path: Path, fmt: str) -> list[Path]:
    """Get paths to Sp02 data CSV files."""
    sp02 = fitbit_path / "Oxygen Saturation"
    pattern = generate_filename("Oxygen saturation", fmt)
    return list(sp02.glob(pattern))


def get_bpm_paths(fitbit_path: Path, fmt: str) -> list[Path]:
    """Get paths to heart rate data JSON files."""
    bpm = fitbit_path / "Heart rate"
    pattern = generate_filename("Heart rate", fmt)
    return list(bpm.glob(pattern))


def get_paths(
    fitbit_path: str, fmt: str
) -> tuple[list[Path], list[Path], list[Path]]:
    """Get paths to sleep, sp02, and bpm files for Health Sync using a given date format."""
    return (
        get_sleep_paths(fitbit_path, fmt),
        get_sp02_paths(fitbit_path, fmt),
        get_bpm_paths(fitbit_path, fmt),
    )
