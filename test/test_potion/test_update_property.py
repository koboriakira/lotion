from unittest import TestCase

import pytest

from page.page_id import PageId
from potion import Potion
from properties.checkbox import Checkbox
from properties.number import Number
from properties.property import Property
from properties.relation import Relation
from properties.status import Status
from properties.text import Text
from properties.title import Title
from properties.url import Url


class TestUpdateProperty(TestCase):
    DATABASE_ID = "1596567a3bbf80d58251f1159e5c40fa"

    def setUp(self) -> None:
        self.suite = Potion.get_instance()
        created_page = self.suite.create_page_in_database(
            database_id=self.DATABASE_ID, properties=[Title.from_plain_text(text="テスト")]
        )
        self.page = self.suite.retrieve_page(page_id=created_page["id"])
        return super().setUp()

    def tearDown(self) -> None:
        self.suite.remove_page(self.page.page_id.value)
        return super().setUp()

    @pytest.mark.post_api()
    def test_名前を変更する(self):
        title = Title.from_plain_text(text="テスト")
        actual = self._update_page(property=title)
        self.assertEqual(actual.get_title().text, "テスト")

    @pytest.mark.post_api()
    def test_テキストを変更する(self):
        text_prop = Text.from_plain_text(name="テキスト", text="テスト")
        actual = self._update_page(property=text_prop)
        self.assertEqual(actual.get_text(name="テキスト").text, "テスト")

    @pytest.mark.post_api()
    def test_数値を変更する(self):
        number_prop = Number.from_num(name="数値", value=1)
        actual = self._update_page(property=number_prop)
        self.assertEqual(actual.get_number(name="数値").number, 1)

    @pytest.mark.post_api()
    def test_セレクトを変更する(self):
        self.skipTest("ユーザが名前ベースでセレクトを選べるようにしたい")

    @pytest.mark.post_api()
    def test_マルチセレクトを変更する(self):
        self.skipTest("ユーザが名前ベースでマルチセレクトを選べるようにしたい")

    @pytest.mark.post_api()
    def test_ファイルを変更する(self):
        self.skipTest("ファイルプロパティを作成するところから")

    @pytest.mark.post_api()
    def test_ユーザーを変更する(self):
        self.skipTest("ユーザープロパティを作成するところから")

    @pytest.mark.post_api()
    def test_メールを変更する(self):
        self.skipTest("メールプロパティを作成するところから")

    @pytest.mark.post_api()
    def test_電話番号を変更する(self):
        self.skipTest("電話番号プロパティを作成するところから")

    @pytest.mark.post_api()
    def test_数式を変更する(self):
        self.skipTest("数式プロパティを作成するところから")

    @pytest.mark.post_api()
    def test_ロールアップを変更する(self):
        self.skipTest("ロールアッププロパティを作成するところから")

    @pytest.mark.post_api()
    def test_ステータスを変更する(self):
        status_prop = Status.from_status_name(name="ステータス", status_name="未着手")
        actual = self._update_page(property=status_prop)
        self.assertEqual(actual.get_status(name="ステータス").status_name, "未着手")

    @pytest.mark.post_api()
    def test_チェックボックスを変更する(self):
        checkbox_prop = Checkbox.true(name="チェックボックス")
        actual = self._update_page(property=checkbox_prop)
        self.assertEqual(actual.get_checkbox(name="チェックボックス").checked, True)

    @pytest.mark.post_api()
    def test_URLを変更する(self):
        url_prop = Url.from_url(name="URL", url="https://example.com")
        actual = self._update_page(property=url_prop)
        self.assertEqual(actual.get_url(name="URL").url, "https://example.com")

    @pytest.mark.post_api()
    def test_リレーションを変更する(self):
        # Given
        related_page = self.suite.create_page_in_database(
            database_id=self.DATABASE_ID, properties=[Title.from_plain_text(text="リレーション用ページ")]
        )
        page_id = PageId(related_page["id"])
        relation_prop = Relation.from_id(name="リレーション", id=page_id.value)

        # When, Then
        actual = self._update_page(property=relation_prop)
        actual_relation = actual.get_relation(name="リレーション")
        self.assertEqual(actual_relation.id_list, [page_id.value])

        # Teardown
        self.suite.remove_page(page_id.value)

    def _update_page(self, property: Property):
        # When
        properties = self.page.properties.append_property(property)
        self.suite.update_page(page_id=self.page.page_id.value, properties=properties.values)

        # Then
        return self.suite.retrieve_page(page_id=self.page.page_id.value)
