import datetime
from collections.abc import Generator
from pathlib import Path

import fitbit2oscar.read_file as read_file
from fitbit2oscar.time_helpers import convert_timestamp
from fitbit2oscar._types import (
    SleepEntry,
    SleepLevels,
    SleepSummary,
    SleepData,
)


def extract_sp02_data(
    csv_rows: Generator[dict[str, str]],
) -> Generator[tuple[datetime.datetime, int], None, None]:
    """
    Extracts timestamp and sp02 values from CSV rows.

    Creates a generator of tuples containing timestamps converted from UTC and
    Sp02 values that are at least 80%, the minimum value that Fitbit reports.
    The generator discards values of "50" which are a stand-in for Fitbit
    recording that the Sp02 value was below 80%.

    Args:
        csv_rows (Generator[dict[str, str]]): Generator of CSV rows of Sp02
            data in format of {"timestamp": str, "value": str}.

    Returns:
        Generator[tuple[datetime.datetime, int], None, None]: Generator of
            tuples containing timestamp and valid sp02 values.
    """
    for row in csv_rows:
        timestamp: datetime.datetime = convert_timestamp(
            row["Date"], use_seconds=False
        )
        sp02: int = round(float(row["Oxygen Saturation"]))
        if sp02 >= 80:
            yield timestamp, sp02


def extract_bpm_data(
    csv_rows: Generator[dict[str, str]],
) -> Generator[tuple[datetime.datetime, int], None, None]:
    """
    Extracts timestamp and BPM values from CSV rows.

    Creates a generator of tuples containing timestamps converted from UTC and
    heart rate in beats per minute.

    Args:
        csv_rows (Generator[dict[str, str]]): Generator of CSV rows of heart rate
            data in format of {"Date": str, "Time": str, "Heart rate": str}.

    Returns:
        Generator[tuple[datetime.datetime, int], None, None]: Generator of
            tuples containing timestamp and valid heart rate values.
    """
    for row in csv_rows:
        timestamp: datetime.datetime = convert_timestamp(
            row["Date"], use_seconds=False
        )
        bpm: int = int(row["Heart rate"])
        yield timestamp, bpm


def is_valid_sleep_entry(
    csv_rows: list[dict[str, str]],
    start_date: datetime.date,
    end_date: datetime.date,
) -> bool:
    is_valid_start: bool = (
        start_date
        <= datetime.date.fromisoformat(csv_rows[-1]["Date"])
        <= end_date
    )

    return is_valid_start and any(
        "light in" in row["Sleep stage"] for row in csv_rows
    )


def format_timestamp(timestamp: str, timestamp_format: str) -> str:
    """Formats the timestamp for the sleep entry."""
    dt = convert_timestamp(timestamp, timestamp_format=timestamp_format)
    return dt.strftime(timestamp_format)


def calculate_stop_time(
    csv_rows: list[dict[str, str]], timestamp_format: str
) -> datetime.datetime:
    """Calculate the stop time of the sleep session."""
    stop_row = csv_rows[-1]
    dt = convert_timestamp(stop_row["Date"], timestamp_format)
    duration = int(stop_row["Duration in seconds"])
    return dt + datetime.timedelta(seconds=duration)


def calculate_duration(
    start_time: datetime.datetime, stop_time: datetime.datetime
) -> int:
    """Calculate the duration of the sleep session in seconds."""
    return int((stop_time - start_time).total_seconds())


