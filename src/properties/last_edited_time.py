from dataclasses import dataclass
from datetime import datetime, timedelta

from datetime_utils import JST
from properties.property import Property


@dataclass
class LastEditedTime(Property):
    value: datetime

    def __init__(
        self,
        name: str,
        value: datetime,
        id: str | None = None,  # noqa: A002
    ) -> None:
        self.name = name
        self.value = value
        self.id = id

    @staticmethod
    def of(name: str, params: dict) -> "LastEditedTime":
        datetime_ = datetime.fromisoformat(params["last_edited_time"]) + timedelta(hours=9)
        datetime_ = datetime_.replace(tzinfo=JST)
        return LastEditedTime(name=name, value=datetime_, id=params.get("id"))

    def __dict__(self) -> dict:
        result = {
            "type": self.type,
            self.type: self.value.isoformat(),
        }
        if self.id is not None:
            result["id"] = self.id
        return result

    def value_for_filter(self) -> str:
        return self.value.isoformat()

    @property
    def type(self) -> str:
        return "last_edited_time"
