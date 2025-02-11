import datetime
import time
from pathlib import Path
from zoneinfo import ZoneInfo

from fitbit2oscar.read_file import read_csv_file
from fitbit2oscar.takeout.paths import profile_path


def convert_timestamp(
    timestamp: str,
    timezone: str | None = None,
    timestamp_format: str = "%Y-%m-%dT%H:%M:%S",
    use_seconds: bool = True,
) -> datetime.datetime:
    """
    Parse timestamp and attach timezone info, converting from UTC if needed.

    Args:
        timestamp (str): Timestamp in ISO 8601 format, optionally ending with
            'Z' for UTC.
        timezone (str): Timezone to convert timestamps to
            (e.g., 'America/New_York').
        time_string_format (str, optional): Format of the timestamp string.
            Defaults to "%Y-%m-%dT%H:%M:%S".

    Returns:
        datetime.datetime: Timezone-aware datetime object in the target
            timezone.
    """
    dt = datetime.datetime.strptime(
        timestamp.removesuffix("Z"), timestamp_format
    )
    tz = ZoneInfo(timezone) if timezone else get_local_timezone()

    local_dt = (
        dt.replace(tzinfo=datetime.timezone.utc).astimezone(tz)
        if timestamp.endswith("Z")
        else dt.replace(tzinfo=tz)
    )

    return local_dt if use_seconds else dt.replace(second=0)


def convert_time_data(minutes: int) -> str:
    """Converts time in minutes to a string in HH:MM:SS format."""
    hours, mins = divmod(minutes, 60)
    return f"{hours:02d}:{mins:02d}:00"


def get_local_timezone() -> datetime.timezone:
    """Determine local timezone."""
    local = time.localtime()
    utc = time.gmtime()

    day_offset = (utc.tm_yday - local.tm_yday) * 24
    offset = local.tm_hour - utc.tm_hour + day_offset

    return datetime.timezone(datetime.timedelta(hours=offset))


def get_timezone_from_profile(fitbit_path: Path) -> str:
    """Get timezone from profile file."""
    for row in read_csv_file(profile_path(fitbit_path)):
        timezone: str = row["timezone"]
    if not timezone:
        raise ValueError("Could not find timezone")
    return timezone
