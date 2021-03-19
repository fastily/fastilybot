"""Tests for core modules of fastilybot"""

from unittest import TestCase

from pwiki.ns import NS

from fastilybot.core import _CACHE_ROOT, CQuery, fetch_report, XQuery

from .base import FastilyBotTestCase, WikiTestCase


class TestCore(TestCase):
    """Tests for core's top level methods"""

    def test_fetch_report(self):
        (target := _CACHE_ROOT / "report2.txt").unlink(missing_ok=True)  # clear test env

        result = fetch_report(2)
        self.assertIsInstance(result, set)
        self.assertTrue(target.is_file())
        self.assertTrue(result)
        self.assertTrue(list(result)[0].startswith("File:"))
        self.assertFalse(any("_" in s for s in result))

        result = fetch_report(2, "User:")
        self.assertTrue(result)
        self.assertTrue(list(result)[0].startswith("User:"))

        result = fetch_report(2, None)
        self.assertTrue(result)
        self.assertFalse(list(result)[0].startswith("File:"))

        target.unlink(missing_ok=True)  # cleanup


class TestBotBase(FastilyBotTestCase):
    """Tests for core's FastilyBotBase class"""

    def test_resolve_entity(self):
        # sets, lists
        expected = {1, 2, 3, 4, 5}
        self.assertSetEqual(expected, self.b._resolve_entity(expected))
        expected = [5, 4, 3, 2, 1]
        self.assertListEqual(expected, self.b._resolve_entity(expected))

        # Categories
        self.assertListEqual([], self.b._resolve_entity(("Category:Fastily Test - Doesn't Exist 634753478", NS.PROJECT)))
        self.assertListEqual(["User:Fastily/Sandbox/Page/2"], self.b._resolve_entity(("Category:Fastily Test2", NS.USER)))
        self.assertCountEqual(["File:FastilyTest.png"], self.b._resolve_entity("Category:Fastily Test2"))
        self.assertCountEqual(["User:Fastily/Sandbox/Page/2", "File:FastilyTest.png"], self.b._resolve_entity("Category:Fastily Test2", None))

        # Templates
        self.assertListEqual([], self.b._resolve_entity("Template:FastilyTest"))
        self.assertListEqual(["FastilyTest"], self.b._resolve_entity(("Template:FastilyTest", NS.MAIN)))

        # Reports
        result = self.b._resolve_entity(2)
        self.assertIsInstance(result, set)

        self.assertTrue(result)
        self.assertTrue(list(result)[0].startswith("File:"))

        result = self.b._resolve_entity((2, NS.CATEGORY))
        self.assertTrue(result)
        self.assertTrue(list(result)[0].startswith("Category:"))

        result = self.b._resolve_entity((2, None))
        self.assertTrue(result)
        self.assertFalse(list(result)[0].startswith("File:"))

        # Config pages
        self.assertCountEqual(["User:Fastily/Sandbox/Page/1", "User:Fastily/Sandbox/Page/2", "User:Fastily/Sandbox/Page/3", "File:FastilyTest.svg",
                               "User:Fastily/Sandbox/T", "FastilyTest"], self.b._resolve_entity("User:Fastily/Sandbox/TestConfig", default_nsl=None))
        self.assertSetEqual({"File:FastilyTest.svg"}, self.b._resolve_entity("User:Fastily/Sandbox/TestConfig"))
        self.assertSetEqual({"FastilyTest"}, self.b._resolve_entity(("User:Fastily/Sandbox/TestConfig", NS.MAIN)))
        self.assertFalse(self.b._resolve_entity("User:Fastily/Sandbox/DoesNotExist238478932"))

        # Errors
        self.assertIsNone(self.b._resolve_entity("Help:Foobar"))

    def test_difference_of(self):
        self.assertSetEqual({"File:FastilyTest.png"}, self.b._difference_of(("Category:Fastily Test2", None),  ["User:Fastily/Sandbox/Page/2"]))
        self.assertFalse(self.b._difference_of(2, 2))
        self.assertSetEqual({"File:FastilyTest.png"}, self.b._difference_of("Category:Fastily Test2"))

    def test_com(self):
        self.assertTrue(self.b.com)
        self.assertEqual("commons.wikimedia.org", self.b.com.domain)


class TestCQuery(WikiTestCase):
    """Tests for core's CQuery class"""

    def test_category_members(self):
        self.assertCountEqual(["User:Fastily/Sandbox/Page/2", "File:FastilyTest.png"], CQuery.category_members(self.wiki, "Category:Fastily Test2"))
        self.assertListEqual(["User:Fastily/Sandbox/Page/2"], CQuery.category_members(self.wiki, "Category:Fastily Test2", NS.USER))
        self.assertFalse(CQuery.category_members(self.wiki, "Category:Literally Does Not Exist 123456", NS.USER_TALK))

    def test_what_transcludes_here(self):
        self.assertFalse(CQuery.what_transcludes_here(self.wiki, "Template:FastilyTest", NS.TALK))
        self.assertListEqual(["FastilyTest"], CQuery.what_transcludes_here(self.wiki, "Template:FastilyTest", NS.MAIN))
        self.assertCountEqual(["User:Fastily/Sandbox/T", "FastilyTest"], CQuery.what_transcludes_here(self.wiki, "Template:FastilyTest"))
        self.assertFalse(CQuery.what_transcludes_here(self.wiki, "Template:Does Not Exist 37846237846"))


class TestXQuery(WikiTestCase):
    """Tests for core's XQuery class"""

    def test_exists_filter(self):
        target = ["Main Page", "User:Fastily/Sandbox", "User:Fastily/NoPageHere"]
        self.assertCountEqual(["Main Page", "User:Fastily/Sandbox"], XQuery.exists_filter(self.wiki, target))
        self.assertSetEqual({"User:Fastily/NoPageHere"}, XQuery.exists_filter(self.wiki, target, False))
