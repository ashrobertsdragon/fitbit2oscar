import datetime
from collections.abc import Callable, Generator
from functools import partial

from fitbit2oscar.time_helpers import convert_time_data
from fitbit2oscar._types import (
    SleepData,
    SleepEntry,
    SleepHealthData,
    VitalsData,
)


def get_next_item(
    item: Generator[VitalsData],
) -> VitalsData:
    """Returns the next item from a generator."""
    return next(item)


def next_sp02(
    sp02_data: Generator[VitalsData, None, None], bpm: VitalsData
) -> tuple[VitalsData, VitalsData]:
    """Returns the next SpO2 and current BPM values."""
    return get_next_item(sp02_data), bpm


def next_bpm(
    bpm_data: Generator[VitalsData, None, None], sp02: VitalsData
) -> tuple[VitalsData, VitalsData]:
    """Returns the next BPM and current SpO2 values."""
    return sp02, get_next_item(bpm_data)


def next_all(
    sp02_data: Generator[VitalsData, None, None],
    bpm_data: Generator[VitalsData, None, None],
) -> tuple[VitalsData, VitalsData]:
    """Returns the next SpO2 and BPM values."""
    return get_next_item(sp02_data), get_next_item(bpm_data)


def sync_timestamps(
    sp02_data: Generator[VitalsData], bpm_data: Generator[VitalsData]
) -> Generator[tuple[VitalsData, VitalsData], None, None]:
    """
    Synchronizes timestamps between SpO2 and BPM data.

    This function takes generators of tuples containing timestamps and SpO2
    and BPM values and synchronizes the timestamps between the two generators.
    It yields tuples containing the synchronized timestamps and SpO2 and BPM
    values.

    Args:
        sp02_data (Generator[VitalsData, None, None]): A generator of tuples
            containing timestamps and SpO2 values.
        bpm_data (Generator[VitalsData, None, None]): A generator of tuples
            containing timestamps and BPM values.

    Yields:
        Generator[tuple[VitalsData, VitalsData], None, None]: Tuples
            containing synchronized timestamps and SpO2 and BPM values.
    """
    sp02 = get_next_item(sp02_data)
    bpm = get_next_item(bpm_data)

    comparison: dict[
        int,
        tuple[Callable, Callable],
    ] = {
        -1: partial(next_sp02, sp02_data, bpm),
        0: partial(next_all, sp02_data, bpm_data),
        1: partial(next_bpm, bpm_data, sp02),
    }

    yield comparison[
        (sp02.timestamp > bpm.timestamp) - (sp02.timestamp < bpm.timestamp)
    ]()


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
) -> dict[str, datetime.datetime | int]:
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

    Returns:
        dict[str, str | int]: A dictionary containing parsed
            sleep metrics, including durations in HH:MM:SS format, start and
            stop times, and a hypnogram as a list of sleep stage names.
    """

    return (
        {
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
        }
        for sleep_data in sleep_data_generator
    )
