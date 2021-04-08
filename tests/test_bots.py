"""Tests for bot module of fastilybot"""

from datetime import timedelta

from fastilybot.bots import _yesterday_and_today, Bots

from .base import WikiTestCase


class TestBots(WikiTestCase):
    """Tests for Bots' helper functions"""

    @classmethod
    def setUpClass(cls) -> None:
        """Sets up an instance of Bots pointed at testwiki."""
        super().setUpClass()
        cls.b = Bots(cls.wiki)

    def test_category_members_recursive(self):
        self.assertCountEqual(["File:FastilyTestCircle1.svg", "File:FastilyTestCircle2.svg"], self.b._category_members_recursive("Category:Fastily Test3"))
        self.assertCountEqual(["User:Fastily/Sandbox/Nested 1", "User:Fastily/Sandbox/Nested 2"], self.b._category_members_recursive("Category:Fastily Test Nested"))
        self.assertFalse(self.b._category_members_recursive("Category:DoesNotExist37458634578"))

    def test_ignore_of(self):
        self.assertRegex(self.b._ignore_of(9000), r"User:.+?/Task/9000/Ignore")

    def test_config_of(self):
        self.assertRegex(self.b._config_of(69420, "Butter"), r"User:.+?/Task/69420/Butter")

    def test_yesterday_and_today(self):
        yesterday, today = _yesterday_and_today()
        self.assertEqual(yesterday, today - timedelta(1))  # can't really test this, sanity check only
