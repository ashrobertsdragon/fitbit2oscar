import argparse
from collections.abc import Generator
from datetime import datetime

from fitbit2oscar import write_file
from fitbit2oscar._types import SleepHealthData, SleepEntry, VitalsData
from fitbit2oscar.factory import DataHandlerFactory
from fitbit2oscar.fitbit_extractor import FitbitExtractor
from fitbit2oscar.parsers import parse_sleep_data, parse_sleep_health_data
from fitbit2oscar._logger import logger


def get_data(
    args: argparse.Namespace,
) -> tuple[
    Generator[VitalsData, None, None],
    Generator[VitalsData, None, None],
    Generator[SleepEntry, None, None],
]:
    """Parse data using the appropriate handler."""
    handler = DataHandlerFactory.create_client(args.input_type, args)
    extractor = FitbitExtractor(args.config, handler.timezone)
    sp02_generator, bpm_generator, sleep_generator = extractor.extract_data(
        handler.paths,
        args.start_date,
        args.end_date,
    )
    return sp02_generator, bpm_generator, sleep_generator


def parse_data(
    sp02_generator: Generator[VitalsData],
    bpm_generator: Generator[VitalsData],
    sleep_generator: Generator[SleepEntry],
) -> tuple[
    Generator[list[SleepHealthData], None, None],
    Generator[dict[str, datetime | int]],
]:
    """Parse data into viatom and dreem formats."""
    viatom_data: Generator[list[SleepHealthData], None, None] = (
        parse_sleep_health_data(sp02_generator, bpm_generator)
    )
    dreem_data: Generator[dict[str, datetime | int]] = parse_sleep_data(
        sleep_generator
    )
    return viatom_data, dreem_data


def chunk_viatom_data(
    viatom_data: list[list[SleepHealthData]],
    chunk_size: int = 4095,
) -> Generator[list[SleepHealthData], None, None]:
    """
    Break up viatom data into chunks of size chunk_size.

    Args:
        viatom_data (list[list[tuple[datetime, int, int]]]): List of
            sleep health data sessions where each session is a list of tuples
            containing timestamps, sp02, and BPM values.
        chunk_size (int, optional): Maximum chunk size. Defaults to 4095.

    yields:
        list[SleepHealthData]: List of sleep health data tuples, up to chunk_size in length for each session.
    """
    for i, session in enumerate(viatom_data, start=1):
        logger.info(
            f"Processing session {i} into {len(session // chunk_size)} chunks"
        )
        for j in range(0, len(session), chunk_size):
            yield session[j : j + chunk_size]


def process_data(args: argparse.Namespace) -> None:
    """Process Fitbit data and convert to OSCAR format."""
    script_start = datetime.now()

    args.export_path.mkdir(parents=True, exist_ok=True)

    sp02_generator, bpm_generator, sleep_generator = get_data(args)

    viatom_data, dreem_data = parse_data(
        sp02_generator, bpm_generator, sleep_generator
    )
    viatom_chunks = chunk_viatom_data(viatom_data)

    write_file.create_viatom_file(args.output_path, viatom_chunks)
    write_file.write_dreem_file(args.output_path, dreem_data)

    finish_message = f"Finished processing in {datetime.now() - script_start}"
    logger.info(finish_message)
