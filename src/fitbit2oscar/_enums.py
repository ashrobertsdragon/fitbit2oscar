from enum import StrEnum


class DateFormat(StrEnum):
    DAILY = "????.??.??"  # YYYY.MM.DD
    WEEKLY = "*-????"  # W-YYYY
    MONTHLY = "* ????"  # Month YYYY


class InputType(StrEnum):
    TAKEOUT = "takeout"
    HEALTH_SYNC = "health_sync"
