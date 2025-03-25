import argparse
import datetime
import importlib
import logging
import pkgutil
import re
import sys
from pathlib import Path

import fitbit2oscar.plugins
import fitbit2oscar.process_data as run
from fitbit2oscar._enums import DateFormat, InputType
from fitbit2oscar.exceptions import FitbitConverterError


logger = logging.getLogger("fitbit2oscar")


def discover_plugins() -> list[str]:
    plugins = []
    plugins.extend(
        name
        for _, name, is_package in pkgutil.walk_packages(
            path=fitbit2oscar.plugins.__path__
        )
        if is_package
    )
    return plugins


def configure_logger(args: argparse.Namespace) -> None:
    """Sets up logger with verbose and log file options."""
    log_format = (
        "%(asctime)s - %(levelname)s - %(message)s"
        if args.level
        else "%(asctime)s - %(message)s"
    )
    logging.basicConfig(
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(), logging.FileHandler(args.log_file)]
        if args.log_file
        else [logging.StreamHandler()],
    )
    logger.setLevel(getattr(logging, args.level))


def get_fitbit_path(input_path: Path, input_type: str) -> Path:
    try:
        InputType(input_type)
    except ValueError as e:
        raise argparse.ArgumentTypeError(
            f"Invalid structure '{input_type}', must be one of {list(InputType)}"
        ) from e
    module = f"fitbit2oscar.plugins.{input_type}.paths"
    import_module = importlib.import_module(module)
    verified_path = getattr(import_module, "verify_input_path")(input_path)
    logger.debug(verified_path)
    return verified_path


class DateArgument(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None) -> None:
        if not values and option_string is not None:
            raise argparse.ArgumentError(
                f"Must set a value for {option_string}"
            )
        datematch = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", values)
        if datematch is None:
            raise argparse.ArgumentError(
                f"Invalid {option_string} date argument '{values}', must match YYYY-M-D format"
            )
        dateobj = datetime.date(
            year=int(datematch[1]),
            month=int(datematch[2]),
            day=int(datematch[3]),
        )
        if not (datetime.date.today() >= dateobj >= datetime.date(2010, 1, 1)):
            raise argparse.ArgumentTypeError(
                f"Invalid {option_string} date {values}, must be on or before today's date and no older than 2010-01-01."
            )

        setattr(namespace, self.dest, dateobj)


class InputPath(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None) -> None:
        input_arg = getattr(namespace, "input_type", None)
        if not input_arg:
            raise argparse.ArgumentError(
                parser.input_type,
                f"{option_string} requires an input type to be set (e.g., 'takeout', 'health_sync').",
            )
        fitbit_path = get_fitbit_path(Path(values), input_arg)
        setattr(namespace, self.dest, fitbit_path)


class StoreLogFile(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None) -> None:
        if not getattr(namespace, "verbosity", 0):
            logger.error(
                "Verbosity must be set to at least 'INFO' to log to a file."
            )
            argparse.ArgumentError(
                parser.log_file,
                "Verbosity level must be set (e.g., --verbose, --very-verbose, -v, -vv).",
            )

        setattr(namespace, self.dest, values)


class DateFormatValidator(argparse.Action):
    def __call__(self, parser, namespace, values, option_string) -> None:
        try:
            if getattr(namespace, "input_type", None) != "health_sync":
                raise argparse.ArgumentError(
                    parser.input_type,
                    f"{option_string} is not valid for input type {namespace.input_type}",
                )
            DateFormat(values)
        except KeyError as e:
            raise argparse.ArgumentError(
                parser.date_format,
                f"{option_string} must be one of {list(DateFormat)}",
            ) from e
        setattr(namespace, self.dest, values)


def create_parser() -> argparse.Namespace:
    """Create an argument parser for the command line interface."""
    input_choices = discover_plugins()
    parser = argparse.ArgumentParser(
        prog="Fitbit to OSCAR Data Converter",
        description="Converts Fitbit data to OSCAR format",
    )

    input_type = parser.add_argument(  # noqa: F841
        "input_type",
        help=(
            f"Source of Fitbit data ({', '.join(input_choices)}) / "
            "Defaults to 'takeout' since Health Sync support is experimental"
        ),
        choices=input_choices,
        default="takeout",
    )

    fitbit_path = parser.add_argument(  # noqa: F841
        "-i",
        "--fitbit-path",
        help="Path to Fitbit data",
        action=InputPath,
        required=True,
    )

    export_path = parser.add_argument(  # noqa: F841
        "-o",
        "--export-path",
        help="Path to export files to, defaults to 'export' in current directory",
        type=Path,
        default=Path("export"),
    )

    dates = parser.add_argument_group("Date options")
    start_date = dates.add_argument(  # noqa: F841
        "-s",
        "--start-date",
        metavar="<YYYY-M-D>",
        action=DateArgument,
        help="Optional start date for data",
        default=datetime.date(2010, 1, 1),
    )

    end_date = dates.add_argument(  # noqa: F841
        "-e",
        "--end-date",
        metavar="<YYYY-M-D>",
        action=DateArgument,
        help="Optional end date for data",
        default=datetime.date.today(),
    )

    verbosity = parser.add_argument_group(title="Logging options")

    verbosity_args = verbosity.add_mutually_exclusive_group()
    verbose = verbosity_args.add_argument(  # noqa: F841
        "-v",  # noqa: F841
        "--verbose",
        help="Set verbose logging",
        action="store_const",
        const="INFO",
        dest="level",
    )
    very_verbose = verbosity.add_argument(  # noqa: F841
        "-vv",
        "--very-verbose",
        help="Set verbose logging",
        action="store_const",
        const="DEBUG",
        dest="level",
    )
    log_file = verbosity.add_argument(  # noqa: F841
        "-l",
        "--logfile",
        metavar="<filename.log>",
        help="Log to file instead of stderr. Logging must be set to verbose or very verbose",
        dest="log_file",
        action=StoreLogFile,
        type=Path,
    )

    date_format = parser.add_argument(  # noqa: F841
        "-f",
        "--date-format",
        help="Date string format to use for Health Sync for input",
        default="DAILY",
        metavar="<DAILY|WEEKLY|MONTHLY>",
        choices=["DAILY", "WEEKLY", "MONTHLY"],
        action=DateFormatValidator,
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
        run.process_data(args)
    except AssertionError as e:
        logger.fatal(f"Error processing data: {e}")
        sys.exit(1)
    except FitbitConverterError as e:
        logger.error(str(e))
    # sys.exit(1)
    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
