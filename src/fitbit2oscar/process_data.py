import argparse
import datetime
import logging

from fitbit2oscar import write_file
from fitbit2oscar._types import SleepHealthData
from fitbit2oscar.factory import DataHandlerFactory
from fitbit2oscar.parse import parse_sleep_data, parse_sleep_health_data


logger = logging.getLogger("fitbit2oscar")


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


def process_data(args: argparse.Namespace) -> None:
    """Process Fitbit data and convert to OSCAR format."""
    script_start = datetime.datetime.now()

    args.export_path.mkdir(parents=True, exist_ok=True)

    viatom_data, dreem_data = get_data(args)
    viatom_chunks = chunk_viatom_data(viatom_data)

    write_file.create_viatom_file(args.output_path, viatom_chunks)
    write_file.write_dreem_file(args.output_path, dreem_data)

    finish_message = (
        f"Finished processing in {datetime.datetime.now() - script_start}"
    )
    logger.info(finish_message)
