import argparse
import datetime
import logging
from pathlib import Path

import fitbit2oscar.helpers as helper
import fitbit2oscar.parse
import fitbit2oscar.write_file

logger = logging.getLogger(__name__)


def process_data(args: argparse.Namespace) -> None:
    """Process Fitbit data and convert to OSCAR format."""
    script_start = datetime.datetime.now()

    args.export_path.mkdir(parents=True, exist_ok=True)

    viatom_data, dreem_data = fitbit2oscar.helpers.get_data(args)
    viatom_chunks = fitbit2oscar.helpers.chunk_viatom_data(viatom_data)

    fitbit2oscar.write_file.create_viatom_file(args.output_path, viatom_chunks)
    fitbit2oscar.write_file.write_dreem_file(args.output_path, dreem_data)

    finish_message = (
        f"Finished processing in {datetime.datetime.now() - script_start}"
    )
    logger.info(finish_message)


def configure_logger(args: argparse.Namespace) -> None:
    """Sets up logger with verbose and log file options."""
    format = (
        "%(asctime)s - %(levelname)s - %(message)s"
        if args.level
        else "%(asctime)s - %(message)s"
    )
    logging.basicConfig(
        format=format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(), logging.FileHandler(args.log_file)]
        if args.log_file
        else [logging.StreamHandler()],
    )
    logger.setLevel(getattr(logging, args.level))


class PackageVersionAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string) -> None:
        package_map = {
            "-H": "health_sync",
            "-T": "takeout",
            "--health_sync": "health_sync",
            "--takeout": "takeout",
        }
        namespace.input_type = package_map[option_string]
        path = helper.get_fitbit_path(
            input_path=values, input_type=namespace.input_type
        )
        setattr(namespace, self.dest, path)


class StoreLogFile(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None) -> None:
        if not getattr(namespace, "verbosity", 0):
            logger.error(
                "Verbosity must be set to at least 'INFO' to log to a file."
            )
            parser.error(
                f"{option_string} requires a verbosity level to be set (e.g., --verbose, --very-verbose, -v, -vv)."
            )

        setattr(namespace, self.dest, values)


def create_parser() -> argparse.Namespace:
    """Create an argument parser for the command line interface."""
    parser = argparse.ArgumentParser(
        prog="Fitbit to OSCAR Data Converter",
        description="Converts Fitbit data to OSCAR format",
    )

    input = parser.add_argument_group("Input path options")
    input_path = input.add_mutually_exclusive_group(required=True)
    input_path.add_argument(
        "-T",
        "--takeout-path",
        help="Path to Takeout folder containing 'Fitbit' or to Takeout folder",
        action=PackageVersionAction,
        dest="fitbit_path",
    )
    input_path.add_argument(
        "-H",
        "--health-sync-path",
        help="Path to Health Sync folder",
        action=PackageVersionAction,
        dest="fitbit_path",
    )

    parser.add_argument(
        "-o",
        "--export-path",
        help="Path to export files to, defaults to 'export' in current directory",
        type=Path,
        default=Path("export"),
    )

    dates = parser.add_argument_group("Date options")
    dates.add_argument(
        "-s",
        "--start-date",
        metavar="<YYYY-M-D>",
        type=helper.process_date_arg,
        help="Optional start date for data",
        default=datetime.date(2010, 1, 1),
    )

    dates.add_argument(
        "-e",
        "--end-date",
        metavar="<YYYY-M-D>",
        type=helper.process_date_arg,
        help="Optional end date for data",
        default=datetime.date.today(),
    )

    verbosity = parser.add_argument_group(title="Logging options")

    verbosity_args = verbosity.add_mutually_exclusive_group()
    verbosity_args.add_argument(
        "-v",
        "--verbose",
        help="Set verbose logging",
        action="store_const",
        const="INFO",
        dest="level",
    )
    verbosity.add_argument(
        "-vv",
        "--very-verbose",
        help="Set verbose logging",
        action="store_const",
        const="DEBUG",
        dest="level",
    )
    verbosity.add_argument(
        "-l",
        "--logfile",
        metavar="<filename.log>",
        help="Log to file instead of stderr. Logging must be set to verbose or very verbose",
        dest="log_file",
        action=StoreLogFile,
        type=Path,
    )

    return parser.parse_args()


def main() -> None:
    args = create_parser()

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
