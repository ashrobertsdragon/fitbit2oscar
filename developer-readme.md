# For Developers

## Plugin System

Fitbit2Oscar supports a plugin-based architecture, allowing additional data sources to be integrated. New plugins should:

- Be placed under the `fitbit2oscar.plugins` package.
- Implement the `get_source_path` function.
- Implement the `SleepKeys` and `VitalsConfig` TypedDicts, and the `SleepConfig` and `Config` Pydantic models.
- Subclass `DataHandler` and implement necessary data extraction methods.

Once a valid plugin is added to the plugins package, it is automatically included in the input_type argument options in argparse, without requiring manual updates.

### Configuration System

Most of the heavy lifting for plugin management exists in a series of TypedDicts and Pydantic models for configuration. Simply initialize these files, and pass your `Config` instance to your `DataHandler` subclass.
When key mappings are nested, as is common when data files are JSON, the key name can be passed as a list `["level1", "key"]` or using dot notation `"level1.key"]` and the path will be automatically parsed.

```py
class Config(BaseModel):
    required_fields: list[DictNotation] = Field(default_factory=list)
    profile_path: str | None = None
    use_seconds: bool = Field(default=True)

    sleep: SleepConfig = Field(default_factory=SleepConfig)
    vitals: VitalsConfig = Field(default_factory=VitalsConfig)
```

#### Sleep Data Configuration

Sleep data configuration includes:

- Key mappings for data files.
- Necessary attributes for locating and parsing the files (directory, glob prefix, and filetype).
- Optional mapping of transformation functions.
- An optional Resolver class to manage dependencies between transformations when necessary.

The key mappings are the keys of the JSON/CSV files that contain the sleep data to find the data needed.

The transformation functions should create a dictionary with keys of "timestamp", "start_time", "stop_time", "duration", "levels", "wake_after_sleep_onset_duration", and "sleep_efficiency".

- timestamp (datetime) - The start of the sleep data collection.
- start_time/stop_time (datetime) - The first and last sleep data points.
- duration (int) - The time in seconds from the start of sleep to end of sleep.
- levels (dict) - A dictionary containing a summary and list of all of the sleep data points.
  - summary (dict) - The nested dictionaries for each sleep stage:
    - wake (dict) - The count of entries and total time spent awake
    - light (dict) - The count of entries and total time spent in light sleep
    - rem (dict) - The count of entries and total time spent in REM sleep
    - deep (dict) - The count of entries and total time spent in deep sleep
  - data (list[dict]) - A list of dictionaries of sleep stage entries
    - stage (dict) - An individual sleep stage entry with the following keys:
      - dateTime (str) - The date of the sleep entry as a string
      - level (str) - The name of the sleep stage for this period (wake/light/rem/deep)
      - seconds (int) - The duration of the sleep stage
- wake_after_sleep_onset_duration (int) - The time in minutes spent awake after first falling asleep.
- sleep_efficiency (float) - The percentage of time asleep to the total sleep duration.

```py
class SleepKeys(TypedDict):
    timestamp: str
    start_time: str
    time_awake_after_sleep_onset_duration: str | None = None
    duration: str | None = None
    stop_time: str | None = None
    sleep_efficiency: str | None = None
    levels: str | None = None

    sleep_stages: DictNotation
    summary: DictNotation | None = None


class SleepConfig(BaseModel):
    glob: str
    filetype: str
    keys: SleepKeys
    sleep_transformations: (
        dict[str, Callable[[Sleep], str | int | SleepLevels]] | None
    ) = None
    resolver: Resolver | None = None
```

#### Vitals Data Configuration

Vitals configuration includes:

- Key mappings for files of SpO2 and heart rate data
- Necessary attributes for locating and parsing the files (directory, glob prefix, and filetype)

```py
class VitalsConfig(TypedDict):
    timestamp: str
    spo2_key: str
    bpm_key: str
    spo2_glob: str
    bpm_glob: str
    spo2_filetype: str
    bpm_filetype: str
    spo2_dir: str
    bpm_dir: str
```

#### Example - Health Sync

```py
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
```

#### Example - Google Takeout

```py
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
    profile_path="Your Profile" / "Profile.csv",
    sleep=takeout_sleep_config,
    vitals=takeout_vitals_config,
)
```

### DataHandler

The DataHandler class has two methods that must be implemented in the subclass, `_build_glob_pattern` and `_get_timezone`.
The first used to generate a glob pattern for a specific data file type (SpO2, Heart rate, and Sleep data) based on how your specific data exporter saves its files. For instance, Health Sync uses a format of `{data_type} {date} Fitbit.csv`, while Google Takeout uses `{data_type}-{date}.{filetype}`. The method signature of `_build_glob_pattern` supports kwargs. If there are arguments that must be passed to the method beyond `data_type` and `filetype` that cannot enter through `self.config` or `self.args`, then you will need to override the `_get_paths` method, as well.
The second is for setting the local timezone for converting timestamps of any data that is not already stored in local time zone. In data files, you will see these with timestamps that end in a "Z" indicating the "Zulu" time zone, better known as "UTC".If your exporter provided a Fitbit profile file, the user timezone will be in listed in there in a format such as "America/Denver". There are functions in the `time_helpers` module that may be used for converting this into a datetime timezone object, as well as a function to retrieve the system time zone, that should work for most systems.

*Note: `time_helpers.get_timezone` depends on IANA and Microsoft Time Zone Index databases, which are provided in a `tz_data` directory in the project. These files will be updated periodically. Eventually, scripts will perform this action automatically for the repository.

#### Example

```py
class TakeoutHandler(DataHandler):
    """Handler for Google Takeout data files"""

    def _build_glob_pattern(self, data_type: str, filetype: str) -> str:
        """Build the glob pattern from data type and file type"""
        return f"{data_type}*.{filetype}"

    def get_timezone(self) -> datetime.timezone | None:
        """Get the user timezone from Fitbit profile CSV"""
        return fitbit2oscar.time_helpers.get_timezone_from_profile(
            self.config.profile_path
        )
```

## TODO

- Automated updating of IANA and MS TZI databases.
- Test coverage.
- Documentation beyond docstrings and README.
- Plugin registration.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for discussion.
