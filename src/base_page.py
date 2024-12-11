from dataclasses import dataclass, field
from datetime import datetime

from base_time import BaseTime
from src.base_operator import BaseOperator
from src.block import Block
from src.page.page_id import PageId
from src.properties.checkbox import Checkbox
from src.properties.cover import Cover
from src.properties.date import Date
from src.properties.icon import Icon
from src.properties.multi_select import MultiSelect
from src.properties.number import Number
from src.properties.properties import Properties
from src.properties.property import Property
from src.properties.relation import Relation
from src.properties.select import Select
from src.properties.status import Status
from src.properties.text import Text
from src.properties.title import Title
from src.properties.url import Url


class NotCreatedError(Exception):
    pass


class NotFoundPropertyError(Exception):
    def __init__(self, class_name: str, prop_name: str):
        super().__init__(f"{class_name} property not found. name: {prop_name}")


@dataclass
class BasePage:
    properties: Properties
    block_children: list[Block] = field(default_factory=list)
    id_: PageId | str | None = None
    url: str | None = None
    created_time: BaseTime | None = None
    last_edited_time: BaseTime | None = None
    _created_by: BaseOperator | None = None
    _last_edited_by: BaseOperator | None = None
    cover: Cover | None = None
    icon: Icon | None = None
    archived: bool | None = False
    parent: dict | None = None
    object = "page"

    @staticmethod
    def create(properties: list[Property] | None = None, blocks: list[Block] | None = None) -> "BasePage":
        return BasePage(
            id_=None,
            url=None,
            created_time=None,
            last_edited_time=None,
            _created_by=None,
            _last_edited_by=None,
            properties=Properties(values=properties or []),
            cover=None,
            icon=None,
            archived=False,
            parent=None,
            block_children=blocks or [],
        )

    def get_slack_text_in_block_children(self) -> str:
        # FIXME: block_childrenをBlocks型にしたうえで、メソッドをBlocksに移動する
        if not self.block_children or len(self.block_children) == 0:
            return ""
        return "\n".join([block.to_slack_text() for block in self.block_children])

    def get_title(self) -> Title:
        return self.properties.get_title()

    def get_title_text(self) -> str:
        return self.get_title().text

    @property
    def title(self) -> str:
        return self.get_title_text()

    @property
    def created_at(self) -> datetime:
        # プロパティとは別にページに埋め込まれた作成日時を取得する
        if self.created_time is None:
            raise NotCreatedError("created_at is None.")
        return self.created_time.value

    @property
    def updated_at(self) -> datetime:
        # プロパティとは別にページに埋め込まれた更新日時を取得する
        if self.last_edited_time is None:
            raise NotCreatedError("updated_at is None.")
        return self.last_edited_time.value

    def get_status(self, name: str) -> Status:
        return self._get_property(name=name, instance_class=Status)  # type: ignore

    def get_text(self, name: str) -> Text:
        return self._get_property(name=name, instance_class=Text)  # type: ignore

    def get_date(self, name: str) -> Date:
        return self._get_property(name=name, instance_class=Date)  # type: ignore

    def get_select(self, name: str) -> Select:
        return self._get_property(name=name, instance_class=Select)  # type: ignore

    def get_multi_select(self, name: str) -> MultiSelect:
        return self._get_property(name=name, instance_class=MultiSelect)  # type: ignore

    def get_relation(self, name: str) -> Relation:
        return self._get_property(name=name, instance_class=Relation)  # type: ignore

    def get_checkbox(self, name: str) -> Checkbox:
        return self._get_property(name=name, instance_class=Checkbox)  # type: ignore

    def get_url(self, name: str) -> Url:
        return self._get_property(name=name, instance_class=Url)  # type: ignore

    def get_number(self, name: str) -> Number:
        return self._get_property(name=name, instance_class=Number)  # type: ignore

    def _get_property(self, name: str, instance_class: type) -> Property:
        result = self.properties.get_property(name=name, instance_class=instance_class)
        if result is None:
            raise NotFoundPropertyError(class_name=instance_class.__name__, prop_name=name)
        return result

    def get_parant_database_id(self) -> str | None:
        """未実装。削除すべきかも"""
        if self.parent is None or "database_id" not in self.parent:
            return None
        return self.parent["database_id"]

    def update_id_and_url(self, page_id: str, url: str) -> None:
        self.id_ = page_id
        self.url = url

    def title_for_slack(self) -> str:
        """Slackでの表示用のリンクつきタイトルを返す"""
        return f"<{self.url}|{self.get_title_text()}>"

    def title_for_markdown(self) -> str:
        """Markdownでの表示用のリンクつきタイトルを返す"""
        return f"[{self.get_title_text()}]({self.url})"

    @property
    def id(self) -> str | None:
        if isinstance(self.id_, str):
            return self.id_
        return self.id_.value if self.id_ is not None else None

    @property
    def page_id(self) -> PageId:
        if self.id_ is None:
            raise NotCreatedError("page_id is None.")
        return PageId(self.id_) if isinstance(self.id_, str) else self.id_

    def is_created(self) -> bool:
        return self.id is not None

    def get_id_and_url(self) -> dict[str, str]:
        if self.id is None or self.url is None:
            raise NotCreatedError("id or url is None")
        return {
            "id": self.id,
            "url": self.url,
        }

    @property
    def created_by(self) -> BaseOperator:
        if self._created_by is None:
            raise NotCreatedError("created_by is None.")
        return self._created_by

    @property
    def edited_by(self) -> BaseOperator:
        if self._last_edited_by is None:
            raise NotCreatedError("created_by is None.")
        return self._last_edited_by
