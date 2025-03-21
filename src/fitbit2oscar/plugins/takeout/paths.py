from pathlib import Path

from fitbit2oscar.exceptions import FitbitConverterDataError


def verify_input_path(input_path: str) -> Path:
    """Get path to Fitbit directory."""
    fitbit = Path(input_path)
    if not fitbit.is_dir():
        raise FitbitConverterDataError(f"{input_path} is not a valid path")
    candidates = [
        fitbit / "Fitbit",
        fitbit / "Takeout" / "Fitbit",
    ]
    for path in candidates:
        if path.exists() and path.is_dir():
            return path
    raise FitbitConverterDataError(f"{input_path} is not a valid path")
