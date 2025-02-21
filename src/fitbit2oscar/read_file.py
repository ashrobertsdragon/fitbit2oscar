import csv
import json
from collections.abc import Generator
from pathlib import Path
from typing import Any

from fitbit2oscar._types import CSVRows


def read_csv_file(file_name: Path) -> Generator[CSVRows, None, None]:
    """Reads and returns rows from a CSV file."""
    with file_name.open("r") as f:
        yield from iter(csv.DictReader(f))


def read_json_file(file_name: Path) -> Generator[dict[str, Any], None, None]:
    """Reads and returns data from a JSON file."""
    with file_name.open("r") as f:
        yield from json.load(f)


def read_file(
    file_name: Path,
) -> Generator[CSVRows | dict[str, Any], None, None]:
    """Reads and returns data from a CSV or JSON file."""
    read_func = read_csv_file if file_name.suffix == "csv" else read_json_file
    yield from read_func(file_name)
