import argparse
import datetime
import sys
from pathlib import Path

from loguru import logger

import fitbit2oscar.helpers
import fitbit2oscar.extract
import fitbit2oscar.write_file


def process_data(args: argparse.Namespace) -> None:
    """Process Fitbit data and convert to OSCAR format."""
    script_start = datetime.datetime.now()

    args.export_path.mkdir(exist_ok=True)

    sleep_paths, sp02_paths, bpm_paths = fitbit2oscar.helpers.get_paths(args)
    timezone = fitbit2oscar.helpers.get_timezone(args.input_path)

    viatom_data = fitbit2oscar.extract.extract_sleep_health_data(
        sp02_paths, bpm_paths, timezone, args.start_date, args.end_date
    )
    fitbit2oscar.write_file.create_viatom_file(args.output_path, viatom_data)

    dreem_data = fitbit2oscar.extract.extract_sleep_data(
        sleep_paths, timezone, args.start_date, args.end_date
    )
    fitbit2oscar.write_file.write_dreem_file(args.output_path, dreem_data)

    finish_message = (
        f"Finished processing in {datetime.datetime.now() - script_start}"
    )
    logger.info(finish_message)


def configure_logger(args) -> None:
    """Sets up logger with verbose and log file options."""
    logger.remove()

    format_str = (
        "{time} {level} {message}" if args.level else "{time} {message}"
    )
    level = args.level or "WARNING"

    sink = args.logfile if args.logfile else sys.stderr
    logger.add(sink=sink, format=format_str, level=level)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="Fitbit to OSCAR Data Converter",
        description="Converts Fitbit data to OSCAR format",
    )

    parser.add_argument(
        "-s",
        "--start-date",
        metavar="<YYYY-M-D>",
        type=lambda x: fitbit2oscar.helpers.process_date_arg(x, "start"),
        help="Optional start date for data",
        default=datetime.date(2010, 1, 1),
    )

    parser.add_argument(
        "-e",
        "--end-date",
        metavar="<YYYY-M-D>",
        type=lambda x: fitbit2oscar.helpers.process_date_arg(x, "end"),
        help="Optional end date for data",
        default=datetime.date.today(),
    )

    parser.add_argument(
        "-v",
        "--verbose",
        help="Set verbose logging",
        action="store_const",
        const="INFO",
        dest="level",
    )
    parser.add_argument(
        "-vv",
        "--very-verbose",
        help="Set verbose logging",
        action="store_const",
        const="DEBUG",
        dest="level",
    )
    parser.add_argument(
        "-l",
        "--logfile",
        metavar="<filename.log>",
        help="Log to file instead of stderr",
    )

    parser.add_argument(
        "input-path",
        help="Path to Takeout folder containing 'Fitbit' or to Takeout folder",
        type=fitbit2oscar.helpers.get_fitbit_path,
    )

    parser.add_argument(
        "-o",
        "--export-path",
        help="Path to export files to, defaults to 'export' in current directory",
        type=lambda x: Path(x),
        nargs="?",
        default=Path("export"),
    )
    args = parser.parse_args()

    configure_logger(args)

    if args.start_date > args.end_date:
        raise argparse.ArgumentError(
            "Start date must be before or the same as the end date"
        )

    try:
        process_data(args)
    except AssertionError as e:
        logger.fatal(f"Error processing data: {e}")
    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")


if __name__ == "__main__":
    main()
