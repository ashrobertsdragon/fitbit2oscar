import datetime
from pathlib import Path
from collections.abc import Generator, Iterable

from fitbit2oscar._types import (
    DictNotation,
    SleepEntry,
    VitalsData,
    Sleep,
)
from fitbit2oscar.config import Config
from fitbit2oscar.read_file import read_file
from fitbit2oscar.time_helpers import convert_timestamp, is_valid_date
from fitbit2oscar._logger import logger


class FitbitExtractor:
    """Extracts and processes Fitbit data from various source formats"""

    SPO2_MIN_VALID = 75
    BPM_MIN_VALID = 50

    def __init__(self, config: Config, timezone: datetime.timezone):
        self.config = config
        self.timezone = timezone

    def get_nested_value(
        self, data: dict, key_path: DictNotation
    ) -> str | int:
        """Retrieves value from nested dictionary using dot or bracket notation"""
        if "." in key_path:
            key_path = key_path.split(".")

        for key in key_path:
            try:
                data = data[key]
            except (KeyError, TypeError):
                data
        return data.keys() if isinstance(data, dict) else data

    def is_valid_sleep_entry(
        self,
        entry: Sleep,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> bool:
        """Validates sleep entry based on format and datetime.date range"""
        if any(
            self.get_nested_value(entry, field) not in entry
            for field in self.config.required_fields
        ):
            return False

        valid_date = is_valid_date(
            timestamp=entry[self.config.vitals["timestamp"]],
            start_date=start_date,
            end_date=end_date,
        )

        light_exists = "light" in self.get_nested_value(
            entry, self.config.sleep_key.sleep_stages
        )

        return valid_date and light_exists

    def extract_vitals_data(
        self,
        vitals_data: Generator[dict, None, None],
        key: DictNotation,
        vitals_type: str,
        timestamp_format: str,
        min_valid: int,
    ) -> Generator[VitalsData, None, None]:
        """Extracts and validates vitals data"""
        extracted_count = valid_count = 0

        for entry in vitals_data:
            print(entry)
            timestamp = convert_timestamp(
                entry[self.config.vitals["timestamp"]],
                timezone=self.timezone,
                timestamp_format=timestamp_format,
                use_seconds=self.config.use_seconds,
            )
            value = self.get_nested_value(entry, key)
            extracted_count += 1

            if value >= min_valid:
                valid_count += 1
                if valid_count % 15 == 0:
                    logger.debug(f"{timestamp}: {vitals_type} {value}")
                yield timestamp, value

        logger.info(
            f"Extracted {valid_count} valid {vitals_type} entries out of "
            f"{extracted_count}"
        )

    def extract_sleep_data(
        self,
        sleep_data: Generator[Sleep, None, None],
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> Generator[SleepEntry, None, None]:
        """Extracts and validates sleep data"""
        for entry in sleep_data:
            if not self.is_valid_sleep_entry(entry, start_date, end_date):
                continue
            yield {
                sleep_key: transform_func(entry)
                for sleep_key, transform_func in self.config.sleep.sleep_transformations
            }

    def collect_vitals_data(
        self,
        vitals_files: Iterable[Path],
        start_date: datetime.datetime.date,
        end_date: datetime.datetime.date,
        vitals_key: DictNotation,
        vitals_type: str,
        timestamp_format: str,
        min_valid: int,
    ) -> Generator[VitalsData, None, None]:
        yield from (
            VitalsData(timestamp, data)
            for file in vitals_files
            for timestamp, data in self.extract_vitals_data(
                read_file(file),
                vitals_key,
                vitals_type,
                timestamp_format,
                min_valid,
            )
            if is_valid_date(timestamp.date(), start_date, end_date)
        )

    def collect_sleep_data(
        self,
        sleep_files: Iterable[Path],
        start_date: datetime.datetime.date,
        end_date: datetime.datetime.date,
    ) -> Generator[SleepEntry, None, None]:
        for file in sleep_files:
            sleep_data = list(
                read_file(file) if file.suffix == "csv" else read_file(file)
            )
            yield from self.extract_sleep_data(
                sleep_data, start_date, end_date
            )

    def extract_data(
        self,
        file_paths: dict[str, Iterable[Path]],
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> tuple[
        Generator[VitalsData, None, None],
        Generator[VitalsData, None, None],
        Generator[SleepEntry, None, None],
    ]:
        """Processes all data files and returns generators for each data type"""
        spo2_data = self.collect_vitals_data(
            file_paths["spo2_paths"],
            start_date,
            end_date,
            vitals_key=self.config.vitals["spo2_key"],
            vitals_type="SpO2",
            timestamp_format=self.config.csv_timestamp_format,
            min_valid=self.SPO2_MIN_VALID,
        )
        bpm_data = self.collect_vitals_data(
            file_paths["bpm_paths"],
            start_date,
            end_date,
            vitals_key=self.config.vitals["bpm_key"],
            vitals_type="Heart rate",
            timestamp_format=self.config.json_timestamp_format,
            min_valid=self.BPM_MIN_VALID,
        )
        sleep_data = self.collect_sleep_data(
            file_paths["sleep_paths"], start_date, end_date
        )

        return spo2_data, bpm_data, sleep_data
