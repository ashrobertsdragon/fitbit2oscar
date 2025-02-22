from collections.abc import Callable

from pydantic import BaseModel, Field

from fitbit2oscar._types import DictNotation, Sleep, SleepLevels


class SleepKeys(BaseModel):
    timestamp: str
    start_time: str
    time_awake_after_sleep_onset_duration: str
    duration: str | None = None
    stop_time: str | None = None
    sleep_efficiency: str | None = None

    sleep_stages: DictNotation
    summary: DictNotation | None = None


class SleepConfig(BaseModel):
    glob: str
    filetype: str
    keys: SleepKeys
    sleep_transformations: (
        dict[str, Callable[[Sleep], str | int | SleepLevels]] | None
    ) = None

    def __post_init__(self) -> None:
        if self.sleep_transformations is None:
            self.sleep_transformations = {
                key: value for key, value in self.keys.items()
            }


class VitalsConfig(BaseModel):
    timestamp: str
    spo2: str
    bpm: str
    spo2_glob: str
    bpm_glob: str
    spo2_filetype: str
    bpm_filetype: str


class Config(BaseModel):
    required_fields: list[DictNotation] = Field(default_factory=list)
    timezone: str | None = None
    profile_path: str | None = None
    use_seconds: bool = Field(default=True)

    sleep: SleepConfig = Field(default_factory=SleepConfig)
    vitals: VitalsConfig = Field(default_factory=VitalsConfig)
