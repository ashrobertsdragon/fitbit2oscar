import datetime
from collections.abc import Generator
from pathlib import Path

from fitbit2oscar import read_file
from fitbit2oscar.time_helpers import convert_timestamp
from fitbit2oscar._types import SleepEntry, VitalsData


def extract_sp02_data(
    csv_rows: Generator[dict[str, str]], timezone: str
) -> Generator[VitalsData, None, None]:
    """
    Extracts timestamp and sp02 values from CSV rows.

    Creates a generator of tuples containing timestamps converted from UTC and
    Sp02 values that are at least 80%, the minimum value that Fitbit reports.
    The generator discards values of "50" which are a stand-in for Fitbit
    recording that the Sp02 value was below 80%.

    Args:
        csv_rows (Generator[dict[str, str]]): Generator of CSV rows of Sp02
            data in format of {"timestamp": str, "value": str}.
        timezone (str): Timezone to convert timestamps to.

    Returns:
        Generator[tuple[datetime.datetime, int], None, None]: Generator of
            tuples containing timestamp and valid sp02 values.
    """
    for row in csv_rows:
        timestamp: datetime.datetime = convert_timestamp(
            row["timestamp"], timezone
        )
        sp02: int = round(float(row["value"]))
        if sp02 >= 80:
            yield timestamp, sp02


def extract_bpm_data(
    json_entries: Generator[dict[str, str | dict[str, int]]],
    timezone: str,
) -> Generator[VitalsData, None, None]:
    """
    Extracts timestamp and BPM values from JSON entries.

    Creates a generator of tuples containing timestamps converted from UTC and
    heart rate in beats per minute.

    Args:
        json_entries (Generator[dict[str, str | dict[str, int]]]): Generator
            of JSON entries of heart rate data in format of
            {"dateTime": str, "value": dict[str, int]}. Value dictionary
            contains beats per minute recorded at timestamp and Fitbit
            confidence level at the reading.
        timezone (str): Timezone to convert timestamps to.

    Returns:
        Generator[tuple[datetime.datetime, int], None, None]: Generator of
            tuples containing timestamp and valid heart rate values.
    """
    for entry in json_entries:
        timestamp: datetime.datetime = convert_timestamp(
            entry["dateTime"], timezone
        )
        bpm: int = entry["value"]["bpm"]
        yield timestamp, bpm


def is_valid_sleep_entry(
    sleep_entry: SleepEntry,
    start_date: datetime.date,
    end_date: datetime.date,
) -> bool:
    """
    Validates a sleep entry based on format, date range, and presence of light
    sleep data.

    Args:
        sleep_entry (SleepEntry): A dictionary containing sleep data with
            keys for 'data', 'dateOfSleep', and 'levels'.
        start_date (datetime.date, optional): The earliest date for a valid
            sleep entry. Defaults to the earliest representable date.
        end_date (datetime.date, optional): The latest date for a valid sleep
            entry. Defaults to today's date.

    Returns:
        bool: True if the sleep entry is valid, False otherwise.
    """

    def is_valid_format() -> bool:
        return all(
            key in sleep_entry for key in ("data", "dateOfSleep", "levels")
        )

    is_valid_start: bool = (
        start_date
        <= datetime.date.fromisoformat(sleep_entry["dateOfSleep"])
        <= end_date
    )

    return (
        is_valid_format()
        and is_valid_start
        and "light" in sleep_entry["levels"]["summary"].keys()
    )


def extract_sleep_data(
    json_entries: Generator[SleepEntry],
    start_date: datetime.date,
    end_date: datetime.date,
) -> Generator[SleepEntry, None, None]:
    """
    Extracts timestamp, duration, levels, start time, stop time, wake after
    sleep onset duration, and sleep efficiency from JSON entries.

    Creates a generator of dictionaries containing the relevant sleep data
    from JSON entries.

    Args:
        json_entries (Generator[SleepEntry]): Generator of JSON entries of
            sleep data in format of: {
                "data": list[dict[str, str | int]],
                "dateOfSleep": str,
                "levels": dict[str, dict[str, dict[str, int]]]
            }

    Returns:
        Generator[SleepEntry, None, None]: Generator of dictionaries
            containing timestamp, duration, levels, start time, stop time,
            wake after sleep onset duration, and sleep efficiency.
    """

    for entry in json_entries:
        if is_valid_sleep_entry(entry, start_date, end_date):
            entry_dict: SleepEntry = {
                "timestamp": entry["dateOfSleep"],
                "duration": entry["duration"],
                "levels": entry["levels"],
                "start_time": entry["startTime"],
                "stop_time": entry["endTime"],
                "wake_after_sleep_onset_duration": entry["minutesAwake"],
                "sleep_efficiency": entry["efficiency"],
            }

            yield entry_dict


def collect_sp02_data(
    sp02_files: list[Path],
    timezone: str,
    start_date: datetime.date,
    end_date: datetime.date,
) -> Generator[VitalsData, None, None]:
    """Yield SpO2 data from CSV files for a given date range."""
    yield (
        (timestamp, sp02)
        for sp02_file in sp02_files
        for timestamp, sp02 in extract_sp02_data(
            read_file.read_csv_file(sp02_file),
            timezone,
        )
        if start_date < timestamp.date() < end_date
    )


def collect_bpm_data(
    bpm_files: list[Path],
    timezone: str,
    start_date: datetime.date,
    end_date: datetime.date,
) -> Generator[VitalsData, None, None]:
    """Yield BPM data from JSON files for a given date range."""
    yield (
        (timestamp, bpm)
        for bpm_file in bpm_files
        for timestamp, bpm in extract_bpm_data(
            read_file.read_json_file(bpm_file),
            timezone,
        )
        if start_date < timestamp.date() < end_date
    )


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
    """
    Extract sleep and vitals data from CSV and JSON files.

    Args:
        sp02_files (list[Path]): List of paths to CSV files containing SpO2
            data.
        bpm_files (list[Path]): List of paths to JSON files containing BPM
            data.
        sleep_files (list[Path]): List of paths to JSON files containing sleep
            data.
        start_date (datetime.date): The earliest date for a valid sleep entry.
        end_date (datetime.date): The latest date for a valid sleep entry.

    Returns:
        tuple[
            Generator[VitalsData, None, None],
            Generator[VitalsData, None, None],
            Generator[SleepEntry, None, None]
        ]: Tuple of generators containing sleep and vitals data.
    """
    sp02_data: Generator[VitalsData[datetime.datetime | int], None, None] = (
        collect_sp02_data(sp02_files, start_date, end_date)
    )
    bpm_data: Generator[VitalsData[datetime.datetime | int], None, None] = (
        collect_bpm_data(bpm_files, start_date, end_date)
    )
    sleep_data = extract_sleep_data(
        read_file.read_json_file(sleep_files), start_date, end_date
    )
    return sp02_data, bpm_data, sleep_data
