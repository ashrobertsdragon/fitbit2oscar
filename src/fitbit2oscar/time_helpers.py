import datetime
import time
from pathlib import Path
from zoneinfo import ZoneInfo

from fitbit2oscar.exceptions import FitbitConverterValueError
from fitbit2oscar.read_file import read_csv_file, read_json_file
from fitbit2oscar._logger import logger


def calculate_duration(
    start_time: datetime.datetime, stop_time: datetime.datetime
) -> int:
    """Calculate the duration of the sleep session in seconds."""
    return int((stop_time - start_time).total_seconds())


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


def convert_time_data(minutes: int = 0, seconds: int = 0) -> str:
    """
    Converts time to a string in HH:MM:SS format.

    Args:
        minutes (int): Number of minutes. Defaults to 0.
        seconds (int): Number of seconds. Defaults to 0.

    Returns:
        str: Time in HH:MM:SS format.
    """
    if not minutes:
        minutes = divmod(seconds, 60)
    hours, mins = divmod(minutes, 60)
    return f"{hours:02d}:{mins:02d}:{seconds:02d}"


def format_timestamp(timestamp: str, timestamp_format: str) -> str:
    """Formats the timestamp for the sleep entry."""
    dt = convert_timestamp(timestamp, timestamp_format=timestamp_format)
    return dt.strftime(timestamp_format)


def is_valid_date(
    date: datetime.date,
    start_date: datetime.date,
    end_date: datetime.date,
) -> bool:
    """Validate if a date falls within the specified range."""
    return start_date <= date <= end_date


def get_local_timezone() -> datetime.timezone:
    """Determine local timezone."""
    local = time.localtime()
    utc = time.gmtime()

    l_dst = local.tm_isdst
    u_dst = utc.tm_isdst
    day_offset = (utc.tm_yday - local.tm_yday) * 24
    logger.debug(f"Local is in DST: {l_dst > 0}. UTC is in DST: {u_dst > 0}")
    offset_hr = local.tm_hour + l_dst - utc.tm_hour + u_dst + day_offset
    offset_min = local.tm_min - utc.tm_min
    if offset_min < 0:
        offset_min += 60
        offset_hr -= 1

    offset = datetime.timedelta(hours=offset_hr, minutes=offset_min)

    return datetime.timezone(offset)


def get_timezone_data(timezone_file: str) -> dict[str, str | dict[str, str]]:
    tz_path = Path(__file__).parent / timezone_file
    return next(read_json_file(tz_path))


def get_timezone_from_profile(profile_path: Path) -> datetime.timezone:
    """Get timezone from profile file."""
    for row in read_csv_file(profile_path):
        timezone: str = row["timezone"]
    if not timezone:
        logger.error("Could not find timezone in profile file")
        raise FitbitConverterValueError("Could not find timezone")
    region = timezone.split("/")[0]
    if region in ["US", "United States", "U.S."]:
        timezone.replace(region, "America")

    iana_zones: dict[str, str] = get_timezone_data("tz_data.json")
    ms_zones: dict[str, dict[str, str]] = get_timezone_data("ms_zones.json")

    if timezone in iana_zones:
        logger.debug(f"Using IANA time zone for {timezone}")
        zone: str = iana_zones[timezone]
    elif timezone in ms_zones:
        logger.debug(f"Using Microsoft Time Zone Index for {timezone}")
        zone: str = ms_zones[timezone]["BaseUtcOffset"]
    else:
        logger.warning(f"Could not find timezone {timezone}")
        return get_local_timezone()

    offset_hr, offset_min = zone.split(":", maxsplit=1)
    offset = datetime.timedelta(
        hours=int(offset_hr), minutes=int(offset_min.split(":")[0])
    )
    return datetime.timezone(offset)
