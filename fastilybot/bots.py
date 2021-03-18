"""Bot tasks for FastilyBot on the English Wikipedia"""

import logging
import re

from collections import deque
from datetime import datetime
from itertools import chain

from pwiki.gquery import GQuery
from pwiki.mquery import MQuery
from pwiki.ns import NS
from pwiki.oquery import OQuery
from pwiki.wiki import Wiki

from .constants import C, T
from .core import CQuery, FastilyBotBase, fetch_report, XQuery

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

    ##################################################################################################
    ######################################## H E L P E R S ###########################################
    ##################################################################################################

    def _regex_for(self, title: str) -> str:
        """Generates a regex matching a template and its redirects, `title`.  This method is cached, so repeated calls to will not result in new queries to the server.

        Args:
            title (str): The template to generate a regex for.

        Returns:
            str: The regex
        """
        if title in self._regex_cache:
            return self._regex_cache[title]

        self._regex_cache[title] = (r := r"(?si)\{\{(Template:)??(" + "|".join([self.wiki.nss(t) for t in (self.wiki.what_links_here(title, True) + [title])]) + r").*?\}\}\n?")
        return r

    def _category_members_recursive(self, title: str) -> set:
        """Recursively fetch pages in the category specified by `title`.  Includes logic to avoid category loops.

        Args:
            title (str): The category to recursively get members of.

        Returns:
            set: All recursively fetched members of the category
        """
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

    ##################################################################################################
    ########################################### B O T S ##############################################
    ##################################################################################################

    def find_deleted_on_commons(self):
        """Replace instances of `{{Nominated for deletion on Commons}}` on files that have been deleted on Commons with `{{Deleted on Commons}}`.  Task 8"""
        nfdc_regex = re.compile(self._regex_for(T.NFDC))
        dc_title = self.wiki.nss(T.DC)

        # grab all files and alleged commons copies
        d = {}
        for k, v in (t_table := MQuery.page_text(self.wiki, CQuery.what_transcludes_here(self.wiki, T.NFDC, NS.FILE))).items():
            try:
                if t := nfdc_regex.search(v).group():
                    d[k] = str(self.wiki.parse(text=t).templates[0].pop())
            except Exception:
                log.warning("Could not parse text of '%s'", k, exc_info=True)

        # normalize
        n_table = OQuery.normalize_titles(self.wiki, list(d.values()))
        d = {k: self.wiki.convert_ns(n_table[v], NS.FILE) for k, v in d.items()}

        # remove existent files and files that were not actually deleted
        e_table = XQuery.exists_filter(self.com, list(d.values()))  # only pages that exist
        for k, v in d.items():
            if v not in e_table and next(GQuery.logs(self.com, v, "delete", "delete"), None):
                self.wiki.edit(k, nfdc_regex.sub(f"{{{{{dc_title}|{self.wiki.nss(v)}}}}}", t_table[k]), "BOT: This file was deleted on Commons")

    def find_license_conflicts(self):
        """Finds files which are labled as both free and non-free.  Task 5"""
        for s in self._difference_of(2, *self.wiki.links_on_page("User:FastilyBot/Task5/Ignore")):
            self.wiki.edit(s, prepend="{{Wrong-license}}\n", summary="BOT: Marking conflict in copyright status")

    def flag_orphaned_free_images(self):
        """Finds freely licensed files with no fileusage and tags them with `{{Orphan image}}`.  Task 10"""
        oi_title = self.wiki.nss(T.OI)
        for s in XQuery.exists_filter(self.wiki, self._difference_of(3, 9, T.B, T.DF, 4, *self.wiki.links_on_page("User:FastilyBot/Task10/Ignore"))):
            self.wiki.edit(s, append=f"\n{{{{{oi_title}}}}}", summary="BOT: this file has no inbound file usage")

    def mtc_clerk(self):
        """Find and fix tags for files tagged for transfer to Commons which have already transferred.  Task 1"""
        ncd_l = set(CQuery.what_transcludes_here(self.wiki, T.NCD))
        mtc_regex = self._regex_for(T.CTC)

        d = {k: v[0] for k, v in MQuery.duplicate_files(self.wiki, list(self._difference_of(fetch_report(1).intersection(CQuery.what_transcludes_here(self.wiki, T.CTC, NS.FILE)),
                                                                                            T.KL, C.CTC_II)), False, True).items() if v}
        texts = MQuery.page_text(self.wiki, list(d.keys()))

        for k, v in d.items():
            if (n := re.sub(mtc_regex, "", texts[k])) != texts[k]:
                self.wiki.edit(k, ("" if k in ncd_l else self.mtc_tag % v + "\n") + n, "BOT: This file has already been copied to Commons")

    def untag_unorphaned_images(self):
        """Removes the Orphan image tag from free files which are no longer orphaned.  Task 4"""
        oi_regex = self._regex_for(T.OI)

        for s in (self._difference_of(9, self._difference_of(3, 4), T.B) & fetch_report(6)):
            self.wiki.replace_text(s, oi_regex, summary="BOT: File contains inbound links")

    def remove_bad_mtc(self):
        """Removes the MTC tag from files which do not appear to be eligible for Commons.  Task 2"""
        l = self._difference_of(T.CTC, self._category_members_recursive(C.CTC_H), C.CTC_II)

        mtc_regex = self._regex_for(T.CTC)

        for s in chain.from_iterable(l.intersection(cat) for cat in self.wiki.links_on_page("User:FastilyBot/Task2/Blacklist")):
            self.wiki.replace_text(s, mtc_regex, summary="BOT: This file does not appear to be eligible for Commons")

    def nominated_for_deleteion_on_commons(self):
        """Replaces `{{Now Commons}}` locally with `{{Nominated for deletion on Commons}}` if the file is nominated for deletion on Commons.  Task 7"""
        ncd_regex = self._regex_for(T.NCD)
        l = set(CQuery.what_transcludes_here(self.com, T.DTT, NS.FILE))

        for k, v in MQuery.duplicate_files(self.wiki, CQuery.what_transcludes_here(self.wiki, T.NCD, NS.FILE), False, True).items():
            if v and v[0] in l:
                self.wiki.replace_text(k, ncd_regex, f"{{{{Nominated for deletion on Commons|{self.wiki.nss(v[0])}}}}}", "BOT: File is up for deletion on Commons")
