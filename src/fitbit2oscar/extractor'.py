import datetime
import logging
from collections.abc import Callable, Generator
from pathlib import Path

from fitbit2oscar._types import CSVData, SleepEntry, VitalsData, SourceFormat
from fitbit2oscar.time_helpers import convert_timestamp, is_valid_date

logger = logging.getLogger("fitbit2oscar")


def get_nested_value(data: dict, key_path: str | list[str]) -> str | int:
    """
    Retrieves a value from a nested dictionary using dot or bracket notation.
    """
    if "[" in key_path and "]" in key_path:
        key_path = key_path[1:-1].split("][")
    elif "." in key_path:
        key_path = key_path.split(".")

    for key in key_path:
        try:
            data = data[key]
        except (KeyError, TypeError):
            data
    result = data.keys() if isinstance(data, dict) else data
    return result


def extract_vitals_data(
    *,
    vitals_data: Generator[dict[str, str | dict[str, int]]],
    vitals_type: str,
    timestamp_key: str,
    value_key: str,
    min_valid: int,
    timezone: str | None = None,
    use_seconds: bool = True,
) -> Generator[VitalsData, None, None]:
    """
    Extracts timestamp and vitals values from CSV or JSON entries.

    Creates a generator of tuples containing timestamps converted to local
    timezone and vitals values.

    Args:
        vitals_data (Generator[dict[str, str | dict[str, int]]]): Generator
            of CSV or JSON entries of vitals data from Fitbit.
        vitals_type (str): Type of vitals data.
        timestamp_key (str): Key of timestamp in CSV or JSON entry.
        value_key (str | list[str]): Key of vitals value in CSV or JSON entry.
            Support for nested keys is provided using dot or bracket notation.
        min_valid (int): Minimum value for valid vitals data.
        timezone (str, optional): Timezone to convert timestamps to. Defaults
            to None.
        use_seconds (bool, optional): Whether to use seconds in timestamp.
            Defaults to True.

    Returns:
        Generator[tuple[datetime.datetime, int], None, None]: Generator of
            tuples containing timestamp and valid vitals values.
    """
    extracted_count = 0
    valid_count = 0
    logger.debug("Showing every 15th %s entry", vitals_type)

    for entry in vitals_data:
        timestamp: datetime.datetime = convert_timestamp(
            entry[timestamp_key], timezone, use_seconds
        )
        value: int = get_nested_value(entry, value_key)
        extracted_count += 1
        if value >= min_valid:
            valid_count += 1
            if extracted_count % 15 == 0:
                logger.debug(f"{timestamp}: {vitals_type} {value}")
            yield timestamp, value
    logger.info(
        f"Extracted {valid_count} valid {vitals_type} entries out of "
        f"{extracted_count}"
    )


def is_valid_sleep_entry(
    entry: SleepEntry | list[CSVData],
    start_date: datetime.date,
    end_date: datetime.date,
    date_field: str,
    light_check_path: str,
    required_fields: list[str] = None,
) -> bool:
    if required_fields and not all(
        field in entry for field in required_fields
    ):
        return False

    valid_date = is_valid_date(
        timestamp=entry[date_field],
        start_date=start_date,
        end_date=end_date,
    )

    light_exists = "light" in get_nested_value(entry, light_check_path)

    return valid_date and light_exists


def extract_sleep_data(
    sleep_data: Generator[SleepEntry | list[CSVData], None, None],
    start_date: datetime.date,
    end_date: datetime.date,
    required_fields: list[str],
    source_format: SourceFormat,
) -> Generator[SleepEntry, None, None]:
    for entry in sleep_data:
        if not is_valid_sleep_entry(
            entry,
            start_date,
            end_date,
            source_format.sleep_keys.timestamp,
            source_format.sleep_keys.sleep_stages,
            required_fields,
        ):
            continue
        yield {
            sleep_key: transform_func
            for sleep_key, transform_func in source_format.transforms
        }
