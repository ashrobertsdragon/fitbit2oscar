import datetime
from collections.abc import Generator
from pathlib import Path
from zoneinfo import ZoneInfo

import fitbit2oscar.read_file as read_file


def convert_timestamp(
    timestamp: str,
    timezone: str,
    timestamp_format: str = "%Y-%m-%dT%H:%M:%S",
) -> datetime.datetime:
    """
    Parse timestamp and attach timezone info, converting from UTC if needed.

    Args:
        timestamp (str): Timestamp in ISO 8601 format, optionally ending with
            'Z' for UTC.
        timezone (str): Timezone to convert timestamps to
            (e.g., 'America/New_York').
        time_string_format (str, optional): Format of the timestamp string.
            Defaults to "%Y-%m-%dT%H:%M:%S".

    Returns:
        datetime.datetime: Timezone-aware datetime object in the target
            timezone.
    """
    dt = datetime.datetime.strptime(
        timestamp.removesuffix("Z"), timestamp_format
    )
    tz = ZoneInfo(timezone)

    return (
        dt.replace(tzinfo=datetime.timezone.utc).astimezone(tz)
        if timestamp.endswith("Z")
        else dt.replace(tzinfo=tz)
    )


def extract_sp02_data(
    csv_rows: Generator[dict[str, str]], timezone: str
) -> Generator[tuple[datetime.datetime, int], None, None]:
    """
    Extracts timestamp and sp02 values from CSV rows.

    Creates a generator of tuples containing timestamps converted from UTC and
    sp02 values in range 61-99.

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
        if 61 <= sp02 <= 99:
            yield timestamp, sp02


def extract_bpm_data(
    json_entries: Generator[dict[str, str | dict[str, int]]],
    timezone: str,
) -> Generator[tuple[datetime.datetime, int], None, None]:
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


def extract_sleep_data(
    sp02_files: list[Path],
    bpm_files: list[Path],
    timezone: str,
    session_split: int = 15,
) -> list[dict[str, datetime.datetime | int]]:
    """
    Extracts sp02 and BPM data from CSV and JSON files.

    Creates a list of sessions, where each session is a list of dictionaries
    containing timestamp, sp02, and BPM from Fitbit data in CSV and JSON
    files, and sessions are periods of time with at least 15 minutes since the
    last data point.

    Args:
        sp02_files (list[Path]): List of paths to CSV files containing Fitbit
            sp02 data.
        bpm_files (list[Path]): List of paths to JSON files containing Fitbit
            BPM data.
        timezone (str): Timezone to convert timestamps to.

    Returns:
        list[list[dict[str, datetime.datetime | int]]]: List of session lists,
            each containing dictionaries containing Sp02 and heart rate for
            given timestamp.
    """
    sp02_data = {
        timestamp: sp02
        for sp02_file in sp02_files
        for timestamp, sp02 in extract_sp02_data(
            read_file.read_csv_file(sp02_file),
            timezone,
        )
    }
    bpm_data = {
        timestamp: bpm
        for bpm_file in bpm_files
        for timestamp, bpm in extract_bpm_data(
            read_file.read_json_file(bpm_file),
            timezone,
        )
    }

    sessions = []
    session = []

    prev_timestamp = None

    for timestamp in sorted(
        set(sp02_data.keys()).intersection(bpm_data.keys())
    ):
        session.append({
            "timestamp": timestamp,
            "Sp02": sp02_data[timestamp],
            "BPM": bpm_data[timestamp],
        })
        if (
            prev_timestamp
            and prev_timestamp + datetime.timedelta(minutes=session_split)
            < timestamp
        ):
            sessions.append(session)
            session = []
        prev_timestamp = timestamp

    return sessions
