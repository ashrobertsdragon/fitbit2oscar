from datetime import datetime
from typing import TypeAlias, NamedTuple

SleepSummary: TypeAlias = dict[str, dict[str, int]]
SleepData: TypeAlias = list[dict[str, str | int]]
SleepLevels: TypeAlias = dict[str, SleepSummary | SleepData]
SleepEntry: TypeAlias = dict[str, str | int | SleepLevels]

SleepHealthData: TypeAlias = tuple[datetime, int, int]


class VitalsData(NamedTuple):
    timestamp: datetime.datetime
    data: int
