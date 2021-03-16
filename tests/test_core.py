from unittest import TestCase

from pwiki.ns import NS
from pwiki.wiki import Wiki

from fastilybot.core import FastilyBotBase, _CACHE_ROOT, fetch_report


class TestCore(TestCase):

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


class TestBotBase(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.wiki = Wiki("test.wikipedia.org", cookie_jar=None)

    def test_resolve_entity(self):
        b = FastilyBotBase(self.wiki)

        # sets, lists
        expected = {1, 2, 3, 4, 5}
        self.assertSetEqual(expected, b._resolve_entity(expected))
        expected = [5, 4, 3, 2, 1]
        self.assertListEqual(expected, b._resolve_entity(expected))

        # Categories
        self.assertListEqual([], b._resolve_entity(("Category:Fastily Test - Doesn't Exist 634753478", NS.PROJECT)))
        self.assertListEqual(["User:Fastily/Sandbox/Page/2"], b._resolve_entity(("Category:Fastily Test2", NS.USER)))
        self.assertCountEqual(["File:FastilyTest.png"], b._resolve_entity("Category:Fastily Test2"))
        self.assertCountEqual(["User:Fastily/Sandbox/Page/2", "File:FastilyTest.png"], b._resolve_entity("Category:Fastily Test2", None))

        # Templates
        self.assertListEqual([], b._resolve_entity("Template:FastilyTest"))
        self.assertListEqual(["FastilyTest"], b._resolve_entity(("Template:FastilyTest", NS.MAIN)))

        # Reports
        result = b._resolve_entity(2)
        self.assertIsInstance(result, set)

        self.assertTrue(result)
        self.assertTrue(list(result)[0].startswith("File:"))

        result = b._resolve_entity((2, NS.CATEGORY))
        self.assertTrue(result)
        self.assertTrue(list(result)[0].startswith("Category:"))

        result = b._resolve_entity((2, None))
        self.assertTrue(result)
        self.assertFalse(list(result)[0].startswith("File:"))
