from datetime import timedelta
from enum import Enum


class ProcessStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class AnalyticsTimeWindow(str, Enum):
    HOUR = "1h"
    HOURS_8 = "8h"
    HOURS_12 = "12h"
    DAY = "1d"
    WEEK = "1w"

    @property
    def delta(self) -> timedelta:
        match self:
            case AnalyticsTimeWindow.HOUR:
                return timedelta(hours=1)
            case AnalyticsTimeWindow.HOURS_8:
                return timedelta(hours=8)
            case AnalyticsTimeWindow.HOURS_12:
                return timedelta(hours=12)
            case AnalyticsTimeWindow.DAY:
                return timedelta(days=1)
            case AnalyticsTimeWindow.WEEK:
                return timedelta(weeks=1)
        raise NotImplementedError

    @property
    def label(self) -> str:
        return self.value
