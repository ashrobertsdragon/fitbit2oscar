import csv
import datetime
import struct
from collections.abc import Generator
from pathlib import Path


def prepare_dreem_data(
    dreem_data: Generator[dict[str, str | int]],
) -> Generator[list[str | int], None, None]:
    """
    Generator that transforms input data into CSV rows.

    Args:
        dreem_data: Generator of dictionary entries

    Yields:
        List of row values for CSV writing
    """
    yield [
        "Start Time",
        "Stop Time",
        "Sleep Onset Duration",
        "Light Sleep Duration",
        "Deep Sleep Duration",
        "REM Duration",
        "Wake After Sleep Onset Duration",
        "Number of awakenings",
        "Sleep efficiency",
        "Hypnogram",
    ]

    for night in dreem_data:
        yield night.values()


def write_dreem_file(
    file_name: Path, dreem_data: Generator[dict[str, str | int]]
) -> None:
    """Writes data to a CSV file."""
    with file_name.open("w", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        for row in prepare_dreem_data(dreem_data):
            writer.writerow(row)


def write_viatom_binary_file(file_name: Path, data: bytes) -> None:
    with file_name.open("wb") as f:
        f.write(data)


def prepare_viatom_binary_data(data) -> bytes:
    """
    Prepare binary data for Viatom file format.

    Args:
        data (list): List of records to be converted to binary format

    Returns:
        bytes: Prepared binary data
    """
    binary_data = bytearray()

    first_record_time = data[0][0]
    binary_data.extend(struct.pack("<BB", 0x5, 0x0))  # HEADER_LSB, HEADER_MSB
    binary_data.extend(struct.pack("<H", first_record_time.year))
    binary_data.extend(
        struct.pack(
            "<BBBBB",
            first_record_time.month,
            first_record_time.day,
            first_record_time.hour,
            first_record_time.minute,
            first_record_time.second,
        )
    )
    binary_data.extend(struct.pack("<I", len(data) * 5 + 40))  # FILESIZE
    binary_data.extend(struct.pack("<H", len(data) * 4))  # DURATION
    binary_data.extend(b"\x00" * 25)  # Padding

    for record in data:
        binary_data.extend(struct.pack("<B", record[1]))
        binary_data.extend(struct.pack("<B", record[2]))
        binary_data.extend(b"\x00\x00\x00")  # Padding

    return bytes(binary_data)


def create_viatom_file(
    export_path: Path,
    data: list[list[tuple[datetime.datetime, int, int]]],
) -> None:
    """
    Write data to a Viatom binary file.

    Args:
        args: Argument object with export_path
        data: List of records to write

    Raises:
        RuntimeError: If data chunk is too long
    """
    for datum in data:
        if len(datum) > 4095:
            raise RuntimeError(
                f"Data chunk ({data[0][0]}, {data[-1][0]}) too long ({len(data)})!"
            )

        bin_file = f"{data[0][0].strftime('%Y%m%d%H%M%S')}.bin"
        binary_data = prepare_viatom_binary_data(data)

        write_viatom_binary_file(export_path / bin_file, binary_data)
