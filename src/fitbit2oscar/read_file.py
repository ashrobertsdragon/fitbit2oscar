import csv
import json
from collections.abc import Generator
from pathlib import Path
from typing import Any


def read_csv_file(file_name: Path) -> Generator[dict[str, str], None, None]:
    """Reads and returns rows from a CSV file."""
    with file_name.open("r") as f:
        yield from iter(csv.DictReader(f))


def read_json_file(file_name: Path) -> Generator[dict[str, Any], None, None]:
    """Reads and returns data from a JSON file."""
    with file_name.open("r") as f:
        yield from json.load(f)
