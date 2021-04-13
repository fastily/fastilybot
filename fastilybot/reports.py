"""Reports run by FastilyBot on the English Wikipedia"""

import json
import logging
import re

from collections.abc import Iterable
from itertools import chain
from typing import Union

from pwiki.mquery import MQuery
from pwiki.ns import NS
from pwiki.wiki import Wiki

from .constants import T
from .core import CQuery, FastilyBotBase, XQuery, fetch_report, listify

log = logging.getLogger(__name__)


_UPDATED_AT = "This report updated at <onlyinclude>~~~~~</onlyinclude>\n"

_UPDATING_REPORT = "BOT: Updating report"

_DBR = "Wikipedia:Database reports/"

_DMY_REGEX = r"\d{1,2}? (January|February|March|April|May|June|July|August|September|October|November|December) \d{4}?"


class Reports(FastilyBotBase):
    """Fastily's Wikipedia database reports"""

    def __init__(self, wiki: Wiki) -> None:
        """Initializer, creates a Reports object.

        Args:
            wiki (Wiki): The Wiki object to use
        """
        super().__init__(wiki, _DBR)

    ##################################################################################################
    ######################################## H E L P E R S ###########################################
    ##################################################################################################

    def _simple_update(self, subpage: str, text: Union[Iterable, str], should_escape: bool = True) -> bool:
        """Convenience method which updates to the specified database report.

        Args:
            subpage (str): The target subpage (without the `Wikipedia:Database reports/` prefix)
            text (Union[Iterable, str]): The text to post (`str`) or an `Iterable` (will be passed to `listify()`)
            should_escape (bool, optional): Set `False` to disable escaping of wikilinks.  Does nothing if `text is a `str`. Defaults to True.

        Returns:
            bool: `True` if the update operation succeeded.
        """
        log.info("Generating report for '%s'", subpage)
        return self.wiki.edit(_DBR + subpage, text if isinstance(text, str) else listify(text, should_escape, _UPDATED_AT), _UPDATING_REPORT)

    def _dump_file_report(self, subpage: str, report_num: int) -> bool:
        """Convenience method which updates a file-based database report using a `fastilybot-toolforge` report.  Equivalent to `self._simple_update(subpage, fetch_report(report_num))`.

        Args:
            subpage (str): The target subpage (without the `Wikipedia:Database reports/` prefix) 
            report_num (int): The `fastilybot-toolforge` report number to use

        Returns:
            bool: `True` if the update operation succeeded.
        """
        return self._simple_update(subpage, fetch_report(report_num))

    def _contents_of_ignore(self, subpage: str) -> list[str]:
        """Convenience method, fetch the links on an ignore page.  Equivalent to `self.wiki.links_on_page(self._ignore_of(subpage))`

        Args:
            subpage (str): The target subpage (without the `Wikipedia:Database reports/` prefix) 

        Returns:
            list[str]: The contents of the ignore page of `subpage`.
        """
        return self.wiki.links_on_page(self._ignore_of(subpage))

    ##################################################################################################
    ######################################## R E P O R T S ###########################################
    ##################################################################################################

    def all_free_license_tags(self):
        """Reports free license tags found on enwp and whether those tags exist on Commons.  Report 3"""
        subpage = "All free license tags"
        self._simple_update(subpage, l := self._difference_of({t for cat in self.wiki.links_on_page(self._config_of(subpage, "Sources"))
                            for t in self.wiki.category_members(cat, NS.TEMPLATE) if not t.endswith("/sandbox")}, self._contents_of_ignore(subpage)), False)
        self._simple_update("Free license tags which do not exist on Commons", XQuery.exists_filter(self.com, l, False), False)

    def duplicate_on_commons(self):
        """Reports files with a duplicate on Commons.  Report 10"""
        subpage = "Local files with a duplicate on Commons"
        self._simple_update(subpage, self._difference_of(1, T.DF, CQuery.what_transcludes_here(self.com, T.DTT, NS.FILE), self._ignore_of(subpage)))

    def impossible_daily_deletion(self):
        """Reports files tagged for daily deletion which are categorized in a non-existent tracking category.  Report 13"""
        p = re.compile(r".+?" + _DMY_REGEX)
        self._simple_update("Files for daily deletion with an impossible date",
                            set(chain.from_iterable(self._difference_of(all_cat, *[c for c in self.wiki.category_members(cat, NS.CATEGORY) if p.match(c)])
                                                    for cat, all_cat in json.loads(self.wiki.page_text("User:FastilyBot/Daily Deletion Categories")).items())))

    def low_resolution_free_files(self):
        """Reports low resolution free files.  Report 11"""
        self._simple_update("Orphaned low-resolution free files", self._difference_of(10, "Category:Wikipedia images available as SVG", "Category:All files proposed for deletion"))

    def malformed_spi_reports(self):
        """Reports malformed SPI reports.  Report 5"""
        subpage = "Malformed SPI Cases"
        self._simple_update(subpage, listify(self._difference_of((17, NS.PROJECT), ("Template:SPI case status", NS.PROJECT), ("Template:SPI archive notice", NS.PROJECT), self._contents_of_ignore(subpage)), False, "{{/Header}}\n" + _UPDATED_AT))

    def missing_file_copyright_tags(self):
        """Reports files misisng a copyright tag.  Report 9"""
        subpage = "Files without a license tag"
        lcl = set(self.wiki.links_on_page("User:FastilyBot/License categories"))
        self._simple_update(subpage, [k for k, v in MQuery.categories_on_page(self.wiki, list(self._difference_of(8, 5, 6, T.DF, self._ignore_of(subpage)))).items() if v and lcl.isdisjoint(v)])

    def mtc_redirects(self):
        """Updates the MTC! redirect page.  Report 4"""
        base = "Wikipedia:MTC!/Redirects"
        d = MQuery.what_links_here(self.wiki, list(set(self.wiki.links_on_page(_DBR + "All free license tags") + self.wiki.links_on_page(base + "/IncludeAlso")
                                                       ).difference(self.wiki.links_on_page(_DBR + "Free license tags which do not exist on Commons"))), True)
        body = "\n".join(["|".join([self.wiki.nss(t) for t in ([k] + v)]) for k, v in d.items()])

        self.wiki.edit(base, f"<pre>\n{body}\n</pre>", _UPDATING_REPORT)

    def non_free_pdfs(self):
        """Reports non-free PDFs.  Report 15"""
        self._dump_file_report("Non-free PDFs", 15)

    def orphaned_pdfs(self):
        """Reports orphaned, freely licensed PDFs.  Report 17"""
        self._simple_update("Orphaned PDFs", [s for s in fetch_report(9) if s.lower().endswith(".pdf")])

    def orphaned_files_for_discussion(self):
        """Reports files transcluding the FfD template without an associated disucssion.  Report 2"""
        self._simple_update("Files tagged for FfD missing an FfD nomination", [k for k, v in MQuery.what_links_here(self.wiki, CQuery.what_transcludes_here(self.wiki, T.F, NS.FILE)).items() if "Wikipedia:Files for discussion" not in v])

    def orphaned_file_talk(self):
        """Reports orphaned file talk pages.  Report 16"""
        self._simple_update("Orphaned file talk pages", self._difference_of((16, NS.FILE_TALK), ("Category:Wikipedia orphaned talk pages that should not be speedily deleted", NS.FILE_TALK)), False)

    def orphaned_keep_local(self):
        """Reports orphaned freely licensed files tagged keep local.  Report 6"""
        self._simple_update("Orphaned free files tagged keep local", fetch_report(9).intersection(CQuery.what_transcludes_here(self.wiki, T.KL, NS.FILE)))

    def oversized_fair_use_files(self):
        """Reports on oversized fair use bitmap files that should be reduced.  Report 8"""
        subpage = "Large fair-use images"
        self._simple_update(subpage, self._difference_of(7, T.DF, self._ignore_of(subpage)))

    def possibly_unsourced_files(self):
        """Reports free files without a machine-readable source.  Report 12"""
        self._dump_file_report("Free files without a machine-readable source", 12)

    def shadows_commons_non_free(self):
        """Reports non-free files that shadow Commons files.  Report 14"""
        self._simple_update("Non-free files shadowing a Commons file", fetch_report(13) & fetch_report(5))

    def shadows_commons_page(self):
        """Reports local files that shadow a commons file or redirect.  Report 1"""
        subpage = "File description pages shadowing a Commons file or redirect"
        self._simple_update(subpage, _UPDATED_AT + "\n".join(f"* {{{{No redirect|{s}}}}}" for s in self._difference_of(11, self._ignore_of(subpage))))

    def transcluded_non_existent_templates(self):
        """Reports non-existent templates that have transclusions.  Report 18"""
        self._simple_update("Transclusions of non-existent templates", sorted(["Special:WhatLinksHere/" + s for s in fetch_report(14, "Template:")]), False)
