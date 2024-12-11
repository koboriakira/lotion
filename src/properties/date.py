from dataclasses import dataclass
from datetime import date, datetime

from src.datetime_utils import convert_to_date_or_datetime
from src.properties.property import Property


@dataclass
class Date(Property):
    start: str | None = None
    end: str | None = None
    time_zone: str | None = None

    DEFAULT_NAME = "日付"

    def __init__(
        self,
        name: str,
        id: str | None = None,  # noqa: A002
        start: str | None = None,
        end: str | None = None,
        time_zone: str | None = None,
    ) -> None:
        self.name = name
        self.id = id
        self.start = start
        self.end = end
        self.time_zone = time_zone

    @property
    def start_time(self) -> date | datetime | None:
        if self.start is None:
            return None
        return convert_to_date_or_datetime(self.start)

    @property
    def start_date(self) -> date | None:
        if self.start is None:
            return None
        return convert_to_date_or_datetime(self.start, cls=date)

    @property
    def start_datetime(self) -> datetime | None:
        if self.start is None:
            return None
        return convert_to_date_or_datetime(self.start, cls=datetime)

    @property
    def end_time(self) -> date | datetime | None:
        if self.end is None:
            return None
        return convert_to_date_or_datetime(self.end)

    @property
    def end_date(self) -> date | None:
        if self.end is None:
            return None
        return convert_to_date_or_datetime(self.end, cls=date)

    @property
    def end_datetime(self) -> datetime | None:
        if self.end is None:
            return None
        return convert_to_date_or_datetime(self.end, cls=datetime)

    @staticmethod
    def of(name: str = DEFAULT_NAME, param: dict | None = None) -> "Date":
        if param is None:
            param = {}
        if param["date"] is None:
            return Date(name=name, id=param["id"])
        return Date(
            name=name,
            id=param["id"],
            start=param["date"]["start"],
            end=param["date"]["end"],
            time_zone=param["date"]["time_zone"],
        )

    @staticmethod
    def from_start_date(name: str = DEFAULT_NAME, start_date: date | datetime | None = None) -> "Date":
        return Date(
            name=name,
            start=start_date.isoformat() if start_date is not None else None,
        )

    @staticmethod
    def from_range(start: date | datetime, end: date | datetime, name: str = DEFAULT_NAME) -> "Date":
        return Date(
            name=name,
            start=start.isoformat(),
            end=end.isoformat(),
        )

    def is_between(self, start: datetime, end: datetime) -> bool:
        start_datetime = self.start_datetime
        if start_datetime is None:
            return True
        if start.timestamp() > start_datetime.timestamp():
            return False
        if start_datetime.timestamp() > end.timestamp():  # noqa: SIM103
            return False
        return True

    @property
    def date(self) -> date:
        return convert_to_date_or_datetime(self.start, cls=date)

    def __dict__(self) -> dict:
        # 未指定の場合を考慮している
        _date = (
            {
                "start": self.start,
                "end": self.end,
                "time_zone": self.time_zone,
            }
            if self.start is not None
            else None
        )
        return {
            self.name: {
                "type": self.type,
                "date": _date,
            },
        }

    @property
    def type(self) -> str:
        return "date"

    def value_for_filter(self) -> str:
        return self.start
