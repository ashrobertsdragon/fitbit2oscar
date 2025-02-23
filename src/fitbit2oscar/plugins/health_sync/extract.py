import datetime
import logging
from collections.abc import Generator
from fitbit2oscar.time_helpers import (
    convert_timestamp,
)
from fitbit2oscar._types import (
    SleepLevels,
    SleepSummary,
    SleepData,
    CSVData,
)

logger = logging.getLogger("fitbit2oscar")


def calculate_stop_time(
    csv_rows: Generator[CSVData], timestamp_format: str
) -> datetime.datetime:
    """Calculate the stop time of the sleep session."""
    stop_row = csv_rows[-1]
    dt = convert_timestamp(stop_row["Date"], timestamp_format)
    duration = int(stop_row["Duration in seconds"])
    return dt + datetime.timedelta(seconds=duration)


def process_sleep_data(
    csv_rows: Generator[CSVData],
    duration: int,
) -> tuple[SleepLevels, int]:
    """
    Process the sleep data and calculate sleep efficiency.

    Args:
        csv_rows (list[dict[str, str]]): List of CSV rows of sleep data in format
            of {"Date": str, "Duration in seconds": str, "Sleep stage": str}.
        duration (int): The duration of the sleep session in seconds.

    Returns:
        tuple[SleepLevels, int]: A tuple containing the sleep levels and sleep
            efficiency.
    """
    stage_data: SleepSummary = {
        "wake": {"count": 0, "time": 0},
        "light": {"count": 0, "time": 0},
        "deep": {"count": 0, "time": 0},
        "rem": {"count": 0, "time": 0},
    }

    levels_dict: SleepLevels = {"summary": {}, "data": []}
    data: SleepData = []

    for row in csv_rows:
        duration_in_seconds = int(row["Duration in seconds"])
        stage = row["Sleep stage"]

        data.append({
            "dateTime": row["Date"],
            "level": stage,
            "seconds": duration_in_seconds,
        })

        if stage in stage_data:
            stage_data[stage]["count"] += 1
            stage_data[stage]["time"] += duration_in_seconds

    levels_dict["data"] = data
    levels_dict["summary"] = {
        stage: {"count": data["count"], "minutes": data["time"] // 60}
        for stage, data in stage_data.items()
    }
    efficiency = int(stage_data["wake"]["time"] / duration * 100)

    return levels_dict, efficiency
