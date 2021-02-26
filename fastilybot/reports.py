import json
import logging
import re

from collections.abc import Iterable
from itertools import chain
from typing import Union

from pwiki.mquery import MQuery
from pwiki.ns import NS
from pwiki.wiki import Wiki

from .utils import CQuery, fetch_report

log = logging.getLogger(__name__)


_UPDATED_AT = "This report updated at <onlyinclude>~~~~~</onlyinclude>\n"

_UPDATING_REPORT = "BOT: Updating report"

_DBR = "Wikipedia:Database reports/"


_DMY_REGEX = r"\d{1,2}? (January|February|March|April|May|June|July|August|September|October|November|December) \d{4}?"


def _listify(l: Iterable, should_escape: bool = True, header: str = _UPDATED_AT) -> str:
    c = ":" if should_escape else ""
    return header + "\n".join((f"*[[{c}{s}]]" for s in l))


class Reports:
    """Fastily's Wikipedia database reports"""

    def __init__(self, wiki: Wiki):
        self.wiki: Wiki = wiki
        self._com: Wiki = None

    def _simple_update(self, subpage: str, text: Union[Iterable, str], should_escape: bool = True) -> bool:
        log.info("Generating report for '%s'", subpage)
        return self.wiki.edit(_DBR + subpage, text if isinstance(text, str) else _listify(text, should_escape), _UPDATING_REPORT)

    def _dump_file_report(self, subpage: str, report_num: int) -> bool:
        return self._simple_update(subpage, fetch_report(report_num))

    def _read_ignore(self, subpage: str, *ns: Union[NS, str]) -> list[str]:
        return self.wiki.links_on_page(f"{_DBR}{subpage}/Ignore", *ns)

    def _resolve_entity(self, e: Union[int, str, tuple, list]) -> Iterable[str]:

        if isinstance(e, list):
            return e

        if isinstance(e, tuple):
            name = e[0]
            nsl = e[1:]
        else:
            name = e
            nsl = (NS.FILE,)

        if isinstance(name, int):
            return fetch_report(name, self.wiki.ns_manager.canonical_prefix(nsl[0]))
        elif name.startswith("Category:"):
            return CQuery.category_members(self.wiki, name, *nsl)
        elif name.startswith("Template:"):
            return CQuery.what_transcludes_here(self.wiki, name, *nsl)

        raise ValueError(f"invalid parameter, what is this: {e}")

    def _difference_of(self, *l: Union[int, str, tuple, list]) -> set:

        if not isinstance(target := self._resolve_entity(l[0]), set):
            target = set(target)

        for e in l[1:]:
            target = target.difference(self._resolve_entity(e))

        return target

    @property
    def com(self):
        if not self._com:
            self._com = Wiki("commons.wikimedia.org", cookie_jar=None)

        return self._com

    def duplicate_on_commons(self):
        """Reports files with a duplicate on Commons.  Report 10"""
        subpage = "Local files with a duplicate on Commons"
        self._simple_update(subpage, self._difference_of(1, "Template:Deletable file", CQuery.what_transcludes_here(self.com, "Template:Deletion template tag", NS.FILE), *self._read_ignore(subpage)))

    def impossible_daily_deletion(self):
        """Reports files tagged for daily deletion which are categorized in a non-existent tracking category.  Report 13"""
        p = re.compile(r".+?" + _DMY_REGEX)
        self._simple_update("Files for daily deletion with an impossible date",
                            set(chain.from_iterable(self._difference_of(all_cat, *[c for c in self.wiki.category_members(cat, NS.CATEGORY) if p.match(c)])
                                                    for cat, all_cat in json.loads(self.wiki.page_text("User:FastilyBot/Daily Deletion Categories")).items())))

    def low_resolution_free_files(self):
        """Reports low resolution free files.  Report 11"""
        self._simple_update("Orphaned low-resolution free files", self._difference_of(10, "Category:Wikipedia images available as SVG", "Category:All files proposed for deletion"))

    def missing_file_copyright_tags(self):
        """Reports files misisng a copyright tag.  Report 9"""
        subpage = "Files without a license tag"
        lcl = set(self.wiki.links_on_page("User:FastilyBot/License categories"))
        self._simple_update(subpage, [k for k, v in MQuery.categories_on_page(self.wiki, list(self._difference_of(8, 5, 6, "Template:Deletable file", *self._read_ignore(subpage)))).items() if v and lcl.isdisjoint(v)])

    def non_free_pdfs(self):
        """Reports non-free PDFs.  Report 15"""
        self._dump_file_report("Non-free PDFs", 15)

    def orphaned_pdfs(self):
        """Reports orphaned, freely licensed PDFs.  Report 17"""
        self._simple_update("Orphaned PDFs", [s for s in fetch_report(9) if s.lower().endswith(".pdf")])

    def orphaned_file_talk(self):
        """Reports orphaned file talk pages.  Report 16"""
        self._simple_update("Orphaned file talk pages", self._difference_of((16, NS.FILE_TALK), ("Category:Wikipedia orphaned talk pages that should not be speedily deleted", NS.FILE_TALK)), False)

    def oversized_fair_use_files(self):
        """Reports on oversized fair use bitmap files that should be reduced.  Report 8"""
        subpage = "Large fair-use images"
        self._simple_update(subpage, self._difference_of(7, "Template:Deletable file", *self._read_ignore(subpage)))

    def possibly_unsourced_files(self):
        """Reports free files without a machine-readable source.  Report 12"""
        self._dump_file_report("Free files without a machine-readable source", 12)

    def shadows_commons_non_free(self):
        """Reports non-free files that shadow Commons files.  Report 14"""
        self._simple_update("Non-free files shadowing a Commons file", fetch_report(13) & fetch_report(5))
