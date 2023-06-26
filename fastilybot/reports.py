"""Reports run by FastilyBot on the English Wikipedia"""

import json
import logging
import re

from collections.abc import Iterable
from contextlib import suppress
from itertools import chain
from typing import Union

from pwiki.mquery import MQuery
from pwiki.ns import NS
from pwiki.wiki import Wiki

from .constants import T
from .core import CQuery, FastilyBotBase, XQuery, fetch_report, listify

log = logging.getLogger(__name__)


_UPDATED_AT = "This report updated at <onlyinclude>~~~~~</onlyinclude> {{Bots|deny=luckyrename}}\n"

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

    def _contents_of_ignore(self, subpage: str) -> list[str]:
        """Convenience method, fetch the links on an ignore page.  Equivalent to `self.wiki.links_on_page(self._ignore_of(subpage))`

        Args:
            subpage (str): The target subpage (without the `Wikipedia:Database reports/` prefix) 

        Returns:
            list[str]: The contents of the ignore page of `subpage`.
        """
        return self.wiki.links_on_page(self._ignore_of(subpage))

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

    def _dump_with_template(self, subpage: str, template_title: str, titles: Iterable[str]) -> bool:
        """Convenience method, dumps a list of titles to the specified subpage, wrapping each title in a the specified template (`template_title`).

        Args:
            subpage (str): The target subpage (without the `Wikipedia:Database reports/` prefix)
            template_title (str): The name of the wiki Template to use to wrap each title with.
            titles (Iterable[str]): The titles to include in the report.

        Returns:
            bool: `True` if the update operation succeeded.
        """
        return self._simple_update(subpage, _UPDATED_AT + "\n".join(f"* {{{{{template_title}|{s}}}}}" for s in titles))

    def _dump_no_redirect(self, subpage: str, titles: Iterable[str]) -> bool:
        """Convenience method, dumps a list of titles to the specified subpage, wrapping each title in a `No redirect` template.

        Args:
            subpage (str): The target subpage (without the `Wikipedia:Database reports/` prefix) 
            titles (Iterable[str]): The titles to include in the report.

        Returns:
            bool: `True` if the update operation succeeded.
        """
        return self._dump_with_template(subpage, "No redirect", titles)

    def _dump_file_report(self, subpage: str, report_num: int) -> bool:
        """Convenience method which updates a `File`-based report page on enwp using a `fastilybot-toolforge` report.

        Args:
            subpage (str): The target subpage (without the `Wikipedia:Database reports/` prefix) 
            report_num (int): The `fastilybot-toolforge` report number to use

        Returns:
            bool: `True` if the update operation succeeded.
        """
        return self._simple_update(subpage, fetch_report(report_num))

    ##################################################################################################
    ######################################## R E P O R T S ###########################################
    ##################################################################################################

    def all_free_license_tags(self) -> None:
        """Reports free license tags found on enwp and whether those tags exist on Commons.  Report 3"""
        subpage = "All free license tags"
        self._simple_update(subpage, l := self._difference_of({t for cat in self.wiki.links_on_page(self._config_of(subpage, "Sources"))
                            for t in self.wiki.category_members(cat, NS.TEMPLATE) if not t.endswith("/sandbox")}, self._contents_of_ignore(subpage)), False)
        self._simple_update("Free license tags which do not exist on Commons", XQuery.exists_filter(self.com, l, False), False)

    def ap_files(self) -> None:
        """Reports files credited to the Associated Press.  Report 24"""
        self._dump_file_report("Files credited to The Associated Press", 24)

    def duplicate_on_commons(self) -> None:
        """Reports files with a duplicate on Commons.  Report 10"""
        self._simple_update(subpage := "Local files with a duplicate on Commons", self._difference_of(1, T.DF, CQuery.what_transcludes_here(self.com, T.DTT, NS.FILE), self._ignore_of(subpage)))

    def flickr_files(self) -> None:
        """Reports free files with links to Flickr.  Report 19"""
        self._simple_update("Free files which link to Flickr", self._difference_of(18, T.KL))

    def fully_protected_user_talk(self) -> None:
        """Fully protected user talk pages.  Report 26"""
        self._simple_update("Fully protected user talk pages", fetch_report(26, "User talk:"), False)

    def getty_files(self) -> None:
        """Reports files credited to Getty Images.  Report 23"""
        ignore_list = set(self._contents_of_ignore(subpage := "Files credited to Getty Images"))
        self._simple_update(subpage, [k for k, v in MQuery.templates_on_page(self.wiki, list(fetch_report(23))).items() if ignore_list.isdisjoint(v)])

    def impossible_daily_deletion(self) -> None:
        """Reports files tagged for daily deletion which are categorized in a non-existent tracking category.  Report 13"""
        subpage = "Files for daily deletion with an impossible date"
        p = re.compile(r".+?" + _DMY_REGEX)
        self._simple_update(subpage, set(chain.from_iterable(self._difference_of(all_cat, *[c for c in self.wiki.category_members(cat, NS.CATEGORY) if p.match(c)]) for cat, all_cat in json.loads(self.wiki.page_text(self._config_of(subpage, "Sources"))).items())))

    def large_ip_talk_pages(self) -> None:
        """Reports unusually large IP talk pages.  Report 20"""
        self._simple_update("Unusually large IP talk pages", fetch_report(20, "User talk:"), False)

    def large_user_talk_pages(self) -> None:
        """Reports unusually large user talk pages.  Report 21"""
        self._simple_update("Unusually large user talk pages", fetch_report(21, "User talk:"), False)

    def low_resolution_free_files(self) -> None:
        """Reports low resolution free files.  Report 11"""
        self._simple_update("Orphaned low-resolution free files", self._difference_of(10, "Category:Wikipedia images available as SVG", "Category:All files proposed for deletion"))

    def malformed_spi_reports(self) -> None:
        """Reports malformed SPI reports.  Report 5"""
        subpage = "Malformed SPI Cases"

        # fend off false positives
        for title, text in MQuery.page_text(self.wiki, list(l := XQuery.exists_filter(self.wiki, self._difference_of((17, NS.PROJECT), ("Template:SPI case status", NS.PROJECT), ("Template:SPI archive notice", NS.PROJECT), self._contents_of_ignore(subpage))))).items():
            with suppress(ValueError):
                self.wiki.edit(title, text, "null edit")

        self._simple_update(subpage, listify(l, False, "{{/Header}}\n" + _UPDATED_AT))

    def missing_file_copyright_tags(self) -> None:
        """Reports files misisng a copyright tag.  Report 9"""
        subpage = "Files without a license tag"
        lcl = set(self.wiki.links_on_page(self._config_of(subpage, "Allow")))
        self._simple_update(subpage, [k for k, v in MQuery.categories_on_page(self.wiki, list(self._difference_of(8, 5, 6, T.DF, self._ignore_of(subpage)))).items() if v and lcl.isdisjoint(v)])

    def multi_ext_filenames(self) -> None:
        """Reports files with multiple extensions in their filenames.  Report 22"""
        self._dump_file_report("Filenames with multiple extensions", 22)

    def non_free_pdfs(self) -> None:
        """Reports non-free PDFs.  Report 15"""
        self._dump_file_report("Non-free PDFs", 15)

    def orphaned_pdfs(self) -> None:
        """Reports orphaned, freely licensed PDFs.  Report 17"""
        self._simple_update("Orphaned PDFs", [s for s in fetch_report(9) if s.lower().endswith(".pdf")])

    def orphaned_files_for_discussion(self) -> None:
        """Reports files transcluding the FfD template without an associated disucssion.  Report 2"""
        self._simple_update("Files tagged for FfD missing an FfD nomination", [k for k, v in MQuery.what_links_here(self.wiki, CQuery.what_transcludes_here(self.wiki, T.F, NS.FILE)).items() if "Wikipedia:Files for discussion" not in v])

    def orphaned_file_talk(self) -> None:
        """Reports orphaned file talk pages.  Report 16"""
        self._simple_update("Orphaned file talk pages", self._difference_of((16, NS.FILE_TALK), ("Category:Wikipedia orphaned talk pages that should not be speedily deleted", NS.FILE_TALK)), False)

    def orphaned_keep_local(self) -> None:
        """Reports orphaned freely licensed files tagged keep local.  Report 6"""
        self._simple_update("Orphaned free files tagged keep local", fetch_report(9).intersection(CQuery.what_transcludes_here(self.wiki, T.KL, NS.FILE)))

    def orphaned_keep_local_with_commons_duplicate(self) -> None:
        """Reports orphaned freely licensed files that are tagged keep local and have a duplicate on Commons.  Report 27"""
        self._simple_update("Orphaned files copied to Commons tagged keep local", fetch_report(1).intersection(fetch_report(9), CQuery.what_transcludes_here(self.wiki, T.KL, NS.FILE)))

    def orphaned_timed_text(self) -> None:
        """Reports pages in the Timed Text namespace without a corresponding File page.  Report 4"""
        self._dump_no_redirect("Timed Text without a corresponding File", fetch_report(19, "TimedText:"))

    def oversized_fair_use_files(self) -> None:
        """Reports on oversized fair use bitmap files that should be reduced.  Report 8"""
        self._simple_update(subpage := "Large fair-use images", self._difference_of(7, T.DF, self._ignore_of(subpage)))

    def possibly_unsourced_files(self) -> None:
        """Reports free files without a machine-readable source.  Report 12"""
        self._dump_file_report("Free files without a machine-readable source", 12)

    def shadows_commons_non_free(self) -> None:
        """Reports non-free files that shadow Commons files.  Report 14"""
        self._dump_with_template("Non-free files shadowing a Commons file", "/Template", fetch_report(13) & fetch_report(5))

    def shadows_commons_page(self) -> None:
        """Reports local files that shadow a commons file or redirect.  Report 1"""
        self._dump_no_redirect(subpage := "File description pages shadowing a Commons file or redirect", self._difference_of(11, self._ignore_of(subpage)))

    def transcluded_non_existent_templates(self) -> None:
        """Reports non-existent templates that have transclusions.  Report 18"""
        self._simple_update("Transclusions of non-existent templates", sorted(["Special:WhatLinksHere/" + s for s in fetch_report(14, "Template:")]), False)

    def unfiled_rfas(self) -> None:
        """Reports unfiled RfAs.  Report 25"""
        self._simple_update(subpage := "Unfiled RfAs", self._difference_of((25, NS.PROJECT), *((s, NS.PROJECT) for s in self._contents_of_ignore(subpage))))
