import datetime

import fitbit2oscar.time_helpers
from fitbit2oscar.handlers import DataHandler
from fitbit2oscar.config import Config, SleepConfig, VitalsConfig, SleepKeys


class TakeoutHandler(DataHandler):
    """Handler for Google Takeout data files"""

    def _build_glob_pattern(self, data_type: str, filetype: str) -> str:
        """Build the glob pattern from data type and file type"""
        return f"{data_type}*.{filetype}"

    def get_timezone(self) -> datetime.timezone | None:
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
    glob="sleep-",
    filetype="json",
    dir="Global Export Data",
    keys=takeout_sleep_keys,
)

takeout_vitals_config = VitalsConfig(
    timestamp="dateTime",
    spo2_key="value.spo2",
    bpm_key="value.bpm",
    spo2_glob="spo2-",
    bpm_glob="heart_rate-",
    spo2_filetype="csv",
    bpm_filetype="json",
    spo2_dir="Oxygen Saturation (SpO2)",
    bpm_dir="Global Export Data",
)

takeout_config = Config(
    required_fields=["data", "dateofSleep", "levels"],
    profile_path=["Your Profile", "Profile.csv"],
    sleep=takeout_sleep_config,
    vitals=takeout_vitals_config,
)
