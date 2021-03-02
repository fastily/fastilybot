import logging
import re

from datetime import datetime

from pwiki.mquery import MQuery
from pwiki.ns import NS
from pwiki.wiki import Wiki

from .core import CQuery, FastilyBotBase, fetch_report

log = logging.getLogger(__name__)


class Bots(FastilyBotBase):
    def __init__(self, wiki: Wiki) -> None:
        super().__init__(wiki)

        self._regex_cache: dict = {}
        self.mtc_tag: str = f"{{{{Now Commons|%s|date={datetime.utcnow():%-d %B %Y}|bot={self.wiki.username}}}}}"

    def _regex_for(self, title: str):

        if title in self._regex_cache:
            return self._regex_cache[title]

        self._regex_cache[title] = (r := r"(?si)\{\{(Template:)??(" + "|".join([self.wiki.nss(t) for t in self.wiki.what_links_here(title, True)]) + r").*?\}\}\n?")
        return r

    def mtc_helper(self):
        """Find and fix tags for files tagged for transfer to Commons which have already transferred.  Task 1"""
        ncd = set(CQuery.what_transcludes_here(self.wiki, "Template:Now Commons"))
        mtc_regex = self._regex_for("Template:Copy to Wikimedia Commons")

        d = {k: v[0] for k, v in MQuery.duplicate_files(self.wiki, list(self._difference_of(fetch_report(1).intersection(CQuery.what_transcludes_here(self.wiki, "Template:Copy to Wikimedia Commons", NS.FILE)),
                                                                                            "Template:Keep local", "Category:Copy to Wikimedia Commons (inline-identified)")), False, True).items() if v}
        texts = MQuery.page_text(self.wiki, list(d.keys()))
        
        for k, v in d.items():
            if (n := re.sub(mtc_regex, "", texts[k])) != texts[k]:
                self.wiki.edit(k, ("" if k in ncd else self.mtc_tag % v + "\n") + n, "BOT: This file has already been copied to Commons")
