from fitbit2oscar.handlers import DataHandler
from fitbit2oscar.config import Config, SleepConfig, VitalsConfig, SleepKeys


class TakeoutHandler(DataHandler):
    package = "takeout"

    def _build_glob_pattern(self, data_type: str, filetype: str) -> str:
        """Build the glob pattern from data type and file type"""
        return f"{data_type}*.{filetype}"

    def get_paths(self) -> None:
        """
        Get lists of Paths to data files in specified format for SpO2, heart
        rate, and sleep data.
        """
        keys = ["spo2", "bpm", "sleep"]
        data_types = [
            self.config.vitals.spo2_glob,
            self.config.vitals.bpm_glob,
            self.config.sleep.glob,
        ]
        filetypes = [
            self.config.vitals.spo2_filetype,
            self.config.vitals.bpm_filetype,
            self.config.sleep.filetype,
        ]

        for key, directory, data_type, filetype in zip(
            keys, self._dirs(), data_types, filetypes
        ):
            pattern = self._build_glob_pattern(data_type, filetype)
            self.paths[f"{key}_paths"] = directory.glob(pattern)


takeout_sleep_keys = SleepKeys(
    timestamp="dateOfSleep",
    duration="duration",
    start_time="startTime",
    stop_time="endTime",
    wake_after_sleep_onset_duration="minutesAwake",
    sleep_efficiency="efficiency",
    sleep_stages="levels.data",
    summary=["levels.summary"],
)

takeout_sleep_config = SleepConfig(
    glob="sleep-", filetype="json", keys=takeout_sleep_keys
)

takeout_vitals_config = VitalsConfig(
    timestamp="dateTime",
    spo2="value.spo2",
    bpm="value.bpm",
    spo2_glob="spo2-",
    bpm_glob="heart-rate-",
    spo2_filetype="csv",
    bpm_filetype="json",
)

takeout_config = Config(
    required_fields=["data", "dateofSleep", "levels"],
    profile_path="Your Profile" / "Profile.csv",
    sleep=takeout_sleep_config,
    vitals=takeout_vitals_config,
)
