from fitbit2oscar import time_helpers
from fitbit2oscar.handlers import DataHandler


class HealthSyncHandler(DataHandler):
    package: str = "health_sync"

    def _build_glob_pattern(self):
        pass

    def _get_paths(self):
        pass

    def _get_timezone(self) -> None:
        self.timezone = time_helpers.get_local_timezone()
