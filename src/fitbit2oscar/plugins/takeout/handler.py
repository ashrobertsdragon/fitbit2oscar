import datetime
from collections.abc import Generator

import fitbit2oscar.time_helpers
from fitbit2oscar.handlers import DataHandler
from fitbit2oscar.config import (
    BPMConfig,
    Config,
    SleepConfig,
    SleepKeys,
    SpO2Config,
    VitalsConfig,
)


class TakeoutHandler(DataHandler):
    """Handler for Google Takeout data files"""

    def _build_glob_pattern(
        self,
        data_type: str,
        filetype: str,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> Generator[str, None, None]:
        """Build the glob pattern from data type and file type for the given date range"""
        glob_date = start_date
        while glob_date <= end_date:
            date_str = glob_date.strftime("%Y-%m-%d")
            yield f"{data_type}*-*{date_str}.{filetype}"
            glob_date += datetime.timedelta(days=1)

    def _get_timezone(self) -> datetime.timezone | None:
        """Get the user timezone from Fitbit profile CSV"""
        return fitbit2oscar.time_helpers.get_timezone_from_profile(
            self.profile_path
        )


takeout_sleep_keys = SleepKeys(
    timestamp="dateOfSleep",
    duration="duration",
    start_time="startTime",
    stop_time="endTime",
    wake_after_sleep_onset_duration="minutesAwake",
    sleep_efficiency="efficiency",
    levels="levels",
    sleep_stages="levels.data",
    summary="levels.summary",
)

takeout_sleep_config = SleepConfig(
    glob="sleep",
    filetype="json",
    dir="Global Export Data",
    date_format="%Y-%m-%d",
    keys=takeout_sleep_keys,
)

takeout_spo2_config = SpO2Config(
    timestamp="timestamp",
    key="value.spo2",
    glob="Minute SpO2",
    filetype="csv",
    dir="Oxygen Saturation (SpO2)",
)

takeout_bpm_config = BPMConfig(
    timestamp="dateTime",
    key="value.bpm",
    glob="heart_rate",
    filetype="json",
    dir="Global Export Data",
)
takeout_vitals_config = VitalsConfig(
    spo2=takeout_spo2_config,
    bpm=takeout_bpm_config,
)

takeout_config = Config(
    required_fields=["data", "dateofSleep", "levels"],
    profile_path=["Your Profile", "Profile.csv"],
    csv_timestamp_format="%Y-%m-%d %H:%M:%S",
    json_timestamp_format="%m/%d/%y %H:%M:%S",
    sleep=takeout_sleep_config,
    vitals=takeout_vitals_config,
)
