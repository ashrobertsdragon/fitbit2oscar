import datetime
from collections.abc import Generator
from pathlib import Path
from typing import TypeAlias
from zoneinfo import ZoneInfo

import fitbit2oscar.read_file as read_file


SleepSummary: TypeAlias = dict[str, dict[str, int]]
SleepData: TypeAlias = list[dict[str, str | int]]
SleepLevels: TypeAlias = dict[str, SleepSummary | SleepData]
SleepEntry: TypeAlias = dict[str, str | int | SleepLevels]


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


def extract_sleep_time_data(
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
            entry_dict = {
                "timestamp": entry["dateOfSleep"],
                "duration": entry["duration"],
                "levels": entry["levels"],
                "start_time": entry["startTime"],
                "stop_time": entry["endTime"],
                "wake_after_sleep_onset_duration": entry["minutesAwake"],
                "sleep_efficiency": entry["efficiency"],
            }

            yield entry_dict


def convert_time_data(minutes: int) -> str:
    """Converts time in minutes to a string in HH:MM:SS format."""
    hours, mins = divmod(minutes, 60)
    return f"{hours:02d}:{mins:02d}:00"


def generate_hypnogram(data: SleepData) -> list[str]:
    """
    Generates a hypnogram from sleep data.

    This function takes a list of sleep data entries, each consisting of a
    timestamp and a sleep level with its duration in seconds, and converts it
    into a hypnogram. A hypnogram is a list of sleep stages, where each stage
    is repeated for every 30-second interval within its duration. The sleep
    stages are mapped to specific labels: "WAKE", "REM", "Light", and "Deep".

    Args:
        data (SleepData): A list of dictionaries, each containing a "level"
            key indicating the sleep stage and a "seconds" key representing
            the duration of that stage.

    Returns:
        list[str]: A list of sleep stage names corresponding to each 30-second
        interval in the input data.
    """

    levels = {"wake": "WAKE", "rem": "REM", "light": "Light", "deep": "Deep"}
    sleep_stages = []

    sleep_stages.extend(
        [levels[stage["level"]]] * (stage["seconds"] // 30)
        for stage in data
        if stage["level"] in levels
    )

    return sleep_stages


def parse_sleep_data(
    sleep_data: SleepEntry,
) -> dict[str, datetime.datetime | int]:
    """
    Parses sleep data into a structured dictionary format.

    This function takes raw sleep data from a Fitbit sleep entry and converts
    it into a dictionary with detailed sleep metrics. The returned dictionary
    includes sleep onset duration, wake after sleep onset duration, durations
    for light, deep, and REM sleep, number of awakenings, sleep efficiency,
    start and stop times, and a hypnogram representing sleep stages.

    Args:
        sleep_data (SleepEntry): A dictionary containing raw sleep data with
            keys for 'duration', 'levels', 'startTime', 'endTime',
            'wake_after_sleep_onset_duration', and 'sleep_efficiency'.

    Returns:
        dict[str, str | int]: A dictionary containing parsed
            sleep metrics, including durations in HH:MM:SS format, start and
            stop times, and a hypnogram as a list of sleep stage names.
    """

    return {
        "start_time": sleep_data["start_time"],
        "stop_time": sleep_data["stop_time"],
        "sleep_onset_duration": convert_time_data(
            sleep_data["duration"] / 60000
        ),
        "light_sleep_duration": convert_time_data(
            sleep_data["levels"]["summary"]["light"]["minutes"]
        ),
        "deep_sleep_duration": convert_time_data(
            sleep_data["levels"]["summary"]["deep"]["minutes"]
        ),
        "rem_sleep_duration": convert_time_data(
            sleep_data["levels"]["summary"]["rem"]["minutes"]
        ),
        "wake_after_sleep_onset_duration": convert_time_data(
            sleep_data["wake_after_sleep_onset_duration"]
        ),
        "number_awakenings": sleep_data["levels"]["summary"]["wake"]["count"],
        "sleep_efficiency": sleep_data["sleep_efficiency"],
        "hypnogram": f"[{','.join(generate_hypnogram(sleep_data["levels"]["data"]))}]",
    }


def extract_sleep_data(
    sleep_files: list[Path],
    timezone: str,
    start_date: datetime.date = datetime.date.fromordinal(1),
    end_date: datetime.date = datetime.date.today(),
) -> Generator[dict[str, str | int], None, None]:
    """
    Extracts sleep data from a list of Fitbit sleep JSON files and timezone.

    Args:
        sleep_files (list[Path]): List of JSON files containing sleep data.
        timezone (str): Timezone to convert timestamps to.

    Returns:
        list[dict[str, str | int]]: List of sleep data
            dictionaries containing sleep onset duration, wake after sleep
            onset duration, light sleep duration, deep sleep duration, REM
            sleep duration, number of awakenings, sleep efficiency, start
            time, stop time, and hypnogram.
    """

    yield from (
        parse_sleep_data(
            extract_sleep_time_data(json_entry), timezone, start_date, end_date
        )
        for json_entry in read_file.read_json_file(sleep_files)
    )


def extract_sleep_health_data(
    sp02_files: list[Path],
    bpm_files: list[Path],
    timezone: str,
    start_date: datetime.date = datetime.date.fromordinal(1),
    end_date: datetime.date = datetime.date.today(),
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
        list[list[tuple[str, datetime.datetime | int]]]: List of session lists,
            each containing tuples containing Sp02 and heart rate for
            given timestamp.
    """
    sp02_data = {
        timestamp: sp02
        for sp02_file in sp02_files
        for timestamp, sp02 in extract_sp02_data(
            read_file.read_csv_file(sp02_file),
            timezone,
        )
        if start_date < timestamp.date() < end_date
    }
    bpm_data = {
        timestamp: bpm
        for bpm_file in bpm_files
        for timestamp, bpm in extract_bpm_data(
            read_file.read_json_file(bpm_file),
            timezone,
        )
        if start_date < timestamp.date() < end_date
    }

    sessions = []
    session = []

    prev_timestamp = None

    for timestamp in sorted(
        set(sp02_data.keys()).intersection(bpm_data.keys())
    ):
        session.append((timestamp, sp02_data[timestamp], bpm_data[timestamp]))
        if (
            prev_timestamp
            and prev_timestamp + datetime.timedelta(minutes=session_split)
            < timestamp
        ):
            sessions.append(session)
            session = []
        prev_timestamp = timestamp

    return sessions
