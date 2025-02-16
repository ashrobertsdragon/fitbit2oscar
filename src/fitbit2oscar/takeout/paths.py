from pathlib import Path

from fitbit2oscar.exceptions import FitbitConverterDataError


def get_takeout_fitbit_path(input_path: str) -> Path:
    """Get path to Fitbit directory."""
    fitbit = Path(input_path)
    if not (fitbit.exists() and fitbit.is_dir()):
        raise FitbitConverterDataError(f"{input_path} is not a valid path")
    candidates = [
        fitbit / "Fitbit",
        fitbit / "Takeout" / "Fitbit",
    ]
    for path in candidates:
        if path.exists() and path.is_dir():
            return path
    raise FitbitConverterDataError(f"{input_path} is not a valid path")


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
