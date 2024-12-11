import os
from logging import Logger, getLogger

from notion_client import Client
from notion_client.errors import APIResponseError, HTTPResponseError

from base_time import BaseTime
from src.base_operator import BaseOperator
from src.base_page import BasePage
from src.block import Block, BlockFactory
from src.filter.filter_builder import FilterBuilder
from src.page.page_id import PageId
from src.properties.cover import Cover
from src.properties.icon import Icon
from src.properties.properties import Properties
from src.properties.property import Property
from src.properties.title import Title
from src.property_translator import PropertyTranslator

NOTION_API_ERROR_BAD_GATEWAY = 502


class AppendBlockError(Exception):
    def __init__(self, block_id: str, blocks: list[dict], e: Exception) -> None:
        self.block_id = block_id
        self.blocks = blocks
        self.e = e
        super().__init__(f"block_id: {block_id}, blocks: {blocks}, error: {e}")


class NotionApiError(Exception):
    def __init__(
        self,
        page_id: str | None = None,
        database_id: str | None = None,
        e: APIResponseError | HTTPResponseError | None = None,
        properties: Properties | dict | None = None,
    ) -> None:
        self.database_id = database_id
        self.e = e
        self.properties = properties

        message = ""
        if e is not None:
            message += f", error: {e}"
        if page_id is not None:
            message += f"page_id: {page_id}"
        if database_id is not None:
            message += f"database_id: {database_id}"
        if properties is not None:
            properties_ = properties.__dict__() if isinstance(properties, Properties) else properties
            message += f", properties: {properties_}"
        super().__init__(message)


