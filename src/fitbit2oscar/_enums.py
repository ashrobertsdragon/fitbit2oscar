from enum import IntEnum, StrEnum


class DateFormat(StrEnum):
    DAILY = "%Y.%m.%d"  # YYYY.MM.DD
    WEEKLY = "%U-%Y"  # W-YYYY
    MONTHLY = "%B %Y"  # Month YYYY


class DateDelta(IntEnum):
    DAILY = 1
    WEEKLY = 7
    MONTHLY = 30


class InputType(StrEnum):
    TAKEOUT = "takeout"
    HEALTH_SYNC = "health_sync"
