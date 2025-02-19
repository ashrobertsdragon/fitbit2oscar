from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Generic, TypeAlias, TypeVar, NamedTuple

CSVData: TypeAlias = dict[str, str]
SleepSummary: TypeAlias = dict[str, dict[str, int]]
SleepData: TypeAlias = list[dict[str, str | int]]
SleepLevels: TypeAlias = dict[str, SleepSummary | SleepData]
SleepEntry: TypeAlias = dict[str, str | int | SleepLevels]

SleepHealthData: TypeAlias = tuple[datetime, int, int]

Sleep = TypeVar("Sleep", CSVData, SleepEntry)


class VitalsData(NamedTuple):
    timestamp: datetime.datetime
    data: int


@dataclass
class SleepKeys(Generic[Sleep]):
    timestamp: str
    duration: str
    start_time: str
    stop_time: str
    awake_time: str
    sleep_efficiency: str

    levels_summary: list[str] | str | None = None
    levels_data: list[str] | str | None = None


@dataclass
class SourceFormat(Generic[Sleep]):
    sleep_keys: SleepKeys[Sleep] = field(default_factory=SleepKeys)
    transforms: (
        dict[str, Callable[[Sleep], str | int | SleepLevels]] | None
    ) = None

    def __post_init__(self) -> None:
        if self.transforms is None:
            self.transforms = {}
