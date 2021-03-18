"""Shared template TestCase classes and methods for use in fastilybot tests"""

from unittest import TestCase

from pwiki.wiki import Wiki

from fastilybot.core import FastilyBotBase


class WikiTestCase(TestCase):
    """Basic template for read-only tests"""

    _WIKI = Wiki("test.wikipedia.org", cookie_jar=None)

    @classmethod
    def setUpClass(cls) -> None:
        """Sets up an instance of a `Wiki` pointed to testwiki"""
        cls.wiki = WikiTestCase._WIKI


class FastilyBotTestCase(WikiTestCase):
    """Basic template for fastilybot-related tests"""

    @classmethod
    def setUpClass(cls) -> None:
        """Sets up an instance of FastilyBotBase pointed at testwiki."""
        super().setUpClass()
        cls.b = FastilyBotBase(cls.wiki)
