import datetime
import logging
from collections.abc import Callable, Generator

from fitbit2oscar.time_helpers import convert_time_data
from fitbit2oscar._types import (
    SleepData,
    SleepEntry,
    SleepHealthData,
    VitalsData,
)

logger = logging.getLogger("fitbit2oscar")


def next_spo2(
    spo2_data: Generator[VitalsData, None, None], bpm: VitalsData
) -> Generator[tuple[VitalsData, VitalsData]]:
    """Returns the next SpO2 and current BPM values."""
    yield from ((spo2, bpm) for spo2 in spo2_data)


def next_bpm(
    bpm_data: Generator[VitalsData, None, None], spo2: VitalsData
) -> Generator[tuple[VitalsData, VitalsData]]:
    """Returns the next BPM and current SpO2 values."""
    yield from ((spo2, bpm) for bpm in bpm_data)


def next_all(
    spo2_data: Generator[VitalsData, None, None],
    bpm_data: Generator[VitalsData, None, None],
) -> Generator[tuple[VitalsData, VitalsData]]:
    """Returns the next SpO2 and BPM values."""
    yield from zip(spo2_data, bpm_data)


def next_none(
    spo2: VitalsData, bpm: VitalsData
) -> Generator[tuple[VitalsData, VitalsData]]:
    """Returns the current spo2 and BPM values"""
    yield (spo2, bpm)


def sync_timestamps(
    spo2_data: Generator[VitalsData], bpm_data: Generator[VitalsData]
) -> Generator[tuple[VitalsData, VitalsData], None, None]:
    """
    Synchronizes timestamps between SpO2 and BPM data.

    This function takes generators of tuples containing timestamps and SpO2
    and BPM values and synchronizes the timestamps between the two generators.
    It yields tuples containing the synchronized timestamps and SpO2 and BPM
    values.

    Args:
        spo2_data (Generator[VitalsData, None, None]): A generator of tuples
            containing timestamps and SpO2 values.
        bpm_data (Generator[VitalsData, None, None]): A generator of tuples
            containing timestamps and BPM values.

    Yields:
        Generator[tuple[VitalsData, VitalsData], None, None]: Tuples
            containing synchronized timestamps and SpO2 and BPM values.
    """
    spo2_count = 0
    bpm_count = 0

    for spo2, bpm in next_all(spo2_data, bpm_data):
        comparison: dict[
            int,
            tuple[Callable, Callable],
        ] = {
            -1: lambda: next_spo2(spo2_data, bpm),
            0: lambda: next_none(spo2, bpm),
            1: lambda: next_bpm(bpm_data, spo2),
        }
        timestamps = (spo2.timestamp > bpm.timestamp) - (
            spo2.timestamp < bpm.timestamp
        )
        spo2_count += timestamps < 0
        bpm_count += timestamps > 0

        yield next(comparison[timestamps]())
        if spo2_count or bpm_count:
            logger.debug(
                f"{spo2_count} spo2 entries, {bpm_count} heart rate entries "
                "skipped to find matching timestamp"
            )
        spo2_count = 0
        bpm_count = 0


def parse_sleep_health_data(
    sp02_data: Generator[VitalsData, None, None],
    bpm_data: Generator[VitalsData, None, None],
    session_split: int = 15,
) -> Generator[list[SleepHealthData], None, None]:
    """
    Parses sleep health data into sessions.

    This function takes tuples containing sp02 and BPM data for each
    timestamp and splits them into sessions based on a specified session split
    time. It yields a session, where each session is a list of tuples
    containing timestamps, sp02, and BPM values.

    Args:
        sp02_data (Generator[VitalsData, None, None]): A generator of tuples
            containing timestamps and sp02 values.
        bpm_data (Generator[VitalsData, None, None]): A generator of tuples
            containing timestamps and BPM values.
        session_split (int, optional): The session split time in minutes.
            Defaults to 15.

    Returns:
        Generator[list[SleepHealthData], None, None]: A generator of sessions
    """
    session: list[SleepHealthData] = []
    prev_timestamp = None

    for sp02, bpm in sync_timestamps(sp02_data, bpm_data):
        session.append((sp02.timestamp, sp02.data, bpm.data))
        if prev_timestamp and (
            sp02.timestamp - prev_timestamp
        ) > datetime.timedelta(minutes=session_split):
            yield session
            session.clear()
        prev_timestamp = sp02.timestamp


def generate_hypnogram(data: SleepData) -> list[str]:
    """
    Generates a hypnogram from sleep data.

    This function takes a list of sleep data entries, each consisting of a
    timestamp and a sleep level with its duration in seconds, and converts it
    into a hypnogram. A hypnogram is a list of sleep stages, where each stage
    is repeated for every 30-second interval within its duration. The sleep
    stages are mapped to specific labels: "WAKE", "REM", "Light", and "Deep".

    Args:
        data (SleepData): A list of dictionaries, each containing a "level"
            key indicating the sleep stage and a "seconds" key representing
            the duration of that stage.

    Returns:
        list[str]: A list of sleep stage names corresponding to each 30-second
        interval in the input data.
    """

    levels = {"wake": "WAKE", "rem": "REM", "light": "Light", "deep": "Deep"}
    sleep_stages = []

    sleep_stages.extend(
        [levels[stage["level"]]] * (stage["seconds"] // 30)
        for stage in data
        if stage["level"] in levels
    )

    return sleep_stages


def parse_sleep_data(
    sleep_data_generator: Generator[SleepEntry],
) -> Generator[dict[str, datetime.datetime | int], None, None]:
    """
    Parses sleep data into a structured dictionary format.

    This function takes raw sleep data from a Fitbit sleep entry and converts
    it into a dictionary with detailed sleep metrics. The returned dictionary
    includes sleep onset duration, wake after sleep onset duration, durations
    for light, deep, and REM sleep, number of awakenings, sleep efficiency,
    start and stop times, and a hypnogram representing sleep stages.

    Args:
        sleep_data (SleepEntry): A dictionary containing raw sleep data with
            keys for 'duration', 'levels', 'startTime', 'endTime',
            'wake_after_sleep_onset_duration', and 'sleep_efficiency'.

    Yields:
        dict[str, str | int]: A dictionary containing parsed
            sleep metrics, including durations in HH:MM:SS format, start and
            stop times, and a hypnogram as a list of sleep stage names.
    """

    for sleep_data in sleep_data_generator:
        yield ({
            "start_time": sleep_data["start_time"],
            "stop_time": sleep_data["stop_time"],
            "sleep_onset_duration": convert_time_data(
                minutes=sleep_data["duration"] / 60000
            ),
            "light_sleep_duration": convert_time_data(
                minutes=sleep_data["levels"]["summary"]["light"]["minutes"]
            ),
            "deep_sleep_duration": convert_time_data(
                minutes=sleep_data["levels"]["summary"]["deep"]["minutes"]
            ),
            "rem_sleep_duration": convert_time_data(
                minutes=sleep_data["levels"]["summary"]["rem"]["minutes"]
            ),
            "wake_after_sleep_onset_duration": convert_time_data(
                minutes=sleep_data["wake_after_sleep_onset_duration"]
            ),
            "number_awakenings": sleep_data["levels"]["summary"]["wake"][
                "count"
            ],
            "sleep_efficiency": sleep_data["sleep_efficiency"],
            "hypnogram": f"[{','.join(generate_hypnogram(sleep_data["levels"]["data"]))}]",
        })