def process_sleep_data(
    csv_rows: list[dict[str, str]],
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


def extract_sleep_data(
    csv_rows_generator: Generator[list[dict[str, str]]],
    start_date: datetime.date,
    end_date: datetime.date,
) -> Generator[SleepEntry, None, None]:
    """
    Extracts sleep data from CSV rows.

    Creates a generator of dictionaries containing timestamp, duration, levels,
    start time, stop time, wake after sleep onset duration, and sleep efficiency
    from CSV rows.

    Args:
        csv_rows_generator (Generator[list[dict[str, str]]]): Generator of CSV
            rows of sleep data in format of {"Date": str, "Time": str, "Duration
            in seconds": str, "Sleep stage": str}.
        start_date (datetime.date): The earliest date for a valid sleep entry.
        end_date (datetime.date): The latest date for a valid sleep entry.
        timezone (str): Timezone to convert timestamps to.

    Returns:
        Generator[SleepEntry, None, None]: Generator of dictionaries containing
            timestamp, duration, levels, start time, stop time, wake after sleep
            onset duration, and sleep efficiency.
    """
    datetime_format = "%Y.%m.%d %H:%M:%S"
    date_format = "%Y.%m.%d"
    time_format = "%H:%M"

    for csv_rows in csv_rows_generator:
        if not is_valid_sleep_entry(csv_rows, start_date, end_date):
            continue
        timestamp = format_timestamp(csv_rows[0]["Date"], date_format)
        start_time = csv_rows[0]["Time"]
        stop_time = calculate_stop_time(csv_rows, datetime_format)
        duration = calculate_duration(
            convert_timestamp(start_time, datetime), stop_time
        )
        levels_dict, efficiency = process_sleep_data(
            csv_rows, start_date, end_date, duration
        )

        yield {
            "timestamp": timestamp,
            "duration": duration,
            "levels": levels_dict,
            "start_time": start_time,
            "stop_time": stop_time.strftime(time_format),
            "wake_after_sleep_onset_duration": levels_dict["summary"]["wake"][
                "minutes"
            ],
            "sleep_efficiency": efficiency,
        }


def extract_sleep_health_data(
    sp02_files: list[Path],
    bpm_files: list[Path],
    timezone: str,
    start_date: datetime.date,
    end_date: datetime.date,
) -> tuple[
    dict[str, datetime.datetime | int], dict[str, datetime.datetime | int]
]:
    """
    Extracts sp02 and BPM data from CSV and JSON files.

    Creates a list of sessions, where each session is a list of dictionaries
    containing timestamp, sp02, and BPM from Fitbit data in CSV files, and
    sessions are periods of time with at least 15 minutes since the last data
    point.

    Args:
        sp02_files (list[Path]): List of paths to CSV files containing Fitbit
            sp02 data.
        bpm_files (list[Path]): List of paths to CSV files containing Fitbit
            BPM data.

    Returns:
        list[list[tuple[str, datetime.datetime | int]]]: List of session lists,
            each containing tuples containing Sp02 and heart rate for
            given timestamp.
    """
    sp02_data = {
        timestamp: sp02
        for sp02_file in sp02_files
        for timestamp, sp02 in extract_sp02_data(
            read_file.read_csv_file(sp02_file)
        )
        if start_date < timestamp.date() < end_date
    }
    bpm_data = {
        timestamp: bpm
        for bpm_file in bpm_files
        for timestamp, bpm in extract_bpm_data(
            read_file.read_csv_file(bpm_file)
        )
        if start_date < timestamp.date() < end_date
    }

    return sp02_data, bpm_data


def create_csv_generator(
    sleep_files: list[Path],
) -> Generator[list[dict[str, str]], None, None]:
    yield (read_file.read_csv_file(sleep_file) for sleep_file in sleep_files)


def extract_data(
    sp02_files: list[Path],
    bpm_files: list[Path],
    sleep_files: list[Path],
    timezone: str,
    start_date: datetime.date,
    end_date: datetime.date,
) -> tuple[
    dict[str, datetime.datetime | int],
    dict[str, str | int],
    Generator[SleepEntry, None, None],
]:
    sp02_data, bpm_data = extract_sleep_health_data(
        sp02_files, bpm_files, start_date, end_date
    )

    sleep_data = extract_sleep_data(
        create_csv_generator(sleep_files), start_date, end_date
    )
    return sp02_data, bpm_data, sleep_data
