"""Tests for bot module of fastilybot"""

import re

from fastilybot.bots import Bots

from .base import WikiTestCase


class TestBots(WikiTestCase):
    """Tests for Bots' helper functions"""

    @classmethod
    def setUpClass(cls) -> None:
        """Sets up an instance of Bots pointed at testwiki."""
        super().setUpClass()
        cls.b = Bots(cls.wiki)

    def test_regex_for(self):
        self.assertEqual(str_regex := self.b._regex_for(target := "Template:FastilyTest"), self.b._regex_for(target))
        p = re.compile(str_regex)

        self.assertTrue(p.search("{{FastilyTest|A|B|3=C}}"))
        self.assertTrue(p.search("\n\nFoobar\n{{fastilyTest2|{{Red|Hello, World!}}}}     "))
        self.assertFalse(p.search("\n\nFoobar\n{{Foobar|{{Blue|baz}}}}     "))
        self.assertTrue(p.search("\n\nFoobar\n{{Foobar|{{template:fastilyTest2|baz}}}}     "))

    def test_category_members_recursive(self):
        self.assertCountEqual(["File:FastilyTestCircle1.svg", "File:FastilyTestCircle2.svg"], self.b._category_members_recursive("Category:Fastily Test3"))
        self.assertCountEqual(["User:Fastily/Sandbox/Nested 1", "User:Fastily/Sandbox/Nested 2"], self.b._category_members_recursive("Category:Fastily Test Nested"))
        self.assertFalse(self.b._category_members_recursive("Category:DoesNotExist37458634578"))
