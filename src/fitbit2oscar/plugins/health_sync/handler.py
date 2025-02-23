from fitbit2oscar import time_helpers
from fitbit2oscar.handlers import DataHandler
from fitbit2oscar._enums import DateFormat
from fitbit2oscar.exceptions import FitbitConverterValueError
from fitbit2oscar.config import (
    Config,
    Resolver,
    SleepConfig,
    SleepKeys,
    VitalsConfig,
)
from fitbit2oscar.plugins.health_sync import extract


class HealthSyncHandler(DataHandler):
    package: str = "health_sync"

    def _build_glob_pattern(
        self,
        data_type: str,
        filetype: str,
    ) -> str:
        """
        Generate filename from data type, date string format.

        Used to create glob patterns for Health Sync data files using one of the
        date formats defined in DateFormat.

        Args:
            data_type (str): Type of data.
            filetype (str): File type. Expected to be "csv".

        Returns:
            str: Generated filename in format:
                "{data_type} {date_format} {suffix}.{filetype}"

        Raises:
            FitbitConverterValueError: If date_type is not a valid DateFormat.
        """
        suffix = "Fitbit"
        try:
            date_type = self.args.date_format
            date_format = DateFormat[date_type]
            return (
                f"Sleep ?? ?? ?? {suffix}.{filetype}"
                if data_type == "Sleep"
                else f"{data_type} {date_format} {suffix}.{filetype}"
            )
        except KeyError:
            raise FitbitConverterValueError(
                f"Invalid date format '{date_type}'"
            )

    def _get_timezone(self) -> None:
        self.timezone = time_helpers.get_local_timezone()


datetime_format = "%Y.%m.%d %H:%M:%S"
date_format = "%Y.%m.%d"
time_format = "%H:%M"


vitals_config = VitalsConfig(
    timestamp="Date",
    spo2="Oxygen saturation",
    bpm="Heart rate",
    spo2_glob="Oxygen saturation",
    bpm_glob="Heart rate",
    spo2_filetype="csv",
    bpm_filetype="csv",
    spo2_dir="Health Sync Oxygen Saturation",
    bpm_dir="Health Sync Heart rate",
)


sleep_keys = SleepKeys(
    timestamp="Date",
    start_time="Time",
    duration="Duration in seconds",
    sleep_stages="Sleep stage",
)


resolver = Resolver()


sleep_config = SleepConfig(
    dir="Health Sync Sleep",
    glob="Sleep",
    filetype="csv",
    keys=sleep_keys,
    sleep_transformations={
        "timestamp": lambda entry: time_helpers.format_timestamp(
            entry[0][sleep_keys["timestamp"]], date_format
        ),
        "start_time": lambda entry: entry[0][sleep_keys["start_time"]],
        "stop_time": lambda entry: extract.calculate_stop_time(
            entry, datetime_format
        ),
        "duration": lambda entry: time_helpers.calculate_duration(
            time_helpers.convert_timestamp(
                resolver.resolve("start_time"),
                timestamp_format=datetime_format,
            ),
            resolver.resolve(entry, "stop_time"),
        ),
        "levels": lambda entry: extract.process_sleep_data(
            entry, resolver.resolve(entry, "duration")
        ),
        "wake_after_sleep_onset_duration": lambda entry: resolver.resolve(
            entry, "levels"
        )["summary"]["wake"]["minutes"],
        "sleep_efficiency": lambda entry: resolver.resolve(
            entry,
            ("wake_after_sleep_onset_duration")
            / resolver.resolve(entry, "duration"),
        )
        * 100,
    },
    resolver=resolver,
)

health_sync_config = Config(
    use_seconds=False, sleep=sleep_config, vitals=vitals_config
)
