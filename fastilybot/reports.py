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

from .utils import CQuery, fetch_report

log = logging.getLogger(__name__)


_UPDATED_AT = "This report updated at <onlyinclude>~~~~~</onlyinclude>\n"

_UPDATING_REPORT = "BOT: Updating report"

_DBR = "Wikipedia:Database reports/"

_DMY_REGEX = r"\d{1,2}? (January|February|March|April|May|June|July|August|September|October|November|December) \d{4}?"


def _listify(l: Iterable, should_escape: bool = True, header: str = _UPDATED_AT) -> str:
    """Convenience method which converts and formats an Iterable into wikitext ready to be posted as a finished database report.

    Args:
        l (Iterable): The Iterable to convert into wikitext
        should_escape (bool, optional): Set `False` to disable escaping of wikilinks. Defaults to True.
        header (str, optional): The header to put at the top of the generated wikitext. Defaults to _UPDATED_AT.

    Returns:
        str: The report wikitext derived from `l`.
    """
    c = ":" if should_escape else ""
    return header + "\n".join((f"*[[{c}{s}]]" for s in l))


class Reports:
    """Fastily's Wikipedia database reports"""

    def __init__(self, wiki: Wiki):
        """Initializer, creates a Reports object.

        Args:
            wiki (Wiki): The Wiki object to use
        """
        self.wiki: Wiki = wiki
        self._com: Wiki = None

    def _simple_update(self, subpage: str, text: Union[Iterable, str], should_escape: bool = True) -> bool:
        """Convenience method which updates to the specified database report.

        Args:
            subpage (str): The target subpage (without the `Wikipedia:Database reports/` prefix)
            text (Union[Iterable, str]): The text to post (`str`) or an `Iterable` (will be passed to `self._listify()`)
            should_escape (bool, optional): Set `False` to disable escaping of wikilinks.  Does nothing if `text is a `str`. Defaults to True.

        Returns:
            bool: `True` if the update operation succeeded.
        """
        log.info("Generating report for '%s'", subpage)
        return self.wiki.edit(_DBR + subpage, text if isinstance(text, str) else _listify(text, should_escape), _UPDATING_REPORT)

    def _dump_file_report(self, subpage: str, report_num: int) -> bool:
        """Convenience method which updates a file-based database report using a `fastilybot-toolforge` report.  Equivalent to `self._simple_update(subpage, fetch_report(report_num))`.

        Args:
            subpage (str): The target subpage (without the `Wikipedia:Database reports/` prefix) 
            report_num (int): The `fastilybot-toolforge` report number to use

        Returns:
            bool: `True` if the update operation succeeded.
        """
        return self._simple_update(subpage, fetch_report(report_num))

    def _read_ignore(self, subpage: str, *ns: Union[NS, str]) -> list[str]:
        """Get the contents of database report's ignore page.  This lists the wikilinks on `subpage`.

        Args:
            subpage (str): The target subpage (without the `Wikipedia:Database reports/` prefix) 
            ns (Union[NS, str]): Only return results in these namespaces.  Optional, leave empty to disable.

        Returns:
            list[str]: The contents of the ignore page of `subpage`.
        """
        return self.wiki.links_on_page(f"{_DBR}{subpage}/Ignore", *ns)

    def _resolve_entity(self, e: Union[int, str, tuple, list, set]) -> Iterable[str]:
        """Takes an object and interprets as follows:
            * `int` - fetch the corresponding fastilybot-toolforge report
            * `str` - if this a category title, get category members, if this is a template title, then get the template's transclusions.
            * `list`/`set` - return the input
            * `tuple` - the first element must be an `int`/`str` and will be interpreted as above.
                * If the first element was a `str`, the remaning elements will be treated as a namespace filter
                * If the first element was an `int`, then the second element will be used as the prefix for all the returned elements.

        Args:
            e (Union[int, str, tuple, list, set]): The object to interpret

        Raises:
            ValueError: If the input could not be matched to any of the above conditions.

        Returns:
            Iterable[str]: The interpreted value of `e` as described above.
        """
        if isinstance(e, (list, set)):
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
        """Subtract database reports and lists of titles from one another.  See `_resolve_entity()` for acceptable inputs.

        Args:
            l (Union[int, str, tuple, list, set]): The object to interpret

        Returns:
            set: The result of the subtraction operation.
        """
        if not isinstance(target := self._resolve_entity(l[0]), set):
            target = set(target)

        for e in l[1:]:
            target = target.difference(self._resolve_entity(e))

        return target

    @property
    def com(self) -> Wiki:
        """An anonymous Wiki object that points to the Wikimedia Commons.  This property is cached and lazy loaded.

        Returns:
            Wiki: An anonymous Wiki object that points to the Wikimedia Commons. 
        """
        if not self._com:
            self._com = Wiki("commons.wikimedia.org", cookie_jar=None)

        return self._com

    def all_free_license_tags(self):
        """Reports free license tags found on enwp and whether those tags exist on Commons.  Report 3"""
        subpage = "All free license tags"
        self._simple_update(subpage, l := self._difference_of({t for cat in self.wiki.links_on_page(f"{_DBR}{subpage}/Sources") for t in self.wiki.category_members(cat, NS.TEMPLATE) if not t.endswith("/sandbox")}, self._read_ignore(subpage)), False)
        self._simple_update("Free license tags which do not exist on Commons", [k for k, v in MQuery.exists(self.com, list(l)).items() if not v], False)

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

    def malformed_spi_reports(self):
        """Reports malformed SPI reports.  Report 5"""
        subpage = "Malformed SPI Cases"
        self._simple_update(subpage, _listify(self._difference_of((17, NS.PROJECT), ("Template:SPI case status", NS.PROJECT), ("Template:SPI archive notice", NS.PROJECT), self._read_ignore(subpage)), False, "{{/Header}}\n" + _UPDATED_AT))

    def missing_file_copyright_tags(self):
        """Reports files misisng a copyright tag.  Report 9"""
        subpage = "Files without a license tag"
        lcl = set(self.wiki.links_on_page("User:FastilyBot/License categories"))
        self._simple_update(subpage, [k for k, v in MQuery.categories_on_page(self.wiki, list(self._difference_of(8, 5, 6, "Template:Deletable file", *self._read_ignore(subpage)))).items() if v and lcl.isdisjoint(v)])

    def mtc_redirects(self):
        """Updates the MTC! redirect page.  Report 4"""
        base = "Wikipedia:MTC!/Redirects"
        d = MQuery.what_links_here(self.wiki, list(set(self.wiki.links_on_page("Wikipedia:Database reports/All free license tags") + self.wiki.links_on_page(base + "/IncludeAlso")
                                                       ).difference(self.wiki.links_on_page("Wikipedia:Database reports/Free license tags which do not exist on Commons"))), True)
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
        self._simple_update("Files tagged for FfD missing an FfD nomination", [k for k, v in MQuery.what_links_here(self.wiki, CQuery.what_transcludes_here(self.wiki, "Template:Ffd", NS.FILE)).items() if "Wikipedia:Files for discussion" not in v])

    def orphaned_file_talk(self):
        """Reports orphaned file talk pages.  Report 16"""
        self._simple_update("Orphaned file talk pages", self._difference_of((16, NS.FILE_TALK), ("Category:Wikipedia orphaned talk pages that should not be speedily deleted", NS.FILE_TALK)), False)

    def orphaned_keep_local(self):
        """Reports orphaned freely licensed files tagged keep local.  Report 6"""
        self._simple_update("Orphaned free files tagged keep local", fetch_report(9) & set(CQuery.what_transcludes_here(self.wiki, "Template:Keep local", NS.FILE)))

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

    def shadows_commons_page(self):
        """Reports local files that shadow a commons file or redirect.  Report 1"""
        subpage = "File description pages shadowing a Commons file or redirect"
        self._simple_update(subpage, "\n".join(f"* {{{{No redirect|{s}}}}}" for s in self._difference_of(11, *self._read_ignore(subpage))))

    def transcluded_non_existent_templates(self):
        """Reports non-existent templates that have transclusions.  Report 18"""
        self._simple_update("Transclusions of non-existent templates", ["Special:WhatLinksHere/" + s for s in fetch_report(14, "Template:")], False)