class Potion:
    def __init__(self, client: Client, max_retry_count: int = 3, logger: Logger | None = None) -> None:
        self.client = client
        self.max_retry_count = max_retry_count
        self._logger = logger or getLogger(__name__)

    @staticmethod
    def get_instance(max_retry_count: int = 3, logger: Logger | None = None) -> "Potion":
        client = Client(auth=os.getenv("NOTION_SECRET"))
        return Potion(client, max_retry_count=max_retry_count, logger=logger)

    def retrieve_page(self, page_id: str, page_model: BasePage | None = None) -> BasePage:
        """指定されたページを取得する"""
        page_entity = self.__retrieve_page(page_id=page_id)
        return self.__convert_page_model(page_entity=page_entity, include_children=True, page_model=page_model)

    def update_page(self, page_id: str, properties: list[Property] | None = None) -> dict:
        """指定されたページを更新する"""
        update_properties = Properties(values=properties or [])
        return self.__update(page_id=page_id, properties=update_properties)

    def retrieve_comments(self, page_id: str) -> list[dict]:
        """指定されたページのコメントを取得する"""
        comments = self.client.comments.list(
            block_id=page_id,
        )
        return comments["results"]

    def create_page_in_database(
        self,
        database_id: str,
        cover: Cover | None = None,
        properties: list[Property] | None = None,
        blocks: list[Block] | None = None,
    ) -> dict:
        """データベース上にページを新規作成する"""
        page = self.__create_page(
            database_id=database_id,
            cover=cover.__dict__() if cover is not None else None,
            properties=(Properties(values=properties).__dict__() if properties is not None else {}),
        )
        if blocks is not None:
            self.append_blocks(block_id=page["id"], blocks=blocks)
        return page

    def retrieve_database(  # noqa: PLR0913
        self,
        database_id: str,
        title: str | None = None,
        filter_param: dict | None = None,
        page_model: BasePage | None = None,
        include_children: bool | None = None,
    ) -> list[BasePage]:
        """指定されたデータベースのページを取得する"""
        results = self._database_query(database_id=database_id, filter_param=filter_param)
        pages: list[BasePage] = []
        for page_entity in results:
            page = self.__convert_page_model(
                page_entity=page_entity,
                include_children=include_children or False,
                page_model=page_model,
            )
            pages.append(page)
        if title is not None:
            pages = list(filter(lambda p: p.properties.get_title().text == title, pages))
        return pages

    def find_page_by_title(
        self,
        database_id: str,
        title: str,
        title_key_name: str | None = "名前",
        page_model: BasePage | None = None,
    ) -> BasePage | None:
        """タイトルだけをもとにデータベースのページを取得する"""
        title_property = Title.from_plain_text(text=title, name=title_key_name)
        filter_param = FilterBuilder.build_simple_equal_condition(title_property)
        results = self.retrieve_database(
            database_id=database_id,
            filter_param=filter_param,
            page_model=page_model,
        )
        if len(results) == 0:
            return None
        if len(results) > 1:
            warning_message = f"Found multiple pages with the same title: {title}"
            self._logger.warning(warning_message)
        return results[0]

    def _database_query(
        self,
        database_id: str,
        filter_param: dict | None = None,
        start_cursor: str | None = None,
    ) -> dict:
        if filter_param is None:
            return self._database_query_without_filter(database_id=database_id, start_cursor=start_cursor)
        results = []
        while True:
            data = self.__database_query(
                database_id=database_id,
                filter_param=filter_param,
                start_cursor=start_cursor,
            )
            results += data.get("results")
            if not data.get("has_more"):
                return results
            start_cursor = data.get("next_cursor")

    def _database_query_without_filter(self, database_id: str, start_cursor: str | None = None) -> dict:
        results = []
        while True:
            data = self.__database_query(
                database_id=database_id,
                start_cursor=start_cursor,
            )
            results += data.get("results")
            if not data.get("has_more"):
                return results
            start_cursor = data.get("next_cursor")

    def list_blocks(self, block_id: str) -> list[Block]:
        """指定されたブロックの子ブロックを取得する"""
        return self.__get_block_children(page_id=block_id)

    def append_block(self, block_id: str, block: Block) -> dict:
        """指定されたブロックに子ブロックを追加する"""
        return self.append_blocks(block_id=block_id, blocks=[block])

    def append_blocks(self, block_id: str, blocks: list[Block]) -> dict:
        """指定されたブロックに子ブロックを追加する"""
        return self.__append_block_children(
            block_id=block_id,
            children=[b.to_dict(for_create=True) for b in blocks],
        )

    def append_comment(self, page_id: str, text: str) -> dict:
        """指定されたページにコメントを追加する"""
        return self.client.comments.create(
            parent={"page_id": page_id},
            rich_text=[{"text": {"content": text}}],
        )

    def clear_page(self, page_id: str) -> None:
        """指定されたページのブロックを削除する"""
        blocks = self.list_blocks(block_id=page_id)
        for block in blocks:
            if block.id is None:
                raise ValueError(f"block_id is None: {block}")
            self.client.blocks.delete(block_id=block.id)

    def remove_page(self, page_id: str) -> None:
        """指定されたページを削除する"""
        self.__archive(page_id=page_id)

    def __append_block_children(self, block_id: str, children: list[dict], retry_count: int = 0) -> dict:
        try:
            return self.client.blocks.children.append(block_id=block_id, children=children)
        except APIResponseError as e:
            if self.__is_able_retry(status=e.status, retry_count=retry_count):
                return self.__append_block_children(block_id=block_id, children=children, retry_count=retry_count + 1)
            raise NotionApiError(page_id=block_id, e=e) from e
        except HTTPResponseError as e:
            if self.__is_able_retry(status=e.status, retry_count=retry_count):
                return self.__append_block_children(block_id=block_id, children=children, retry_count=retry_count + 1)
            raise NotionApiError(page_id=block_id, e=e) from e
        except TypeError as e:
            raise AppendBlockError(block_id=block_id, blocks=children, e=e) from e

    def __convert_page_model(
        self,
        page_entity: dict,
        include_children: bool | None = None,
        page_model: BasePage | None = None,
    ) -> BasePage:
        include_children = (
            include_children if include_children is not None else True
        )  # 未指定の場合はchildrenを取得する

        id_ = PageId(page_entity["id"])
        url = page_entity["url"]
        created_time = BaseTime.of(page_entity["created_time"])
        last_edited_time = BaseTime.of(page_entity["last_edited_time"])
        created_by = BaseOperator.of(page_entity["created_by"])
        last_edited_by = BaseOperator.of(page_entity["last_edited_by"])
        cover = Cover.of(page_entity["cover"]) if page_entity["cover"] is not None else None
        icon = Icon.of(page_entity["icon"]) if page_entity["icon"] is not None else None
        archived = page_entity["archived"]
        properties = PropertyTranslator.from_dict(page_entity["properties"])
        block_children = self.__get_block_children(page_id=id_.value) if include_children else []

        return BasePage(
            id_=id_,
            url=url,
            created_time=created_time,
            last_edited_time=last_edited_time,
            _created_by=created_by,
            _last_edited_by=last_edited_by,
            cover=cover,
            icon=icon,
            archived=archived,
            properties=properties,
            block_children=block_children,
        )

    def __retrieve_page(self, page_id: str, retry_count: int = 0) -> dict:
        try:
            return self.client.pages.retrieve(page_id=page_id)
        except APIResponseError as e:
            if self.__is_able_retry(status=e.status, retry_count=retry_count):
                return self.__retrieve_page(page_id=page_id, retry_count=retry_count + 1)
            raise NotionApiError(page_id=page_id, e=e) from e
        except HTTPResponseError as e:
            if self.__is_able_retry(status=e.status, retry_count=retry_count):
                return self.__retrieve_page(page_id=page_id, retry_count=retry_count + 1)
            raise NotionApiError(page_id=page_id, e=e) from e

    def __get_block_children(self, page_id: str) -> list[Block]:
        block_entities = self.__list_blocks(block_id=page_id)["results"]
        return [BlockFactory.create(b) for b in block_entities]

    def __list_blocks(self, block_id: str, retry_count: int = 0) -> dict:
        try:
            return self.client.blocks.children.list(block_id=block_id)
        except APIResponseError as e:
            if self.__is_able_retry(status=e.status, retry_count=retry_count):
                return self.__list_blocks(block_id=block_id, retry_count=retry_count + 1)
            raise NotionApiError(page_id=block_id, e=e) from e
        except HTTPResponseError as e:
            if self.__is_able_retry(status=e.status, retry_count=retry_count):
                return self.__list_blocks(block_id=block_id, retry_count=retry_count + 1)
            raise NotionApiError(page_id=block_id, e=e) from e

    def __archive(self, page_id: str, retry_count: int = 0) -> dict:
        try:
            return self.client.pages.update(
                page_id=page_id,
                archived=True,
            )
        except APIResponseError as e:
            if self.__is_able_retry(status=e.status, retry_count=retry_count):
                return self.__archive(page_id=page_id, retry_count=retry_count + 1)
            raise NotionApiError(page_id=page_id, e=e) from e
        except HTTPResponseError as e:
            if self.__is_able_retry(status=e.status, retry_count=retry_count):
                return self.__archive(page_id=page_id, retry_count=retry_count + 1)
            raise NotionApiError(page_id=page_id, e=e) from e

    def __update(self, page_id: str, properties: Properties, retry_count: int = 0) -> dict:
        try:
            return self.client.pages.update(
                page_id=page_id,
                properties=properties.exclude_button().__dict__(),
            )
        except APIResponseError as e:
            if self.__is_able_retry(status=e.status, retry_count=retry_count):
                return self.__update(page_id=page_id, properties=properties, retry_count=retry_count + 1)
            raise NotionApiError(page_id=page_id, e=e, properties=properties) from e
        except HTTPResponseError as e:
            if self.__is_able_retry(status=e.status, retry_count=retry_count):
                return self.__update(page_id=page_id, properties=properties, retry_count=retry_count + 1)
            raise NotionApiError(page_id=page_id, e=e, properties=properties) from e

    def __create_page(
        self,
        database_id: str,
        properties: dict,
        cover: dict | None = None,
        retry_count: int = 0,
    ) -> dict:
        try:
            return self.client.pages.create(
                parent={"type": "database_id", "database_id": database_id},
                cover=cover,
                properties=properties if properties != {} else None,
            )
        except APIResponseError as e:
            if self.__is_able_retry(status=e.status, retry_count=retry_count):
                self.__create_page(
                    database_id=database_id,
                    properties=properties,
                    cover=cover,
                    retry_count=retry_count + 1,
                )
            raise NotionApiError(database_id=database_id, e=e, properties=properties) from e
        except HTTPResponseError as e:
            if self.__is_able_retry(status=e.status, retry_count=retry_count):
                self.__create_page(
                    database_id=database_id,
                    properties=properties,
                    cover=cover,
                    retry_count=retry_count + 1,
                )
            raise NotionApiError(database_id=database_id, e=e, properties=properties) from e

    def __database_query(
        self,
        database_id: str,
        start_cursor: str | None = None,
        filter_param: dict | None = None,
        retry_count: int = 0,
    ) -> dict:
        try:
            if filter_param is None:
                return self.client.databases.query(
                    database_id=database_id,
                    start_cursor=start_cursor,
                )
            return self.client.databases.query(
                database_id=database_id,
                start_cursor=start_cursor,
                filter=filter_param,
            )
        except APIResponseError as e:
            if self.__is_able_retry(status=e.status, retry_count=retry_count):
                return self.__database_query(
                    database_id=database_id,
                    start_cursor=start_cursor,
                    filter_param=filter_param,
                    retry_count=retry_count + 1,
                )
            raise NotionApiError(database_id=database_id, e=e) from e
        except HTTPResponseError as e:
            if self.__is_able_retry(status=e.status, retry_count=retry_count):
                return self.__database_query(
                    database_id=database_id,
                    start_cursor=start_cursor,
                    filter_param=filter_param,
                    retry_count=retry_count + 1,
                )
            raise NotionApiError(database_id=database_id, e=e) from e

    def __is_able_retry(self, status: int, retry_count: int) -> bool:
        return status == NOTION_API_ERROR_BAD_GATEWAY and retry_count < self.max_retry_count
