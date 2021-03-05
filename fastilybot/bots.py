"""Bot tasks for FastilyBot on the English Wikipedia"""

import logging
import re

from collections import deque
from datetime import datetime
from itertools import chain

from pwiki.mquery import MQuery
from pwiki.ns import NS
from pwiki.wiki import Wiki

from .core import CQuery, FastilyBotBase, fetch_report

log = logging.getLogger(__name__)


class Bots(FastilyBotBase):
    """Fastily's Wikipedia bot tasks"""

    def __init__(self, wiki: Wiki) -> None:
        """Initializer, creates a new Bots object.

        Args:
            wiki (Wiki): The Wiki object to use
        """
        super().__init__(wiki)

        self._regex_cache: dict = {}
        self.mtc_tag: str = f"{{{{Now Commons|%s|date={datetime.utcnow():%-d %B %Y}|bot={self.wiki.username}}}}}"

    def _regex_for(self, title: str) -> str:
        """Generates a regex matching a template and its redirects, `title`.  This method is cached, so repeated calls to will not result in new queries to the server.

        Args:
            title (str): The template to generate a regex for.

        Returns:
            str: The regex
        """
        if title in self._regex_cache:
            return self._regex_cache[title]

        self._regex_cache[title] = (r := r"(?si)\{\{(Template:)??(" + "|".join([self.wiki.nss(t) for t in self.wiki.what_links_here(title, True)]) + r").*?\}\}\n?")
        return r

    def _category_members_recursive(self, title: str) -> set:
        q = deque([title])
        visited = set()
        out = set()

        cat_ns = self.wiki.ns_manager.stringify(NS.CATEGORY)

        while q:
            if (cat := q.pop()) in visited:
                continue

            for s in self.wiki.category_members(cat):
                if self.wiki.which_ns(s) == cat_ns:
                    q.append(s)
                else:
                    out.add(s)

            visited.add(cat)

        return out

    def find_license_conflicts(self):
        """Finds files which are labled as both free and non-free.  Task 5"""
        for s in self._difference_of(2, *self.wiki.links_on_page("User:FastilyBot/Task5/Ignore")):
            self.wiki.edit(s, prepend="{{Wrong-license}}\n", summary="BOT: Marking conflict in copyright status")

    def mtc_clerk(self):
        """Find and fix tags for files tagged for transfer to Commons which have already transferred.  Task 1"""
        ncd = set(CQuery.what_transcludes_here(self.wiki, "Template:Now Commons"))
        mtc_regex = self._regex_for("Template:Copy to Wikimedia Commons")

        d = {k: v[0] for k, v in MQuery.duplicate_files(self.wiki, list(self._difference_of(fetch_report(1).intersection(CQuery.what_transcludes_here(self.wiki, "Template:Copy to Wikimedia Commons", NS.FILE)),
                                                                                            "Template:Keep local", "Category:Copy to Wikimedia Commons (inline-identified)")), False, True).items() if v}
        texts = MQuery.page_text(self.wiki, list(d.keys()))

        for k, v in d.items():
            if (n := re.sub(mtc_regex, "", texts[k])) != texts[k]:
                self.wiki.edit(k, ("" if k in ncd else self.mtc_tag % v + "\n") + n, "BOT: This file has already been copied to Commons")

    def untag_unorphaned_images(self):
        """Removes the Orphan image tag from free files which are no longer orphaned.  Task 4"""
        oi_regex = self._regex_for("Template:Orphan image")

        for s in (self._difference_of(9, self._difference_of(3, 4), "Template:Bots") & fetch_report(6)):
            self.wiki.replace_text(s, oi_regex, summary="BOT: File contains inbound links")

    def remove_bad_mtc(self):
        """Removes the MTC tag from files which do not appear to be eligible for Commons.  Task 2"""
        l = self._difference_of("Template:Copy to Wikimedia Commons", self._category_members_recursive("Category:Copy to Wikimedia Commons reviewed by a human"), "Category:Copy to Wikimedia Commons (inline-identified)")

        mtc_regex = self._regex_for("Template:Copy to Wikimedia Commons")

        for s in list(chain.from_iterable(l.intersection(cat) for cat in self.wiki.links_on_page("User:FastilyBot/Task2/Blacklist"))):
            self.wiki.replace_text(s, mtc_regex, summary="BOT: This file does not appear to be eligible for Commons")

    def nominated_for_deleteion_on_commons(self):
        """Replaces `{{Now Commons}}` locally with `{{Nominated for deletion on Commons}}` if the file is nominated for deletion on Commons.  Task 7"""
        ncd = "Template:Now Commons"
        ncd_regex = self._regex_for(ncd)
        l = set(CQuery.what_transcludes_here(self.com, "Template:Deletion template tag", NS.FILE))

        for k, v in MQuery.duplicate_files(self.wiki, CQuery.what_transcludes_here(self.wiki, ncd, NS.FILE), False, True).items():
            if v and v[0] in l:
                self.wiki.replace_text(k, ncd_regex, f"{{{{Nominated for deletion on Commons|{self.wiki.nss(v[0])}}}}}", "BOT: File is up for deletion on Commons")
