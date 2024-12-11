from dataclasses import dataclass
from datetime import datetime, timedelta

from datetime_utils import JST


@dataclass
class BaseTime:
    value: datetime

    @staticmethod
    def of(value: str) -> "BaseTime":
        datetime_ = datetime.fromisoformat(value) + timedelta(hours=9)
        datetime_ = datetime_.replace(tzinfo=JST)
        return BaseTime(value=datetime_)
