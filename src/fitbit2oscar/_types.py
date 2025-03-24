from dataclasses import dataclass
from datetime import datetime
from typing import TypeAlias, TypeVar

DictNotation: TypeAlias = list[str] | str

CSVData: TypeAlias = dict[str, str]
CSVRows: TypeAlias = list[CSVData]
SleepSummary: TypeAlias = dict[str, dict[str, int]]
SleepData: TypeAlias = list[dict[str, str | int]]
SleepLevels: TypeAlias = dict[str, SleepSummary | SleepData]
SleepEntry: TypeAlias = dict[str, str | int | SleepLevels]

SleepHealthData: TypeAlias = tuple[datetime, int, int]

Sleep = TypeVar("Sleep", CSVRows, SleepEntry)


@dataclass(slots=True)
class VitalsData:
    timestamp: datetime
    data: int


@dataclass(slots=True)
class Vitals:
    spo2: VitalsData
    bpm: VitalsData
