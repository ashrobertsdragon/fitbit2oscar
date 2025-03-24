from collections.abc import Callable
from typing import TypedDict, get_type_hints, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fitbit2oscar._types import DictNotation, Sleep, SleepLevels

datetime_format = "%Y.%m.%d %H:%M:%S"
date_format = "%Y.%m.%d"
time_format = "%H:%M"


class Resolver:
    _computed: dict = {}

    def resolve(self, entry: Sleep, key: str) -> str | int | SleepLevels:
        """Ensure transformation function arguments exist when called"""
        if key not in self._computed:
            self._computed[key] = self.sleep_transformations[key](entry)
        return self._computed[key]

    def clear(self) -> None:
        self._computed.clear()


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
    model_config = ConfigDict(arbitrary_types_allowed=True)

    dir: str
    glob: str
    filetype: str
    keys: SleepKeys
    sleep_transformations: (
        dict[str, Callable[[Sleep], str | int | SleepLevels]] | None
    ) = None
    resolver: Resolver | None = None

    def model_post_init(self, __context=None) -> None:
        if self.sleep_transformations is None:
            self.sleep_transformations = {
                key: lambda entry: entry[key] for key in self.keys.values()
            }

    @field_validator("keys", mode="before")
    @classmethod
    def set_default_sleep_keys(cls, keys: SleepKeys) -> SleepKeys:
        validated_keys = {
            key: (
                None
                if hasattr(key_type, "__args__")
                and type(None) in get_args(key_type)
                and key not in keys
                else keys[key]
            )
            for key, key_type in get_type_hints(SleepKeys).items()
        }
        return SleepKeys(**validated_keys)

    def _reset_before_entry(self):
        self.resolver.clear()

    def __getattr__(self, item):
        if self.resolver and item == "sleep_transformations":
            self._reset_before_entry()
        return super().__getattr__(item)


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


class Config(BaseModel):
    required_fields: list[DictNotation] = Field(default_factory=list)
    profile_path: list[str] | None = None
    use_seconds: bool = Field(default=True)
    csv_timestamp_format: str | None = None
    json_timestamp_format: str | None = None

    sleep: SleepConfig = Field(default_factory=SleepConfig)
    vitals: VitalsConfig = Field(default_factory=VitalsConfig)
