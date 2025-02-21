from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TypeAlias, TypeVar, NamedTuple

DictNotation: TypeAlias = list[str] | str

CSVData: TypeAlias = dict[str, str]
CSVRows: TypeAlias = list[CSVData]
SleepSummary: TypeAlias = dict[str, dict[str, int]]
SleepData: TypeAlias = list[dict[str, str | int]]
SleepLevels: TypeAlias = dict[str, SleepSummary | SleepData]
SleepEntry: TypeAlias = dict[str, str | int | SleepLevels]

SleepHealthData: TypeAlias = tuple[datetime, int, int]

Sleep = TypeVar("Sleep", CSVRows, SleepEntry)


class VitalsData(NamedTuple):
    timestamp: datetime.datetime
    data: int


@dataclass
class Keys:
    timestamp: str
    start_time: str
    time_awake_after_sleep_onset: str
    duration: str | None = None
    stop_time: str | None = None
    sleep_efficiency: str | None = None

    sleep_stages: DictNotation
    summary: DictNotation | None = None


@dataclass
class SleepConfig:
    keys: Keys
    sleep_transformations: (
        dict[str, Callable[[Sleep], str | int | SleepLevels]] | None
    ) = None

    def __post_init__(self) -> None:
        if self.sleep_transformations is None:
            self.sleep_transformations = {
                key: value for key, value in self.keys.items()
            }


@dataclass
class VitalsConfig:
    timestamp: str
    spo2: str
    bpm: str


@dataclass
class Config:
    required_fields: list[DictNotation] = field(default_factory=list)
    timezone: str | None = None
    use_seconds: bool = field(default=True)

    sleep: SleepConfig = field(default_factory=SleepConfig)
    vitals: VitalsConfig = field(default_factory=VitalsConfig)
