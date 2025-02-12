import argparse
import datetime
import importlib
import logging
import re
from pathlib import Path

from fitbit2oscar._enums import InputType
from fitbit2oscar._types import SleepHealthData
from fitbit2oscar.factory import DataHandlerFactory
from fitbit2oscar.parse import parse_sleep_data, parse_sleep_health_data


logger = logging.getLogger("fitbit2oscar")


def get_fitbit_path(input_path: Path, input_type: str) -> Path:
    try:
        InputType(input_type)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid structure '{input_type}', must be one of {list(InputType)}"
        )
    module = f"fitbit2oscar.{input_type}.paths"
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
) -> tuple[
    list[dict[str, datetime.datetime | int]], list[dict[str, str | int]]
]:
    """Parse data using the appropriate handler."""
    handler = DataHandlerFactory.create_client(args.input_type, args)
    sp02_files, bpm_files, sleep_files, timezone = (
        handler.get_paths_and_timezone()
    )
    sp02_data, bpm_data, sleep_data_generator = handler.extract_data(
        sp02_files,
        bpm_files,
        sleep_files,
        timezone,
        args.start_date,
        args.end_date,
    )
    viatom_data = parse_sleep_health_data(sp02_data, bpm_data)
    dreem_data = parse_sleep_data(sleep_data_generator)
    return viatom_data, dreem_data


def chunk_viatom_data(
    viatom_data: list[list[SleepHealthData]],
    chunk_size: int = 4095,
) -> list[list[SleepHealthData]]:
    """
    Break up viatom data into chunks of size chunk_size.

    Args:
        viatom_data (list[list[tuple[datetime.datetime, int, int]]]): List of
            sleep health data sessions where each session is a list of tuples
            containing timestamps, sp02, and BPM values.
        chunk_size (int, optional): Maximum chunk size. Defaults to 4095.

    Returns:
        list[list[tuple[datetime.datetime, int, int]]]: List of data chunks.
    """
    chunks = [
        session[i : i + chunk_size]
        for session in viatom_data
        for i in range(0, len(session), chunk_size)
    ]
    logger.info(
        f"Chunked viatom data into {[len(chunk) for chunk in chunks]} "
        f"chunks of size {chunk_size}"
    )
    return chunks
