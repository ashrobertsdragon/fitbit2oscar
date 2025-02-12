import datetime
import logging
import time
from pathlib import Path
from zoneinfo import ZoneInfo

from fitbit2oscar.read_file import read_csv_file, read_json_file
from fitbit2oscar.takeout.paths import profile_path

logger = logging.getLogger("fitbit2oscar")


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


def get_timezone_from_profile(fitbit_path: Path) -> datetime.timezone:
    """Get timezone from profile file."""
    for row in read_csv_file(profile_path(fitbit_path)):
        timezone: str = row["timezone"]
    if not timezone:
        logger.error("Could not find timezone in profile file")
        raise ValueError("Could not find timezone")
    region = timezone.split("/")[0]
    if region in ["US", "United States", "U.S."]:
        timezone.replace(region, "America")

    iana_zones = get_timezone_data("tz_data.json")
    ms_zones = get_timezone_data("ms_zones.json")

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
