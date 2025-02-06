import argparse
import datetime
import importlib
import re
from pathlib import Path
from zoneinfo import ZoneInfo

from fitbit2oscar._enums import InputType


def get_fitbit_path(input_path: Path, input_type: str) -> Path:
    try:
        InputType(input_type)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid structure '{input_type}', must be one of {list(InputType)}"
        )
    module = f"{input_type}.helpers"
    importlib.import_module(module)
    func = f"get_{input_type}_fitbit_path"
    return getattr(module, func)(input_path)


def process_date_arg(datestring: str, argtype: str) -> datetime.date:
    datematch = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", datestring)
    if datematch is None:
        raise argparse.ArgumentTypeError(
            f"Invalid {argtype} date argument '{datestring}', must match YYYY-M-D format"
        )
    dateobj = datetime.date(
        year=int(datematch.group(1)),
        month=int(datematch.group(2)),
        day=int(datematch.group(3)),
    )
    if not (datetime.date.today() >= dateobj >= datetime.date(2010, 1, 1)):
        raise argparse.ArgumentTypeError(
            f"Invalid {argtype} date {datestring}, must be on or before today's date and no older than 2010-01-01."
        )

    adjustments = {
        "start": lambda d: d - datetime.timedelta(days=1),
        "end": lambda d: d + datetime.timedelta(days=1),
        "file": lambda d: d,
    }
    return adjustments[argtype](dateobj)


def get_data(
    args: argparse.Namespace,
) -> tuple[list[dict[str, datetime.datetime | int]], list]:
    package = args.input_type
    helpers = importlib.import_module(f"{package}.helpers")
    parser = importlib.import_module(f"{package}.parser")

    if package == "takeout":
        sleep_paths, sp02_paths, bpm_paths = helpers.get_paths(
            args.fitbit_path
        )
        timezone = helpers.get_timezone(args.fitbit_path)
        viatom_data = parser.get_sleep_health_data(
            sp02_paths, bpm_paths, timezone, args.start_date, args.end_date
        )
        dreem_data = parser.get_sleep_data(
            sleep_paths, timezone, args.start_date, args.end_date
        )
    elif package == "health_sync":
        timezone = datetime._local_timezone()
        sleep_paths, sp02_paths, bpm_paths = helpers.get_paths(
            args.fitbit_path, args.date_format
        )
        viatom_data = parser.get_sleep_health_data(
            sp02_paths, bpm_paths, args.start_date, args.end_date
        )
        dreem_data = parser.get_sleep_data(
            sleep_paths, args.start_date, args.end_date
        )

    return viatom_data, dreem_data
