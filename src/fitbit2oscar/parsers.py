import datetime
from collections.abc import Callable, Generator
from functools import partial

from fitbit2oscar.time_helpers import convert_time_data
from fitbit2oscar._types import (
    SleepData,
    SleepEntry,
    SleepHealthData,
    VitalsData,
    Vitals,
)
from fitbit2oscar._logger import logger


def advance_spo2(spo2_data: Generator[VitalsData], vitals: Vitals) -> Vitals:
    next_spo2: VitalsData = next(spo2_data, vitals.spo2)
    return next_spo2, vitals.bpm


def advance_bpm(bpm_data: Generator[VitalsData], vitals: Vitals) -> Vitals:
    next_bpm: VitalsData = next(bpm_data, vitals.bpm)
    return vitals.spo2, next_bpm


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
    spo2_entries = 0
    bpm_entries = 0
    sync_from: dict[int, Callable[[VitalsData, Vitals], Vitals]] = {
        -1: partial(advance_spo2, spo2_data),
        1: partial(advance_bpm, bpm_data),
    }

    while True:
        spo2: VitalsData = next(spo2_data, False)
        bpm: VitalsData = next(bpm_data, False)
        if not spo2 or not bpm:
            break
        while spo2.timestamp != bpm.timestamp:
            spo2_count = bpm_count = 0
            timestamps_of = (spo2.timestamp > bpm.timestamp) - (
                spo2.timestamp < bpm.timestamp
            )

            spo2_count += timestamps_of > 0
            bpm_count += timestamps_of < 0

            spo2_and_bpm_vitals = Vitals(spo2, bpm)
            spo2, bpm = sync_from[timestamps_of](spo2_and_bpm_vitals)
            if spo2_and_bpm_vitals == Vitals(spo2, bpm):
                return
        print(spo2, bpm)
        yield spo2, bpm
        if spo2_count or bpm_count:
            logger.debug(
                f"{spo2_count} spo2 entries, {bpm_count} heart rate entries "
                "skipped to find matching timestamp"
            )

        spo2_entries += spo2_count + 1
        bpm_entries += bpm_count + 1
    logger.debug(
        f"{spo2_entries} Sp02 entries, {bpm_entries} heart rate entries processed"
    )


def parse_sleep_health_data(
    spo2_data: Generator[VitalsData, None, None],
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
        spo2_data (Generator[VitalsData, None, None]): A generator of tuples
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

    for sp02, bpm in sync_timestamps(spo2_data, bpm_data):
        session.append((
            sp02.timestamp,
            sp02.data,
            bpm.data,
        ))
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
