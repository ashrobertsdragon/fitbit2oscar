import argparse
import datetime
import re
from pathlib import Path

from fitbit2oscar.read_file import read_csv_file


def get_fitbit_path(input_path: str) -> Path:
    """Get path to Fitbit directory."""
    fitbit = Path(input_path)
    if not fitbit.exists() and fitbit.is_dir():
        raise FileExistsError(f"{input_path} is not a valid path")
    candidates = [
        fitbit / "Fitbit",
        fitbit / "Takeout" / "Fitbit",
    ]
    for path in candidates:
        if path.exists() and path.is_dir():
            return path
    raise FileExistsError(f"{input_path} is not a valid path")


def profile_path(fitbit_path: Path) -> Path:
    """Get path to profile file."""
    return fitbit_path / "Your Profile" / "Profile.csv"


def export_path(fitbit_path: Path) -> Path:
    """Get path to export data directory."""
    return fitbit_path / "Global Export Data"


def get_sleep_paths(fitbit_path: Path) -> list[Path]:
    """Get paths to sleep data JSON files."""
    return list(export_path(fitbit_path).glob("sleep-*.json"))


def get_sp02_paths(fitbit_path: Path) -> list[Path]:
    """Get paths to Sp02 data CSV files."""
    sp02 = fitbit_path / "Oxygen Saturation (SpO2)"
    return list(sp02.glob("spo2-*.csv"))


def get_bpm_paths(fitbit_path: Path) -> list[Path]:
    """Get paths to heart rate data JSON files."""
    return list(export_path(fitbit_path).glob("heart-rate-*.json"))


def get_paths(fitbit_path: str) -> tuple[list[Path], list[Path], list[Path]]:
    """Get paths to sleep, sp02, and bpm files."""
    return (
        get_sleep_paths(fitbit_path),
        get_sp02_paths(fitbit_path),
        get_bpm_paths(fitbit_path),
    )


def get_timezone(fitbit_path: Path) -> str:
    """Get timezone from profile file."""
    for row in read_csv_file(profile_path(fitbit_path)):
        timezone: str = row["timezone"]
    if not timezone:
        raise ValueError("Could not find timezone")
    return timezone


def process_date_arg(datestring: str, argtype: str) -> datetime.date:
    datematch = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", datestring)
    if datematch is None:
        raise argparse.ArgumentError(
            f"Invalid {argtype} date argument '{datestring}', must match YYYY-M-D format"
        )
    dateobj = datetime.date(
        year=int(datematch.group(1)),
        month=int(datematch.group(2)),
        day=int(datematch.group(3)),
    )
    if not (datetime.date.today() >= dateobj >= datetime.date(2010, 1, 1)):
        raise argparse.ArgumentError(
            f"Invalid {argtype} date {datestring}, must be on or before today's date and no older than 2010-01-01."
        )

    adjustments = {
        "start": lambda d: d - datetime.timedelta(days=1),
        "end": lambda d: d + datetime.timedelta(days=1),
        "file": lambda d: d,
    }
    return adjustments[argtype](dateobj)
