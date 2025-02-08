import datetime
from collections.abc import Generator

from fitbit2oscar.time_helpers import convert_time_data
from fitbit2oscar._types import SleepData, SleepEntry


def parse_sleep_health_data(
    sp02_data: dict[datetime.datetime, int],
    bpm_data: dict[datetime.datetime, int],
    session_split: int = 15,
) -> list[list[tuple[datetime.datetime, int, int]]]:
    """
    Parses sleep health data into sessions.

    This function takes dictionaries containing sp02 and BPM data for each
    timestamp and splits them into sessions based on a specified session split
    time. It returns a list of sessions, where each session is a list of tuples
    containing timestamps, sp02, and BPM values.

    Args:
        sp02_data (dict[datetime.datetime, int]): A dictionary containing sp02
            data for each timestamp.
        bpm_data (dict[datetime.datetime, int]): A dictionary containing BPM
            data for each timestamp.
        session_split (int, optional): The session split time in minutes.
            Defaults to 15.

    Returns:
        list[list[tuple[datetime.datetime, int, int]]]: A list of sessions,
            where each session is a list of tuples containing timestamps,
            sp02, and BPM values.
    """
    sessions = []
    session = []

    prev_timestamp = None

    for timestamp in sorted(
        set(sp02_data.keys()).intersection(bpm_data.keys())
    ):
        session.append((timestamp, sp02_data[timestamp], bpm_data[timestamp]))
        if (
            prev_timestamp
            and prev_timestamp + datetime.timedelta(minutes=session_split)
            < timestamp
        ):
            sessions.append(session)
            session = []
        prev_timestamp = timestamp

    return sessions


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
                sleep_data["duration"] / 60000
            ),
            "light_sleep_duration": convert_time_data(
                sleep_data["levels"]["summary"]["light"]["minutes"]
            ),
            "deep_sleep_duration": convert_time_data(
                sleep_data["levels"]["summary"]["deep"]["minutes"]
            ),
            "rem_sleep_duration": convert_time_data(
                sleep_data["levels"]["summary"]["rem"]["minutes"]
            ),
            "wake_after_sleep_onset_duration": convert_time_data(
                sleep_data["wake_after_sleep_onset_duration"]
            ),
            "number_awakenings": sleep_data["levels"]["summary"]["wake"][
                "count"
            ],
            "sleep_efficiency": sleep_data["sleep_efficiency"],
            "hypnogram": f"[{','.join(generate_hypnogram(sleep_data["levels"]["data"]))}]",
        }
        for sleep_data in sleep_data_generator
    )
