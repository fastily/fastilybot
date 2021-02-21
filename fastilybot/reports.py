import json
import logging
import re

from collections.abc import Iterable
from itertools import chain
from typing import Union

from pwiki.mquery import MQuery
from pwiki.ns import NS
from pwiki.wiki import Wiki

from .utils import fetch_report

log = logging.getLogger(__name__)


_UPDATED_AT = "This report updated at <onlyinclude>~~~~~</onlyinclude>\n"

_UPDATING_REPORT = "BOT: Updating report"

_DBR = "Wikipedia:Database reports/"


_DMY_REGEX = r"\d{1,2}? (January|February|March|April|May|June|July|August|September|October|November|December) \d{4}?"


def _listify(l: Iterable, should_escape: bool = True, header: str = _UPDATED_AT) -> str:
    c = ":" if should_escape else ""
    return header + "\n".join((f"*[[{c}{s}]]" for s in l))


class Reports:

    def __init__(self, wiki: Wiki):
        self.wiki: Wiki = wiki
        self._com: Wiki = None

    def _simple_update(self, subpage: str, text: Union[Iterable, str], should_escape: bool = True) -> bool:
        log.info("Generating report for '%s'", subpage)
        return self.wiki.edit(_DBR + subpage, text if isinstance(text, str) else _listify(text, should_escape), _UPDATING_REPORT)

    def _dump_file_report(self, subpage: str, report_num: int) -> bool:
        return self._simple_update(subpage, fetch_report(report_num))

    def _subtract_cats(self, target: Iterable[str], cats: Iterable[str], nsl: list[Union[NS, str]] = [NS.FILE]) -> set:
        return (target if isinstance(target, set) else set(target)).difference(*(self.wiki.category_members(c, nsl) for c in cats))

    def _read_ignore(self, subpage: str, *ns: Union[NS, str]) -> list[str]:
        return self.wiki.links_on_page(f"{_DBR}{subpage}/Ignore", *ns)

    @property
    def com(self):
        if not self._com:
            self._com = Wiki("commons.wikimedia.org", cookie_jar=None)

        return self._com

    def duplicate_on_commons(self):
        """Reports files with a duplicate on Commons.  Report 10"""
        subpage = "Local files with a duplicate on Commons"
        self._simple_update(subpage, self._subtract_cats(fetch_report(1).difference(self.wiki.what_transcludes_here("Template:Deletable file", NS.FILE),
                                                                                    self.com.what_transcludes_here("Template:Deletion template tag", NS.FILE)), self._read_ignore(subpage)))

    def impossible_daily_deletion(self):
        """Reports files tagged for daily deletion which are categorized in a non-existent tracking category.  Report 13"""
        p = re.compile(r".+?" + _DMY_REGEX)
        self._simple_update("Files for daily deletion with an impossible date",
                            set(chain.from_iterable(self._subtract_cats(self.wiki.category_members(all_cat, NS.FILE), [c for c in self.wiki.category_members(cat, NS.CATEGORY) if p.match(c)])
                                                    for cat, all_cat in json.loads(self.wiki.page_text("User:FastilyBot/Daily Deletion Categories")).items())))

    def low_resolution_free_files(self):
        """Reports low resolution free files.  Report 11"""
        self._simple_update("Orphaned low-resolution free files", self._subtract_cats(fetch_report(10), ["Category:Wikipedia images available as SVG", "Category:All files proposed for deletion"]))

    def missing_file_copyright_tags(self):
        """Reports files misisng a copyright tag.  Report 9"""
        subpage = "Files without a license tag"
        if l := self._subtract_cats(fetch_report(8).difference(fetch_report(5), fetch_report(6), self.wiki.what_transcludes_here("Template:Deletable file", NS.FILE)), self._read_ignore(subpage)):
            lcl = set(self.wiki.links_on_page("User:FastilyBot/License categories"))
            self._simple_update(subpage, [k for k, v in MQuery.categories_on_page(self.wiki, list(l)).items() if v and lcl.isdisjoint(v)])

    def non_free_pdfs(self):
        """Reports non-free PDFs.  Report 15"""
        self._dump_file_report("Non-free PDFs", 15)

    def orphaned_pdfs(self):
        """Reports orphaned, freely licensed PDFs.  Report 17"""
        self._simple_update("Orphaned PDFs", [s for s in fetch_report(9) if s.lower().endswith(".pdf")])

    def orphaned_file_talk(self):
        """Reports orphaned file talk pages.  Report 16"""
        self._simple_update("Orphaned file talk pages", fetch_report(16, "File talk:").difference(self.wiki.category_members("Category:Wikipedia orphaned talk pages that should not be speedily deleted", NS.FILE_TALK)), False)

    def oversized_fair_use_files(self):
        """Reports on oversized fair use bitmap files that should be reduced.  Report 8"""
        subpage = "Large fair-use images"
        self._simple_update(subpage, self._subtract_cats(fetch_report(7).difference(self.wiki.what_transcludes_here("Template:Deletable file")), self._read_ignore(subpage)))

    def possibly_unsourced_files(self):
        """Reports free files without a machine-readable source.  Report 12"""
        self._dump_file_report("Free files without a machine-readable source", 12)

    def shadows_commons_non_free(self):
        """Reports non-free files that shadow Commons files.  Report 14"""
        self._simple_update("Non-free files shadowing a Commons file", fetch_report(13) & fetch_report(5))
