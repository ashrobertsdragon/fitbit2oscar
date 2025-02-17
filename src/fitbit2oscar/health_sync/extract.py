import datetime
import logging
from collections.abc import Generator
from pathlib import Path

import fitbit2oscar.read_file as read_file
from fitbit2oscar.time_helpers import (
    calculate_duration,
    convert_timestamp,
    format_timestamp,
    is_valid_date,
)
from fitbit2oscar._types import (
    SleepEntry,
    SleepLevels,
    SleepSummary,
    SleepData,
    VitalsData,
)

logger = logging.getLogger("fitbit2oscar")


def extract_sp02_data(
    csv_rows: Generator[dict[str, str]],
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

    Returns:
        Generator[tuple[datetime.datetime, int], None, None]: Generator of
            tuples containing timestamp and valid sp02 values.
    """
    extracted_count = 0
    valid_count = 0
    logger.debug("Showing every 15th Sp02 entry")
    for row in csv_rows:
        timestamp: datetime.datetime = convert_timestamp(
            row["Date"], use_seconds=False
        )
        sp02: int = round(float(row["Oxygen Saturation"]))
        extracted_count += 1
        if sp02 >= 80:
            valid_count += 1
            if valid_count % 15 == 0:
                logger.debug(f"{timestamp}: Sp02 {sp02}")
            yield timestamp, sp02
    logger.info(
        f"Sp02 Extraction Summary: Extracted {extracted_count} entries, "
        f"{valid_count} valid entries for {timestamp.date()}."
    )


def extract_bpm_data(
    csv_rows: Generator[dict[str, str]],
) -> Generator[VitalsData, None, None]:
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
    extraction_count = 0
    logger.debug("Showing every 15th Heart rate entry")
    for row in csv_rows:
        timestamp: datetime.datetime = convert_timestamp(
            row["Date"], use_seconds=False
        )
        bpm: int = int(row["Heart rate"])
        extraction_count += 1
        if extraction_count % 15 == 0:
            logger.debug(f"{timestamp}: BPM {bpm}")
        yield timestamp, bpm

    logger.info(
        f"BPM Extraction Summary: Extracted {extraction_count} entries for "
        f"{timestamp.date()}."
    )


def is_valid_sleep_entry(
    csv_rows: list[dict[str, str]],
    start_date: datetime.date,
    end_date: datetime.date,
) -> bool:
    valid_start: bool = is_valid_date(
        timestamp=csv_rows[0]["Date"],
        start_date=start_date,
        end_date=end_date,
    )

    return valid_start and any(
        "light in" in row["Sleep stage"] for row in csv_rows
    )


def calculate_stop_time(
    csv_rows: list[dict[str, str]], timestamp_format: str
) -> datetime.datetime:
    """Calculate the stop time of the sleep session."""
    stop_row = csv_rows[-1]
    dt = convert_timestamp(stop_row["Date"], timestamp_format)
    duration = int(stop_row["Duration in seconds"])
    return dt + datetime.timedelta(seconds=duration)


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
    csv_data: Generator[list[dict[str, str]]],
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

    for csv_rows in csv_data:
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


def collect_sp02_data(
    sp02_files: list[Path], start_date: datetime.date, end_date: datetime.date
) -> Generator[VitalsData, None, None]:
    """Yield SpO2 data from CSV files for a given date range."""
    yield (
        (timestamp, sp02)
        for sp02_file in sp02_files
        for timestamp, sp02 in extract_sp02_data(
            read_file.read_csv_file(sp02_file)
        )
        if is_valid_date(timestamp.date(), start_date, end_date)
    )


def collect_bpm_data(
    bpm_files: list[Path], start_date: datetime.date, end_date: datetime.date
) -> Generator[VitalsData, None, None]:
    """Yield BPM data from CSV files for a given date range."""
    yield (
        (timestamp, bpm)
        for bpm_file in bpm_files
        for timestamp, bpm in extract_bpm_data(
            read_file.read_csv_file(bpm_file)
        )
        if is_valid_date(timestamp.date(), start_date, end_date)
    )


def collect_sleep_data(
    sleep_files: list[Path],
) -> Generator[list[dict[str, str]], None, None]:
    """Yield sleep data from CSV files."""
    yield (read_file.read_csv_file(sleep_file) for sleep_file in sleep_files)


def extract_data(
    sp02_files: list[Path],
    bpm_files: list[Path],
    sleep_files: list[Path],
    start_date: datetime.date,
    end_date: datetime.date,
) -> tuple[
    Generator[VitalsData, None, None],
    Generator[VitalsData, None, None],
    Generator[SleepEntry, None, None],
]:
    """
    Extract sleep and vitals data from CSV files.

    Args:
        sp02_files (list[Path]): List of paths to CSV files containing SpO2
            data.
        bpm_files (list[Path]): List of paths to CSV files containing BPM
            data.
        sleep_files (list[Path]): List of paths to CSV files containing sleep
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

    sleep_data: Generator[SleepEntry, None, None] = extract_sleep_data(
        collect_sleep_data(sleep_files), start_date, end_date
    )
    return sp02_data, bpm_data, sleep_data
